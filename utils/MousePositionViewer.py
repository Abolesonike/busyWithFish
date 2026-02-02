import ctypes
import os
import sys
import time
from dataclasses import dataclass
from typing import Callable, Optional, Tuple


@dataclass(frozen=True)
class MousePosition:
    x: int
    y: int


class MousePositionViewer:
    """
    实时显示鼠标位置的工具类（Windows）。

    - 控制台模式：持续在同一行刷新坐标
    - 悬浮窗模式：PyQt6 置顶小窗显示坐标（适合 GUI 调试）
    """

    class _POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    _user32 = ctypes.windll.user32
    _GetCursorPos = _user32.GetCursorPos
    _GetCursorPos.argtypes = [ctypes.POINTER(_POINT)]
    _GetCursorPos.restype = ctypes.c_bool

    @classmethod
    def get_position(cls) -> MousePosition:
        """获取当前鼠标坐标（屏幕坐标系，左上角为 (0,0)）。"""
        pt = cls._POINT()
        ok = cls._GetCursorPos(ctypes.byref(pt))
        if not ok:
            raise OSError("GetCursorPos 调用失败")
        return MousePosition(int(pt.x), int(pt.y))

    @classmethod
    def watch_console(
        cls,
        interval_s: float = 0.05,
        on_change: Optional[Callable[[MousePosition], None]] = None,
    ) -> None:
        """
        在控制台实时显示鼠标坐标。

        - interval_s: 刷新间隔（秒）
        - on_change: 可选回调，仅当坐标变化时触发
        """
        last: Optional[MousePosition] = None
        try:
            while True:
                pos = cls.get_position()
                if pos != last:
                    if on_change is not None:
                        on_change(pos)
                    else:
                        # \r 回到行首并覆盖输出；末尾补空格避免残留字符
                        sys.stdout.write(f"\rMouse: ({pos.x}, {pos.y})      ")
                        sys.stdout.flush()
                    last = pos
                time.sleep(max(interval_s, 0.001))
        except KeyboardInterrupt:
            sys.stdout.write("\n")
            sys.stdout.flush()

    @classmethod
    def create_overlay_window(
        cls,
        interval_ms: int = 50,
        anchor: str = "top-left",
        offset: Tuple[int, int] = (20, 20),
    ):
        """
        创建一个 PyQt6 悬浮窗（置顶、无边框）实时显示坐标。

        返回 QWidget 实例（你负责 show() / close()）。
        """
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication

        class _Overlay(QWidget):
            def __init__(self):
                super().__init__()
                self.setWindowFlags(
                    Qt.WindowType.WindowStaysOnTopHint
                    | Qt.WindowType.FramelessWindowHint
                    | Qt.WindowType.Tool
                )
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

                self.label = QLabel("Mouse: (0, 0)")
                self.label.setStyleSheet(
                    "color: white;"
                    "background-color: rgba(0, 0, 0, 160);"
                    "border-radius: 8px;"
                    "padding: 8px 10px;"
                    "font-size: 12px;"
                    "font-weight: bold;"
                )

                lay = QVBoxLayout(self)
                lay.setContentsMargins(0, 0, 0, 0)
                lay.addWidget(self.label)

                self._timer = QTimer(self)
                self._timer.setInterval(max(int(interval_ms), 10))
                self._timer.timeout.connect(self._tick)
                self._timer.start()

                self._place(anchor, offset)

            def _place(self, anchor_: str, offset_: Tuple[int, int]):
                app = QApplication.instance()
                screen = (app.primaryScreen() if app else None)
                geom = (screen.availableGeometry() if screen else None)
                if geom is None:
                    self.move(offset_[0], offset_[1])
                    return

                self.adjustSize()
                w, h = self.width(), self.height()
                ox, oy = offset_

                if anchor_ == "top-left":
                    x, y = geom.x() + ox, geom.y() + oy
                elif anchor_ == "top-right":
                    x, y = geom.x() + geom.width() - w - ox, geom.y() + oy
                elif anchor_ == "bottom-left":
                    x, y = geom.x() + ox, geom.y() + geom.height() - h - oy
                elif anchor_ == "bottom-right":
                    x, y = geom.x() + geom.width() - w - ox, geom.y() + geom.height() - h - oy
                else:
                    x, y = geom.x() + ox, geom.y() + oy

                self.move(x, y)

            def _tick(self):
                pos = cls.get_position()
                self.label.setText(f"Mouse: ({pos.x}, {pos.y})")
                self.adjustSize()

        return _Overlay()


def _main():
    """
    直接运行本文件时：
    - 默认进入控制台模式（按 Ctrl+C 退出）
    - 若设置环境变量 MOUSE_OVERLAY=1，则启动悬浮窗模式
    """
    overlay = os.environ.get("MOUSE_OVERLAY", "").strip() == "1"
    if not overlay:
        MousePositionViewer.watch_console()
        return

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = MousePositionViewer.create_overlay_window(anchor="top-left", offset=(20, 20))
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    _main()

