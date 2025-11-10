from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import QLabel

from utils.systemUtils import get_resource_path


class GifLabel(QLabel):
    loop_count = 15  # 动画分割次数

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScaledContents(True)

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

        # ---- 初始停到第一段第一帧 ----
        self.movie.jumpToFrame(0)
        self.movie.setPaused(True)

    # ---- 切换 ----
    def switch_gif(self, path, loop_count):
        # 设置参数
        self.total = self.movie.frameCount()
        self.loop_count = loop_count
        self.cur_seg = 0
        self.seg_size = self.total // self.loop_count
        # 加载图片
        self._load(path)
        # 播放第一帧
        self.movie.jumpToFrame(0)

    # ---- 加载 ----
    def _load(self, path):
        path = get_resource_path(path)
        self.movie = QMovie(path)
        self.setMovie(self.movie)

    # ---- 播放 ----
    def animate(self):
        if self.playing:  # 还没播完，直接忽略
            return
        self._play_next_segment()

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
            self.playing = False
            # 段索引 +1，循环
            self.cur_seg = (self.cur_seg + 1) % self.loop_count