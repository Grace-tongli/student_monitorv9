"""
Flask Web应用：提供监控系统的Web界面
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import threading
import time
import os
import csv
import json
from datetime import datetime
import sys
import logging
from logging.handlers import RotatingFileHandler

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 获取项目根目录的绝对路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__,
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR)
app.secret_key = 'your_secret_key_here_change_in_production'  # 请在生产环境中更改

# 配置日志
log_dir = os.path.join(BASE_DIR, 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(log_dir, 'app.log'),
            maxBytes=1024 * 1024,  # 1MB
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)

# 监控器实例
monitors = {
    'keyboard': None,
    'mouse': None,
    'emotion': None
}

stop_event = threading.Event()

# 用户数据文件路径
USERS_FILE = os.path.join(BASE_DIR, 'data', 'users.json')

# 加载用户数据函数
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载用户数据失败: {str(e)}")
            return {}
    return {}

# 保存用户数据函数
def save_users(users_data):
    try:
        # 确保数据目录存在
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)

        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"保存用户数据失败: {str(e)}")
        return False

# 初始化用户数据库
users = load_users()
# 如果没有用户，添加默认用户
if not users:
    users = {
        'admin': {'password': 'admin123', 'role': 'admin'},
        'student1': {'password': 'student123', 'role': 'student'},
        'student2': {'password': 'student123', 'role': 'student'}
    }
    save_users(users)


@app.route('/')
def index():
    if 'username' in session:
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    success = request.args.get('success')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # 重新加载用户数据，确保获取最新
        users = load_users()

        if username in users and users[username]['password'] == password:
            session['username'] = username
            session['role'] = users[username]['role']
            logging.info(f"用户 {username} 登录成功")
            return redirect(url_for('index'))
        else:
            logging.warning(f"登录失败: 用户名 {username}")
            return render_template('login.html', error='用户名或密码错误')

    return render_template('login.html', success=success)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form.get('role', 'student')  # 默认角色为学生

        # 验证输入
        if not username or not password:
            return render_template('register.html', error='用户名和密码不能为空')

        if password != confirm_password:
            return render_template('register.html', error='密码确认不匹配')

        # 重新加载用户数据，确保获取最新
        users = load_users()

        if username in users:
            return render_template('register.html', error='用户名已存在')

        # 添加新用户
        users[username] = {'password': password, 'role': role}
        if save_users(users):
            logging.info(f"新用户注册成功: {username}, 角色: {role}")
            return redirect(url_for('login', success='注册成功，请登录'))
        else:
            return render_template('register.html', error='注册失败，请稍后重试')

    return render_template('register.html')


@app.route('/logout')
def logout():
    username = session.get('username', '未知用户')
    session.pop('username', None)
    session.pop('role', None)
    logging.info(f"用户 {username} 退出登录")
    return redirect(url_for('login'))


@app.route('/admin')
def admin_dashboard():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    # 获取所有注册的学生用户
    users_data = load_users()
    students = []

    for username, user_info in users_data.items():
        if user_info.get('role') == 'student':
            # 检查学生是否有监控数据文件
            data_dir = os.path.join(BASE_DIR, 'data')
            mouse_file = os.path.join(data_dir, f"{username}_mouse_performance.csv")
            keyboard_file = os.path.join(data_dir, f"{username}_keyboard_performance.csv")

            # 获取最后活动时间
            last_active = "暂无活动"
            if os.path.exists(mouse_file):
                try:
                    with open(mouse_file, 'r', newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                        if rows:
                            last_active = rows[-1].get('end_time', '暂无活动')
                except:
                    pass
            elif os.path.exists(keyboard_file):
                try:
                    with open(keyboard_file, 'r', newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                        if rows:
                            last_active = rows[-1].get('end_time', '暂无活动')
                except:
                    pass

            # 检查监控状态（这里简化处理，实际应该检查监控器运行状态）
            monitoring = os.path.exists(mouse_file) or os.path.exists(keyboard_file)

            students.append({
                'name': username,
                'monitoring': monitoring,
                'last_active': last_active,
                'data_files': {
                    'mouse': os.path.exists(mouse_file),
                    'keyboard': os.path.exists(keyboard_file),
                    'emotion': os.path.exists(os.path.join(data_dir, f"{username}_emotion_performance.csv"))
                }
            })

    return render_template('admin_dashboard.html', name=session['username'], students=students)


@app.route('/student')
def student_dashboard():
    if 'username' not in session or session['role'] != 'student':
        return redirect(url_for('login'))

    # 获取监控状态
    status = {
        'mouse': monitors['mouse'] is not None and hasattr(monitors['mouse'], 'is_listening') and monitors[
            'mouse'].is_listening,
        'keyboard': monitors['keyboard'] is not None and hasattr(monitors['keyboard'], 'is_listening') and monitors[
            'keyboard'].is_listening,
        'emotion': monitors['emotion'] is not None and hasattr(monitors['emotion'], 'is_running') and monitors[
            'emotion'].is_running,
        'start_time': None
    }

    if status['mouse'] or status['keyboard'] or status['emotion']:
        status['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return render_template('student_dashboard.html', name=session['username'], status=status)


@app.route('/api/save_emotion_selected', methods=['POST'])
def save_emotion_selected():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    username = session['username']
    data = request.get_json()
    mood_type = data.get('mood_type', 'all')
    emotions = {
        "A": {"letter": "A", "name": "专注", "description": "流畅编码，完全投入"},
        "B": {"letter": "B", "name": "无聊", "description": "简单重复，缺乏挑战"},
        "C": {"letter": "C", "name": "沮丧", "description": "反复报错，难以解决"},
        "D": {"letter": "D", "name": "困惑", "description": "思路卡壳，不知方向"}
    }

    from monitoring.emotion_monitor import EmotionMonitor
    emotion_file = os.path.join(data_dir, f"{username}_emotion_performance.csv")

    emotion = EmotionMonitor(
        interval=120,
        output_file=emotion_file,
        stop_event=stop_event
    )
    monitors['emotion'] = emotion
    emotion.on_emotion_selected(emotions[mood_type])

    return jsonify({'success': True, 'message': f'success'})


@app.route('/api/start_monitoring', methods=['POST'])
def start_monitoring():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    data = request.get_json()
    monitor_type = data.get('type', 'all')

    global stop_event
    stop_event = threading.Event()

    try:
        # 确保数据目录存在
        data_dir = os.path.join(BASE_DIR, 'data')
        os.makedirs(data_dir, exist_ok=True)

        username = session['username']
        logging.info(f"用户 {username} 启动监控，类型: {monitor_type}")

        # 启动键盘监控
        if monitor_type in ['all', 'keyboard']:
            from monitoring.keyboard_monitor import KeyboardMonitor
            keyboard_file = os.path.join(data_dir, f"{username}_keyboard_performance.csv")

            monitors['keyboard'] = KeyboardMonitor(
                analysis_interval=60,  # 改为60秒，方便测试
                output_file=keyboard_file,
                stop_event=stop_event
            )

            keyboard_thread = threading.Thread(target=monitors['keyboard'].run)
            keyboard_thread.daemon = True
            keyboard_thread.start()
            logging.info(f"键盘监控已启动，输出文件: {keyboard_file}")

        # 启动鼠标监控
        if monitor_type in ['all', 'mouse']:
            from monitoring.mouse_monitor import MouseMonitor
            mouse_file = os.path.join(data_dir, f"{username}_mouse_performance.csv")

            monitors['mouse'] = MouseMonitor(
                analysis_interval=60,  # 改为60秒，方便测试
                output_file=mouse_file,
                stop_event=stop_event
            )

            mouse_thread = threading.Thread(target=monitors['mouse'].run)
            mouse_thread.daemon = True
            mouse_thread.start()
            logging.info(f"鼠标监控已启动，输出文件: {mouse_file}")

        return jsonify({'success': True, 'message': '监控已启动'})

    except Exception as e:
        logging.error(f"启动监控失败: {str(e)}")
        return jsonify({'success': False, 'message': f'启动监控失败: {str(e)}'})


@app.route('/api/stop_monitoring', methods=['POST','GET'])
def stop_monitoring():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'})

    username = session['username']
    logging.info(f"用户 {username} 请求停止监控")

    try:
        stop_event.set()

        # 停止所有监控器
        stopped_count = 0
        for monitor_type, monitor in monitors.items():
            if monitor:
                try:
                    logging.info(f"正在停止 {monitor_type} 监控器...")

                    if monitor_type in ['keyboard', 'mouse']:
                        if hasattr(monitor, 'stop_listener') and callable(getattr(monitor, 'stop_listener')):
                            monitor.stop_listener()
                            stopped_count += 1
                            logging.info(f"成功停止 {monitor_type} 监控器")
                        else:
                            logging.warning(f"{monitor_type} 监控器没有 stop_listener 方法")

                    elif monitor_type == 'emotion':
                        if hasattr(monitor, 'stop') and callable(getattr(monitor, 'stop')):
                            monitor.stop()
                            stopped_count += 1
                            logging.info(f"成功停止 {monitor_type} 监控器")
                        else:
                            logging.warning(f"{monitor_type} 监控器没有 stop  方法")

                except Exception as e:
                    logging.error(f"停止 {monitor_type} 监控器时出错: {str(e)}")
                finally:
                    monitors[monitor_type] = None

        # 给线程一些时间来完成停止操作
        time.sleep(1)

        # 重置停止事件，以便下次使用
        stop_event.clear()

        logging.info(f"用户 {username} 的监控停止完成，共停止了 {stopped_count} 个监控器")
        return jsonify({'success': 1, 'message': f'成功停止了 {stopped_count} 个监控器'})

    except Exception as e:
        logging.error(f"停止监控时发生未知错误: {str(e)}")
        return jsonify({'success': 0, 'message': f'停止监控时发生错误: {str(e)}'})


@app.route('/api/monitoring_data')
def get_monitoring_data():
    if 'username' not in session:
        return jsonify({'error': '未登录'})

    data_type = request.args.get('type', 'mouse')
    student = request.args.get('student', session['username'])

    try:
        data_dir = os.path.join(BASE_DIR, 'data')
        file_path = os.path.join(data_dir, f"{student}_{data_type}_performance.csv")

        if not os.path.exists(file_path):
            return jsonify({'data': []})

        data = []
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 根据数据类型格式化返回结果
                if data_type == 'mouse':
                    data.append({
                        'time': row.get('start_time', ''),
                        'action': f"移动 (距离: {row.get('total_distance', 0)}px)",
                        'position': f"熵: {row.get('move_entropy', 0)}"
                    })
                elif data_type == 'keyboard':
                    data.append({
                        'time': row.get('start_time', ''),
                        'key': f"按键次数: {row.get('total_keypresses', 0)}",
                        'duration': f"IKD中位数: {row.get('median_ikd', 0)}s"
                    })

        # 返回最近10条记录
        return jsonify({'data': data[-10:]})
    except Exception as e:
        logging.error(f"获取监控数据失败: {str(e)}")
        return jsonify({'error': str(e)})


@app.route('/api/student_monitoring_data')
def get_student_monitoring_data():
    if 'username' not in session or session['role'] != 'admin':
        return jsonify({'error': '未登录或权限不足'})

    student = request.args.get('student')
    data_type = request.args.get('type', 'mouse')

    if not student:
        return jsonify({'error': '未指定学生'})

    try:
        data_dir = os.path.join(BASE_DIR, 'data')
        file_path = os.path.join(data_dir, f"{student}_{data_type}_performance.csv")

        if not os.path.exists(file_path):
            return jsonify({'data': [], 'student': student, 'type': data_type})

        data = []
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if data_type == 'mouse':
                    data.append({
                        'time': row.get('start_time', ''),
                        'action': f"移动 (距离: {row.get('total_distance', 0)}px)",
                        'position': f"熵: {row.get('move_entropy', 0)}",
                        'duration': row.get('duration_sec', '0'),
                        'clicks': row.get('click_count', '0')
                    })
                elif data_type == 'keyboard':
                    data.append({
                        'time': row.get('start_time', ''),
                        'key': f"按键次数: {row.get('total_keypresses', 0)}",
                        'duration': f"IKD中位数: {row.get('median_ikd', 0)}s",
                        'backspace_rate': f"{float(row.get('auto_correction_rate', 0)) * 100:.1f}%"
                    })
                elif data_type == 'emotion':
                    data.append({
                        'time': row.get('timestamp', ''),
                        'emotion': row.get('emotion', ''),
                        'description': row.get('description', '')
                    })

        # 返回所有记录
        return jsonify({'data': data, 'student': student, 'type': data_type})
    except Exception as e:
        logging.error(f"获取学生监控数据失败: {str(e)}")
        return jsonify({'error': str(e)})


@app.route('/api/students')
def get_students():
    if 'username' not in session or session['role'] != 'admin':
        return jsonify({'error': '未登录或权限不足'})

    users_data = load_users()
    students = []

    for username, user_info in users_data.items():
        if user_info.get('role') == 'student':
            students.append({
                'name': username,
                'registered_time': user_info.get('registered_time', '未知')
            })

    return jsonify({'students': students})


@app.route('/api/status')
def get_status():
    """获取监控器状态"""
    if 'username' not in session:
        return jsonify({'error': '未登录'})

    status = {
        'keyboard': {
            'running': monitors['keyboard'] is not None,
            'listening': monitors['keyboard'].is_listening if monitors['keyboard'] and hasattr(monitors['keyboard'],
                                                                                               'is_listening') else False
        },
        'mouse': {
            'running': monitors['mouse'] is not None,
            'listening': monitors['mouse'].is_listening if monitors['mouse'] and hasattr(monitors['mouse'],
                                                                                         'is_listening') else False
        },
        'emotion': {
            'running': monitors['emotion'] is not None,
            'listening': monitors['emotion'].is_running if monitors['emotion'] and hasattr(monitors['emotion'],
                                                                                           'is_running') else False
        }
    }

    return jsonify(status)


@app.route('/api/debug')
def debug_info():
    """调试信息"""
    if 'username' not in session:
        return jsonify({'error': '未登录'})

    username = session['username']
    data_dir = os.path.join(BASE_DIR, 'data')

    debug_info = {
        'user': username,
        'keyboard_monitor': {
            'exists': monitors['keyboard'] is not None,
            'is_listening': monitors['keyboard'].is_listening if monitors['keyboard'] else False,
            'events_count': len(monitors['keyboard'].events) if monitors['keyboard'] and hasattr(monitors['keyboard'],
                                                                                                 'events') else 0
        },
        'keyboard_file': os.path.join(data_dir, f"{username}_keyboard_performance.csv"),
        'keyboard_file_exists': os.path.exists(os.path.join(data_dir, f"{username}_keyboard_performance.csv")),
        'mouse_file': os.path.join(data_dir, f"{username}_mouse_performance.csv"),
        'mouse_file_exists': os.path.exists(os.path.join(data_dir, f"{username}_mouse_performance.csv")),
        'emotion_file': os.path.join(data_dir, f"{username}_emotion_performance.csv"),
        'emotion_file_exists': os.path.exists(os.path.join(data_dir, f"{username}_emotion_performance.csv"))
    }

    return jsonify(debug_info)


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '页面不存在'}), 404


@app.errorhandler(500)
def internal_error(error):
    logging.error(f"服务器内部错误: {str(error)}")
    return jsonify({'error': '服务器内部错误'}), 500


if __name__ == '__main__':
    # 确保数据目录和日志目录存在
    data_dir = os.path.join(BASE_DIR, 'data')
    logs_dir = os.path.join(BASE_DIR, 'logs')
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    print(f"项目根目录: {BASE_DIR}")
    print(f"模板目录: {TEMPLATE_DIR}")
    print(f"静态文件目录: {STATIC_DIR}")
    print(f"数据目录: {data_dir}")
    print(f"日志目录: {logs_dir}")

    # 检查模板目录
    if os.path.exists(TEMPLATE_DIR):
        print(f"模板文件: {os.listdir(TEMPLATE_DIR)}")
    else:
        print("警告: 模板目录不存在")

    # 检查静态文件目录
    if os.path.exists(STATIC_DIR):
        print(f"静态文件: {os.listdir(STATIC_DIR)}")
    else:
        print("警告: 静态文件目录不存在")

    print("启动Flask应用...")
    app.run(debug=True, port=5000, use_reloader=False)