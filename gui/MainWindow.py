from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QAction, QActionGroup
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication, QSystemTrayIcon, QMenu, QMainWindow, QStackedWidget, \
    QHBoxLayout, QDialog, QLineEdit, QLabel, QPushButton
from pynput import keyboard

from character.GifWidget import GifWidget
from character.WoodFishWidget import WoodFishWidget
from utils.TcpClient import TcpClient
from utils.systemUtils import get_resource_path, generate_uid
from utils.KeypressRecorder import KeypressRecorder
from utils.KeyboardVisualizer import KeyboardVisualizerDialog
from utils.MouseHeatmapTracker import OptimizedMouseHeatmapTracker  # 替换为优化版本
from utils.MouseHeatmapVisualizer import MouseHeatmapDialog
from utils.DataCacheManager import shutdown_cache_manager  # 新增导入
from utils.BailianAnalyzer import BailianAnalyzer
from gui.AnalysisResultDialog import AnalysisResultDialog, LoadingDialog

SNAP_TO_EDGE_MARGIN = 50  # 边缘吸附范围
TRAY_ICON_IMG = 'resource/icon/fish.ico' # 任务栏图标

class Win(QMainWindow):
    # 键盘信号
    trigger_key = pyqtSignal(object)
    # 远程触发信号
    trigger_key_with_data = pyqtSignal(object)
    drag_start_pos: QPoint | None = None

    def __init__(self):
        super().__init__()

        # 窗口设置
        self.setWindowTitle("busy with fish")
        self.setFixedSize(130, 130)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # ----- 数据初始化 ------ #
        # 客户端UID
        self.uid = generate_uid()
        # 在线状态
        self.is_online = True
        # 目标UID
        self.target_uid = "未连接"
        # 目标是否在线
        self.target_online = False

        # 内容堆叠
        self.woodFishWidget = WoodFishWidget()
        self.gifWidget = GifWidget()
        self.stack = QStackedWidget()
        self.stack.addWidget(self.woodFishWidget)
        self.stack.addWidget(self.gifWidget)

        self.currentWidget = self.woodFishWidget

        # ---- 主布局 ----
        central = QWidget()
        self.setCentralWidget(central)
        lay = QHBoxLayout(central)
        lay.addWidget(self.stack)

        # 键盘监听
        self.trigger_key.connect(self.currentWidget.animate)
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

        # 远程信号
        self.trigger_key_with_data.connect(self.handle_remote_trigger)

        # 初始位置：屏幕右下角
        scr = QApplication.primaryScreen().geometry()
        self.move(scr.width() - self.width(),
                  scr.height() - self.height() - 50)
        self.original_geom = self.frameGeometry()

        # 边缘吸附（优化：降低频率）
        self.edge_snap_timer = QTimer(self)
        self.edge_snap_timer.setInterval(500)  # 从200ms改为500ms
        self.edge_snap_timer.timeout.connect(self.snap_to_edge)

        # 托盘任务图标
        img_path = get_resource_path(TRAY_ICON_IMG)
        self.pixmap = QPixmap(str(img_path))

        # 创建系统托盘图标
        self.create_tray_icon()
        self.tray_icon.show()


        # 初始化客户端
        self.client = TcpClient('1.14.69.161', 9100, self.uid)
        self.client.set_main_window(self)
        # 客户端默认在线并连接到服务器
        self.client.start()

        self.keypressRecorder = KeypressRecorder()
        # 启动鼠标监听器
        self.keypressRecorder.mouse_recorder.start_listening()

        # 鼠标热力图跟踪器（优化版本）
        self.mouse_heatmap_tracker = OptimizedMouseHeatmapTracker(
            cell_size=48,
            data_root="data/mouse_heatmap",
            max_buffer_size=2000,      # 增大缓冲区
            flush_threshold=1000,      # 更大的刷盘阈值
            inactive_timeout=3.0       # 延长静止检测时间
        )
        self.mouse_heatmap_tracker.start()

        # 初始化AI分析器
        self.bailian_analyzer = BailianAnalyzer()
        # 连接分析器信号
        #self.bailian_analyzer.analysis_started.connect(self.on_analysis_started)
        self.bailian_analyzer.analysis_completed.connect(self.on_analysis_completed)
        self.bailian_analyzer.analysis_error.connect(self.on_analysis_error)
        self.bailian_analyzer.progress_updated.connect(self.on_progress_updated)




    # ---------- 系统托盘 ----------
    def create_tray_icon(self):
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self.pixmap))

        # 创建托盘菜单
        self.tray_menu = QMenu(self)

        # 添加UID显示动作
        self.uid_action = QAction(f"UID: {self.uid}", self)
        self.uid_action.setEnabled(True)  # 设置为可点击
        self.uid_action.triggered.connect(self.copy_uid_to_clipboard)  # 连接复制函数
        self.tray_menu.addAction(self.uid_action)

        # 分隔线
        self.tray_menu.addSeparator()

        self.connect_action = QAction("连接", self)
        self.connect_action.triggered.connect(self.show_connect_dialog)
        self.tray_menu.addAction(self.connect_action)

        # 分隔线
        self.tray_menu.addSeparator()

        # 在线/离线状态单选按钮组
        self.status_menu = QMenu("状态", self)
        self.tray_menu.addMenu(self.status_menu)
        
        # 创建动作组以确保单选行为
        status_group = QActionGroup(self)
        status_group.setExclusive(True)
        
        # 在线状态
        self.online_action = QAction("在线", self)
        self.online_action.setCheckable(True)
        self.online_action.setChecked(True)
        status_group.addAction(self.online_action)
        self.status_menu.addAction(self.online_action)
        
        # 离线状态
        self.offline_action = QAction("离线", self)
        self.offline_action.setCheckable(True)
        status_group.addAction(self.offline_action)
        self.status_menu.addAction(self.offline_action)
        
        # 连接状态变更信号
        self.online_action.triggered.connect(self.set_online)
        self.offline_action.triggered.connect(self.set_offline)

        # 分隔线
        self.tray_menu.addSeparator()

        # 角色切换菜单
        self.character_menu = QMenu("切换", self)
        self.tray_menu.addMenu(self.character_menu)

        # 添加角色选项
        self.wooden_fish_action = QAction("木鱼", self)
        self.wooden_fish_action.triggered.connect(
            lambda: self.switch_widget(0, self.woodFishWidget))
        self.character_menu.addAction(self.wooden_fish_action)

        self.desktop_pet_action = QAction("pop cat", self)
        self.desktop_pet_action.triggered.connect(
            lambda: self.switch_widget_gif(1, "resource/gif/popcat.gif", self.gifWidget, 3))
        self.character_menu.addAction(self.desktop_pet_action)

        self.zen_circle_action = QAction("铁山靠（施工中）", self)
        # self.zen_circle_action.triggered.connect(
        #     lambda: self.switch_widget_gif(1, "resource/gif/tsk.gif", self.gifWidget, 4))
        self.character_menu.addAction(self.zen_circle_action)

        # 分隔线
        self.tray_menu.addSeparator()

        # 显示/隐藏动作
        self.toggle_action = QAction("显示/隐藏", self)
        self.toggle_action.triggered.connect(self.toggle_window)
        self.tray_menu.addAction(self.toggle_action)

        # 分隔线
        self.tray_menu.addSeparator()

        # 键盘可视化动作
        self.keyboard_visualizer_action = QAction("按键统计可视化", self)
        self.keyboard_visualizer_action.triggered.connect(self.open_keyboard_visualizer)
        self.tray_menu.addAction(self.keyboard_visualizer_action)

        # 鼠标热力图动作
        self.mouse_heatmap_action = QAction("鼠标热力图", self)
        self.mouse_heatmap_action.triggered.connect(self.open_mouse_heatmap)
        self.tray_menu.addAction(self.mouse_heatmap_action)

        # AI分析动作
        self.ai_analysis_action = QAction("🤖 AI智能分析", self)
        self.ai_analysis_action.triggered.connect(self.start_ai_analysis)
        self.tray_menu.addAction(self.ai_analysis_action)

        # 分隔线
        self.tray_menu.addSeparator()

        # 退出动作
        self.quit_action = QAction("退出", self)
        self.quit_action.triggered.connect(self.quit_app)
        self.tray_menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.icon_activated)

    def open_keyboard_visualizer(self):
        """打开键盘可视化弹窗"""
        # 检查是否已经打开了可视化窗口，如果没有则创建
        if not hasattr(self, 'keyboard_visualizer'):
            self.keyboard_visualizer = KeyboardVisualizerDialog(self)
        self.keyboard_visualizer.show()
        self.keyboard_visualizer.raise_()
        self.keyboard_visualizer.activateWindow()

    def open_mouse_heatmap(self):
        """打开鼠标热力图弹窗"""
        # 先刷新一次热力图数据到文件
        try:
            if hasattr(self, "mouse_heatmap_tracker"):
                self.mouse_heatmap_tracker.flush()
        except Exception:
            pass
        if not hasattr(self, 'mouse_heatmap_dialog'):
            self.mouse_heatmap_dialog = MouseHeatmapDialog(self)
        self.mouse_heatmap_dialog.refresh_image()
        self.mouse_heatmap_dialog.show()
        self.mouse_heatmap_dialog.raise_()
        self.mouse_heatmap_dialog.activateWindow()

    def start_ai_analysis(self):
        """启动AI分析"""
        # 检查API密钥配置
        if not self.bailian_analyzer.api_key:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "API密钥未配置",
                "尚未配置百炼大模型API密钥，是否前往配置？\n\n您需要：\n1. 注册阿里云账号\n2. 开通百炼服务\n3. 获取API密钥\n4. 设置配置文件",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.show_api_config_help()
            return
        
        # 显示加载对话框
        self.loading_dialog = LoadingDialog(self)
        self.loading_dialog.show()
        
        # 异步执行分析
        self.bailian_analyzer.analyze_async(days=1)
    
    def show_api_config_help(self):
        """显示API配置帮助"""
        help_text = """📝 百炼大模型API配置指南

1. 访问阿里云官网注册账号
   https://www.aliyun.com/

2. 开通百炼平台服务
   https://help.aliyun.com/zh/bailian/

3. 获取API密钥
   - 进入百炼控制台
   - 点击左侧导航栏的"密钥管理"
   - 单击"创建API-KEY"
   - 复制生成的API密钥

4. 修改配置
   修改配置文件：config.json
   "DASHSCOPE_API_KEY": "your_api_key_here", # API密钥
   "MODEL_NAME": "model_name" # 模型名称
   
   模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models

5. 重启应用程序使配置生效
"""
        
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "API配置帮助", help_text)
    
    def on_analysis_started(self):
        """分析开始回调"""
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.update_progress(0, "开始分析...")
    
    def on_progress_updated(self, percentage: int, message: str):
        """进度更新回调"""
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.update_progress(percentage, message)
    
    def on_analysis_completed(self, result: dict):
        """分析完成回调"""
        # 关闭加载对话框
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.accept()
            del self.loading_dialog
        
        # 显示结果对话框
        if not hasattr(self, 'analysis_result_dialog'):
            self.analysis_result_dialog = AnalysisResultDialog(self)
        self.analysis_result_dialog.show_analysis_result(result)
        self.analysis_result_dialog.show()
        self.analysis_result_dialog.raise_()
        self.analysis_result_dialog.activateWindow()
    
    def on_analysis_error(self, error_message: str):
        """分析错误回调"""
        # 关闭加载对话框
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.reject()
            del self.loading_dialog
        
        # 显示错误信息
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "分析失败", f"AI分析过程中发生错误:\n\n{error_message}")

    def copy_uid_to_clipboard(self):
        """ 复制UID """
        clipboard = QApplication.clipboard()
        clipboard.setText(self.uid)
        # 可选：显示提示信息
        self.tray_icon.showMessage(
            "UID 已复制",
            f"UID {self.uid} 已复制到剪贴板",
            QSystemTrayIcon.MessageIcon.Information,
            1000
        )

    def set_online(self):
        """设置为在线状态"""
        self.is_online = True
        self.client.start()
        # 根据当前在线状态更新连接菜单项的可用性
        self.connect_action.setEnabled(self.is_online)
        self.tray_icon.showMessage(
            "状态变更",
            "已设置为在线状态",
            QSystemTrayIcon.MessageIcon.Information,
            1000
        )

    def set_offline(self):
        """设置为离线状态"""
        self.is_online = False
        self.client.stop(graceful=True)  # 优雅关闭
        # 根据当前在线状态更新连接菜单项的可用性
        self.connect_action.setEnabled(self.is_online)
        self.tray_icon.showMessage(
            "状态变更",
            "已设置为离线状态",
            QSystemTrayIcon.MessageIcon.Information,
            1000
        )

    def show_connect_dialog(self):
        """ 显示连接对话框 """
        dialog = QDialog(self)
        dialog.setWindowTitle("连接到目标")
        dialog.setFixedSize(300, 150)

        layout = QVBoxLayout(dialog)

        # 添加说明标签
        label = QLabel("请输入目标UID:")
        layout.addWidget(label)

        # 添加输入框
        uid_input = QLineEdit()
        uid_input.setPlaceholderText("输入6位UID")
        layout.addWidget(uid_input)

        # 添加连接按钮
        connect_btn = QPushButton("连接")
        layout.addWidget(connect_btn)

        # 连接按钮事件
        def on_connect():
            target_uid = uid_input.text().strip()
            self.connect_to_target(target_uid)
            dialog.accept()

        connect_btn.clicked.connect(on_connect)

        dialog.exec()

    def connect_to_target(self, target_uid):
        """ 连接到目标UID """
        # 这里实现实际的连接逻辑
        if target_uid == self.uid :
            self.tray_icon.showMessage(
                "警告",
                "危险！别这样干 (._.`)",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            return

        self.target_uid = target_uid
        self.client.bind(target_uid)
        # self.tray_icon.showMessage(
        #     "连接提示",
        #     f"尝试连接到目标UID: {target_uid}",
        #     QSystemTrayIcon.MessageIcon.Information,
        #     2000
        # )

    def update_target_status(self, status):
        """更新UID状态指示器"""
        if status == "bind offline":
            self.target_online = False
            text = "离线"
        elif status == "bind online":
            self.target_online = True
            text = "在线"
        elif status == "unbind":
            self.target_online = False
            self.target_uid = ""
            text = "未绑定"
        else:  # error
            self.target_online = False
            self.target_uid = ""
            text = "连接错误"

        self.connect_action.setText(f'连接（{self.target_uid} {text}）')

    def icon_activated(self, reason):
        """ 单击托盘图标切换显示/隐藏 """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            #
            self.toggle_window()

    def toggle_window(self):
        """显示/隐藏窗口"""
        if self.isHidden():
            self.show()
            self.activateWindow()
        else:
            self.hide()

    def switch_widget(self, idx: int, currentWidget):
        """切换窗口内容 切换Widget"""
        self.currentWidget = currentWidget
        self.stack.setCurrentIndex(idx)
        self.reBindKeyBoardListener()

    def switch_widget_gif(self, idx: int, path: str, currentWidget, loop_count):
        """GIF Widget使用，切换到Widget，并切换GIF内容"""
        self.currentWidget = currentWidget
        self.stack.setCurrentIndex(idx)
        self.currentWidget.switch_gif(path, loop_count)
        self.reBindKeyBoardListener()

    def quit_app(self):
        """退出应用程序（优化版）"""
        # 停止AI分析线程
        try:
            if hasattr(self, "bailian_analyzer") and hasattr(self.bailian_analyzer, "worker_thread"):
                worker = self.bailian_analyzer.worker_thread
                if worker and worker.isRunning():
                    worker.stop()
                    worker.wait(2000)  # 等待最多2秒
        except Exception as e:
            print(f"Warning: Error stopping analysis worker: {e}")
        
        # 停止后台线程
        try:
            if hasattr(self, "mouse_heatmap_tracker"):
                self.mouse_heatmap_tracker.stop()
        except Exception as e:
            print(f"Warning: Error stopping heatmap tracker: {e}")
        
        # 关闭缓存管理器
        try:
            from utils.DataCacheManager import shutdown_cache_manager
            shutdown_cache_manager()
        except Exception as e:
            print(f"Warning: Error shutting down cache manager: {e}")
            
        QApplication.quit()

    def closeEvent(self, event):
        """重写关闭事件，使窗口关闭时最小化到托盘"""
        # 隐藏窗口
        self.hide()
        # 在系统托盘显示提示信息
        self.tray_icon.showMessage(
            "busy with fish",
            "bye ~",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        # 忽略关闭事件，防止程序退出
        event.ignore()

    def reBindKeyBoardListener(self):
        """重新绑定键盘监听器，切换Widget时重新绑定"""
        self.trigger_key.disconnect()
        self.trigger_key.connect(self.currentWidget.animate)

    # ---------- 拖拽 start---------- #
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.edge_snap_timer.stop()

    def mouseMoveEvent(self, event):
        if self.drag_start_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_start_pos)

    def mouseReleaseEvent(self, _):
        self.drag_start_pos = None
        self.original_geom = self.frameGeometry()  # 更新基准
        self.edge_snap_timer.start()
    # ---------- 拖拽 end---------- #

    def snap_to_edge(self):
        """边缘吸附（优化版）"""
        if self.currentWidget.animating:  # 动画期间直接返回
            return
        self.edge_snap_timer.stop()
        geom = self.frameGeometry()
        screen = self.screen().availableGeometry()
        margin = SNAP_TO_EDGE_MARGIN
        x, y = geom.x(), geom.y()

        if abs(x) < margin:
            x = 0
        elif abs(x + geom.width() - screen.width()) < margin:
            x = screen.width() - geom.width()

        if abs(y) < margin:
            y = 0
        elif abs(y + geom.height() - screen.height()) < margin:
            y = screen.height() - geom.height()

        if (x, y) != (geom.x(), geom.y()):
            self.move(x, y)
        self.original_geom = self.frameGeometry()

    def on_key_press(self, _key):
        """按下键盘触发方法"""

        # 将 Key 对象转换为可序列化的字符串
        if isinstance(_key, keyboard.Key):
            key_value = _key.name
        else:
            key_value = _key.char

        # 记录按键
        self.keypressRecorder.record_keypress(key_value)
        if self.is_online and self.target_uid != "未连接" and self.target_online:
            # 在线模式，发送给对方
            self.client.on_key_press(key_value)
        else :
            # 离线线模式，自己触发
            if self.stack.currentIndex() == 1 :
                self.trigger_key.emit(_key)
            else:
                self.trigger_key.emit(None)
        #print(_key)

    def handle_remote_trigger(self, data):
        """处理远程触发的动画"""
        print(f"Remote trigger with data: {data}")
        self.currentWidget.animate(data)