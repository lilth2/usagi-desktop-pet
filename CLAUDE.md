# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

使用 PyQt5 + QPainter 矢量绘图的透明无边框桌面桌宠应用，无需任何外部图片资源。

## 运行与打包

```bash
pip install PyQt5
python desktop_pet.py          # 运行
pythonw desktop_pet.py         # Windows 无控制台窗口运行

# 打包为独立 exe
pip install pyinstaller
pyinstaller --onefile --windowed --name "DesktopPet" desktop_pet.py
```

## 架构

**单文件**: `desktop_pet.py`（~515 行），按注释区块分隔：

1. **常量配置** (L28-74) — 所有可调参数集中管理，包括窗口/身体尺寸、颜色、动画周期/幅度/速度、眨眼/Walk 定时范围
2. **`PetState` 枚举** — `IDLE` / `WALK` / `GRABBED` 三种状态
3. **`AnimationData` 类** — 每帧动画可变数据（浮动偏移、缩放、眨眼、Walk 摇摆/压扁、抓起缩放），`reset_for_idle()` 复位到默认值
4. **`DesktopPetWindow(QMainWindow)`** — 主窗口，包含三个子系统：
   - **状态机** (`_on_tick` → `_update_idle`/`_update_walk`/`_update_grabbed`) — 40ms 定时器驱动，`_enter_walk()` / `_enter_idle()` 处理状态切换
   - **绘制** (`paintEvent` → `_draw_shadow`/`_draw_body`/`_draw_highlight`/`_draw_eyes`/`_draw_mouth`) — QPainter 矢量绘制，贝塞尔曲线身体 + 渐变填充
   - **鼠标事件** — 左键拖拽进入 Grabbed 态，右键弹出退出菜单

**状态转换**: `IDLE ↔ WALK`（定时触发/行走结束），任何状态 → `GRABBED`（左键按下），`GRABBED` → `IDLE`（松开）

**关键设计点**:
- 所有动画用 `math.sin()` 正弦波驱动，无外部资源依赖
- 窗口置顶 + 透明背景 + 无边框实现"桌宠浮在桌面上"效果
- `Qt.Tool` 标志使窗口不出现在任务栏
- Grabbed 状态在 `paintEvent` 中走独立渲染路径（提前 return），不应用 Walk/Idle 的动画偏移
