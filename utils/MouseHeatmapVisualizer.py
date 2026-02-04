from datetime import date
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QScrollArea,
    QDateEdit,
)

from utils.MouseHeatmapTracker import OptimizedMouseHeatmapTracker as MouseHeatmapTracker  # 使用优化版本


class MouseHeatmapDialog(QDialog):
    """
    鼠标热力图可视化弹窗（类似键盘按键可视化）。

    - 默认展示"今天"的热力图
    - 可通过日期选择器从 data 目录中查看历史数据
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("鼠标热力图")
        self.setModal(False)
        # 默认窗口缩小一半，避免占用过多屏幕空间
        self.resize(400, 250)

        # 原始热力图 Pixmap（用于根据弹窗大小自适应缩放）
        self._base_pixmap: QPixmap | None = None

        main_layout = QVBoxLayout(self)

        # 顶部区域：日期选择 + 刷新按钮
        header_layout = QHBoxLayout()
        self.date_label = QLabel("日期：")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())
        # 当日期改变时自动刷新热力图
        self.date_edit.dateChanged.connect(self.refresh_image)
        # 禁止键盘输入，但仍允许通过日历选择
        self.date_edit.lineEdit().setReadOnly(True)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_image)

        header_layout.addWidget(self.date_label)
        header_layout.addWidget(self.date_edit)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(header_layout)

        # 中间：滚动区域展示图片
        self.image_label = QLabel("暂无数据")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("color: gray;")

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.image_label)

        main_layout.addWidget(self.scroll)

        # 默认加载"今天"数据
        self.refresh_image()
        # 延迟一次缩放，确保第一次打开时根据最终布局尺寸适配
        QTimer.singleShot(0, self._update_scaled_pixmap)

    def showEvent(self, event):
        """每次重新打开弹窗时，自动切回今天的数据。"""
        super().showEvent(event)
        self.date_edit.setDate(date.today())
        self.refresh_image()

    def resizeEvent(self, event):
        """窗口大小变化时，自适应缩放当前热力图。"""
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def refresh_image(self):
        """根据当前选择的日期重新生成并加载热力图。"""
        day_str = self.date_edit.date().toString("yyyy-MM-dd")

        try:
            meta, grid = MouseHeatmapTracker.load_day(day_str, data_root="data/mouse_heatmap", cell_size=48)
        except FileNotFoundError:
            self._show_no_data()
            return
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载热力图数据失败：{e}")
            self._show_no_data()
            return

        # 如果没有任何有效数据
        has_value = any(any(v > 0 for v in row) for row in grid)
        if not has_value:
            self._show_no_data()
            return

        # 直接在内存中渲染 QImage，而不是落盘为 PNG
        img = MouseHeatmapTracker.render_heatmap_qimage(
            meta,
            grid,
            blur_radius_cells=1,
            blur_passes=1,
            use_log=True,
            gamma=0.6,
            upscale_to_screen=False,  # 先生成网格大小，再按弹窗尺寸缩放
            background_rgba=(0, 0, 0, 0),
            min_visible_t=0.04,
            max_alpha=220,
        )

        pix = QPixmap.fromImage(img)
        if pix.isNull():
            self._show_no_data()
            return
        # 记录原始图像，后续按窗口大小自适应缩放
        self._base_pixmap = pix
        self._update_scaled_pixmap()

    def _show_no_data(self):
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("暂无鼠标热力数据")
        self.image_label.setStyleSheet("color: gray;")
        self._base_pixmap = None

    def _update_scaled_pixmap(self):
        """根据当前滚动区域大小重新缩放热力图。"""
        if not isinstance(self._base_pixmap, QPixmap) or self._base_pixmap.isNull():
            return

        viewport_size = self.scroll.viewport().size()
        if viewport_size.width() <= 0 or viewport_size.height() <= 0:
            # 还没布局完成，直接用原始图
            self.image_label.setPixmap(self._base_pixmap)
            self.image_label.setScaledContents(False)
            return

        scaled = self._base_pixmap.scaled(
            viewport_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)
        self.image_label.setScaledContents(False)