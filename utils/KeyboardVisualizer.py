from datetime import date
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QDialog, QScrollArea, QFrame, QHBoxLayout, QDateEdit
from PyQt6.QtCore import Qt
from utils.KeypressRecorder import KeypressRecorder


class KeyboardKeyWidget(QLabel):
    """自定义键盘按键控件，用于显示按键颜色"""
    
    def __init__(self, key_name, press_count=0, max_count=255):
        super().__init__()
        self.key_name = key_name
        self.press_count = press_count
        self.max_count = max_count  # 固定为150

        # 根据按压次数计算颜色插值，从白色(255,255,255)渐变到深红色(178,34,34)
        ratio = min(press_count / self.max_count, 1.0)
        
        # 白色起始值 (255, 255, 255)
        start_r, start_g, start_b = 255, 255, 255
        # 目标深红色值 (178, 34, 34)
        end_r, end_g, end_b = 178, 34, 34
        
        # 计算当前颜色值
        r = int(start_r + (end_r - start_r) * ratio)
        g = int(start_g + (end_g - start_g) * ratio)
        b = int(start_b + (end_b - start_b) * ratio)
        
        bg_color = f"rgb({r}, {g}, {b})"
        
        # 设置样式：背景色从白色渐变到深红色，字体为黑色
        self.setStyleSheet(
            f"background-color: {bg_color}; "
            f"border: 1px solid #888; "
            f"border-radius: 4px; "
            f"padding: 4px; "
            f"font-weight: bold; "
            f"color: black;"
        )
        
        # 设置按键文本
        display_text = self._format_key_name(key_name)
        self.setText(display_text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(20, 20)  # 调整按键大小为30x30
        
        # 设置提示信息
        self.setToolTip(f"{key_name}: {press_count} 次")

    def _format_key_name(self, key_name):
        """格式化按键名称以便显示"""
        # 处理控制字符（如\x03代表Ctrl+C）
        if len(key_name) == 1 and ord(key_name) < 32:
            control_char_map = {
                "\x03": "Ctrl+C",
                "\x16": "Ctrl+V",
                "\x01": "Ctrl+A",
                "\x08": "Backspace",
                "\t": "Tab",
                "\r": "Enter",
                "\x1a": "Ctrl+Z",
                "\x18": "Ctrl+X",
                "\x11": "Ctrl+Q",
                "\x05": "Ctrl+E",
                "\x12": "Ctrl+R",
                "\x13": "Ctrl+S",
                "\x14": "Ctrl+T",
                "\x19": "Ctrl+Y",
                "\x15": "Ctrl+U",
                "\x0f": "Ctrl+O",
                "\x10": "Ctrl+P",
                "\x07": "Ctrl+G",
                "\x08": "Ctrl+H",
                "\x0a": "Ctrl+J",
                "\x0b": "Ctrl+K",
                "\x0c": "Ctrl+L",
                "\x06": "Ctrl+F",
                "\x0e": "Ctrl+N",
                "\x02": "Ctrl+B",
                "\x04": "Ctrl+D",
                "\x1b": "Esc"
            }
            return control_char_map.get(key_name, f"Ctrl+{chr(ord(key_name) + 64)}")
        
        # 常见特殊键的显示名称
        key_display_names = {
            'space': '空格',
            'enter': '回车',
            'backspace': '退格',
            'tab': 'Tab',
            'caps_lock': '大写锁定',
            'shift': 'Shift_L',
            'shift_r': 'Shift_R',
            'ctrl_l': 'Ctrl_L',
            'ctrl_r': 'Ctrl_R',
            'alt_l': 'Alt_L',
            'alt_r': 'Alt_R',
            'win': 'Win',
            'esc': 'Esc',
            'up': '↑',
            'down': '↓',
            'left': '←',
            'right': '→',
            'page_up': 'PgUp',
            'page_down': 'PgDn',
            'home': 'Home',
            'end': 'End',
            'insert': 'Ins',
            'delete': 'Del',
            'f1': 'F1', 'f2': 'F2', 'f3': 'F3', 'f4': 'F4',
            'f5': 'F5', 'f6': 'F6', 'f7': 'F7', 'f8': 'F8',
            'f9': 'F9', 'f10': 'F10', 'f11': 'F11', 'f12': 'F12'
        }
        
        return key_display_names.get(key_name, key_name.upper())


class KeyboardVisualizerDialog(QDialog):
    """键盘可视化弹窗对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("按键统计可视化")
        self.setModal(False)
        self.resize(800, 300)  # 将窗口缩小一半
        
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # 添加日期选择控件
        date_layout = QHBoxLayout()
        date_label = QLabel("选择日期:")
        self.date_edit = QDateEdit()
        self.date_edit.setDate(date.today())  # 默认设置为今天
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setCalendarPopup(True)
        # 当日期改变时自动刷新数据
        self.date_edit.dateChanged.connect(self.refresh_data)
        # 禁止键盘输入，但仍允许通过日历选择
        self.date_edit.lineEdit().setReadOnly(True)
        
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_edit)
        
        self.layout.addLayout(date_layout)
        
        # 创建滚动区域以支持大量按键
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # 创建主容器
        container = QWidget()
        scroll_area.setWidget(container)
        
        # 主容器布局
        main_layout = QVBoxLayout(container)
        
        # 创建键盘网格
        self.keyboard_grid = QGridLayout()
        self.keyboard_grid.setSpacing(2)  # 进一步减小间距
        self.keyboard_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 添加键盘网格到主布局
        main_layout.addLayout(self.keyboard_grid)
        
        # 将滚动区域添加到主布局
        self.layout.addWidget(scroll_area)
        
        # 初始化记录器
        self.keypress_recorder = KeypressRecorder()
        
        # 加载并显示数据
        self.refresh_data()

    def refresh_data(self):
        """刷新按键统计数据"""
        # 清除现有按键
        for i in reversed(range(self.keyboard_grid.count())):
            widget = self.keyboard_grid.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        
        # 获取选定的日期
        selected_date = self.date_edit.date().toString("yyyy-MM-dd")
        
        # 获取指定日期的按键记录
        keys_data = self.keypress_recorder.get_daily_all_keys(selected_date)
        
        if not keys_data:
            # 如果指定日期没有按键记录，显示提示
            hint_label = QLabel(f"{selected_date} 暂无按键记录")
            hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint_label.setStyleSheet("font-size: 14px; color: gray;")
            self.keyboard_grid.addWidget(hint_label, 0, 0)
            return
        
        # 固定最大按压次数为500
        max_count = 500
        
        # 定义键盘布局（简化版）
        keyboard_layout = [
            ['esc', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12'],
            ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'backspace'],
            ['tab', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\\'],
            ['caps_lock', 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', '\'', 'enter'],
            ['shift', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', 'up', 'shift_r'],
            ['ctrl_l', 'win', 'alt_l', 'space', 'alt_r', 'win', 'menu', 'ctrl_r', 'left', 'down', 'right']
        ]

        # 组合键
        combo_keys = [
            "\x03", # Ctrl+C
            "\x16", # Ctrl+A
            "\x01", # Ctrl+V
            "\x1a", # Ctrl+Z
            "\x18", # Ctrl+X
            "\x13", # Ctrl+S
            "\x06" # Ctrl+F
        ]

        # 创建按键网格
        row_idx = 0
        for row in keyboard_layout:
            col_idx = 0
            for key in row:
                # 获取该按键的按压次数
                press_count = keys_data.get(key, 0)
                
                # 创建按键控件
                key_widget = KeyboardKeyWidget(key, press_count, max_count)

                if key == 'space':
                    self.keyboard_grid.addWidget(key_widget, row_idx, col_idx, 1, 4)
                    col_idx += 4  # 空格键占用4个位置
                elif key == 'enter':
                    self.keyboard_grid.addWidget(key_widget, row_idx, col_idx, 1, 2)
                    col_idx += 2  # enter键占用3个位置
                elif key == 'shift':
                    self.keyboard_grid.addWidget(key_widget, row_idx, col_idx, 1, 2)
                    col_idx += 2  # 左Shift键占用2个位置
                else:
                    self.keyboard_grid.addWidget(key_widget, row_idx, col_idx, 1, 1)
                    col_idx += 1
            row_idx += 1

        # 为不在标准布局中的按键单独添加
        extra_keys = []
        for key in keys_data.keys():
            if key not in [k for row in keyboard_layout for k in row]:
                if key in combo_keys:
                    extra_keys.append(key)

        if extra_keys:
            # 添加额外按键部分
            extra_title = QLabel("\n其他按键:")
            extra_title.setStyleSheet("font-size: 14px; font-weight: bold; padding-top: 10px;")
            self.keyboard_grid.addWidget(extra_title, row_idx, 0, 1, len(keyboard_layout[0]))
            row_idx += 1

            for i, key in enumerate(extra_keys):
                press_count = keys_data.get(key, 0)
                key_widget = KeyboardKeyWidget(key, press_count, max_count)
                col_pos = i % len(keyboard_layout[0])
                row_pos = row_idx + (i // len(keyboard_layout[0]))
                self.keyboard_grid.addWidget(key_widget, row_pos, col_pos)

            row_idx += (len(extra_keys) // len(keyboard_layout[0])) + 1

    def showEvent(self, event):
        # 每次打开弹窗时重置为默认状态（当前日期）
        self.date_edit.setDate(date.today())
        self.refresh_data()
        super().showEvent(event)