import json
import os
import sys
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from openai import OpenAI
import requests
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from utils.DataCacheManager import get_data_cache_manager
from utils.MouseHeatmapTracker import OptimizedMouseHeatmapTracker


def get_config_file_path():
    """获取配置文件的路径"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件，从同级目录查找配置文件
        config_path = os.path.join(os.path.dirname(sys.executable), 'config.json')
    else:
        # 如果是开发环境，从当前工作目录查找配置文件
        config_path = os.path.join(os.getcwd(), 'config.json')
    return config_path


def load_config():
    """加载配置文件"""
    config_path = get_config_file_path()
    default_config = {
        "DASHSCOPE_API_KEY": "",
        "model_name": "qwen3-max-2026-01-23",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置和文件配置
                default_config.update(config)
        except Exception as e:
            print(f"配置文件读取失败: {e}")
    
    return default_config


class BailianAnalyzer(QObject):
    """
    阿里云百炼大模型分析器
    用于分析键盘鼠标使用数据，提供智能化的行为洞察
    """
    
    # 信号定义
    analysis_started = pyqtSignal()
    analysis_completed = pyqtSignal(dict)  # 发送分析结果
    analysis_error = pyqtSignal(str)       # 发送错误信息
    progress_updated = pyqtSignal(int, str)  # 进度更新 (百分比, 描述)
    
    def __init__(self, api_key: str = None, model_name: str = None):
        super().__init__()
        
        # 加载配置
        config = load_config()
        
        # 设置API密钥
        self.api_key = api_key or config.get("DASHSCOPE_API_KEY", "")
        if os.getenv("DASHSCOPE_API_KEY") :
            self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.model_name = model_name or config.get("MODEL_NAME", "qwen-plus")
        if os.getenv("MODEL_NAME") :
            self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.base_url = config.get("BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        if os.getenv("BASE_URL") :
            self.api_key = os.getenv("DASHSCOPE_API_KEY")
        
        # 数据源
        self.cache_manager = get_data_cache_manager()
        
        # 分析配置
        self.default_days = 1  # 默认分析最近7天数据
        
    def set_api_key(self, api_key: str):
        """设置API密钥"""
        self.api_key = api_key
        
    def collect_data(self, days: int = None) -> Dict:
        """
        收集指定天数内的键盘鼠标数据（异步优化版本）
        """
        if days is None:
            days = self.default_days
            
        # 注释掉可能导致UI阻塞的进度更新
        # self.progress_updated.emit(10, "正在收集键盘鼠标数据...")
        print(10, "正在收集键盘鼠标数据...")

        # 计算日期范围
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)
        
        collected_data = {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'keyboard_stats': {},
            'mouse_stats': {},
            'daily_summary': [],
            'hotspot_data': []
        }
        
        # 收集每日数据
        current_date = start_date
        processed_days = 0
        total_days = (end_date - start_date).days + 1
        
        while current_date <= end_date:
            date_str = current_date.isoformat()
            
            # 获取键盘数据
            keyboard_data = self.cache_manager.get_key_stats(date_str)
            merit_count = self.cache_manager.get_merit_count(date_str)
            
            # 获取鼠标数据
            mouse_data = self.cache_manager.get_mouse_stats(date_str)
            mouse_total = sum(mouse_data.values()) if mouse_data else 0
            
            daily_summary = {
                'date': date_str,
                'keyboard_keys': keyboard_data,
                'keyboard_total': sum(keyboard_data.values()) if keyboard_data else 0,
                'merit_count': merit_count,
                'mouse_buttons': mouse_data,
                'mouse_total': mouse_total,
                'total_interactions': sum(keyboard_data.values()) + mouse_total if keyboard_data else mouse_total
            }
            
            collected_data['daily_summary'].append(daily_summary)
            
            # 累计键盘统计
            for key, count in keyboard_data.items():
                if key in collected_data['keyboard_stats']:
                    collected_data['keyboard_stats'][key] += count
                else:
                    collected_data['keyboard_stats'][key] = count
            
            # 累计鼠标统计
            for button, count in mouse_data.items():
                if button in collected_data['mouse_stats']:
                    collected_data['mouse_stats'][button] += count
                else:
                    collected_data['mouse_stats'][button] = count
            
            current_date += timedelta(days=1)
            processed_days += 1
            
            # 异步更新进度（避免频繁触发）
            if processed_days % 2 == 0:  # 每处理2天更新一次进度
                progress = int(10 + (processed_days / total_days) * 20)
                # self.progress_updated.emit(progress, f"正在收集数据...({processed_days}/{total_days})")
        
        # self.progress_updated.emit(30, "数据收集完成")
        print(30, "数据收集完成")
        return collected_data
    
    def collect_hotspot_data(self, days: int = None) -> List:
        """
        收集鼠标热点数据
        """
        if days is None:
            days = self.default_days
            
        # self.progress_updated.emit(40, "正在收集鼠标热点数据...")
        print(40, "正在收集鼠标热点数据...")

        hotspot_data = []
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.isoformat()
            try:
                # 加载当天的热力图数据
                meta, grid = OptimizedMouseHeatmapTracker.load_day(
                    date_str, 
                    data_root="data/mouse_heatmap", 
                    cell_size=48
                )
                
                # 计算热点区域（高活跃度区域）
                if grid and len(grid) > 0:
                    max_value = max(max(row) for row in grid) if grid else 0
                    if max_value > 0:
                        # 找出前10个最活跃的区域
                        active_areas = []
                        for y, row in enumerate(grid):
                            for x, value in enumerate(row):
                                if value > max_value * 0.3:  # 超过30%最大值的区域
                                    active_areas.append({
                                        'x': x,
                                        'y': y,
                                        'value': value,
                                        'normalized_value': value / max_value
                                    })
                        
                        # 按活跃度排序，取前10个
                        active_areas.sort(key=lambda a: a['value'], reverse=True)
                        top_areas = active_areas[:10]
                        
                        hotspot_data.append({
                            'date': date_str,
                            'active_areas': top_areas,
                            'max_activity': max_value,
                            'total_cells': len([cell for row in grid for cell in row if cell > 0])
                        })
            except Exception as e:
                print(f"Failed to load heatmap data for {date_str}: {e}")
            
            current_date += timedelta(days=1)
        
        print(50, "热点数据收集完成")
        return hotspot_data
    
    def prepare_analysis_prompt(self, collected_data: Dict) -> str:
        """
        准备发送给大模型的分析提示词
        """
        print(60, "正在准备分析请求...")
        
        # 构建详细的数据描述
        keyboard_summary = self._summarize_keyboard_data(collected_data['keyboard_stats'])
        mouse_summary = self._summarize_mouse_data(collected_data['mouse_stats'])
        daily_patterns = self._analyze_daily_patterns(collected_data['daily_summary'])
        hotspot_insights = self._analyze_hotspot_data(collected_data.get('hotspot_data', []))
        
        prompt = f"""
