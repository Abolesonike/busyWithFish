import json
import math
import os
import threading
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils.MousePositionViewer import MousePositionViewer


@dataclass(frozen=True)
class HeatmapMeta:
    version: int
    day: str
    screen_width: int
    screen_height: int
    cell_size: int
    grid_width: int
    grid_height: int
    unit: str  # "ms"

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "day": self.day,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "cell_size": self.cell_size,
            "grid_width": self.grid_width,
            "grid_height": self.grid_height,
            "unit": self.unit,
        }

    @staticmethod
    def from_dict(d: dict) -> "HeatmapMeta":
        return HeatmapMeta(
            version=int(d["version"]),
            day=str(d["day"]),
            screen_width=int(d["screen_width"]),
            screen_height=int(d["screen_height"]),
            cell_size=int(d["cell_size"]),
            grid_width=int(d["grid_width"]),
            grid_height=int(d["grid_height"]),
            unit=str(d["unit"]),
        )


class MouseHeatmapTracker:
    """
    鼠标热力图统计器（按天 JSON 聚合，使用停留时间 ms）。

    存储结构（默认 data/mouse_heatmap/YYYY-MM-DD/cell_XX/）：
    - meta.json：分辨率、网格参数等
    - grid.json：当天累计网格（二维数组，单位 ms）
    """

    META_FILENAME = "meta.json"
    GRID_FILENAME = "grid.json"
    VERSION = 1

    def __init__(
        self,
        cell_size: int = 48,
        data_root: Optional[str] = None,
        sample_interval_ms: int = 50,
        flush_interval_s: float = 30.0,
    ):
        self.cell_size = int(cell_size)
        self.data_root = Path(data_root) if data_root else self._default_data_root()
        self.sample_interval_ms = max(int(sample_interval_ms), 10)
        self.flush_interval_s = max(float(flush_interval_s), 1.0)

        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # (gx, gy) -> total_ms
        self._acc: Dict[Tuple[int, int], int] = {}
        # 本周期变化的增量： (gx, gy) -> delta_ms
        self._dirty: Dict[Tuple[int, int], int] = {}

        self._meta: Optional[HeatmapMeta] = None
        self._day_dir: Optional[Path] = None

    @staticmethod
    def _get_screen_size() -> Tuple[int, int]:
        # Windows：GetSystemMetrics(0/1) 获取主屏分辨率（像素）
        import ctypes

        user32 = ctypes.windll.user32
        w = int(user32.GetSystemMetrics(0))
        h = int(user32.GetSystemMetrics(1))
        return w, h

    @staticmethod
    def _today_str() -> str:
        return str(date.today())

    @staticmethod
    def _default_data_root() -> Path:
        """
        默认落盘路径：项目相对目录 data/mouse_heatmap

        与键盘记录 data/ 保持一致，便于打包一起分发。
        """
        return Path("data") / "mouse_heatmap"

    def _day_dir_for(self, day: str) -> Path:
        # 同一天允许不同 cell_size 并存，避免 meta 冲突
        return self.data_root / day / f"cell_{self.cell_size}"

    def _ensure_day_files(self) -> None:
        day = self._today_str()
        screen_w, screen_h = self._get_screen_size()
        grid_w = (screen_w + self.cell_size - 1) // self.cell_size
        grid_h = (screen_h + self.cell_size - 1) // self.cell_size

        day_dir = self._day_dir_for(day)
        day_dir.mkdir(parents=True, exist_ok=True)

        meta_path = day_dir / self.META_FILENAME
        if meta_path.exists():
            loaded = HeatmapMeta.from_dict(json.loads(meta_path.read_text(encoding="utf-8")))
            if (
                loaded.screen_width != screen_w
                or loaded.screen_height != screen_h
                or loaded.cell_size != self.cell_size
            ):
                # 分辨率已变化：备份旧 grid 文件，重新开始当天的统计，避免程序崩溃
                grid_path = day_dir / self.GRID_FILENAME
                if grid_path.exists():
                    backup = grid_path.with_name(
                        f"grid_{loaded.screen_width}x{loaded.screen_height}.json"
                    )
                    try:
                        grid_path.rename(backup)
                    except OSError:
                        pass
                meta = HeatmapMeta(
                    version=self.VERSION,
                    day=day,
                    screen_width=screen_w,
                    screen_height=screen_h,
                    cell_size=self.cell_size,
                    grid_width=grid_w,
                    grid_height=grid_h,
                    unit="ms",
                )
                meta_path.write_text(
                    json.dumps(meta.to_dict(), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            else:
                meta = loaded
        else:
            meta = HeatmapMeta(
                version=self.VERSION,
                day=day,
                screen_width=screen_w,
                screen_height=screen_h,
                cell_size=self.cell_size,
                grid_width=grid_w,
                grid_height=grid_h,
                unit="ms",
            )
            meta_path.write_text(json.dumps(meta.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

        self._meta = meta
        self._day_dir = day_dir

    def start(self) -> None:
        """开始后台采样与定时写入。"""
        with self._lock:
            if self._running:
                return
            self._ensure_day_files()
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, name="MouseHeatmapTracker", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """停止采样，并强制 flush 一次。"""
        with self._lock:
            self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self.flush()

    def flush(self) -> None:
        """将本周期的增量合并到当天 grid.json 中。"""
        with self._lock:
            if not self._dirty:
                return
            if self._day_dir is None or self._meta is None:
                self._ensure_day_files()

            items = [(gx, gy, int(delta)) for (gx, gy), delta in self._dirty.items() if delta > 0]
            self._dirty.clear()

        if not items:
            return

        grid_path = self._day_dir / self.GRID_FILENAME

        # 读取已有 grid（若不存在则初始化为全 0）
        if grid_path.exists():
            try:
                raw = json.loads(grid_path.read_text(encoding="utf-8"))
                grid = raw.get("grid_ms")
                if (
                    not isinstance(grid, list)
                    or len(grid) != self._meta.grid_height
                    or any(len(row) != self._meta.grid_width for row in grid)
                ):
                    raise ValueError("invalid grid size")
            except Exception:
                grid = [[0 for _ in range(self._meta.grid_width)] for _ in range(self._meta.grid_height)]
        else:
            grid = [[0 for _ in range(self._meta.grid_width)] for _ in range(self._meta.grid_height)]

        # 应用增量
        for gx, gy, delta in items:
            if 0 <= gx < self._meta.grid_width and 0 <= gy < self._meta.grid_height:
                grid[gy][gx] += delta

        # 覆盖写回 JSON
        payload = {
            "version": self.VERSION,
            "day": self._meta.day,
            "cell_size": self._meta.cell_size,
            "unit": self._meta.unit,
            "grid_ms": grid,
        }
        grid_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _run_loop(self) -> None:
        # 采样归因策略：
        # 将 (last_t, now_t] 这段时间的停留 ms 计入“当前采样到的格子”。
        # 这样视觉上更贴近你看到的鼠标位置，避免快速移动时热区明显滞后。
        last_t = time.perf_counter()
        next_flush = time.monotonic() + self.flush_interval_s

        while True:
            with self._lock:
                if not self._running:
                    break

            time.sleep(self.sample_interval_ms / 1000.0)

            now_t = time.perf_counter()
            dt_ms = int(max((now_t - last_t) * 1000.0, 0.0))
            if dt_ms <= 0:
                continue

            pos = MousePositionViewer.get_position()
            cell = self._pos_to_cell(pos.x, pos.y)
            self._add_time(cell, dt_ms)
            last_t = now_t

            if time.monotonic() >= next_flush:
                self.flush()
                next_flush = time.monotonic() + self.flush_interval_s

    def _pos_to_cell(self, x: int, y: int) -> Tuple[int, int]:
        assert self._meta is not None
        gx = max(0, min(self._meta.grid_width - 1, x // self.cell_size))
        gy = max(0, min(self._meta.grid_height - 1, y // self.cell_size))
        return gx, gy

    def _add_time(self, cell: Tuple[int, int], dt_ms: int) -> None:
        with self._lock:
            self._acc[cell] = self._acc.get(cell, 0) + dt_ms
            self._dirty[cell] = self._dirty.get(cell, 0) + dt_ms

    # --------- 读取与绘制（供测试/工具使用） ---------
    @classmethod
    def load_day(
        cls,
        day: str,
        data_root: Optional[str] = None,
        cell_size: int = 48,
    ) -> Tuple[HeatmapMeta, List[List[int]]]:
        """加载某天的 grid.json 并返回网格（单位 ms）。"""
        root = Path(data_root) if data_root else cls._default_data_root()
        day_dir = root / day / f"cell_{int(cell_size)}"
        meta_path = day_dir / cls.META_FILENAME
        grid_path = day_dir / cls.GRID_FILENAME

        meta = HeatmapMeta.from_dict(json.loads(meta_path.read_text(encoding="utf-8")))
        grid = [[0 for _ in range(meta.grid_width)] for _ in range(meta.grid_height)]

        if not grid_path.exists():
            return meta, grid

        raw = json.loads(grid_path.read_text(encoding="utf-8"))
        grid_raw = raw.get("grid_ms")
        if (
            isinstance(grid_raw, list)
            and len(grid_raw) == meta.grid_height
            and all(isinstance(row, list) and len(row) == meta.grid_width for row in grid_raw)
        ):
            for y in range(meta.grid_height):
                for x in range(meta.grid_width):
                    try:
                        grid[y][x] = int(grid_raw[y][x])
                    except Exception:
                        grid[y][x] = 0
        return meta, grid

    @staticmethod
    def _box_blur(grid: List[List[float]], radius: int = 1, passes: int = 1) -> List[List[float]]:
        """简单盒式模糊（渲染阶段用，降低颗粒感）。"""
        if radius <= 0 or passes <= 0:
            return grid
        h = len(grid)
        w = len(grid[0]) if h else 0

        cur = [row[:] for row in grid]
        for _ in range(passes):
            nxt = [[0.0 for _ in range(w)] for _ in range(h)]
            for y in range(h):
                y0 = max(0, y - radius)
                y1 = min(h - 1, y + radius)
                for x in range(w):
                    x0 = max(0, x - radius)
                    x1 = min(w - 1, x + radius)
                    s = 0.0
                    c = 0
                    for yy in range(y0, y1 + 1):
                        row = cur[yy]
                        for xx in range(x0, x1 + 1):
                            s += row[xx]
                            c += 1
                    nxt[y][x] = s / c if c else 0.0
            cur = nxt
        return cur

    @staticmethod
    def _colormap_viridis_like(t: float) -> Tuple[int, int, int]:
        """t in [0,1] -> RGB（简化 viridis 风格，够用且好看）"""
        t = max(0.0, min(1.0, t))
        stops = [
            (0.00, (68, 1, 84)),
            (0.25, (59, 82, 139)),
            (0.50, (33, 145, 140)),
            (0.75, (94, 201, 98)),
            (1.00, (253, 231, 37)),
        ]
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t <= t1:
                if t1 == t0:
                    return c1
                k = (t - t0) / (t1 - t0)
                r = int(c0[0] + (c1[0] - c0[0]) * k)
                g = int(c0[1] + (c1[1] - c0[1]) * k)
                b = int(c0[2] + (c1[2] - c0[2]) * k)
                return r, g, b
        return stops[-1][1]

    @classmethod
    def render_heatmap_qimage(
        cls,
        meta: HeatmapMeta,
        grid_ms: List[List[int]],
        blur_radius_cells: int = 1,
        blur_passes: int = 2,
        use_log: bool = True,
        gamma: float = 0.6,
        upscale_to_screen: bool = True,
        background_rgba: Tuple[int, int, int, int] = (0, 0, 0, 0),
        min_visible_t: float = 0.03,
        max_alpha: int = 220,
    ):
        """
        将网格数据渲染成 PNG。
        - blur_*：渲染阶段平滑（不影响存储）
        - use_log/gamma：让层次更丰富
        - upscale_to_screen：将网格图放大到屏幕分辨率输出（更直观）
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QColor, QImage

        h = meta.grid_height
        w = meta.grid_width

        # 转 float + 轻微模糊
        grid_f: List[List[float]] = [[float(grid_ms[y][x]) for x in range(w)] for y in range(h)]
        grid_f = cls._box_blur(grid_f, radius=blur_radius_cells, passes=blur_passes)

        vmax = max((grid_f[y][x] for y in range(h) for x in range(w)), default=0.0)
        if vmax <= 0.0:
            img = QImage(
                meta.screen_width if upscale_to_screen else w,
                meta.screen_height if upscale_to_screen else h,
                QImage.Format.Format_ARGB32,
            )
            img.fill(QColor(*background_rgba))
            return img

        # 先生成网格尺寸图，再按需放大
        base = QImage(w, h, QImage.Format.Format_ARGB32)
        base.fill(QColor(*background_rgba))
        for y in range(h):
            for x in range(w):
                v = grid_f[y][x]
                t = v / vmax
                if use_log:
                    # t' = log(1 + a*t) / log(1+a)，a 控制对比度
                    a = 40.0
                    t = math.log1p(a * t) / math.log1p(a)
                t = pow(max(0.0, min(1.0, t)), gamma)
                # 低热度直接透明，避免“整屏泛色”
                if t < min_visible_t:
                    continue
                r, g, b = cls._colormap_viridis_like(t)
                alpha = int(max(0.0, min(1.0, (t - min_visible_t) / (1.0 - min_visible_t))) * max_alpha)
                base.setPixelColor(x, y, QColor(r, g, b, alpha))

        if upscale_to_screen:
            # 平滑放大：减少像素化观感
            img = base.scaled(
                meta.screen_width,
                meta.screen_height,
                aspectRatioMode=Qt.AspectRatioMode.IgnoreAspectRatio,
                transformMode=Qt.TransformationMode.SmoothTransformation,
            )
        else:
            img = base

        return img

    @classmethod
    def render_heatmap_png(
        cls,
        meta: HeatmapMeta,
        grid_ms: List[List[int]],
        out_path: str,
        blur_radius_cells: int = 1,
        blur_passes: int = 2,
        use_log: bool = True,
        gamma: float = 0.6,
        upscale_to_screen: bool = True,
        background_rgba: Tuple[int, int, int, int] = (0, 0, 0, 0),
        min_visible_t: float = 0.03,
        max_alpha: int = 220,
    ) -> None:
        """保留 PNG 接口（用于单独导出），内部复用 QImage 渲染。"""
        img = cls.render_heatmap_qimage(
            meta,
            grid_ms,
            blur_radius_cells=blur_radius_cells,
            blur_passes=blur_passes,
            use_log=use_log,
            gamma=gamma,
            upscale_to_screen=upscale_to_screen,
            background_rgba=background_rgba,
            min_visible_t=min_visible_t,
            max_alpha=max_alpha,
        )
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path)

