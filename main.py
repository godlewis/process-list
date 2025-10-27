import sys
import psutil
import re
import time
from typing import Dict, List, Set, Optional
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QLabel, QHeaderView, QDialog, QTextEdit, QMenu, QAction, QDesktopWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
import pyperclip # 导入pyperclip库用于复制内容

# 进程数据缓存管理类
class ProcessCache:
    """进程信息缓存管理器，提供快速查询和增量更新功能"""

    def __init__(self, cache_expiry_seconds: int = 10):
        self.cache_expiry_seconds = cache_expiry_seconds
        self.process_data: Dict[str, Dict] = {}  # PID -> 进程数据
        self.name_index: Dict[str, List[str]] = {}  # 进程名 -> PID列表
        self.port_index: Dict[str, str] = {}  # 端口 -> PID
        self.username_index: Dict[str, List[str]] = {}  # 用户名 -> PID列表

        self.last_update_time = 0
        self.is_cache_valid = False
        self._update_lock = False  # 防止并发更新

    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        return time.time() - self.last_update_time > self.cache_expiry_seconds

    def is_valid(self) -> bool:
        """检查缓存是否有效"""
        return self.is_cache_valid and not self.is_expired()

    def get_process_by_pid(self, pid: str) -> Optional[Dict]:
        """根据PID获取进程数据"""
        return self.process_data.get(pid)

    def get_processes_by_name(self, name: str) -> List[Dict]:
        """根据进程名获取进程列表"""
        pids = self.name_index.get(name, [])
        return [self.process_data[pid] for pid in pids if pid in self.process_data]

    def get_process_by_port(self, port: str) -> Optional[Dict]:
        """根据端口获取进程数据"""
        pid = self.port_index.get(port)
        return self.process_data.get(pid) if pid else None

    def search_processes(self, keyword: str) -> List[Dict]:
        """搜索进程，支持PID、进程名、端口、用户名的模糊搜索"""
        if not keyword:
            return list(self.process_data.values())

        keyword = keyword.lower()
        pattern = re.escape(keyword).replace(r'\*', '.*')
        regex = re.compile(pattern, re.IGNORECASE)

        results = []
        seen_pids = set()

        # 搜索PID
        for pid in self.process_data:
            if regex.search(pid):
                if pid not in seen_pids:
                    results.append(self.process_data[pid])
                    seen_pids.add(pid)

        # 搜索进程名
        for name in self.name_index:
            if regex.search(name):
                for pid in self.name_index[name]:
                    if pid not in seen_pids and pid in self.process_data:
                        results.append(self.process_data[pid])
                        seen_pids.add(pid)

        # 搜索端口
        for port in self.port_index:
            if regex.search(port):
                pid = self.port_index[port]
                if pid not in seen_pids and pid in self.process_data:
                    results.append(self.process_data[pid])
                    seen_pids.add(pid)

        # 搜索用户名
        for username in self.username_index:
            if regex.search(username):
                for pid in self.username_index[username]:
                    if pid not in seen_pids and pid in self.process_data:
                        results.append(self.process_data[pid])
                        seen_pids.add(pid)

        return results

    def update_cache(self, process_list: List[Dict]):
        """更新缓存数据"""
        if self._update_lock:
            return

        self._update_lock = True

        try:
            # 清空现有索引
            self.process_data.clear()
            self.name_index.clear()
            self.port_index.clear()
            self.username_index.clear()

            # 重建数据结构和索引
            for proc in process_list:
                pid = proc['pid']
                name = proc['name']
                username = proc['username']
                ports = proc['ports']

                # 存储进程数据
                self.process_data[pid] = proc

                # 建立名称索引
                if name not in self.name_index:
                    self.name_index[name] = []
                self.name_index[name].append(pid)

                # 建立用户名索引
                if username not in self.username_index:
                    self.username_index[username] = []
                self.username_index[username].append(pid)

                # 建立端口索引
                if ports:
                    for port in ports.split(','):
                        port = port.strip()
                        if port:
                            self.port_index[port] = pid

            self.last_update_time = time.time()
            self.is_cache_valid = True

        finally:
            self._update_lock = False

    def invalidate_cache(self):
        """使缓存失效"""
        self.is_cache_valid = False

    def clear_cache(self):
        """清空缓存"""
        self.process_data.clear()
        self.name_index.clear()
        self.port_index.clear()
        self.username_index.clear()
        self.is_cache_valid = False
        self.last_update_time = 0

# 系统数据获取类 - 负责从系统获取原始进程数据
class SystemDataFetcher:
    """负责从系统获取原始进程数据，不包含缓存逻辑"""

    @staticmethod
    def fetch_all_processes() -> List[Dict]:
        """从系统获取所有进程信息"""
        proc_list = []
        port_map = {}

        # 获取所有网络连接，建立端口到PID的映射
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'LISTEN' and conn.laddr and conn.pid:
                    port = conn.laddr.port
                    if conn.pid not in port_map:
                        port_map[conn.pid] = set()
                    port_map[conn.pid].add(str(port))
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            # 如果无法获取网络连接信息，继续处理进程信息
            pass

        # 遍历所有进程
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cmdline']):
            try:
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
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                # 跳过无法访问的进程
                continue

        return proc_list