你是一个专业的用户行为分析师，请基于以下键盘鼠标使用数据分析用户的操作习惯和行为特征。

数据概览：
- 分析周期：{collected_data['period']['start_date']} 至 {collected_data['period']['end_date']} ({collected_data['period']['days']}天)
- 总按键次数：{sum(collected_data['keyboard_stats'].values()) if collected_data['keyboard_stats'] else 0}
- 总鼠标点击：{sum(collected_data['mouse_stats'].values()) if collected_data['mouse_stats'] else 0}

键盘使用详情：
{keyboard_summary}

鼠标使用详情：
{mouse_summary}

日常使用模式：
{daily_patterns}

鼠标热点区域分析：
{hotspot_insights}

请提供以下方面的专业分析：

1. **使用场景评估**：更具鼠标和键盘使用情况，猜猜用户的工作性质或使用场景（如果是工作，则猜测工作职位。游戏，则猜测是什么游戏。娱乐，则猜测娱乐场景）。
2. **使用强度评估**：整体使用频率是否正常，是否存在过度使用风险
3. **习惯偏好分析**：主要使用的按键和鼠标操作类型
4. **潜在问题提醒**：可能存在的不良使用习惯或健康风险
5. **优化建议**：改善使用效率和保护健康的实用建议
6. **个性化洞察**：根据使用模式推测的工作性质或使用场景

