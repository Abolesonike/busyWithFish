from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextOption
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QPushButton, QProgressBar, QFrame,
    QWidget, QSplitter, QTextBrowser
)
import json
from datetime import datetime
import markdown


class AnalysisResultDialog(QDialog):
    """
    AI分析结果展示对话框（支持Markdown格式）
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("键盘鼠标使用AI分析报告")
        self.setModal(True)
        self.resize(800, 400)
        
        # 存储分析结果
        self.analysis_result = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("📊 键盘鼠标使用行为AI分析报告")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 进度条（初始隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("正在分析...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧面板 - 概要信息
        left_panel = self.create_summary_panel()
        splitter.addWidget(left_panel)
        
        # 右侧面板 - 详细分析（支持Markdown）
        right_panel = self.create_markdown_detail_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割比例
        splitter.setSizes([300, 500])
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("💾 保存报告")
        self.save_button.clicked.connect(self.save_report)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def create_summary_panel(self) -> QWidget:
        """创建左侧概要面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # 面板标题
        title = QLabel("📈 数据概览")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 统计信息显示
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(200)
        layout.addWidget(self.summary_text)
        
        # 时间范围
        self.period_label = QLabel()
        layout.addWidget(self.period_label)
        
        return panel
    
    def create_detail_panel(self) -> QWidget:
        """创建右侧详细分析面板（原始版本）"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # 面板标题
        title = QLabel("🤖 AI分析结果")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 分析结果显示
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        layout.addWidget(self.result_text)
        
        return panel
    
    def create_markdown_detail_panel(self) -> QWidget:
        """创建支持Markdown的右侧详细分析面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # 面板标题
        title = QLabel("🤖 AI分析结果（Markdown格式）")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Markdown渲染的分析结果显示
        self.markdown_result_browser = QTextBrowser()
        self.markdown_result_browser.setOpenExternalLinks(True)  # 允许打开外部链接
        self.markdown_result_browser.setOpenLinks(True)
        layout.addWidget(self.markdown_result_browser)
        
        return panel
    
    def show_progress(self, show: bool = True):
        """显示/隐藏进度条"""
        self.progress_bar.setVisible(show)
        self.status_label.setVisible(not show)
        
    def update_progress(self, percentage: int, message: str):
        """更新进度"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)
        
    def show_analysis_result(self, result: dict):
        """显示分析结果"""
        self.analysis_result = result
        
        # 更新概要信息
        self.update_summary(result)
        
        # 更新Markdown格式的详细分析
        self.update_markdown_detail(result)
        
        # 启用保存按钮
        self.save_button.setEnabled(True)
        
        # 隐藏进度条
        self.show_progress(False)
        
    def update_summary(self, result: dict):
        """更新数据概要"""
        if 'raw_data_summary' in result:
            summary = result['raw_data_summary']
            period = result['period']
            
            summary_text = f"""总按键次数: {summary.get('keyboard_total', 0)}
总鼠标点击: {summary.get('mouse_total', 0)}
记录天数: {summary.get('daily_records', 0)}

分析周期: {period['start_date']} 至 {period['end_date']}
分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            
            self.summary_text.setPlainText(summary_text)
            self.period_label.setText(f"📅 分析周期: {period['start_date']} 至 {period['end_date']}")
    
    def update_detail(self, result: dict):
        """更新详细分析结果（原始版本）"""
        if 'ai_analysis' in result:
            self.result_text.setPlainText(result['ai_analysis'])
        else:
            self.result_text.setPlainText("暂无分析结果")
    
    def update_markdown_detail(self, result: dict):
        """更新Markdown格式的详细分析结果"""
        if 'ai_analysis' in result and result['ai_analysis']:
            markdown_text = result['ai_analysis']
            
            # 使用markdown库转换为HTML
            try:
                html_content = markdown.markdown(
                    markdown_text,
                    extensions=['fenced_code', 'tables', 'nl2br'],
                    output_format='html'
                )
                
                # 设置CSS样式
                styled_html = f"""
                <style>
                    body {{
                        font-family: "Microsoft YaHei", Arial, sans-serif;
                        font-size: 14px;
                        line-height: 1.6;
                        color: #333;
                    }}
                    h1, h2, h3, h4, h5, h6 {{
                        color: #2c3e50;
                        margin-top: 1.5em;
                        margin-bottom: 0.5em;
                    }}
                    h1 {{ font-size: 24px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                    h2 {{ font-size: 20px; border-bottom: 1px solid #bdc3c7; padding-bottom: 8px; }}
                    h3 {{ font-size: 18px; }}
                    p {{ margin: 0.8em 0; }}
                    ul, ol {{ margin: 0.8em 0; padding-left: 2em; }}
                    li {{ margin: 0.3em 0; }}
                    code {{
                        background-color: #f8f9fa;
                        padding: 2px 4px;
                        border-radius: 3px;
                        font-family: "Consolas", "Courier New", monospace;
                        font-size: 13px;
                    }}
                    pre {{
                        background-color: #f8f9fa;
                        padding: 12px;
                        border-radius: 5px;
                        border-left: 4px solid #3498db;
                        overflow-x: auto;
                        margin: 1em 0;
                    }}
                    pre code {{
                        background-color: transparent;
                        padding: 0;
                        border-radius: 0;
                    }}
                    blockquote {{
                        border-left: 4px solid #bdc3c7;
                        margin: 1em 0;
                        padding-left: 16px;
                        color: #7f8c8d;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 1em 0;
                    }}
                    th, td {{
                        border: 1px solid #bdc3c7;
                        padding: 8px 12px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #ecf0f1;
                        font-weight: bold;
                    }}
                    tr:nth-child(even) {{
                        background-color: #f8f9fa;
                    }}
                </style>
                {html_content}
                """
                
                self.markdown_result_browser.setHtml(styled_html)
                
            except Exception as e:
                # 如果Markdown转换失败，回退到纯文本显示
                print(f"Markdown转换失败: {e}")
                self.markdown_result_browser.setPlainText(markdown_text)
        else:
            self.markdown_result_browser.setPlainText("暂无分析结果")
    
    def save_report(self):
        """保存分析报告"""
        if not self.analysis_result:
            return
            
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtCore import QDateTime
        
        # 生成默认文件名
        timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
        default_filename = f"键盘鼠标分析报告_{timestamp}.json"
        
        # 选择保存路径
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存分析报告",
            default_filename,
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            try:
                # 保存为JSON格式
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.analysis_result, f, ensure_ascii=False, indent=2)
                
                # 显示成功消息
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "保存成功",
                    f"分析报告已保存至:\n{filename}"
                )
                
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self,
                    "保存失败",
                    f"保存报告时发生错误:\n{str(e)}"
                )
    
    def show_error(self, error_message: str):
        """显示错误信息"""
        self.status_label.setText(f"❌ {error_message}")
        self.result_text.setPlainText(f"分析过程中发生错误:\n\n{error_message}")
        self.show_progress(False)


class LoadingDialog(QDialog):
    """
    加载对话框 - 显示分析进度
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("正在分析...")
        self.setModal(True)
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("🤖 AI智能分析")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 进度条
        # self.progress_bar = QProgressBar()
        # self.progress_bar.setRange(0, 100)
        # layout.addWidget(self.progress_bar)
        
        # 状态文本
        self.status_label = QLabel("正在分析，需要一段时间 ...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(cancel_button)
        
    def update_progress(self, percentage: int, message: str):
        """更新进度"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)