# 定义一个工作线程类 - 现在使用缓存
class ProcessFetcher(QThread):
    finished = pyqtSignal(list) # 定义一个信号，用于在数据处理完成后发送数据
    update_cache = pyqtSignal() # 请求更新缓存的信号

    def __init__(self, keyword, cache, force_refresh=False, parent=None):
        super().__init__(parent)
        self.keyword = keyword
        self.cache = cache
        self.force_refresh = force_refresh

    def run(self):
        # 检查缓存是否有效，如果无效或强制刷新则更新缓存
        if not self.cache.is_valid() or self.force_refresh:
            # 请求更新缓存
            self.update_cache.emit()

            # 等待缓存更新完成
            max_wait = 5  # 最多等待5秒
            wait_time = 0
            while not self.cache.is_valid() and wait_time < max_wait:
                self.msleep(100)  # 等待100毫秒
                wait_time += 0.1

        # 使用缓存进行搜索
        if self.cache.is_valid():
            proc_list = self.cache.search_processes(self.keyword)
        else:
            # 如果缓存仍然无效，回退到直接查询
            proc_list = SystemDataFetcher.fetch_all_processes()

            # 应用过滤逻辑
            if self.keyword:
                pattern = re.escape(self.keyword).replace(r'\*', '.*')
                regex = re.compile(pattern, re.IGNORECASE)

                filtered_procs = []
                for p in proc_list:
                    if (
                        regex.search(p['pid']) or
                        regex.search(p['name']) or
                        regex.search(p['username']) or
                        regex.search(p['ports'])
                    ):
                        filtered_procs.append(p)
                proc_list = filtered_procs

        self.finished.emit(proc_list) # 发送处理好的数据

# 缓存管理器类 - 负责后台定时更新缓存
class CacheManager(QThread):
    cache_updated = pyqtSignal(list)  # 缓存更新完成信号
    cache_update_failed = pyqtSignal(str)  # 缓存更新失败信号

    def __init__(self, cache: ProcessCache, parent=None):
        super().__init__(parent)
        self.cache = cache
        self.update_interval = 10000  # 10秒更新间隔（毫秒）
        self.is_running = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_cache)
        self.timer.moveToThread(self)

    def start_auto_update(self):
        """开始自动更新"""
        self.is_running = True
        self.timer.start(self.update_interval)

    def stop_auto_update(self):
        """停止自动更新"""
        self.is_running = False
        self.timer.stop()

    def update_cache(self):
        """更新缓存数据"""
        try:
            # 在后台线程中获取系统数据
            proc_list = SystemDataFetcher.fetch_all_processes()

            # 更新缓存
            self.cache.update_cache(proc_list)

            # 发送更新完成信号
            self.cache_updated.emit(proc_list)

        except Exception as e:
            # 发送更新失败信号
            self.cache_update_failed.emit(str(e))

    def force_update(self):
        """强制立即更新缓存"""
        self.update_cache()

