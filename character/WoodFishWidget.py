import sys

from PyQt6.QtCore import QPropertyAnimation, Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel

from character.PWidget import PWidget
from utils.KeypressRecorder import KeypressRecorder
from utils.systemUtils import get_resource_path

# --------------- 可调参数 ---------------
# 木鱼图片（透明 PNG）
WOOD_FISH_IMG = 'resource/image/woodfish.png'
# 木鱼音效
WOOD_FISH_SND = 'woodfish.wav'
# 图片缩放（0~1）
SCALE = 0.2
# 按下时下沉像素
DOWN_OFFSET = 8
# 回弹动画时长
BOUNCE_BACK_MS = 80
# ---------------------------------------

class WoodFishWidget(PWidget):

    def __init__(self):
        super().__init__()

        # --- 功德计数 ---
        self.recorder = KeypressRecorder()
        self.merit = self.recorder.get_daily_merit()  # 从数据中读取今天的功德值
        self.merit_label = QLabel(self)  # 专门显示文字
        self.merit_label.setStyleSheet(
            "color:#FFD700;font-size:14px;font-weight:bold;background:transparent;"
        )
        self.merit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.merit_label.hide()

        # 加载木鱼图片
        img_path = get_resource_path(WOOD_FISH_IMG)
        self.pixmap = QPixmap(str(img_path))
        if self.pixmap.isNull():
            sys.exit(f'图片加载失败：{img_path}')

        # 按缩放设置窗口大小
        self.pixmap = self.pixmap.scaled(
            int(self.pixmap.width() * SCALE),
            int(self.pixmap.height() * SCALE),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setFixedSize(self.pixmap.width(), self.pixmap.height() + 20)  # 留 30 px 给文字

        # 木鱼标签 —— 完全居中，不再移动它
        self.label = QLabel(self)
        self.label.setPixmap(self.pixmap)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setScaledContents(False)  # 让图自动缩放到 QLabel 大小
        # 放在窗口下半部（30 px 留给文字）
        self.label.setGeometry(0, 20, self.pixmap.width(), self.pixmap.height())

        # 3. 功德标签放在顶部 30 px 区域，绝对不再被裁
        self.merit_label.raise_()  # 保证在最上层
        self.merit_label.move(
            (self.width() - self.merit_label.width()) // 2,
            10
        )

        # 动画对象：整个窗口（self）
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(BOUNCE_BACK_MS)
        self.original_geom = self.frameGeometry()  # 记录原始位置

    # ---------- 动画开始 ----------
    def animate(self, data=None):
        if self.animation.state() == QPropertyAnimation.State.Running:
            return
        self.animating = True  # 锁住吸附
        self.show_merit(data)
        down_geom = self.original_geom.translated(0, DOWN_OFFSET)
        self.animation.setStartValue(self.original_geom)
        self.animation.setEndValue(down_geom)
        self.animation.start()
        self.animation.finished.connect(self.fish_up)

    # ---------- 动画回弹 ----------
    def fish_up(self):
        self.animation.finished.disconnect(self.fish_up)
        self.animation.setStartValue(self.frameGeometry())
        self.animation.setEndValue(self.original_geom)
        self.animation.start()
        # 等动画彻底结束再允许吸附（多加 50 ms 保险）
        QTimer.singleShot(self.animation.duration() + 50, self._release_anim_lock)

    # ---------- 显示功德 ----------
    @pyqtSlot()
    def show_merit(self, data=None):
        self.merit += 1
        if data:
            self.merit_label.setText(f"{data}\n功德 +{self.merit}")
        else:
            self.merit_label.setText(f"功德 +{self.merit}")
        self.merit_label.adjustSize()
        # 居中放在窗口最顶部
        self.merit_label.move((self.width() - self.merit_label.width()) // 2, 10)
        self.merit_label.show()
        QTimer.singleShot(800, self.merit_label.hide)  # 1.5 秒后消失