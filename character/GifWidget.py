from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import QLabel, QVBoxLayout

from character.PWidget import PWidget
from utils.systemUtils import get_resource_path


class GifWidget(PWidget):
    loop_count = 15  # 动画分割次数

    def __init__(self):
        super().__init__()
        # 用 QLabel 做画布
        self.label = QLabel(self)
        self.label.setScaledContents(True)

        # ---- 键标签 ----
        self.key_label = QLabel(self)
        self.key_label.setStyleSheet(
            "color:#FFD700;font-size:24px;font-weight:bold;background:transparent;"
        )
        self.key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_label.hide()

        # 加载图片
        self.idx = 0
        self._load("resource/gif/tsk.gif")

        # 动画分割
        self.total = self.movie.frameCount()  # 总帧数
        self.seg_size = self.total // self.loop_count  # 每段长度
        self.cur_seg = 0  # 当前段 0 ~ loop_count

        # ---- 轮询定时器：20 ms 检查一次播到哪儿 ----
        self.poller = QTimer(self)
        self.poller.setInterval(20)
        self.poller.timeout.connect(self._check_stop)
        self.playing = False  # 是否正在播放

        # 设置标签大小和位置，使它们重叠
        self.setFixedSize(130, 130)  # 设置窗口大小
        self.label.setGeometry(0, 0, 130, 130)  # GIF 标签充满整个窗口
        self.key_label.setGeometry(0, 0, 130, 130)  # 键标签充满整个窗口，与 GIF 标签重叠

        # 确保键标签在最上层
        self.key_label.raise_()

        # ---- 初始停到第一段第一帧 ----
        self.movie.jumpToFrame(0)
        self.movie.setPaused(True)

    # ---- 切换 ----
    def switch_gif(self, path, loop_count):
        # 设置参数
        self.loop_count = loop_count
        self.cur_seg = 0
        # 加载图片
        self._load(path)
        # 计算总帧数和每段长度
        self.total = self.movie.frameCount()
        self.seg_size = self.total // self.loop_count
        # 播放第一帧
        self.movie.jumpToFrame(0)

    # ---- 加载 ----
    def _load(self, path):
        path = get_resource_path(path)
        self.movie = QMovie(path)
        self.label.setMovie(self.movie)

    # ---- 播放 ----
    def animate(self, data=None):
        if self.playing:  # 还没播完，直接忽略
            return
        # 每次播放都从第一段开始
        self.cur_seg = 0
        # 显示敲击的键
        key_text = self._get_key_text(data)
        self.key_label.setText(key_text)
        self.key_label.show()
        self.key_label.raise_()  # 确保在最上层
        self._play_next_segment()

    # ---- 获取键的友好文本表示 ----
    def _get_key_text(self, key):
        if not key:
            return ""
        try:
            # 尝试获取字符表示
            return key.char
        except AttributeError:
            # 对于特殊键，返回其名称的首字母大写形式
            return str(key).replace("Key.", "").capitalize()

    # ---- 播放下一段 ----
    def _play_next_segment(self):
        start = self.cur_seg * self.seg_size
        end   = (self.cur_seg + 1) * self.seg_size
        if self.cur_seg == self.loop_count - 1:        # 最后一段可能多几帧
            end = self.total

        self.playing = True
        self.poller.start()          # 启动轮询
        self.movie.jumpToFrame(start)
        self.movie.setPaused(False)  # 真正开始播放

        # 保存边界，供轮询函数使用
        self._end_frame = end - 1

    # ---- 轮询：到达段末就停 ----
    def _check_stop(self):
        if self.movie.currentFrameNumber() >= self._end_frame:
            self.movie.setPaused(True)
            self.poller.stop()
            # 检查是否还有下一段
            if self.cur_seg < self.loop_count - 1:
                # 播放下一段
                self.cur_seg += 1
                self._play_next_segment()
            else:
                # 所有段都播放完毕
                self.playing = False
                # 隐藏键标签
                self.key_label.hide()
                # 回到第一帧
                self.movie.jumpToFrame(0)