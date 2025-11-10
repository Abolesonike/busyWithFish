from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QAction
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication, QSystemTrayIcon, QMenu
from pynput import keyboard

from character.GifLabel import GifLabel
from utils.systemUtils import get_resource_path

SNAP_TO_EDGE_MARGIN = 50  # 边缘吸附范围
TRAY_ICON_IMG = 'resource/icon/fish.ico' # 任务栏图标

class Win(QWidget):
    trigger_key = pyqtSignal()
    drag_start_pos: QPoint | None = None

    def __init__(self):
        super().__init__()

        # 窗口设置
        self.setWindowTitle("busy with fish")
        self.setFixedSize(100, 100)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 加载GIF
        self.label = GifLabel()
        lay = QVBoxLayout(self)
        lay.addWidget(self.label)

        # 键盘监听
        self.trigger_key.connect(self.label.animate)
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

        # 初始位置：屏幕右下角
        scr = QApplication.primaryScreen().geometry()
        self.move(scr.width() - self.width(),
                  scr.height() - self.height() - 50)
        self.original_geom = self.frameGeometry()

        # 边缘吸附
        self.edge_snap_timer = QTimer(self)
        self.edge_snap_timer.setInterval(200)
        self.edge_snap_timer.timeout.connect(self.snap_to_edge)

        # 托盘任务图标
        img_path = get_resource_path(TRAY_ICON_IMG)
        self.pixmap = QPixmap(str(img_path))

        # 创建系统托盘图标
        self.create_tray_icon()
        self.tray_icon.show()

        # 动画是否正在运行
        self._animating = False


    # ---------- 系统托盘 ----------
    def create_tray_icon(self):
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self.pixmap))

        # 创建托盘菜单
        self.tray_menu = QMenu(self)

        # 显示/隐藏动作
        self.toggle_action = QAction("显示/隐藏", self)
        self.toggle_action.triggered.connect(self.toggle_window)
        self.tray_menu.addAction(self.toggle_action)

        # 分隔线
        self.tray_menu.addSeparator()

        # 角色切换菜单
        self.character_menu = QMenu("切换", self)
        self.tray_menu.addMenu(self.character_menu)

        # 添加角色选项
        self.wooden_fish_action = QAction("电子木鱼", self)
        self.wooden_fish_action.triggered.connect(
            lambda: self.label.switch_gif("resource/image/woodfish.png", 8))
        self.character_menu.addAction(self.wooden_fish_action)

        self.desktop_pet_action = QAction("pop cat", self)
        self.desktop_pet_action.triggered.connect(
            lambda: self.label.switch_gif("resource/gif/tsk.gif", 8))
        self.character_menu.addAction(self.desktop_pet_action)

        self.zen_circle_action = QAction("铁山靠", self)
        self.zen_circle_action.triggered.connect(
            lambda: self.label.switch_gif("resource/gif/tsk.gif", 16))
        self.character_menu.addAction(self.zen_circle_action)

        # 分隔线
        self.tray_menu.addSeparator()

        # 退出动作
        self.quit_action = QAction("退出", self)
        self.quit_action.triggered.connect(self.quit_app)
        self.tray_menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.icon_activated)

    def icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # 单击托盘图标切换显示/隐藏
            self.toggle_window()

    # 显示/隐藏窗口
    def toggle_window(self):
        if self.isHidden():
            self.show()
            self.activateWindow()
        else:
            self.hide()

    def quit_app(self):
        # 退出应用程序
        QApplication.quit()

    # 重写关闭事件，使窗口关闭时最小化到托盘
    def closeEvent(self, event):
        # 隐藏窗口
        self.hide()
        # 在系统托盘显示提示信息
        self.tray_icon.showMessage(
            "电子木鱼",
            "程序已最小化到系统托盘，双击图标可恢复窗口",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        # 忽略关闭事件，防止程序退出
        event.ignore()

    # ---------- 拖拽 start----------
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
    # ---------- 拖拽 end----------

    # ---------- 边缘吸附 ----------
    def snap_to_edge(self):
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

    # ---------- 键盘 ----------
    def on_key_press(self, _key):
        self.trigger_key.emit()