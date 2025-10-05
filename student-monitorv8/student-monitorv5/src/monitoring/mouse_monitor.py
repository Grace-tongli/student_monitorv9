"""
鼠标行为监控与分析系统
功能：
1. 实时监控鼠标移动、点击和滚动行为
2. 每120秒分析一次鼠标使用情况
3. 计算移动熵、有效路径比、平均速度、加速度方差
4. 将分析结果保存到CSV文件
"""

import csv
import time
import os
import math
import numpy as np
import pandas as pd
import threading
from datetime import datetime, timedelta
from pynput import mouse
import logging

# 配置日志
os.makedirs("../../logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("../../logs/mouse_monitor.log"),
        logging.StreamHandler()
    ]
)

class MouseMonitor:
    def __init__(self, analysis_interval=120, output_file="../../data/mouse_performance.csv", stop_event=None):
        """
        初始化鼠标监控器
        :param analysis_interval: 分析间隔（秒）
        :param output_file: 输出文件路径
        :param stop_event: 停止事件
        """
        self.analysis_interval = analysis_interval
        self.output_file = output_file
        self.events = []  # 存储鼠标事件
        self.analysis_results = []  # 存储分析结果
        self.is_listening = False
        self.listener = None
        self.analysis_thread = None
        self.start_time = None
        self.last_analysis_time = None
        self.lock = threading.Lock()
        self.stop_event = stop_event or threading.Event()
        self.last_position = None
        self.last_move_time = None

        # 确保输出目录存在
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        # 初始化分析结果文件
        self.init_analysis_file()

    def init_analysis_file(self):
        """初始化分析结果文件"""
        if not os.path.exists(self.output_file):
            with open(self.output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'start_time', 'end_time', 'duration_sec',
                    'move_entropy', 'effective_path_ratio',
                    'avg_speed', 'acceleration_variance',
                    'total_distance', 'click_count', 'scroll_count'
                ])

    def on_move(self, x, y):
        """处理鼠标移动事件"""
        current_time = datetime.now()

        # 计算移动距离和速度
        distance = 0
        speed = 0
        if self.last_position and self.last_move_time:
            dx = x - self.last_position[0]
            dy = y - self.last_position[1]
            distance = math.sqrt(dx**2 + dy**2)
            time_diff = (current_time - self.last_move_time).total_seconds()
            if time_diff > 0:
                speed = distance / time_diff

        event = {
            'timestamp': current_time,
            'event_type': 'move',
            'x': x,
            'y': y,
            'distance': distance,
            'speed': speed
        }

        with self.lock:
            self.events.append(event)

        # 更新最后位置和时间
        self.last_position = (x, y)
        self.last_move_time = current_time

        return True

    def on_click(self, x, y, button, pressed):
        """处理鼠标点击事件"""
        event = {
            'timestamp': datetime.now(),
            'event_type': 'click',
            'x': x,
            'y': y,
            'button': str(button),
            'pressed': pressed
        }

        with self.lock:
            self.events.append(event)

        return True

    def on_scroll(self, x, y, dx, dy):
        """处理鼠标滚动事件"""
        event = {
            'timestamp': datetime.now(),
            'event_type': 'scroll',
            'x': x,
            'y': y,
            'dx': dx,
            'dy': dy
        }

        with self.lock:
            self.events.append(event)

        return True

    def start_listener(self):
        """启动鼠标监听器"""
        if not self.is_listening:
            logging.info("鼠标监听已启动...")
            self.is_listening = True
            self.start_time = datetime.now()
            self.last_analysis_time = self.start_time
            self.last_position = None
            self.last_move_time = None

            # 启动监听线程
            self.listener = mouse.Listener(
                on_move=self.on_move,
                on_click=self.on_click,
                on_scroll=self.on_scroll
            )
            self.listener.start()

            # 启动分析线程
            self.analysis_thread = threading.Thread(target=self.periodic_analysis)
            self.analysis_thread.daemon = True
            self.analysis_thread.start()

    def stop_listener(self):
        """停止鼠标监听器"""
        if self.is_listening:
            logging.info("停止鼠标监听...")
            self.is_listening = False

            if self.listener and self.listener.is_alive():
                self.listener.stop()

            # 执行最后一次分析
            self.analyze_period()

    def periodic_analysis(self):
        """定期执行分析"""
        while self.is_listening and not self.stop_event.is_set():
            current_time = datetime.now()
            elapsed = (current_time - self.last_analysis_time).total_seconds()

            if elapsed >= self.analysis_interval:
                self.analyze_period()
                self.last_analysis_time = current_time

            time.sleep(1)

    def calculate_move_entropy(self, move_events):
        """计算移动熵"""
        if len(move_events) < 2:
            return 0.0

        # 计算移动方向角度
        angles = []
        for i in range(1, len(move_events)):
            dx = move_events[i]['x'] - move_events[i-1]['x']
            dy = move_events[i]['y'] - move_events[i-1]['y']
            if dx == 0 and dy == 0:
                continue
            angle = math.atan2(dy, dx)
            angles.append(angle)

        if not angles:
            return 0.0

        # 将角度分为8个区间
        bins = np.linspace(-np.pi, np.pi, 9)
        hist, _ = np.histogram(angles, bins=bins)
        probs = hist / hist.sum()

        # 计算熵
        entropy = -np.sum([p * np.log2(p) for p in probs if p > 0])
        return entropy

    def calculate_effective_path_ratio(self, move_events):
        """计算有效路径比"""
        if len(move_events) < 2:
            return 0.0

        # 计算总移动距离
        total_distance = sum(event['distance'] for event in move_events[1:])

        # 计算起点到终点的直线距离
        start_x, start_y = move_events[0]['x'], move_events[0]['y']
        end_x, end_y = move_events[-1]['x'], move_events[-1]['y']
        direct_distance = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)

        # 避免除以零
        if total_distance == 0:
            return 0.0

        return direct_distance / total_distance

    def calculate_avg_speed(self, move_events):
        """计算平均速度"""
        if len(move_events) < 2:
            return 0.0

        # 计算总移动距离和时间
        total_distance = sum(event['distance'] for event in move_events[1:])
        time_diff = (move_events[-1]['timestamp'] - move_events[0]['timestamp']).total_seconds()

        if time_diff == 0:
            return 0.0

        return total_distance / time_diff  # 像素/秒

    def calculate_acceleration_variance(self, move_events):
        """计算加速度方差"""
        if len(move_events) < 3:
            return 0.0

        # 提取速度序列
        speeds = [event['speed'] for event in move_events[1:] if event['speed'] > 0]

        if len(speeds) < 2:
            return 0.0

        # 计算加速度
        accelerations = []
        for i in range(1, len(speeds)):
            time_diff = (move_events[i+1]['timestamp'] - move_events[i]['timestamp']).total_seconds()
            if time_diff > 0:
                acceleration = (speeds[i] - speeds[i-1]) / time_diff
                accelerations.append(acceleration)

        if not accelerations:
            return 0.0

        return np.var(accelerations)

    def analyze_period(self):
        """分析当前时间段的数据"""
        with self.lock:
            if not self.events or self.stop_event.is_set():
                logging.info("没有可分析的数据或系统已停止")
                return

            # 创建当前时间段的数据副本
            events_copy = self.events.copy()

            # 清空事件列表（保留最后几秒的事件以避免丢失）
            # 保留最后5秒的事件以确保连续性
            cutoff_time = datetime.now() - timedelta(seconds=5)
            self.events = [e for e in self.events if e['timestamp'] >= cutoff_time]

        # 计算时间段
        if not events_copy:
            logging.info("没有可分析的事件数据")
            return

        start_time = min(e['timestamp'] for e in events_copy)
        end_time = max(e['timestamp'] for e in events_copy)
        duration = (end_time - start_time).total_seconds()

        # 分离移动事件
        move_events = [e for e in events_copy if e['event_type'] == 'move']
        click_events = [e for e in events_copy if e['event_type'] == 'click' and e['pressed']]
        scroll_events = [e for e in events_copy if e['event_type'] == 'scroll']

        # 计算总移动距离
        total_distance = sum(event['distance'] for event in move_events[1:])

        # 计算指标
        move_entropy = self.calculate_move_entropy(move_events)
        effective_path_ratio = self.calculate_effective_path_ratio(move_events)
        avg_speed = self.calculate_avg_speed(move_events)
        acceleration_variance = self.calculate_acceleration_variance(move_events)

        # 保存分析结果
        result = {
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_sec': round(duration, 2),
            'move_entropy': round(move_entropy, 4),
            'effective_path_ratio': round(effective_path_ratio, 4),
            'avg_speed': round(avg_speed, 2),
            'acceleration_variance': round(acceleration_variance, 4),
            'total_distance': round(total_distance, 2),
            'click_count': len(click_events),
            'scroll_count': len(scroll_events)
        }

        # 保存到内存和文件
        self.analysis_results.append(result)
        self.save_analysis_result(result)

        logging.info(f"分析完成: {start_time} 到 {end_time}")
        logging.info(f"- 移动熵: {move_entropy:.4f}, 有效路径比: {effective_path_ratio:.4f}")
        logging.info(f"- 平均速度: {avg_speed:.2f} 像素/秒, 加速度方差: {acceleration_variance:.4f}")
        logging.info(f"- 总移动距离: {total_distance:.2f} 像素, 点击次数: {len(click_events)}, 滚动次数: {len(scroll_events)}")

    def save_analysis_result(self, result):
        """保存分析结果到CSV文件"""
        try:
            with open(self.output_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    result['start_time'],
                    result['end_time'],
                    result['duration_sec'],
                    result['move_entropy'],
                    result['effective_path_ratio'],
                    result['avg_speed'],
                    result['acceleration_variance'],
                    result['total_distance'],
                    result['click_count'],
                    result['scroll_count']
                ])
            logging.info(f"分析结果已保存到 {self.output_file}")
        except Exception as e:
            logging.error(f"保存分析结果失败: {str(e)}")

    def run(self):
        """启动监控系统"""
        logging.info("鼠标监控系统启动")
        logging.info(f"分析间隔: {self.analysis_interval}秒")
        logging.info(f"数据文件: {self.output_file}")
        self.start_listener()

        try:
            # 保持主线程运行
            while self.is_listening and not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("用户中断...")
            self.stop_listener()
        except Exception as e:
            logging.error(f"发生未预期错误: {str(e)}")
            self.stop_listener()

        logging.info("鼠标监控系统已停止")