# 进程详情窗口
class ProcessDetailDialog(QDialog):
    def __init__(self, cmdline_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle('进程命令行详情')
        self.setGeometry(200, 200, 800, 300)
        
        # 对话框居中
        self.center_dialog()

        layout = QVBoxLayout(self)

        self.cmdline_display = QTextEdit()
        self.cmdline_display.setReadOnly(True)
        self.cmdline_display.setText(cmdline_text)
        layout.addWidget(self.cmdline_display)

        copy_button = QPushButton('复制')
        copy_button.clicked.connect(self.copy_cmdline)
        layout.addWidget(copy_button)

    def center_dialog(self):
        """将对话框居中显示在屏幕上"""
        # 获取屏幕几何信息
        screen = QDesktopWidget().screenGeometry()
        # 获取对话框几何信息
        dialog = self.geometry()
        # 计算居中位置
        x = (screen.width() - dialog.width()) // 2
        y = (screen.height() - dialog.height()) // 2
        # 移动对话框到居中位置
        self.move(x, y)

    def copy_cmdline(self):
        try:
            pyperclip.copy(self.cmdline_display.toPlainText())
            QMessageBox.information(self, '复制成功', '命令行内容已复制到剪贴板！')
        except Exception as e:
            QMessageBox.warning(self, '复制失败', f'复制内容失败: {e}\n请手动复制。')

class ProcessManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('进程管理器（含端口）- 优化版')
        self.setGeometry(100, 100, 1600, 900)
        self.setWindowIcon(QIcon('process_manager_icon.png'))  # 设置窗口图标

        # 窗口居中
        self.center_window()

        # 初始化缓存系统
        self.cache = ProcessCache(cache_expiry_seconds=10)
        self.cache_manager = CacheManager(self.cache, self)

        # 连接缓存管理器信号
        self.cache_manager.cache_updated.connect(self.on_cache_updated)
        self.cache_manager.cache_update_failed.connect(self.on_cache_update_failed)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # 搜索栏
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('输入进程名、PID或端口进行过滤（支持*通配符，实时搜索）')
        self.search_input.textChanged.connect(self.on_search_text_changed)  # 实时搜索
        search_layout.addWidget(QLabel('查找:'))
        search_layout.addWidget(self.search_input)

        # 添加刷新按钮
        self.refresh_button = QPushButton('刷新')
        self.refresh_button.clicked.connect(self.force_refresh)
        search_layout.addWidget(self.refresh_button)

        # 添加状态标签
        self.status_label = QLabel('正在初始化...')
        search_layout.addWidget(self.status_label)

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
        self.last_search_keyword = ''  # 记录上次搜索关键词

        # 启动缓存管理器
        self.cache_manager.start()
        self.cache_manager.start_auto_update()

        # 初始加载
        self.force_refresh()

    def center_window(self):
        """将窗口居中显示在屏幕上"""
        # 获取屏幕几何信息
        screen = QDesktopWidget().screenGeometry()
        # 获取窗口几何信息
        window = self.geometry()
        # 计算居中位置
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        # 移动窗口到居中位置
        self.move(x, y)

    def resizeEvent(self, event):
        # 窗口大小变化时输出宽高日志 (已移除)
        super().resizeEvent(event)

    def on_search_text_changed(self):
        """搜索文本变化时的处理函数，实现实时搜索"""
        keyword = self.search_input.text().strip()

        # 如果缓存有效，立即进行搜索
        if self.cache.is_valid():
            self.perform_search(keyword)
        else:
            # 如果缓存无效，显示加载状态
            self.status_label.setText('缓存失效，正在刷新...')

    def perform_search(self, keyword):
        """执行搜索操作"""
        try:
            # 使用缓存进行搜索
            proc_list = self.cache.search_processes(keyword)
            self.update_table_data(proc_list)
            self.status_label.setText(f'找到 {len(proc_list)} 个进程 (缓存)')

            # 更新搜索关键词记录
            self.last_search_keyword = keyword

        except Exception as e:
            self.status_label.setText(f'搜索失败: {str(e)}')

    def force_refresh(self):
        """强制刷新缓存"""
        self.status_label.setText('正在强制刷新...')
        self.refresh_button.setEnabled(False)

        # 直接调用缓存管理器强制更新
        self.cache_manager.force_update()

    def on_cache_updated(self, proc_list):
        """缓存更新完成时的回调"""
        self.status_label.setText(f'缓存已更新，共 {len(proc_list)} 个进程')
        self.refresh_button.setEnabled(True)

        # 如果有当前搜索，重新执行搜索
        current_keyword = self.search_input.text().strip()
        if current_keyword:
            self.perform_search(current_keyword)
        else:
            # 显示所有进程
            self.update_table_data(proc_list)

    def on_cache_update_failed(self, error_msg):
        """缓存更新失败时的回调"""
        self.status_label.setText(f'缓存更新失败: {error_msg}')
        self.refresh_button.setEnabled(True)
        QMessageBox.warning(self, '错误', f'更新进程数据失败: {error_msg}')

    def start_refresh(self):
        """常规刷新，优先使用缓存"""
        keyword = self.search_input.text().strip()

        # 如果缓存有效，直接使用缓存进行搜索
        if self.cache.is_valid():
            self.perform_search(keyword)
            return

        # 如果缓存无效，强制刷新
        self.force_refresh()

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
        # 将所有列的调整模式设置为根据内容调整
        # 确保所有列都可以手动调整
        for i in range(self.table.columnCount()):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Interactive)

        # 初始时根据内容调整所有列的宽度，除了进程名列
        for i in range(self.table.columnCount()):
            if i != 1: # 进程名列（索引为1）不进行内容自适应，因为它将拉伸
                self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        # 设置“进程名”列（索引为1）为拉伸模式，使其自动填充剩余空间
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        # 确保最后一列不自动拉伸，因为我们已经指定了拉伸列
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

                # 从缓存中移除已终止的进程
                if str(pid) in self.cache.process_data:
                    del self.cache.process_data[str(pid)]
                    # 重建索引
                    self.cache.update_cache(list(self.cache.process_data.values()))

            except Exception as e:
                QMessageBox.warning(self, '错误', f'无法终止进程 {pid}: {e}')

            # 强制刷新缓存以确保数据同步
            self.force_refresh()

def main():
    app = QApplication(sys.argv)
    win = ProcessManager()
    win.resize(1800, 900)
    win.show()

    # 确保应用程序关闭时正确清理资源
    def cleanup():
        try:
            win.cache_manager.stop_auto_update()
            win.cache_manager.quit()
            win.cache_manager.wait(1000)  # 等待最多1秒
        except:
            pass

    app.aboutToQuit.connect(cleanup)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
