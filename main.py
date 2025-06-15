import sys
import psutil
import re
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QLabel, QHeaderView, QDialog, QTextEdit, QPushButton, QMenu, QAction
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QCursor, QIcon
import pyperclip # 导入pyperclip库用于复制内容

# 定义一个工作线程类
class ProcessFetcher(QThread):
    finished = pyqtSignal(list) # 定义一个信号，用于在数据处理完成后发送数据

    def __init__(self, keyword, parent=None):
        super().__init__(parent)
        self.keyword = keyword

    def run(self):
        proc_list = []
        port_map = {}
        # 获取所有网络连接，建立端口到PID的映射
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr and conn.pid:
                port = conn.laddr.port
                if conn.pid not in port_map:
                    port_map[conn.pid] = set()
                port_map[conn.pid].add(str(port))

        # 遍历所有进程
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cmdline']):
            pid = proc.info['pid']
            name = proc.info.get('name', '')
            username = proc.info.get('username', '')
            cmdline_raw = proc.info.get('cmdline', [])
            if not isinstance(cmdline_raw, (list, tuple)):
                cmdline_raw = [str(cmdline_raw)] if cmdline_raw else []
            cmdline = ' '.join(cmdline_raw)
            ports = ','.join(port_map.get(pid, []))
            proc_list.append({
                'pid': str(pid),
                'name': name,
                'username': username,
                'cmdline': cmdline,
                'ports': ports
            })

        # 过滤逻辑 (排除命令行字段)
        if self.keyword:
            pattern = re.escape(self.keyword).replace(r'\*', '.*')
            regex = re.compile(pattern, re.IGNORECASE)

            filtered_procs = []
            for p in proc_list:
                if (
                    regex.search(p['pid']) or
                    regex.search(p['name']) or
                    regex.search(p['username']) or
                    # regex.search(p['cmdline']) or # 不再过滤命令行
                    regex.search(p['ports'])
                ):
                    filtered_procs.append(p)
            proc_list = filtered_procs

        self.finished.emit(proc_list) # 发送处理好的数据