请用中文回复，结构清晰，语言专业但易懂。
"""
        
        return prompt
    
    def _summarize_keyboard_data(self, keyboard_stats: Dict) -> str:
        """汇总键盘数据"""
        if not keyboard_stats:
            return "无键盘使用数据"
        
        total_presses = sum(keyboard_stats.values())
        sorted_keys = sorted(keyboard_stats.items(), key=lambda x: x[1], reverse=True)
        top_keys = sorted_keys[:10]  # 前10个最常用按键
        
        summary = f"- 总按键次数：{total_presses}\n"
        summary += "- 最常用按键：\n"
        for key, count in top_keys:
            percentage = (count / total_presses) * 100
            key_display = self._format_key_name(key)
            summary += f"  • {key_display}: {count}次 ({percentage:.1f}%)\n"
        
        return summary
    
    def _summarize_mouse_data(self, mouse_stats: Dict) -> str:
        """汇总鼠标数据"""
        if not mouse_stats:
            return "无鼠标使用数据"
        
        total_clicks = sum(mouse_stats.values())
        sorted_buttons = sorted(mouse_stats.items(), key=lambda x: x[1], reverse=True)
        
        summary = f"- 总点击次数：{total_clicks}\n"
        summary += "- 按键使用分布：\n"
        for button, count in sorted_buttons:
            percentage = (count / total_clicks) * 100
            button_display = self._format_mouse_button(button)
            summary += f"  • {button_display}: {count}次 ({percentage:.1f}%)\n"
        
        return summary
    
    def _analyze_daily_patterns(self, daily_summary: List) -> str:
        """分析日常使用模式"""
        if not daily_summary:
            return "无日常数据"
        
        total_interactions = [day['total_interactions'] for day in daily_summary]
        avg_daily = sum(total_interactions) / len(total_interactions) if total_interactions else 0
        max_daily = max(total_interactions) if total_interactions else 0
        min_daily = min(total_interactions) if total_interactions else 0
        
        # 识别周末vs工作日模式
        weekday_totals = []
        weekend_totals = []
        
        for day_data in daily_summary:
            date_obj = datetime.fromisoformat(day_data['date'])
            if date_obj.weekday() >= 5:  # 5=周六, 6=周日
                weekend_totals.append(day_data['total_interactions'])
            else:
                weekday_totals.append(day_data['total_interactions'])
        
        summary = f"- 日均交互次数：{avg_daily:.0f}\n"
        summary += f"- 最高单日：{max_daily}次\n"
        summary += f"- 最低单日：{min_daily}次\n"
        
        if weekday_totals and weekend_totals:
            avg_weekday = sum(weekday_totals) / len(weekday_totals)
            avg_weekend = sum(weekend_totals) / len(weekend_totals)
            summary += f"- 工作日平均：{avg_weekday:.0f}次\n"
            summary += f"- 周末平均：{avg_weekend:.0f}次\n"
        
        return summary
    
    def _analyze_hotspot_data(self, hotspot_data: List) -> str:
        """分析热点数据"""
        if not hotspot_data:
            return "无热点数据"
        
        total_active_days = len(hotspot_data)
        avg_active_cells = sum(day['total_cells'] for day in hotspot_data) / total_active_days if total_active_days > 0 else 0
        
        summary = f"- 有活动记录的天数：{total_active_days}天\n"
        summary += f"- 日均活跃区域数：{avg_active_cells:.0f}个\n"
        
        # 分析热点集中度
        if hotspot_data:
            recent_hotspots = hotspot_data[-1].get('active_areas', [])
            if recent_hotspots:
                primary_area = recent_hotspots[0]
                summary += f"- 主要活跃区域集中度：{primary_area['normalized_value']*100:.1f}%\n"
        
        return summary
    
    def _format_key_name(self, key_name: str) -> str:
        """格式化按键名称显示"""
        key_mapping = {
            'space': '空格',
            'enter': '回车',
            'backspace': '退格',
            'tab': 'Tab',
            'shift': '左Shift',
            'shift_r': '右Shift',
            'ctrl_l': '左Ctrl',
            'ctrl_r': '右Ctrl',
            'alt_l': '左Alt',
            'alt_r': '右Alt',
            'caps_lock': '大写锁定',
            'esc': 'Esc',
            'up': '↑',
            'down': '↓',
            'left': '←',
            'right': '→'
        }
        return key_mapping.get(key_name, key_name)
    
    def _format_mouse_button(self, button_name: str) -> str:
        """格式化鼠标按键名称显示"""
        button_mapping = {
            'mouse_left': '左键',
            'mouse_right': '右键',
            'mouse_middle': '中键',
            'mouse_x1': '侧键1',
            'mouse_x2': '侧键2',
            'scroll_up': '滚轮上滚',
            'scroll_down': '滚轮下滚'
        }
        return button_mapping.get(button_name, button_name)
    
    def call_bailian_api(self, prompt: str) -> Optional[str]:
        """
        调用百炼大模型API（使用OpenAI兼容格式）
        """
        print(70, "正在调用百炼大模型...")
        
        if not self.api_key:
            raise ValueError("未设置API密钥，请先配置DASHSCOPE_API_KEY环境变量")

        client = OpenAI(
            # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
            api_key=self.api_key,
            base_url=self.base_url,
        )
        
        # 使用OpenAI兼容的messages格式
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的用户行为分析师，请基于提供的键盘鼠标使用数据分析用户的操作习惯和行为特征。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            completion = client.chat.completions.create(
                # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
                model=self.model_name,
                messages=messages
            )

            result = completion.model_dump_json()
            if isinstance(result, str):
                result = json.loads(result)
            # OpenAI兼容格式的响应解析
            if 'choices' in result and len(result['choices']) > 0:
                choice = result['choices'][0]
                if 'message' in choice and 'content' in choice['message']:
                    print(90, "分析完成")
                    return choice['message']['content']
                elif 'delta' in choice and 'content' in choice['delta']:
                    # 流式响应处理
                    return choice['delta']['content']
            else:
                raise ValueError(f"API响应格式异常: {result}")
                
        except requests.exceptions.Timeout as e:
            raise ConnectionError(f"API请求超时: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"网络连接失败: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"网络请求失败: {str(e)}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"API响应解析失败: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"API调用失败: {str(e)}")
    
    def analyze(self, days: int = None) -> Dict:
        """
        执行完整分析流程（增强资源管理）
        """
        try:
            self.analysis_started.emit()
            
            # 1. 收集数据
            collected_data = self.collect_data(days)
            collected_data['hotspot_data'] = self.collect_hotspot_data(days)
            
            # 2. 准备分析提示词
            prompt = self.prepare_analysis_prompt(collected_data)
            
            # 3. 调用大模型
            analysis_result = self.call_bailian_api(prompt)
            
            # 4. 整合结果
            final_result = {
                'timestamp': datetime.now().isoformat(),
                'period': collected_data['period'],
                'raw_data_summary': {
                    'keyboard_total': sum(collected_data['keyboard_stats'].values()),
                    'mouse_total': sum(collected_data['mouse_stats'].values()),
                    'daily_records': len(collected_data['daily_summary'])
                },
                'ai_analysis': analysis_result,
                'collected_data': collected_data
            }
            
            self.analysis_completed.emit(final_result)
            return final_result
            
        except Exception as e:
            error_msg = f"分析过程出错: {str(e)}"
            self.analysis_error.emit(error_msg)
            raise
    
    def analyze_async(self, days: int = None):
        """
        异步执行分析（用于GUI线程）
        """
        # 如果已有工作线程在运行，先停止它
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.worker_thread.wait(3000)  # 等待最多3秒
            
        self.worker_thread = AnalysisWorker(self, days)
        self.worker_thread.analysis_completed.connect(self.analysis_completed)
        self.worker_thread.analysis_error.connect(self.analysis_error)
        self.worker_thread.progress_updated.connect(self.progress_updated)
        self.worker_thread.start()


class AnalysisWorker(QThread):
    """分析工作线程"""
    
    analysis_completed = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)
    progress_updated = pyqtSignal(int, str)
    
    def __init__(self, analyzer: BailianAnalyzer, days: int = None):
        super().__init__()
        self.analyzer = analyzer
        self.days = days
        self._is_running = True
        
    def stop(self):
        """安全停止线程"""
        self._is_running = False
        
    def run(self):
        try:
            # 连接进度信号
            self.analyzer.progress_updated.connect(self.progress_updated)
            
            # 检查是否应该继续运行
            if not self._is_running:
                return
            
            # 执行分析
            result = self.analyzer.analyze(self.days)
            
            # 检查是否应该继续运行
            if not self._is_running:
                return
                
            self.analysis_completed.emit(result)
            
        except Exception as e:
            if self._is_running:
                error_msg = f"分析过程出错: {str(e)}"
                self.analysis_error.emit(error_msg)
        finally:
            # 断开信号连接
            try:
                self.analyzer.progress_updated.disconnect(self.progress_updated)
            except:
                pass