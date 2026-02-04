import json
import os
from datetime import date
from typing import Dict, List
from utils.MouseClickRecorder import MouseClickRecorder


class KeypressRecorder:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.file_path = os.path.join(data_dir, "keypress_records.json")
        self._ensure_data_directory()
        self._initialize_file()
        # 初始化鼠标记录器
        self.mouse_recorder = MouseClickRecorder(data_dir)

    def _ensure_data_directory(self):
        """确保数据目录存在"""
        os.makedirs(self.data_dir, exist_ok=True)

    def _initialize_file(self):
        """初始化记录文件，如果不存在则创建"""
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def record_keypress(self, key: str):
        """记录一次按键并增加功德值"""
        records = self._load_records()  # 使用过滤后的记录
        today = str(date.today())

        # 查找今天的记录
        today_record = None
        for record in records:
            if record.get('date') == today and 'keys' in record:
                today_record = record
                break

        # 如果今天还没有记录，则创建新记录
        if today_record is None:
            today_record = {
                'date': today,
                'keys': {},
                'merit': 0,  # 初始化功德值
                'mouse_buttons': {},  # 鼠标按键统计
                'mouse_total': 0     # 鼠标总点击次数
            }
            records.append(today_record)

        # 确保today_record中有必要的字段
        if 'keys' not in today_record:
            today_record['keys'] = {}
        if 'merit' not in today_record:
            today_record['merit'] = 0
        if 'mouse_buttons' not in today_record:
            today_record['mouse_buttons'] = {}
        if 'mouse_total' not in today_record:
            today_record['mouse_total'] = 0

        # 更新按键计数
        if key in today_record['keys']:
            today_record['keys'][key] += 1
        else:
            today_record['keys'][key] = 1
        
        # 每次按键功德+1
        today_record['merit'] += 1
            
        self._save_records(records)

    def get_records(self) -> List[Dict]:
        """获取所有按键记录"""
        return self._load_records()

    def get_daily_record(self, key: str, target_date: str = None) -> int:
        """获取指定日期的特定按键次数"""
        if target_date is None:
            target_date = str(date.today())
        
        records = self._load_records()
        for record in records:
            if record['date'] == target_date:
                return record.get('keys', {}).get(key, 0)
        return 0

    def get_daily_merit(self, target_date: str = None) -> int:
        """获取指定日期的特定按键次数"""
        if target_date is None:
            target_date = str(date.today())

        records = self._load_records()
        for record in records:
            if record['date'] == target_date:
                return record.get('merit')
        return 0

    def get_daily_all_keys(self, target_date: str = None) -> Dict[str, int]:
        """获取指定日期的所有按键记录"""
        if target_date is None:
            target_date = str(date.today())
        
        records = self._load_records()
        for record in records:
            if record['date'] == target_date:
                return record.get('keys', {})
        return {}

    def record_mouse_click(self, button_name: str):
        """记录鼠标点击（代理到MouseClickRecorder，但保存在同一文件中）"""
        records = self._load_records()
        today = str(date.today())

        # 查找今天的记录
        today_record = None
        for record in records:
            if record.get('date') == today:
                today_record = record
                break

        # 如果今天还没有记录，则创建新记录
        if today_record is None:
            today_record = {
                'date': today,
                'keys': {},
                'merit': 0,
                'mouse_buttons': {},
                'mouse_total': 0
            }
            records.append(today_record)

        # 确保today_record中有必要的字段
        if 'mouse_buttons' not in today_record:
            today_record['mouse_buttons'] = {}
        if 'mouse_total' not in today_record:
            today_record['mouse_total'] = 0

        # 更新鼠标按键计数
        if button_name in today_record['mouse_buttons']:
            today_record['mouse_buttons'][button_name] += 1
        else:
            today_record['mouse_buttons'][button_name] = 1
        
        # 每次鼠标点击总次数+1
        today_record['mouse_total'] += 1
            
        self._save_records(records)

    def get_daily_mouse_buttons(self, target_date: str = None) -> Dict[str, int]:
        """获取指定日期的所有鼠标按键记录"""
        if target_date is None:
            target_date = str(date.today())
        
        records = self._load_records()
        for record in records:
            if record['date'] == target_date:
                return record.get('mouse_buttons', {})
        return {}

    def get_daily_mouse_total(self, target_date: str = None) -> int:
        """获取指定日期的鼠标总点击次数"""
        if target_date is None:
            target_date = str(date.today())
        
        records = self._load_records()
        for record in records:
            if record['date'] == target_date:
                return record.get('mouse_total', 0)
        return 0

    def _load_records(self) -> List[Dict]:
        """从文件加载记录"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            # 如果文件损坏，返回空列表
            return []

    def _save_records(self, records: List[Dict]):
        """保存记录到文件"""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)