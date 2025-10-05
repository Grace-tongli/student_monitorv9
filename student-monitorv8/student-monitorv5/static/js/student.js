
function save_emotion_selected(mood_type) {
    fetch('/api/save_emotion_selected', {
        method: 'POST',
        headers: {
            'Content-type': 'application/json'
        },
        body: JSON.stringify({mood_type})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('save emotion success!')
        } else {
            console.log('save emotion error')
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function startMonitoring(options_data = {}) {
    const monitorMouse = document.getElementById('monitor-mouse').checked;
    const monitorKeyboard = document.getElementById('monitor-keyboard').checked;

    let type = 'all';
    if (monitorMouse && !monitorKeyboard) type = 'mouse';
    if (!monitorMouse && monitorKeyboard) type = 'keyboard';

    fetch('/api/start_monitoring', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ type: type, ...options_data })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('监控已启动');
            location.reload();
        } else {
            alert('启动监控失败: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('启动监控时发生错误');
    });
}

function stopMonitoring() {
    fetch('/api/stop_monitoring', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message || '监控已停止');
            location.reload();
        } else {
            alert('停止监控失败: ' + (data.message || '未知错误'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('停止监控时发生网络错误');
    });
}

function showTab(tabName) {
    // 隐藏所有标签内容
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.style.display = 'none';
    });

    // 移除所有标签的活动状态
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // 显示选中的标签内容
    document.getElementById(`${tabName}-data`).style.display = 'block';

    // 设置选中的标签为活动状态
    event.target.classList.add('active');

    // 加载数据
    loadActivityData(tabName);
}

// 加载活动数据
function loadActivityData(dataType) {
    fetch(`/api/monitoring_data?type=${dataType}`)
    .then(response => response.json())
    .then(data => {
        // 先检查元素是否存在
        const container = document.getElementById(`${dataType}-data-body`);
        if (!container) {
            // 元素不存在时，仅在控制台提示，不执行后续操作
            console.log(`数据展示区域 ${dataType}-data-body 未定义，跳过渲染`);
            return;
        }

        // 元素存在时才处理数据
        if (data.error) {
            container.innerHTML = `<tr><td colspan="3">${data.error}</td></tr>`;
        } else if (data.data && data.data.length > 0) {
            let html = '';
            data.data.forEach(item => {
                if (dataType === 'mouse') {
                    html += `<tr>
                        <td>${item.time}</td>
                        <td>${item.action}</td>
                        <td>${item.position}</td>
                    </tr>`;
                } else {
                    html += `<tr>
                        <td>${item.time}</td>
                        <td>${item.key}</td>
                        <td>${item.duration}</td>
                    </tr>`;
                }
            });
            container.innerHTML = html;
        } else {
            container.innerHTML = '<tr><td colspan="3">暂无活动数据</td></tr>';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        // 错误处理时也检查元素是否存在
        const errorContainer = document.getElementById(`${dataType}-data-body`);
        if (errorContainer) {
            errorContainer.innerHTML = '<tr><td colspan="3">加载数据时发生错误</td></tr>';
        } else {
            console.log(`数据展示区域 ${dataType}-data-body 未定义，无法显示错误信息`);
        }
    });
}


// 添加自动提交函数
function autoSubmitEmotion(mood_type) {
    // 保存情绪数据
    fetch('/api/save_emotion_selected', {
        method: 'POST',
        headers: {
            'Content-type': 'application/json'
        },
        body: JSON.stringify({mood_type})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('自动保存情绪成功!');
            // 关闭模态框
            $('#myModal').modal('hide');

            // 如果是首次启动监控，自动开始
            if (isOk === '0') {
                startMonitoring();
            } else {
                // 刷新页面或更新状态
                location.reload();
            }
        } else {
            console.log('自动保存情绪错误');
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}




// 页面加载时获取数据
document.addEventListener('DOMContentLoaded', function() {
    // 初始加载鼠标数据
    loadActivityData('mouse');
});