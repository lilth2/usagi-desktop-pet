# 桌面桌宠 - 乌萨奇 (Usagi Pet)

基于 PyQt5 的透明无边框桌面桌宠，角色为 Chiikawa 系列的乌萨奇。

- 🖼️ 贴图渲染（支持 PNG + GIF 动画）
- 🫧 Idle 呼吸浮动 + Walk 随机走动摇摆
- 🖱️ 左键拖拽 + 右键退出
- 📦 可打包为独立 exe（无需 Python 环境）

## 快速使用

### 直接运行

```bash
pip install PyQt5
python desktop_pet.py
```

### 下载打包版（免 Python）

从 [Releases](https://github.com/ruochengwu/usagi-desktop-pet/releases) 下载 `UsagiPet.exe`，双击运行。

## 贴图文件

| 文件 | 用途 | 必需 |
|------|------|------|
| `usagi_idle.png` | Idle 站立 | ✅ |
| `usagi_walk1.gif` | Walk 行走动画 | 可选 |
| `usagi_walk2.png` | Walk 备用帧 | 可选 |
| `usagi_grabbed.gif` | 抓起表情 | 可选 |

替换为自己的贴图即可更换角色。

## 交互

| 操作 | 效果 |
|------|------|
| 左键拖拽 | 抓起宠物，缩小至 70%，跟随鼠标 |
| 右键点击 | 弹出菜单 → 退出程序 |
| 什么都不做 | Idle 浮动呼吸 + Walk 随机走动 |

## 自行打包

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "UsagiPet" ^
    --add-data "usagi_idle.png;." ^
    --add-data "usagi_walk1.gif;." ^
    --add-data "usagi_walk2.png;." ^
    --add-data "usagi_grabbed.gif;." ^
    desktop_pet.py
```

## 配置

编辑 `desktop_pet.py` 顶部常量区可调整：

| 常量 | 说明 | 默认值 |
|------|------|--------|
| `TEXTURE_DISPLAY_W/H` | 贴图显示尺寸 | 200px |
| `WINDOW_WIDTH/HEIGHT` | 窗口大小 | 200px |
| `FRAME_INTERVAL` | 动画帧间隔 | 40ms (25FPS) |
| `WALK_INTERVAL_MIN/MAX` | 行走触发间隔 | 3-8s |
| `WALK_SPEED_MIN/MAX` | 行走速度 | 3-5 px/帧 |


## 本地陪聊版

本项目基于 [ruochengwu/usagi-desktop-pet](https://github.com/ruochengwu/usagi-desktop-pet) 修改。

- 单击乌萨奇，或右键选择「聊聊天」，打开对话窗口。
- 输入文字后按回车或点发送；也可点「你好」「今天好累」「抱抱」快捷按钮。
- 根据问候、心情、学习、休息等关键词返回预设台词，无需 API 密钥，不联网，不是 AI 大模型。
- 聊天窗口打开时暂停触发新的随机走动；左键拖动仍然保留。
- 不保存聊天记录；关闭聊天窗口即清空。

安装：`python -m pip install -r requirements.txt`，启动：`python desktop_pet.py`。
Windows 已配置本地虚拟环境时，可双击「启动乌萨奇.bat」。其他电脑请先运行 `python -m venv .venv`，再运行 `.venv\Scripts\python -m pip install -r requirements.txt`。
