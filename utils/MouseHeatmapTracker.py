import json
import math
import os
import threading
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Deque
from collections import deque

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
    unit: str

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


class OptimizedMouseHeatmapTracker:
    """
    优化版鼠标热力图追踪器
    
    性能优化要点：
    1. 内存缓冲池：减少频繁内存分配
    2. 智能采样：只在鼠标移动时采样
    3. 增量更新：避免重复计算
    4. 分层存储：内存+磁盘双层缓存
    """
    
    META_FILENAME = "meta.json"
    GRID_FILENAME = "grid.json"
    VERSION = 1
    
    def __init__(
        self,
        cell_size: int = 48,
        data_root: Optional[str] = None,
        max_buffer_size: int = 1000,  # 内存缓冲最大条目数
        flush_threshold: int = 500,    # 缓冲达到此数量时自动刷盘
        inactive_timeout: float = 2.0  # 鼠标静止超时时间(秒)
    ):
        self.cell_size = int(cell_size)
        self.data_root = Path(data_root) if data_root else Path("data") / "mouse_heatmap"
        self.max_buffer_size = max_buffer_size
        self.flush_threshold = flush_threshold
        self.inactive_timeout = inactive_timeout
        
        # 线程安全
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # 内存缓冲区
        self._buffer: Deque[Tuple[int, int, int]] = deque(maxlen=max_buffer_size)  # (gx, gy, duration_ms)
        self._current_cell: Optional[Tuple[int, int]] = None
        self._last_active_time: float = 0.0
        
        # 累计数据（用于快速查询）
        self._acc: Dict[Tuple[int, int], int] = {}
        
        # 元数据
        self._meta: Optional[HeatmapMeta] = None
        self._day_dir: Optional[Path] = None
        
        # 性能统计
        self._stats = {
            'samples_collected': 0,
            'flush_operations': 0,
            'buffer_hits': 0,
            'disk_reads': 0
        }
    
    @staticmethod
    def _get_screen_size() -> Tuple[int, int]:
        import ctypes
        user32 = ctypes.windll.user32
        return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
    
    def _ensure_day_files(self) -> None:
        """确保当日文件结构存在"""
        day = str(date.today())
        screen_w, screen_h = self._get_screen_size()
        grid_w = math.ceil(screen_w / self.cell_size)
        grid_h = math.ceil(screen_h / self.cell_size)
        
        day_dir = self.data_root / day / f"cell_{self.cell_size}"
        day_dir.mkdir(parents=True, exist_ok=True)
        
        meta_path = day_dir / self.META_FILENAME
        if not meta_path.exists():
            meta = HeatmapMeta(
                version=self.VERSION,
                day=day,
                screen_width=screen_w,
                screen_height=screen_h,
                cell_size=self.cell_size,
                grid_width=grid_w,
                grid_height=grid_h,
                unit="ms"
            )
            meta_path.write_text(
                json.dumps(meta.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            self._meta = meta
        else:
            self._meta = HeatmapMeta(**json.loads(meta_path.read_text(encoding="utf-8")))
        
        self._day_dir = day_dir
    
    def start(self) -> None:
        """启动追踪器"""
        with self._lock:
            if self._running:
                return
            self._ensure_day_files()
            self._running = True
            self._thread = threading.Thread(
                target=self._sampling_loop,
                name="OptimizedMouseTracker",
                daemon=True
            )
            self._thread.start()
    
    def stop(self) -> None:
        """停止追踪器并强制刷盘"""
        with self._lock:
            self._running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        self.flush()
    
    def _sampling_loop(self) -> None:
        """优化的采样循环"""
        last_pos = None
        last_sample_time = time.perf_counter()
        
        while True:
            with self._lock:
                if not self._running:
                    break
            
            # 获取当前鼠标位置
            try:
                pos = MousePositionViewer.get_position()
                current_pos = (pos.x, pos.y)
            except Exception:
                time.sleep(0.05)  # 50ms
                continue
            
            now = time.perf_counter()
            
            # 只在鼠标移动时采样（节省CPU）
            if last_pos != current_pos:
                self._last_active_time = now
                
                # 计算在上一个位置停留的时间
                if last_pos is not None:
                    duration_ms = int((now - last_sample_time) * 1000)
                    if duration_ms > 0:
                        cell = self._pos_to_cell(last_pos[0], last_pos[1])
                        self._add_sample(cell[0], cell[1], duration_ms)
                
                last_pos = current_pos
                last_sample_time = now
            else:
                # 鼠标静止，检查是否超时
                if now - self._last_active_time > self.inactive_timeout:
                    # 长时间静止，强制记录当前位置
                    if last_pos is not None:
                        duration_ms = int((now - last_sample_time) * 1000)
                        if duration_ms > 0:
                            cell = self._pos_to_cell(last_pos[0], last_pos[1])
                            self._add_sample(cell[0], cell[1], duration_ms)
                            last_sample_time = now
            
            # 检查是否需要刷盘
            with self._lock:
                if len(self._buffer) >= self.flush_threshold:
                    self.flush()
            
            time.sleep(0.05)  # 50ms采样间隔
    
    def _pos_to_cell(self, x: int, y: int) -> Tuple[int, int]:
        """坐标转网格单元"""
        assert self._meta is not None
        gx = max(0, min(self._meta.grid_width - 1, x // self.cell_size))
        gy = max(0, min(self._meta.grid_height - 1, y // self.cell_size))
        return gx, gy
    
    def _add_sample(self, gx: int, gy: int, duration_ms: int) -> None:
        """添加采样数据"""
        with self._lock:
            # 添加到缓冲区
            self._buffer.append((gx, gy, duration_ms))
            
            # 更新累计数据
            cell_key = (gx, gy)
            self._acc[cell_key] = self._acc.get(cell_key, 0) + duration_ms
            
            # 统计
            self._stats['samples_collected'] += 1
    
    def flush(self) -> None:
        """刷盘缓冲数据"""
        with self._lock:
            if not self._buffer or not self._day_dir:
                return
            
            # 复制缓冲数据
            samples_to_flush = list(self._buffer)
            self._buffer.clear()
            self._stats['flush_operations'] += 1
        
        if not samples_to_flush:
            return
        
        # 合并相同单元格的数据
        cell_updates: Dict[Tuple[int, int], int] = {}
        for gx, gy, duration in samples_to_flush:
            cell_updates[(gx, gy)] = cell_updates.get((gx, gy), 0) + duration
        
        # 读取现有数据
        grid_path = self._day_dir / self.GRID_FILENAME
        try:
            if grid_path.exists():
                raw = json.loads(grid_path.read_text(encoding="utf-8"))
                grid = raw.get("grid_ms", [])
                self._stats['disk_reads'] += 1
            else:
                grid = [[0 for _ in range(self._meta.grid_width)] 
                       for _ in range(self._meta.grid_height)]
        except Exception:
            grid = [[0 for _ in range(self._meta.grid_width)] 
                   for _ in range(self._meta.grid_height)]
        
        # 应用更新
        for (gx, gy), duration in cell_updates.items():
            if 0 <= gy < len(grid) and 0 <= gx < len(grid[0]):
                grid[gy][gx] += duration
        
        # 写回文件
        payload = {
            "version": self.VERSION,
            "day": self._meta.day,
            "cell_size": self._meta.cell_size,
            "unit": self._meta.unit,
            "grid_ms": grid,
        }
        
        temp_path = grid_path.with_suffix('.tmp')
        try:
            temp_path.write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8"
            )
            temp_path.replace(grid_path)
        except Exception as e:
            print(f"Error writing heatmap data: {e}")
    
    def get_current_grid(self) -> List[List[int]]:
        """获取当前累计的网格数据（包含内存缓冲）"""
        with self._lock:
            # 先获取磁盘数据
            if self._day_dir:
                grid_path = self._day_dir / self.GRID_FILENAME
                try:
                    if grid_path.exists():
                        raw = json.loads(grid_path.read_text(encoding="utf-8"))
                        grid = raw.get("grid_ms", [])
                    else:
                        grid = [[0 for _ in range(self._meta.grid_width)] 
                               for _ in range(self._meta.grid_height)]
                except Exception:
                    grid = [[0 for _ in range(self._meta.grid_width)] 
                           for _ in range(self._meta.grid_height)]
            else:
                grid = [[0 for _ in range(self._meta.grid_width)] 
                       for _ in range(self._meta.grid_height)]
            
            # 应用内存缓冲的增量
            for gx, gy, duration in self._buffer:
                if 0 <= gy < len(grid) and 0 <= gx < len(grid[0]):
                    grid[gy][gx] += duration
            
            return grid
    
    def get_stats(self) -> Dict[str, int]:
        """获取性能统计信息"""
        with self._lock:
            return self._stats.copy()
    
    @classmethod
    def load_day_grid(cls, day: str, data_root: str = None, cell_size: int = 48) -> List[List[int]]:
        """加载指定日期的网格数据"""
        root = Path(data_root) if data_root else Path("data") / "mouse_heatmap"
        day_dir = root / day / f"cell_{cell_size}"
        grid_path = day_dir / cls.GRID_FILENAME
        meta_path = day_dir / cls.META_FILENAME
        
        if not grid_path.exists() or not meta_path.exists():
            # 返回空网格
            meta = HeatmapMeta(**json.loads(meta_path.read_text(encoding="utf-8")))
            return [[0 for _ in range(meta.grid_width)] for _ in range(meta.grid_height)]
        
        try:
            raw = json.loads(grid_path.read_text(encoding="utf-8"))
            return raw.get("grid_ms", [])
        except Exception:
            meta = HeatmapMeta(**json.loads(meta_path.read_text(encoding="utf-8")))
            return [[0 for _ in range(meta.grid_width)] for _ in range(meta.grid_height)]

    # ======== 兼容性方法：从原 MouseHeatmapTracker 复制 ========
    
    @classmethod
    def load_day(cls, day: str, data_root: Optional[str] = None, cell_size: int = 48) -> Tuple[HeatmapMeta, List[List[int]]]:
        """加载某天的 grid.json 并返回网格（单位 ms）。"""
        root = Path(data_root) if data_root else Path("data") / "mouse_heatmap"
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
        import math

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
                # 低热度直接透明，避免"整屏泛色"
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