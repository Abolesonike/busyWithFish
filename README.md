# 🐟 Busy With Fish - 上班摸鱼神器 

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
<br>
✨ 摸鱼必备神器 ✨ 积累功德 ✨ 联机互动 ✨ 换肤体验 ✨

[![](https://img.shields.io/static/v1?label=%E2%AD%90&message=Star&style=social)](#)
[![](https://img.shields.io/static/v1?label=%F0%9F%8D%B4&message=Watch&style=social)](#)

</div>

---

## 🎯 项目简介

🐟 **Busy With Fish** 是一款专为上班族设计的摸鱼神器，让你在工作时悄悄积累功德，享受片刻放松！敲击键盘即可获得功德值，还可以与朋友联机互动，一起摸鱼修仙 😏

## 🌟 特色功能

### ✨ 积累功德系统
敲击任意按键，木鱼就会发出清脆的声音，同时功德值 +1 🙏
- 实时显示功德值
- 敲击后有特效提示
- 离线也能攒功德

### 💫 多种角色皮肤
- 🥉 **木鱼模式** - 经典版本，敲击木鱼积累功德
- 🥈 **Pop Cat模式** - 可爱的Pop Cat动画，更有趣的体验
- 🥇 **铁山靠模式** - 施工中，敬请期待

### 📊 数据统计功能
- 📈 **本地数据存储** - 所有数据均保存在本地，保护您的隐私
- 🗓️ **按日统计** - 自动记录每天的敲击次数和功德值
- 📅 **历史记录** - 查看过往日期的统计数据
- 🛡️ **隐私安全** - 数据完全离线存储，不会上传到任何服务器

### 🌐 联机互动功能
- 👥 **实时联机** - 与好友一起摸鱼
- 🔗 **UID匹配** - 通过UID连接到其他用户
- ⚡ **实时同步** - 对方敲击时你的界面也会响应
- 🌍 **云端服务** - 通过服务器连接全球摸鱼伙伴
后端服务器项目地址：https://github.com/Abolesonike/busyWithFishServer

### 🎨 便捷操作
- 🖱️ **拖拽移动** - 随意调整窗口位置
- 📌 **边缘吸附** - 自动吸附到屏幕边缘
- 🍃 **系统托盘** - 最小化到托盘，随时呼出
- ⌨️ **全局热键** - 随时随地敲击功德

## 🛠️ 技术栈

| 技术 | 说明 |
|------|------|
| [PyQt6](https://pypi.org/project/PyQt6/) | GUI框架，提供跨平台支持 |
| [pynput](https://pypi.org/project/pynput/) | 键盘监听，捕捉按键事件 |
| Python Socket | TCP通信，实现联机功能 |
| GIF动画 | 提供流畅的角色动画效果 |

## 📦 安装与运行

### 环境要求
- Python 3.8 或更高版本
- Windows/macOS/Linux

### 安装步骤

1. 克隆或下载项目：
```bash
git clone https://github.com/yourusername/busyWithFish.git
cd busyWithFish
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 运行程序：
```bash
python main.py
```

### 依赖列表
```txt
pyqt6-sip
pynput
```

## 🎮 使用指南

### 快速上手
1. 🚀 运行程序后，桌面会出现一个木鱼小窗口
2. ⌨️ 随意敲击键盘任意按键，木鱼会下沉并显示功德值
3. 🎯 点击系统托盘图标进行更多设置

### 托盘菜单功能
- **UID显示** - 显示你的唯一ID，用于联机
- **连接功能** - 输入他人UID建立连接
- **状态切换** - 在线/离线状态切换
- **角色切换** - 在木鱼/PopCat等模式间切换
- **显示/隐藏** - 快速显示或隐藏界面
- **退出** - 安全退出程序

### 联机玩法
1. 点击托盘图标 → 状态 → 在线
2. 点击连接 → 输入对方UID
3. 连接成功后，双方敲击键盘都会在对方界面产生动画效果
4. 开始愉快的联机摸鱼时光！

## 📝 更新日志

### 2026-01-27
- ✨ **新增数据统计功能**：添加了本地数据统计功能，记录每日敲击次数和功德值
- 🛡️ **隐私保护**：所有统计数据均保存在本地文件中，不会上传至任何服务器
- 📊 **按日统计**：支持查看每日的详细统计数据
- 📈 **历史记录**：可以查阅过往日期的敲击记录

## 🎨 界面预览

<div align="center">

| 功能 | 截图 |
|------|------|
| 木鱼模式 | 🐟 敲击时下沉+功德显示 |
| Pop Cat模式 | 🐱 可爱GIF动画效果 |
| 系统托盘 | 🍃 隐藏到托盘，随时呼出 |
| 联机互动 | 🌐 实时同步敲击效果 |

</div>

## 🌍 平台支持

| 平台 | 支持情况 | 构建脚本 |
|------|----------|----------|
| Windows | ✅ 完全支持 | 直接运行 |
| macOS | ✅ 完全支持 | build_mac.py |
| Linux | ✅ 基础支持 | 待测试 |

## 🤝 贡献指南

我们欢迎各种形式的贡献！ 🎉

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🎊 鸣谢

- PyQt6 提供强大的GUI支持
- pynput 实现键盘监听
- 所有开源社区贡献者

## 📞 联系方式

如果对项目有任何疑问或建议，欢迎随时联系！

---

<div align="center">

### 如果你觉得这个项目有趣，请给我一个 ⭐ Star！

> 🐟 *上班不摸鱼，下班徒伤悲*  
> 🙏 *积少成多，功德无量*  
> 🎮 *联机摸鱼，快乐加倍*

</div>
