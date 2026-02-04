import json
import os
from datetime import date
from typing import Dict, List
from pynput import mouse
from utils.systemUtils import get_resource_path


class MouseClickRecorder:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.file_path = os.path.join(data_dir, "keypress_records.json")
        self._ensure_data_directory()
        self._initialize_file()
        self.listener = None

    def _ensure_data_directory(self):
        """确保数据目录存在"""
        os.makedirs(self.data_dir, exist_ok=True)

    def _initialize_file(self):
        """初始化记录文件，如果不存在则创建"""
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def start_listening(self):
        """开始监听鼠标按键"""
        if self.listener is None:
            self.listener = mouse.Listener(
                on_click=self._on_click,
                on_scroll=self._on_scroll
            )
            self.listener.start()

    def stop_listening(self):
        """停止监听鼠标按键"""
        if self.listener is not None:
            self.listener.stop()
            self.listener = None

    def _on_click(self, x, y, button, pressed):
        """鼠标点击事件处理"""
        if pressed:  # 只记录按下事件，避免重复统计
            button_name = self._get_button_name(button)
            self.record_mouse_click(button_name)
            # 同时通知主记录器更新数据
            if hasattr(self, '_main_recorder') and self._main_recorder:
                self._main_recorder.record_mouse_click(button_name)

    def _on_scroll(self, x, y, dx, dy):
        """鼠标滚轮事件处理"""
        # 记录滚轮滚动，正数表示向上滚动，负数表示向下滚动
        scroll_direction = "scroll_up" if dy > 0 else "scroll_down"
        self.record_mouse_click(scroll_direction)
        # 同时通知主记录器更新数据
        if hasattr(self, '_main_recorder') and self._main_recorder:
            self._main_recorder.record_mouse_click(scroll_direction)

    def _get_button_name(self, button):
        """获取鼠标按键名称"""
        if button == mouse.Button.left:
            return "mouse_left"
        elif button == mouse.Button.right:
            return "mouse_right"
        elif button == mouse.Button.middle:
            return "mouse_middle"
        elif button == mouse.Button.x1:
            return "mouse_x1"  # 侧键1（通常在鼠标左侧）
        elif button == mouse.Button.x2:
            return "mouse_x2"  # 侧键2（通常在鼠标右侧）
        else:
            return f"mouse_unknown_{button}"

    def record_mouse_click(self, button_name: str):
        """记录一次鼠标按键点击"""
        records = self._load_records()
        today = str(date.today())

        # 查找今天的记录
        today_record = None
        for record in records:
            if record.get('date') == today and 'mouse_buttons' in record:
                today_record = record
                break

        # 如果今天还没有记录，则创建新记录
        if today_record is None:
            today_record = {
                'date': today,
                'mouse_buttons': {},
                'mouse_total': 0  # 鼠标总点击次数
            }
            records.append(today_record)

        # 确保today_record中有mouse_buttons字典和mouse_total字段
        if 'mouse_buttons' not in today_record:
            today_record['mouse_buttons'] = {}
        if 'mouse_total' not in today_record:
            today_record['mouse_total'] = 0

        # 更新按键计数
        if button_name in today_record['mouse_buttons']:
            today_record['mouse_buttons'][button_name] += 1
        else:
            today_record['mouse_buttons'][button_name] = 1
        
        # 每次鼠标点击总次数+1
        today_record['mouse_total'] += 1
            
        self._save_records(records)

    def get_records(self) -> List[Dict]:
        """获取所有鼠标按键记录"""
        return self._load_records()

    def get_daily_record(self, button_name: str, target_date: str = None) -> int:
        """获取指定日期的特定鼠标按键次数"""
        if target_date is None:
            target_date = str(date.today())
        
        records = self._load_records()
        for record in records:
            if record['date'] == target_date:
                return record.get('mouse_buttons', {}).get(button_name, 0)
        return 0

    def get_daily_total(self, target_date: str = None) -> int:
        """获取指定日期的鼠标总点击次数"""
        if target_date is None:
            target_date = str(date.today())

        records = self._load_records()
        for record in records:
            if record['date'] == target_date:
                return record.get('mouse_total', 0)
        return 0

    def get_daily_all_buttons(self, target_date: str = None) -> Dict[str, int]:
        """获取指定日期的所有鼠标按键记录"""
        if target_date is None:
            target_date = str(date.today())
        
        records = self._load_records()
        for record in records:
            if record['date'] == target_date:
                return record.get('mouse_buttons', {})
        return {}

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