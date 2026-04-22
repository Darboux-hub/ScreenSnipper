# ScreenSnipper

一个面向 Windows 11 的轻量级截图工具，支持全局热键、悬浮窗、系统托盘、开机自启和直接写入剪贴板。

An ultra-lightweight screenshot tool for Windows 11 with global hotkeys, floating launcher, system tray control, startup integration, and in-memory clipboard output.

## 功能特性

- 全局热键触发截图
- 全屏冻结与拖拽框选
- 截图结果直接写入系统剪贴板
- 悬浮窗入口与系统托盘控制
- 悬浮窗支持拖动、三档大小和图片 UI
- 截图前自动隐藏悬浮窗，避免被截入结果
- 开机自启动开关
- 热键自定义并支持冲突回滚
- 使用 `PyInstaller` 打包单文件 EXE

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

启动后程序会常驻后台，并显示悬浮窗与系统托盘图标。

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

可能是默认热键被其他程序占用了。此时程序仍可通过悬浮窗或托盘截图，并可在菜单中重新设置热键。

### 2. 为什么截图里没有悬浮窗？

这是设计行为。无论通过悬浮窗还是热键触发截图，程序都会先隐藏悬浮窗，再开始抓屏，避免截图结果中包含它自己。

### 3. 打包为什么失败，提示无法覆盖 `ScreenSnipper.exe`？

通常是旧的 `ScreenSnipper.exe` 正在运行，Windows 锁住了 `dist` 中的文件。先退出正在运行的程序，再重新打包。

### 4. 为什么没有系统托盘图标？

如果当前会话不支持系统托盘，程序会初始化失败。该工具设计为桌面交互式会话使用，不支持无托盘环境。

### 5. 为什么 GitHub 仓库里不建议提交 EXE？

因为构建产物体积大、变更频繁，不利于源码仓库维护。更推荐用 GitHub Release 托管打包好的 EXE。

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
