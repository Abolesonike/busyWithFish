import json
import os
import threading
import time
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class DataCacheManager:
    """
    数据缓存管理器 - 优化文件I/O性能
    
    核心优化策略：
    1. 内存缓存：避免频繁磁盘读写
    2. 批量写入：合并多个操作为单次写入
    3. 异步持久化：后台线程定期刷盘
    4. 写入合并：相同键的操作合并为一次更新
    """
    
    def __init__(self, data_dir: str = "data", flush_interval: float = 5.0):
        self.data_dir = Path(data_dir)
        self.flush_interval = flush_interval
        self.file_path = self.data_dir / "keypress_records.json"
        
        # 内存缓存
        self._cache: Dict[str, Any] = {}
        self._dirty_keys: set = set()  # 标记需要写入的键
        self._lock = threading.RLock()
        
        # 后台刷盘线程
        self._running = False
        self._flush_thread: Optional[threading.Thread] = None
        
        # 确保目录存在
        self.data_dir.mkdir(exist_ok=True)
        self._initialize_cache()
        
    def _initialize_cache(self):
        """初始化缓存，从磁盘加载现有数据"""
        try:
            if self.file_path.exists():
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 转换为字典形式便于快速查找
                    self._cache = {record['date']: record for record in data}
            else:
                self._cache = {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load cache, starting fresh: {e}")
            self._cache = {}
    
    def start_auto_flush(self):
        """启动自动刷盘线程"""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._flush_thread = threading.Thread(
                target=self._flush_worker,
                name="DataCacheFlusher",
                daemon=True
            )
            self._flush_thread.start()
    
    def stop_auto_flush(self):
        """停止自动刷盘并强制刷盘"""
        with self._lock:
            self._running = False
        
        # 等待刷盘线程结束
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=2.0)
        
        # 强制刷盘剩余数据
        self.flush()
    
    def _flush_worker(self):
        """后台刷盘工作线程"""
        while True:
            with self._lock:
                if not self._running:
                    break
            
            time.sleep(self.flush_interval)
            
            # 定期刷盘
            if self._dirty_keys:
                self.flush()
    
    def get_today_record(self) -> Dict[str, Any]:
        """获取今日记录（带缓存）"""
        today = str(date.today())
        with self._lock:
            if today not in self._cache:
                # 创建新的今日记录，确保所有必要字段都存在
                self._cache[today] = {
                    'date': today,
                    'keys': {},           # 确保这个字段存在
                    'merit': 0,
                    'mouse_buttons': {},  # 确保这个字段存在
                    'mouse_total': 0
                }
                self._dirty_keys.add(today)
            
            # 确保返回的记录包含所有必要字段
            record = self._cache[today]
            if 'keys' not in record:
                record['keys'] = {}
            if 'mouse_buttons' not in record:
                record['mouse_buttons'] = {}
            if 'merit' not in record:
                record['merit'] = 0
            if 'mouse_total' not in record:
                record['mouse_total'] = 0
            
            return record
    
    def increment_key_count(self, key: str, count: int = 1):
        """增加按键计数（批量操作）"""
        today_record = self.get_today_record()
        with self._lock:
            # 更新按键计数
            if key in today_record['keys']:
                today_record['keys'][key] += count
            else:
                today_record['keys'][key] = count
            
            # 增加功德值
            today_record['merit'] += count
            self._dirty_keys.add(today_record['date'])
    
    def increment_mouse_count(self, button_name: str, count: int = 1):
        """增加鼠标点击计数"""
        today_record = self.get_today_record()
        with self._lock:
            # 更新鼠标按键计数
            if button_name in today_record['mouse_buttons']:
                today_record['mouse_buttons'][button_name] += count
            else:
                today_record['mouse_buttons'][button_name] = count
            
            # 增加鼠标总次数
            today_record['mouse_total'] += count
            self._dirty_keys.add(today_record['date'])
    
    def flush(self):
        """立即将缓存数据刷入磁盘"""
        with self._lock:
            if not self._dirty_keys:
                return
            
            # 准备要写入的数据
            dirty_dates = list(self._dirty_keys)
            self._dirty_keys.clear()
        
        # 转换为列表格式用于存储
        records_to_save = list(self._cache.values())
        
        # 写入文件（在锁外执行以减少锁定时间）
        try:
            temp_file = self.file_path.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(records_to_save, f, ensure_ascii=False, indent=2)
            
            # 原子性替换
            temp_file.replace(self.file_path)
            
        except IOError as e:
            print(f"Error flushing data to disk: {e}")
            # 恢复脏标记以便下次重试
            with self._lock:
                self._dirty_keys.update(dirty_dates)
    
    def get_key_stats(self, target_date: str = None) -> Dict[str, int]:
        """获取指定日期的按键统计"""
        if target_date is None:
            target_date = str(date.today())
        
        with self._lock:
            record = self._cache.get(target_date, {})
            return record.get('keys', {}).copy()
    
    def get_merit_count(self, target_date: str = None) -> int:
        """获取指定日期的功德值"""
        if target_date is None:
            target_date = str(date.today())
        
        with self._lock:
            record = self._cache.get(target_date, {})
            return record.get('merit', 0)
    
    def get_mouse_stats(self, target_date: str = None) -> Dict[str, int]:
        """获取指定日期的鼠标统计"""
        if target_date is None:
            target_date = str(date.today())
        
        with self._lock:
            record = self._cache.get(target_date, {})
            return record.get('mouse_buttons', {}).copy()
    
    def force_reload(self):
        """强制从磁盘重新加载数据（用于外部修改的情况）"""
        with self._lock:
            self._initialize_cache()
            self._dirty_keys.clear()


# 全局单例实例
_data_cache_manager: Optional[DataCacheManager] = None
_manager_lock = threading.Lock()


def get_data_cache_manager() -> DataCacheManager:
    """获取全局缓存管理器单例"""
    global _data_cache_manager
    
    with _manager_lock:
        if _data_cache_manager is None:
            _data_cache_manager = DataCacheManager()
            _data_cache_manager.start_auto_flush()
    
    return _data_cache_manager


def shutdown_cache_manager():
    """关闭缓存管理器（程序退出时调用）"""
    global _data_cache_manager
    
    with _manager_lock:
        if _data_cache_manager:
            _data_cache_manager.stop_auto_flush()
            _data_cache_manager = None