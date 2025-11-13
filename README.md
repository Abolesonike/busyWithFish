# busyWithFish

这是一个有趣的桌面应用程序，包含一个木鱼和一个可以互动的角色。

## 跨平台构建说明

由于PyInstaller不支持跨平台编译，即不能在Windows上直接生成Mac可执行文件，也不能在Mac上生成Windows可执行文件。为了实现跨平台构建，我们提供了以下几种解决方案：

### 方案一：使用GitHub Actions自动化构建（推荐）

项目包含了GitHub Actions工作流配置文件，可以自动构建所有平台的可执行文件：

1. 将代码推送到GitHub仓库
2. GitHub Actions会自动为Windows、Mac和Linux构建相应的可执行文件
3. 构建完成后可以在Actions页面下载各平台的可执行文件

### 方案二：在目标平台本地构建

#### 构建Mac版本
在Mac系统上执行以下命令：
```bash
pip install -r requirements-mac.txt
python build_mac.py
```

这将会生成Mac应用程序包，位于`dist`目录下。

#### 构建Windows版本
在Windows系统上执行以下命令：
```cmd
pip install -r requirements.txt
pyinstaller busyWithFish.spec
```

### 方案三：使用虚拟机或云服务

如果无法访问物理Mac设备，可以考虑使用以下方法：
1. Mac虚拟机（如VMware或VirtualBox）
2. 云服务（如AWS EC2上的Mac实例）

## 项目结构

- `main.py`: 程序入口点
- `gui/`: 图形界面相关代码
- `character/`: 角色相关的组件
- `utils/`: 工具类和网络通信模块
- `resource/`: 图片、声音等资源文件

## 依赖

- Python 3.8+
- PyQt6
- pynput
- netstruct