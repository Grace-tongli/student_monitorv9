"""
编程情绪监控系统
功能：
1. 每120秒弹出极简情绪量表
2. 收集学生选择的情绪状态
3. 将选择结果保存到CSV文件（含时间戳）
"""

import csv
import time
import threading
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import logging
import queue

# 配置日志
os.makedirs("../../logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("../../logs/emotion_monitor.log"),
        logging.StreamHandler()
    ]
)

class EmotionMonitor:
    def __init__(self, interval=120, output_file="../../data/emotion_performance.csv", stop_event=None):
        """
        初始化情绪监控器
        :param interval: 弹出间隔（秒）
        :param output_file: 输出文件名
        :param stop_event: 停止事件
        """
        self.interval = interval
        self.output_file = output_file
        self.is_running = False
        self.thread = None
        self.root = None
        self.stop_event = stop_event or threading.Event()
        self.gui_queue = queue.Queue()
        self.gui_thread = None
        self.response_received = threading.Event()

        # 确保输出目录存在
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        # 确保输出文件存在
        self.init_output_file()

        logging.info(f"情绪监控器初始化完成，间隔: {interval}秒")

    def init_output_file(self):
        """初始化输出文件"""
        if not os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['timestamp', 'emotion', 'description'])
                logging.info(f"创建新的输出文件: {self.output_file}")
            except Exception as e:
                logging.error(f"创建输出文件失败: {str(e)}")

    def save_response(self, emotion, description):
        """保存情绪响应到CSV文件"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, emotion, description])
            logging.info(f"记录情绪: {emotion} - {description}")
        except Exception as e:
            logging.error(f"保存情绪响应失败: {str(e)}")

    def run_gui(self):
        """在单独的线程中运行GUI"""
        try:
            self.root = tk.Tk()
            self.root.title("编程情绪微量表")
            self.root.geometry("600x400")
            self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)

            # 隐藏窗口而不是立即显示
            self.root.withdraw()

            # 处理GUI队列中的命令
            self.process_gui_queue()

            # 运行Tkinter主循环
            self.root.mainloop()
        except Exception as e:
            logging.error(f"GUI线程错误: {str(e)}")
        finally:
            if self.root:
                try:
                    self.root.quit()
                    self.root.destroy()
                except:
                    pass
            self.root = None

    def process_gui_queue(self):
        """处理GUI命令队列"""
        try:
            while True:
                try:
                    # 非阻塞获取队列命令
                    command, args = self.gui_queue.get_nowait()
                    if command == 'show_dialog':
                        self._show_emotion_scale()
                    elif command == 'close_dialog':
                        self._close_dialog()
                    elif command == 'quit':
                        break
                except queue.Empty:
                    break
        except Exception as e:
            logging.error(f"处理GUI队列错误: {str(e)}")

        # 继续处理队列
        if self.root and not self.stop_event.is_set():
            self.root.after(100, self.process_gui_queue)

    def _show_emotion_scale(self):
        """显示情绪量表窗口（在GUI线程中执行）"""
        if not self.root or self.stop_event.is_set():
            return

        try:
            # 如果窗口已经存在，先销毁
            if hasattr(self, '_current_window') and self._current_window:
                try:
                    self._current_window.destroy()
                except:
                    pass

            # 创建新窗口
            self._current_window = tk.Toplevel(self.root)
            self._current_window.title("编程情绪微量表")
            self._current_window.geometry("600x400")

            # 增强窗口置顶和可见性
            self._current_window.attributes("-topmost", True)  # 始终置顶
            self._current_window.attributes("-alpha", 1.0)     # 确保不透明
            self._current_window.focus_force()                 # 强制获得焦点
            self._current_window.grab_set()                    # 模态窗口，阻止其他操作

            # 设置窗口位置为屏幕中央
            self._current_window.update_idletasks()
            width = self._current_window.winfo_width()
            height = self._current_window.winfo_height()
            x = (self._current_window.winfo_screenwidth() // 2) - (width // 2)
            y = (self._current_window.winfo_screenheight() // 2) - (height // 2)
            self._current_window.geometry(f"+{x}+{y}")

            self._current_window.resizable(False, False)
            self._current_window.protocol("WM_DELETE_WINDOW", lambda: self.on_dialog_close(None))

            # 创建主框架
            main_frame = ttk.Frame(self._current_window, padding=20)
            main_frame.pack(fill=tk.BOTH, expand=True)

            # 标题 - 使用更大的字体和更醒目的颜色
            title_label = ttk.Label(
                main_frame,
                text="编程情绪微量表",
                font=("Arial", 18, "bold"),
                foreground="#2c3e50"
            )
            title_label.pack(pady=(0, 15))

            question_label = ttk.Label(
                main_frame,
                text="问题：当前最符合你状态的描述是？",
                font=("Arial", 14),
                foreground="#34495e"
            )
            question_label.pack(pady=(0, 25))

            # 情绪选项
            emotions = [
                {"letter": "A", "name": "专注", "description": "流畅编码，完全投入"},
                {"letter": "B", "name": "无聊", "description": "简单重复，缺乏挑战"},
                {"letter": "C", "name": "沮丧", "description": "反复报错，难以解决"},
                {"letter": "D", "name": "困惑", "description": "思路卡壳，不知方向"}
            ]

            # 创建选项按钮
            self.selected_emotion = tk.StringVar(value=emotions[0]["name"])

            for emotion in emotions:
                frame = ttk.Frame(main_frame, padding=10)
                frame.pack(fill=tk.X, pady=8, padx=15)

                option_text = f"{emotion['letter']}. {emotion['name']}（{emotion['description']}）"

                rb = ttk.Radiobutton(
                    frame,
                    text=option_text,
                    variable=self.selected_emotion,
                    value=emotion['name'],
                    command=lambda e=emotion: self.on_emotion_selected(e),
                    style="TRadiobutton"
                )
                rb.pack(anchor=tk.W)

            # 关闭按钮
            close_btn = ttk.Button(
                main_frame,
                text="关闭窗口（不保存）",
                command=lambda: self.on_dialog_close(None),
                style="TButton"
            )
            close_btn.pack(pady=25)

            # 显示窗口并确保可见
            self._current_window.deiconify()
            self._current_window.lift()
            self._current_window.attributes('-topmost', True)
            self._current_window.after(100, lambda: self._current_window.attributes('-topmost', True))

        except Exception as e:
            logging.error(f"显示情绪量表错误: {str(e)}")

    def _close_dialog(self):
        """关闭对话框（在GUI线程中执行）"""
        if hasattr(self, '_current_window') and self._current_window:
            try:
                self._current_window.destroy()
            except:
                pass
            self._current_window = None

    def on_emotion_selected(self, emotion):
        """处理情绪选择"""
        # 保存响应
        option_text = f"{emotion['letter']}.{emotion['name']}（{emotion['description']}）"
        self.save_response(emotion['name'], option_text)

        # 关闭对话框
        self.gui_queue.put(('close_dialog', None))
        self.response_received.set()

        logging.info(f"情绪选择已保存: {emotion['name']}")

    def on_dialog_close(self, event):
        """处理对话框关闭"""
        self.gui_queue.put(('close_dialog', None))
        self.response_received.set()

    def on_window_close(self):
        """处理主窗口关闭"""
        self.stop_event.set()
        if self.root:
            self.root.quit()

    def show_emotion_scale(self):
        """显示情绪量表窗口（线程安全）"""
        if not self.is_running or self.stop_event.is_set():
            return False

        # 重置响应事件
        self.response_received.clear()

        # 发送显示命令到GUI队列
        self.gui_queue.put(('show_dialog', None))

        # 等待响应或超时
        response_wait = self.response_received.wait(timeout=30)  # 30秒超时

        if not response_wait:
            logging.warning("情绪量表响应超时")
            self.gui_queue.put(('close_dialog', None))

        return response_wait

    def periodic_prompt(self):
        """定期弹出情绪量表"""
        while self.is_running and not self.stop_event.is_set():
            try:
                logging.info("弹出情绪量表...")
                self.show_emotion_scale()

                # 等待下一个周期
                for _ in range(self.interval):
                    if not self.is_running or self.stop_event.is_set():
                        break
                    time.sleep(1)

            except Exception as e:
                logging.error(f"定期提示错误: {str(e)}")
                time.sleep(1)

    def start(self):
        """启动情绪监控器"""
        if not self.is_running:
            logging.info("启动情绪监控器")
            self.is_running = True

            # 启动GUI线程
            self.gui_thread = threading.Thread(target=self.run_gui)
            self.gui_thread.daemon = True
            self.gui_thread.start()

            # 等待GUI初始化
            time.sleep(1)

            # 启动提示线程
            self.thread = threading.Thread(target=self.periodic_prompt)
            self.thread.daemon = True
            self.thread.start()

    def stop(self):
        """停止情绪监控器"""
        if self.is_running:
            logging.info("停止情绪监控器")
            self.is_running = False

            # 发送退出命令到GUI线程
            try:
                self.gui_queue.put(('quit', None))
            except:
                pass

            # 关闭GUI
            if self.root:
                try:
                    self.root.after(100, self.root.quit)
                except:
                    pass

            # 等待线程结束
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2)
            if self.gui_thread and self.gui_thread.is_alive():
                self.gui_thread.join(timeout=2)

    def run(self):
        """运行情绪监控器"""
        self.start()
        try:
            # 保持主线程运行
            while self.is_running and not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            logging.error(f"发生错误: {str(e)}")
            self.stop()