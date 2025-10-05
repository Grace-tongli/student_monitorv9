function viewStudentData(student) {
    document.getElementById('selected-student').textContent = student;
    document.getElementById('student-details').style.display = 'block';

    // 加载所有类型的数据
    loadStudentData(student, 'mouse');
    loadStudentData(student, 'keyboard');
    loadStudentData(student, 'emotion');
}

function loadStudentData(student, dataType) {
    fetch(`/api/student_monitoring_data?student=${student}&type=${dataType}`)
    .then(response => response.json())
    .then(data => {
        const tbody = document.getElementById(`${dataType}-data-body`);
        tbody.innerHTML = '';

        if (data.data && data.data.length > 0) {
            data.data.forEach(item => {
                const row = document.createElement('tr');

                if (dataType === 'mouse') {
                    row.innerHTML = `
                        <td>${item.time}</td>
                        <td>${item.action}</td>
                        <td>${item.position}</td>
                        <td>${item.duration}</td>
                        <td>${item.clicks}</td>
                    `;
                } else if (dataType === 'keyboard') {
                    row.innerHTML = `
                        <td>${item.time}</td>
                        <td>${item.key}</td>
                        <td>${item.duration}</td>
                        <td>${item.backspace_rate}</td>
                    `;
                } else if (dataType === 'emotion') {
                    row.innerHTML = `
                        <td>${item.time}</td>
                        <td>${item.emotion}</td>
                        <td>${item.description}</td>
                    `;
                }

                tbody.appendChild(row);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="5">暂无数据</td></tr>';
        }
    })
    .catch(error => {
        console.error('Error loading data:', error);
        document.getElementById(`${dataType}-data-body`).innerHTML =
            '<tr><td colspan="5">加载数据时发生错误</td></tr>';
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

    // 如果已选择学生，则重新加载数据
    const selectedStudent = document.getElementById('selected-student').textContent;
    if (selectedStudent) {
        loadStudentData(selectedStudent, tabName);
    }
}