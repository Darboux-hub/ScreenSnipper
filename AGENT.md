# ScreenSnipper Agent Guide

本文件是 `ScreenSnipper` 仓库级协作契约，面向后续维护者、AI 工程代理与协作者。
它的目标不是重复产品介绍，而是统一开发约束、文档职责、打包发布流程和 GitHub 提交边界。

## 1. 项目定位

- 项目名称：`ScreenSnipper`
- 目标平台：`Windows 11`
- 开发语言：`Python 3.10+`
- GUI 技术栈：`PyQt5`
- 关键系统能力：
  - 全局热键截图
  - 全屏冻结与框选
  - 剪贴板输出
  - 托盘常驻
  - 悬浮窗入口
  - 开机自启动
  - `PyInstaller` 单文件 EXE 打包

## 2. 当前源码边界

源码仓库应只包含以下核心内容：

- `screen_snipper.py`
- `ScreenSnipper.spec`
- `assets/floating_button.png`
- `README.md`
- `AGENT.md`
- `LICENSE`
- `docs/DEVELOPMENT_LOG.md`
- `.gitignore`

以下内容属于本地开发或构建产物，禁止提交到 GitHub：

- `.build-venv/`
- `build/`
- `dist/`
- `__pycache__/`
- `*.pyc`
- IDE、系统和临时缓存文件

## 3. 代码约束

### 3.1 通用约束

- 所有源码与文档统一使用 `UTF-8` 编码。
- 任何修改涉及中文 UI 文本时，必须检查是否出现乱码回归。
- 项目当前以 `screen_snipper.py` 单文件主程序为核心，除非有明确收益，否则不要随意拆成多个模块。
- 保持“轻量常驻”设计，不引入不必要的后台线程、轮询器或长期大对象缓存。
- 截图流程必须全程内存处理，不允许写本地临时图片文件。

### 3.2 UI/交互约束

- 悬浮窗、托盘菜单和截图主流程必须保持行为一致。
- 无论通过悬浮窗点击、托盘菜单还是全局热键触发截图，悬浮窗都必须先隐藏，再开始抓屏。
- 截图完成或取消后，只有在用户未主动隐藏悬浮窗时才自动恢复显示。
- 热键修改必须先尝试注册，注册失败时必须回滚到旧热键并给出提示。
- 托盘菜单与悬浮窗右键菜单必须保持同一套核心动作。
- 悬浮窗图片资源与托盘图标应保持同源，不得随意分叉成不同品牌视觉。

### 3.3 平台约束

- 该项目当前只面向 `Windows 11`。
- Windows API、注册表、自启动与热键相关行为是当前实现的一部分，不需要为 macOS/Linux 做兼容层。

## 4. 文档职责与更新矩阵

以下文件是仓库的文档主入口，任何功能变更都要同步维护：

- `README.md`
  - 面向使用者和 GitHub 访问者
  - 负责介绍功能、运行方式、构建方式、目录结构和常见问题
- `docs/DEVELOPMENT_LOG.md`
  - 面向维护者
  - 负责记录按日期倒序排列的工程开发日志
- `LICENSE`
  - 负责授权说明
- `.gitignore`
  - 负责界定哪些文件不应进入 Git 仓库

### 更新规则

- 修改用户可见功能：
  - 必须更新 `README.md`
  - 必须追加 `docs/DEVELOPMENT_LOG.md`
- 修改打包方式、资源路径或构建入口：
  - 必须检查 `ScreenSnipper.spec`
  - 必须更新 `README.md` 的构建章节
  - 必须追加 `docs/DEVELOPMENT_LOG.md`
- 修改自启动、热键、悬浮窗或截图交互：
  - 必须确认 `README.md` 的功能说明和 FAQ 仍然准确
- 增加仓库新文件或新目录：
  - 必须确认 `.gitignore` 是否需要同步更新

## 5. 开发流程建议

### 5.1 修改前

- 先阅读：
  - `README.md`
  - `docs/DEVELOPMENT_LOG.md`
  - `screen_snipper.py`
  - `ScreenSnipper.spec`
- 确认本次修改是否影响：
  - 用户可见功能
  - 打包方式
  - 资源路径
  - GitHub 仓库边界

### 5.2 修改后最小检查

建议至少执行以下检查：

```powershell
python -m py_compile D:\ScreenShot\screen_snipper.py
```

如涉及打包，建议使用：

```powershell
D:\ScreenShot\.build-venv\Scripts\python -m PyInstaller --noconfirm --clean D:\ScreenShot\ScreenSnipper.spec
```

打包前必须确认没有正在运行的 `ScreenSnipper.exe`，否则 Windows 可能锁住 `dist\ScreenSnipper.exe`。

### 5.3 提交前检查

- 检查文档是否同步更新
- 检查中文是否乱码
- 检查资源路径是否仍可用于源码运行和打包运行
- 检查 `.gitignore` 是否覆盖本地产物
- 确认未把 `dist/`、`build/`、`.build-venv/` 等目录提交进 Git

## 6. GitHub 工作流约束

### 6.1 仓库初始化建议

首次上传到 GitHub 前，推荐流程：

```powershell
git init
git add .gitignore AGENT.md README.md LICENSE docs/DEVELOPMENT_LOG.md screen_snipper.py ScreenSnipper.spec assets/floating_button.png
git commit -m "chore: initialize ScreenSnipper repository"
```

### 6.2 推荐提交粒度

推荐按以下粒度提交：

- 一个功能改动一个提交
- 一组文档补充一个提交
- 构建/发布配置调整一个提交

避免把“功能改动 + 大量文档重写 + 打包产物”混在同一个提交里。

### 6.3 发布策略

- 源码仓库不提交 `dist/ScreenSnipper.exe`
- EXE 应通过 GitHub Release 分发，而不是直接进入源码仓库
- 发布前建议：
  - 更新 `README.md`
  - 追加 `docs/DEVELOPMENT_LOG.md`
  - 重新打包验证

## 7. 开发日志要求

`docs/DEVELOPMENT_LOG.md` 必须长期维护，采用工程日志而不是纯版本号变更表。

每条日志建议使用以下模板：

```md
## YYYY-MM-DD

### 背景
- 为什么做这次改动

### 改动
- 做了什么

### 验证
- 验证了什么

### 遗留 / 待办
- 还未解决的问题
```

日志按日期倒序追加，较新的内容放在前面。

## 8. README 最低要求

`README.md` 至少要覆盖：

- 中文项目简介
- English summary
- 功能清单
- 运行环境与依赖
- 从源码运行
- EXE 打包
- 目录结构
- FAQ
- License

如果 README 与真实实现不一致，应以修正文档为优先事项之一。

## 9. 已知维护提醒

- 当前项目历史上出现过中文乱码问题，后续修改任何中文字符串都要进行编码检查。
- 悬浮窗资源打包依赖 `ScreenSnipper.spec` 中的 `datas` 配置，修改资源路径时不要漏改。
- 悬浮窗首次定位、尺寸档位与热键配置都依赖 `QSettings`，涉及键名变更时要考虑兼容迁移。

