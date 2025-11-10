import sys

from PyQt6.QtWidgets import QApplication
from gui.MainWindow import Win

# 设置应用程序在最后一个窗口关闭时不退出，这样托盘图标可以继续工作
QApplication.setQuitOnLastWindowClosed(False)

"""
启动程序
"""
if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = Win()
    mainWindow.show()
    # 添加以下代码确保窗口在最前端显示
    mainWindow.activateWindow()
    mainWindow.raise_()
    sys.exit(app.exec())