# 进程详情窗口
class ProcessDetailDialog(QDialog):
    def __init__(self, cmdline_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle('进程命令行详情')
        self.setGeometry(200, 200, 800, 300)

        layout = QVBoxLayout(self)

        self.cmdline_display = QTextEdit()
        self.cmdline_display.setReadOnly(True)
        self.cmdline_display.setText(cmdline_text)
        layout.addWidget(self.cmdline_display)

        copy_button = QPushButton('复制')
        copy_button.clicked.connect(self.copy_cmdline)
        layout.addWidget(copy_button)

    def copy_cmdline(self):
        try:
            pyperclip.copy(self.cmdline_display.toPlainText())
            QMessageBox.information(self, '复制成功', '命令行内容已复制到剪贴板！')
        except Exception as e:
            QMessageBox.warning(self, '复制失败', f'复制内容失败: {e}\n请手动复制。')

class ProcessManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('进程管理器（含端口）')
        self.setGeometry(100, 100, 1600, 900)
        self.setWindowIcon(QIcon('process_manager_icon.png'))  # 设置窗口图标
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # 搜索栏
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('输入进程名、PID或端口进行过滤（支持*通配符，回车搜索）')
        self.search_input.returnPressed.connect(self.start_refresh) # 回车后才过滤
        search_layout.addWidget(QLabel('查找:'))
        search_layout.addWidget(self.search_input)
        self.layout.addLayout(search_layout)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(5) # 命令行字段不再显示
        self.table.setHorizontalHeaderLabels([
            'PID', '进程名', '用户名', '监听端口', '操作' # 命令行字段不再显示
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)  # 整行高亮
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # 禁止编辑
        self.table.setSortingEnabled(True)  # 支持表头排序
        self.table.horizontalHeader().setSectionsClickable(True)
        # self.table.horizontalHeader().setStretchLastSection(True) # 取消最后一列自动拉伸
        self.layout.addWidget(self.table)

        # 连接双击信号和右键菜单信号
        self.table.doubleClicked.connect(self.show_process_detail)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        self.process_fetcher_thread = None # 用于存储线程实例
        self.all_processes_data = [] # 存储所有进程的原始数据，包括命令行，用于详情显示

        self.start_refresh() # 初始加载

    def start_refresh(self):
        # 如果线程已经在运行，则等待它完成或取消（这里选择简单等待）
        if self.process_fetcher_thread and self.process_fetcher_thread.isRunning():
            self.process_fetcher_thread.quit()
            self.process_fetcher_thread.wait()

        # 设置忙碌鼠标指针
        QApplication.setOverrideCursor(Qt.WaitCursor)

        keyword = self.search_input.text().strip()
        self.process_fetcher_thread = ProcessFetcher(keyword)
        self.process_fetcher_thread.finished.connect(self.update_table_data)
        self.process_fetcher_thread.start()

    def update_table_data(self, procs):
        # 恢复正常鼠标指针
        QApplication.restoreOverrideCursor()

        self.all_processes_data = procs # 存储完整的进程数据
        self.table.setRowCount(len(procs))
        for row, proc in enumerate(procs):
            self.table.setItem(row, 0, QTableWidgetItem(proc['pid']))
            self.table.setItem(row, 1, QTableWidgetItem(proc['name']))
            self.table.setItem(row, 2, QTableWidgetItem(proc['username']))
            self.table.setItem(row, 3, QTableWidgetItem(proc['ports']))
            btn = QPushButton('终止进程') # 修改按钮文本
            btn.clicked.connect(lambda _, pid=proc['pid'], name=proc['name']: self.kill_process(pid, name))
            self.table.setCellWidget(row, 4, btn)

        # 列宽设置优化
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 90)   # PID
        self.table.setColumnWidth(1, 350)  # 进程名
        self.table.setColumnWidth(2, 300)  # 用户名
        self.table.setColumnWidth(3, 320)  # 监听端口
        self.table.setColumnWidth(4, 150)  # 操作
        self.table.horizontalHeader().setStretchLastSection(False)

    def show_process_detail(self, index):
        # 获取双击行的进程数据
        row = index.row()
        # 确保索引有效且数据存在
        if 0 <= row < len(self.all_processes_data):
            proc = self.all_processes_data[row]
            cmdline_text = proc.get('cmdline', '无命令行信息')
            detail_dialog = ProcessDetailDialog(cmdline_text, self)
            detail_dialog.exec_()

    def show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return

        # 获取右键点击行的进程数据
        row = index.row()
        if not (0 <= row < len(self.all_processes_data)):
            return
        
        proc = self.all_processes_data[row]
        pid = proc['pid']
        name = proc['name']
        cell_content = self.table.item(row, index.column()).text() if self.table.item(row, index.column()) else ''

        menu = QMenu()

        kill_action = QAction('终止进程', self)
        kill_action.triggered.connect(lambda: self.kill_process(pid, name))
        menu.addAction(kill_action)

        copy_action = QAction('复制内容', self)
        copy_action.triggered.connect(lambda: self.copy_to_clipboard(cell_content))
        menu.addAction(copy_action)

        menu.exec_(self.table.mapToGlobal(pos))

    def copy_to_clipboard(self, text):
        try:
            pyperclip.copy(text)
            QMessageBox.information(self, '复制成功', '内容已复制到剪贴板！')
        except Exception as e:
            QMessageBox.warning(self, '复制失败', f'复制内容失败: {e}\n请手动复制。')

    def kill_process(self, pid, name):
        reply = QMessageBox.question(self, '确认终止', f'确定要终止进程 {pid} ({name}) 吗？',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                p = psutil.Process(int(pid))
                p.terminate()
                p.wait(timeout=3)
                QMessageBox.information(self, '提示', f'进程 {pid} 已终止')
            except Exception as e:
                QMessageBox.warning(self, '错误', f'无法终止进程 {pid}: {e}')
            self.start_refresh() # 终止后刷新

def main():
    app = QApplication(sys.argv)
    win = ProcessManager()
    win.resize(1600, 900)
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
