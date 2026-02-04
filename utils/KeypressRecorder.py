import json
import os
from datetime import date
from typing import Dict, List
from utils.MouseClickRecorder import MouseClickRecorder
from utils.DataCacheManager import get_data_cache_manager


class KeypressRecorder:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        # 使用缓存管理器替代直接文件操作
        self.cache_manager = get_data_cache_manager()
        # 初始化鼠标记录器
        self.mouse_recorder = MouseClickRecorder(data_dir)
        # 设置鼠标记录器的主记录器引用
        self.mouse_recorder._main_recorder = self

    def record_keypress(self, key: str):
        """记录一次按键并增加功德值（优化版）"""
        # 直接使用缓存管理器，避免文件I/O
        self.cache_manager.increment_key_count(key, 1)

    def get_records(self) -> List[Dict]:
        """获取所有按键记录"""
        # 从缓存管理器获取数据
        return list(self.cache_manager._cache.values())

    def get_daily_record(self, key: str, target_date: str = None) -> int:
        """获取指定日期的特定按键次数"""
        stats = self.cache_manager.get_key_stats(target_date)
        return stats.get(key, 0)

    def get_daily_merit(self, target_date: str = None) -> int:
        """获取指定日期的功德值"""
        return self.cache_manager.get_merit_count(target_date)

    def get_daily_all_keys(self, target_date: str = None) -> Dict[str, int]:
        """获取指定日期的所有按键记录"""
        return self.cache_manager.get_key_stats(target_date)

    def record_mouse_click(self, button_name: str):
        """记录鼠标点击（优化版）"""
        self.cache_manager.increment_mouse_count(button_name, 1)

    def get_daily_mouse_buttons(self, target_date: str = None) -> Dict[str, int]:
        """获取指定日期的所有鼠标按键记录"""
        return self.cache_manager.get_mouse_stats(target_date)

    def get_daily_mouse_total(self, target_date: str = None) -> int:
        """获取指定日期的鼠标总点击次数"""
        stats = self.cache_manager.get_mouse_stats(target_date)
        return sum(stats.values()) if stats else 0

    # 保留原有接口兼容性
    def _load_records(self) -> List[Dict]:
        """向后兼容：从缓存管理器获取记录"""
        return self.get_records()

    def _save_records(self, records: List[Dict]):
        """向后兼容：手动触发刷盘"""
        self.cache_manager.flush()
