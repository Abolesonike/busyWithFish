# 获取资源文件绝对路径
import os
import secrets
import sys


def get_resource_path( relative_path):
    """获取资源文件的绝对路径，支持开发环境和打包环境"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def generate_uid(length=8):
    """生成一个指定长度的UID"""
    return secrets.token_hex(length // 2 + 1)[:length]