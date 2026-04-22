# ScreenSnipper

一个面向 Windows 11 的轻量级截图工具，支持全局热键、悬浮窗、系统托盘、开机自启、中英文切换，以及直接写入剪贴板的截图流程。

An ultra-lightweight screenshot tool for Windows 11 with global hotkeys, a floating launcher, system tray control, startup integration, bilingual UI, and in-memory clipboard capture.

## 下载

- 最新版本下载：
  [ScreenSnipper.exe](https://github.com/Darboux-hub/ScreenSnipper/releases/latest/download/ScreenSnipper.exe)
- 最新 Release 页面：
  [Releases](https://github.com/Darboux-hub/ScreenSnipper/releases)

## 界面预览

![ScreenSnipper Floating Button](assets/floating_button.png)

当前版本采用图片化悬浮入口，启动后默认显示在主显示器中央，可拖动、可隐藏，并与系统托盘共用控制菜单。

## 功能特性

- 全局热键触发截图
- 全屏冻结与拖拽框选
- `极简模式`：框选后立即复制到系统剪贴板
- `精调模式`：框选后保留冻结画面，可继续调整选区再复制
- 悬浮窗入口与系统托盘控制
- 悬浮窗支持拖动、三档大小和图片 UI
- 截图前自动隐藏悬浮窗，避免被截入结果
- 开机自启动开关
- 统一 `设置...` 窗口，支持语言、截图模式和热键管理
- 中英文界面切换，设置后立即生效
- 热键自定义并支持冲突回滚
- 使用 `PyInstaller` 打包单文件 EXE

## 快速开始

### 方式一：直接使用已打包 EXE

1. 从 Release 页面下载 `ScreenSnipper.exe`
2. 双击运行，程序会驻留后台并显示悬浮窗与托盘图标
3. 通过悬浮窗左键或全局热键开始截图

### 方式二：从源码运行

```powershell
pip install PyQt5
python D:\ScreenShot\screen_snipper.py
```

## 使用说明

### 截图入口

- 左键点击悬浮窗开始截图
- 或按下已配置的全局热键
- 或通过系统托盘菜单点击 `截图`

### 两种截图模式

- `极简模式`
  - 适合快速截图
  - 鼠标松开后立即把选区写入剪贴板
- `精调模式`
  - 适合需要二次微调的场景
  - 首次框选后保留冻结画面
  - 支持拖动选区、拖边拖角缩放、重新框选
  - 支持双击、回车或工具条 `完成` 按钮确认

### 设置入口

- 右键悬浮窗可打开菜单
- 托盘图标右键也可打开同一套菜单
- 通过 `设置...` 可统一调整：
  - 中英文语言
  - 截图模式
  - 全局热键

### 剪贴板行为

- 程序全程在内存中处理截图，不会生成临时图片文件
- 成功确认后，截图结果会直接写入系统剪贴板
- 可直接粘贴到聊天窗口、画图工具、Office 或其它支持图片粘贴的软件中

## 运行环境

- 操作系统：`Windows 11`
- Python：`3.10+`
- GUI：`PyQt5`
- 打包工具：`PyInstaller`（仅构建时需要）

## 依赖安装

```powershell
pip install PyQt5
pip install pyinstaller
```

如果你使用当前目录内的本地构建虚拟环境，也可以直接执行显式安装命令：

```powershell
D:\ScreenShot\.build-venv\Scripts\python -m pip install PyQt5 pyinstaller
```

## 从源码运行

```powershell
python D:\ScreenShot\screen_snipper.py
```

启动后程序会常驻后台，并显示悬浮窗与系统托盘图标。默认截图模式为 `精调模式`；如需更快的“一框即复制”流程，可在 `设置...` 中切换为 `极简模式`。

## 打包 EXE

推荐直接使用项目内的 `spec` 文件打包：

```powershell
pyinstaller --noconfirm --clean D:\ScreenShot\ScreenSnipper.spec
```

或使用本地构建虚拟环境：

```powershell
D:\ScreenShot\.build-venv\Scripts\python -m PyInstaller --noconfirm --clean D:\ScreenShot\ScreenSnipper.spec
```

构建完成后产物位于：

```text
D:\ScreenShot\dist\ScreenSnipper.exe
```

## 目录结构

以下是推荐上传到 GitHub 的最小源码结构：

```text
ScreenSnipper/
├─ screen_snipper.py
├─ ScreenSnipper.spec
├─ assets/
│  └─ floating_button.png
├─ docs/
│  └─ DEVELOPMENT_LOG.md
├─ AGENT.md
├─ README.md
├─ LICENSE
└─ .gitignore
```

## GitHub 仓库建议

源码仓库建议只提交源码、资源和文档，不提交以下本地产物：

- `.build-venv/`
- `build/`
- `dist/`
- `__pycache__/`
- `*.pyc`

建议将打包好的 `ScreenSnipper.exe` 通过 GitHub Release 分发，而不是直接提交到源码仓库。

## 常见问题

### 1. 为什么热键没有生效？

可能是默认热键被其他程序占用了。此时程序仍可通过悬浮窗或托盘截图，并可在 `设置...` 中重新设置热键。

### 2. 为什么截图里没有悬浮窗？

这是设计行为。无论通过悬浮窗还是热键触发截图，程序都会先隐藏悬浮窗，再开始抓屏，避免截图结果中包含它自己。

### 3. 打包为什么失败，提示无法覆盖 `ScreenSnipper.exe`？

通常是旧的 `ScreenSnipper.exe` 正在运行，Windows 锁住了 `dist` 中的文件。先退出正在运行的程序，再重新打包。

### 4. 为什么没有系统托盘图标？

如果当前会话不支持系统托盘，程序会初始化失败。该工具设计为桌面交互式会话使用，不支持无托盘环境。

### 5. 精调模式和极简模式有什么区别？

`极简模式` 会在鼠标松开后立刻把选区写入剪贴板；`精调模式` 会保留冻结画面，允许你继续拖动、缩放或重选截图框，再通过双击、回车或工具条按钮确认。

### 6. 为什么 GitHub 仓库里不建议提交 EXE？

因为构建产物体积大、变更频繁，不利于源码仓库维护。更推荐用 GitHub Release 托管打包好的 EXE。

## English Summary

ScreenSnipper is a lightweight Windows 11 screenshot utility with a floating launcher, system tray controls, global hotkeys, bilingual UI, and in-memory clipboard capture. It now supports both `Minimal Mode` for instant copy and `Refine Mode` for post-selection adjustment before copying. Download the latest standalone executable from the Release page if you do not want to run it from source.

## 维护文档

仓库文档职责如下：

- `AGENT.md`：仓库级协作契约与开发约束
- `docs/DEVELOPMENT_LOG.md`：工程开发日志
- `LICENSE`：开源协议
- `.gitignore`：Git 仓库边界

## License

本项目采用 `MIT License`。

## 致谢

- `PyQt5`
- Windows 原生 `RegisterHotKey` / GDI 截图能力
- `PyInstaller`
