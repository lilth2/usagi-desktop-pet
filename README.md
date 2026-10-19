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
| `TEXTURE_DISPLAY_W/H` | 贴图显示尺寸 | 90px（贴图）/ 120px（窗口） |
| `WINDOW_WIDTH/HEIGHT` | 窗口大小 | 90px（贴图）/ 120px（窗口） |
| `FRAME_INTERVAL` | 动画帧间隔 | 40ms (25FPS) |
| `WALK_INTERVAL_MIN/MAX` | 行走触发间隔 | 15-30s |
| `WALK_SPEED_MIN/MAX` | 行走速度 | 1 px/帧 |


## 轻量陪伴版

本项目基于 [ruochengwu/usagi-desktop-pet](https://github.com/ruochengwu/usagi-desktop-pet) 修改。

- 保留自动关怀、拖拽和小范围散步，已移除聊天功能。
- 右键打开乌萨奇风格菜单：角色头像、奶油黄背景、圆角、暖色悬停和圆形开关。
- 菜单中可以开关自动关怀、预览暖心话、开关散步及退出；打开菜单时暂停散步。

安装：`python -m pip install -r requirements.txt`，启动：`python desktop_pet.py`。
Windows 已配置本地虚拟环境时，可双击「启动乌萨奇.bat」。其他电脑请先运行 `python -m venv .venv`，再运行 `.venv\Scripts\python -m pip install -r requirements.txt`。


## 自动关怀与轻量走动

- 角色贴图从 200px 缩至 90px；每 15–30 秒走动一次，每次 8–14 秒，到左右边界自动折返。
- 始终限制在启动位置或最后拖放位置左右各 30px 内，避免连续走动漂移到屏幕中央。
- Windows 下读取系统「距离最后一次键鼠输入的时间」，每 10 秒检查一次。持续使用约 30 分钟弹出关怀气泡，10 秒后消失，不抢输入焦点。
- 连续 5 分钟无键鼠输入视为休息并重置计时；休眠或恢复造成的长采样间隔也重置。观看视频等没有键鼠操作的场景可能被视为空闲。
- 不读取输入内容，不判断真实情绪，不联网，不存储使用记录。非 Windows 平台不启用使用时长提醒。
- 10 句预设关怀包含休息、喝水、肩颈放松、安慰、鼓励和陪伴，每轮随机且不重复。
- 右键菜单可以关闭自动关怀、关闭走动，或点「送你一句暖心话 ♡」立即预览。开关仅对本次运行生效。
