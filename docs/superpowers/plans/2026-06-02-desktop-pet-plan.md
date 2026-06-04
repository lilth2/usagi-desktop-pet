# 桌面桌宠应用 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个使用 PyQt5 + QPainter 矢量绘制的透明无边框桌面桌宠应用（蓝绿渐变史莱姆）

**Architecture:** 单文件 `desktop_pet.py`，包含配置常量、状态枚举、动画数据容器、桌宠窗口类（含状态机+绘制+事件处理）、主入口。所有渲染通过 QPainter 矢量绘制。

**Tech Stack:** Python 3, PyQt5

---

## 文件结构

```
desktop_pet/
├── desktop_pet.py          # 主程序（单文件）
└── docs/superpowers/
    ├── specs/2026-06-02-desktop-pet-design.md
    └── plans/2026-06-02-desktop-pet-plan.md
```

## 职责划分

`desktop_pet.py` 内部按注释分隔为以下区块:
1. **导入与常量** — 所有配置参数集中管理
2. **PetState 枚举** — 三种状态定义
3. **AnimationData 类** — 每帧动画可变数据的容器
4. **DesktopPetWindow 类** — 主窗口，含状态机、绘制、事件处理
5. **main()** — 入口

---

### Task 1: 项目骨架 — 导入、常量与主入口

**Files:**
- Create: `D:/desktop_pet/desktop_pet.py`

- [ ] **Step 1: 创建文件骨架**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桌面桌宠 - 蓝绿渐变果冻史莱姆
使用 PyQt5 + QPainter 矢量绘图构建的透明无边框桌面宠物应用

运行方式:
    pip install PyQt5
    python desktop_pet.py

打包方式:
    pip install pyinstaller
    pyinstaller --onefile --windowed desktop_pet.py
"""

import sys
import math
import random
from enum import Enum

from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QAction
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import (
    QPainter, QBrush, QColor, QLinearGradient,
    QPainterPath, QPen, QFont
)

# ============================================================================
# 常量配置
# ============================================================================

# 窗口尺寸
WINDOW_WIDTH = 200
WINDOW_HEIGHT = 200

# 宠物主体尺寸（正常状态下的绘制基准）
BODY_WIDTH = 130
BODY_HEIGHT = 140

# 渐变颜色：蓝绿渐变
COLOR_TOP = QColor(0x48, 0xC9, 0xB0)    # 浅绿 #48C9B0
COLOR_BOTTOM = QColor(0x34, 0x98, 0xDB)  # 浅蓝 #3498DB

# 动画帧间隔 (ms)，约 25 FPS
FRAME_INTERVAL = 40

# Idle 动画参数
IDLE_FLOAT_PERIOD = 2000       # 浮动周期 ms
IDLE_FLOAT_AMPLITUDE = 9       # 浮动幅度 px
IDLE_BREATH_RANGE = 0.05       # 呼吸缩放范围 ±5%

# 眨眼参数
BLINK_INTERVAL_MIN = 2000      # 最小眨眼间隔 ms
BLINK_INTERVAL_MAX = 4000      # 最大眨眼间隔 ms
BLINK_DURATION = 80            # 闭眼持续 ms (约2帧)

# Walk 动画参数
WALK_INTERVAL_MIN = 3000       # 最小行走触发间隔 ms
WALK_INTERVAL_MAX = 8000       # 最大行走触发间隔 ms
WALK_DURATION_MIN = 2000       # 最短行走时长 ms
WALK_DURATION_MAX = 5000       # 最长行走时长 ms
WALK_SPEED_MIN = 3             # 最小行走速度 px/帧
WALK_SPEED_MAX = 5             # 最大行走速度 px/帧
WALK_WOBBLE_PERIOD = 500       # 行走身体摇摆周期 ms
WALK_WOBBLE_AMPLITUDE = 3      # 行走身体摇摆幅度 px
WALK_SQUASH_PERIOD = 250       # 行走压扁/拉伸周期 ms
WALK_SQUASH_RANGE = 0.1        # 行走压扁范围

# 抓起状态参数
GRAB_SCALE = 0.7               # 抓起时缩放比例

# 宠物在窗口中的绘制中心
BODY_CENTER_X = WINDOW_WIDTH // 2   # 100
BODY_CENTER_Y = WINDOW_HEIGHT // 2  # 100


def main():
    """应用入口"""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    pet = DesktopPetWindow()
    pet.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 验证可运行（预期报错 DesktopPetWindow 未定义）**

```bash
python desktop_pet.py
```

Expected: `NameError: name 'DesktopPetWindow' is not defined`

---

### Task 2: 状态枚举与动画数据容器

**Files:**
- Modify: `D:/desktop_pet/desktop_pet.py` — 在常量区块之后、DesktopPetWindow 之前插入

- [ ] **Step 1: 添加 PetState 和 AnimationData**

在 `# 宠物在窗口中的绘制中心` 行之后、`def main():` 行之前插入:

```python
# ============================================================================
# 状态枚举
# ============================================================================

class PetState(Enum):
    """宠物状态枚举"""
    IDLE = 0
    WALK = 1
    GRABBED = 2


# ============================================================================
# 动画数据容器
# ============================================================================

class AnimationData:
    """保存每帧动画所需的所有动态数据，集中管理避免散落在窗口类中"""
    
    def __init__(self):
        # Idle 动画
        self.float_offset_y = 0.0      # 身体浮动 Y 偏移
        self.breath_scale = 1.0        # 呼吸缩放因子
        
        # 眨眼
        self.is_blinking = False       # 当前是否闭眼
        self.blink_timer_ms = 0        # 眨眼阶段计时
        
        # Walk 动画
        self.walk_dir = 1              # 行走方向: 1=右, -1=左
        self.walk_speed = 4            # 行走速度 px/帧
        self.walk_wobble_offset = 0.0  # 行走身体左右摇摆 X 偏移
        self.walk_squash = 1.0         # 行走压扁/拉伸因子 (>1=压扁宽, <1=拉伸高)
        
        # Grabbed 动画
        self.grab_scale = 1.0          # 抓起缩放 (1.0 → GRAB_SCALE 平滑过渡)
    
    def reset_for_idle(self):
        """复位到 Idle 默认值"""
        self.walk_wobble_offset = 0.0
        self.walk_squash = 1.0
        self.walk_dir = 1
        self.is_blinking = False
        self.blink_timer_ms = 0
```

- [ ] **Step 2: 验证语法正确**

```bash
python -c "from desktop_pet import PetState, AnimationData; print('OK:', PetState.IDLE, AnimationData())"
```

Expected: `OK: PetState.IDLE <...AnimationData object...>`

---

### Task 3: 窗口框架 — 透明无边框置顶

**Files:**
- Modify: `D:/desktop_pet/desktop_pet.py` — 在 AnimationData 之后、main() 之前添加 DesktopPetWindow 基础框架

- [ ] **Step 1: 添加 DesktopPetWindow 基础框架**

```python
# ============================================================================
# 桌宠主窗口
# ============================================================================

class DesktopPetWindow(QMainWindow):
    """透明无边框桌宠窗口，负责状态机、事件处理和绘制调度"""
    
    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_state()
        self._setup_timer()
    
    def _setup_window(self):
        """配置透明无边框置顶窗口"""
        self.setWindowFlags(
            Qt.FramelessWindowHint       # 无边框
            | Qt.WindowStaysOnTopHint    # 置顶
            | Qt.Tool                     # 不在任务栏显示独立图标
        )
        self.setAttribute(Qt.WA_TranslucentBackground)  # 透明背景
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # 定位到屏幕右下角（留 50px 边距）
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.right() - WINDOW_WIDTH - 50,
            screen.bottom() - WINDOW_HEIGHT - 50
        )
        
        # 拖拽相关变量
        self._dragging = False
        self._drag_offset = QPoint()
    
    def _setup_state(self):
        """初始化状态机变量"""
        self._state = PetState.IDLE
        self._anim = AnimationData()
        self._state_timer_ms = 0          # 当前状态已持续毫秒
        
        # Idle 状态下需要的随机定时器
        self._next_blink_ms = random.randint(BLINK_INTERVAL_MIN, BLINK_INTERVAL_MAX)
        self._next_walk_ms = random.randint(WALK_INTERVAL_MIN, WALK_INTERVAL_MAX)
        
        # Walk 状态参数
        self._walk_duration_ms = 0
    
    def _setup_timer(self):
        """启动动画驱动定时器，每 FRAME_INTERVAL ms 触发一帧"""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(FRAME_INTERVAL)
    
    def paintEvent(self, event):
        """绘制事件：暂为空，后续任务填充"""
        pass
```

- [ ] **Step 2: 运行验证 — 窗口出现但为空白**

```bash
python desktop_pet.py
```

Expected: 屏幕右下角出现一个 200x200 的透明窗口（看不到内容因为还没绘制），按 Alt+F4 关闭

---

### Task 4: 身体渲染 — 渐变史莱姆身体 + 阴影 + 高光

**Files:**
- Modify: `D:/desktop_pet/desktop_pet.py` — 替换 paintEvent 并添加绘制方法

- [ ] **Step 1: 替换 paintEvent 模板，添加绘制方法**

在 DesktopPetWindow 类中，替换 `paintEvent` 并添加 3 个绘制方法:

```python
    # ========================================================================
    # 绘制系统
    # ========================================================================
    
    def paintEvent(self, event):
        """主绘制入口：按图层顺序绘制宠物"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 将原点平移到窗口中心（后续绘制都相对于此中心）
        painter.translate(BODY_CENTER_X, BODY_CENTER_Y)
        
        # 应用动画 Y 偏移
        painter.translate(0, self._anim.float_offset_y)
        
        scale_x = self._anim.breath_scale
        scale_y = self._anim.breath_scale
        
        self._draw_shadow(painter, scale_x, scale_y)
        self._draw_body(painter, scale_x, scale_y)
        self._draw_highlight(painter, scale_x, scale_y)
        
        painter.end()
    
    def _draw_shadow(self, painter, scale_x, scale_y):
        """绘制底部投影 — 深色半透明扁椭圆"""
        painter.save()
        shadow_w = int(BODY_WIDTH * scale_x * 0.75)
        shadow_h = 10
        shadow_y = int(BODY_HEIGHT * scale_y * 0.42)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 35))  # 半透明黑色
        painter.drawEllipse(-shadow_w // 2, shadow_y, shadow_w, shadow_h)
        painter.restore()
    
    def _draw_body(self, painter, scale_x, scale_y):
        """绘制史莱姆身体 — 水滴形贝塞尔曲线 + 蓝绿渐变填充"""
        painter.save()
        
        body_w = int(BODY_WIDTH * scale_x)
        body_h = int(BODY_HEIGHT * scale_y)
        half_w = body_w // 2
        half_h = body_h // 2
        
        # 线性渐变：从上到下，浅绿 → 浅蓝
        gradient = QLinearGradient(0, -half_h, 0, half_h)
        gradient.setColorAt(0.0, COLOR_TOP)
        gradient.setColorAt(1.0, COLOR_BOTTOM)
        
        # 水滴形路径：顶部窄，底部宽，模拟果冻Q弹感
        path = QPainterPath()
        path.moveTo(0, -half_h)  # 顶部中心
        
        # 右侧曲线 — 向外鼓出，底部更宽
        path.cubicTo(
            half_w + 12, -half_h,        # 控制点1: 右上外扩
            half_w + 15, half_h * 0.5,   # 控制点2: 中段外扩
            half_w, half_h               # 终点: 右下
        )
        # 底部弧线 — 略向下凹
        path.quadTo(0, half_h + 6, -half_w, half_h)
        # 左侧曲线 — 与右侧对称
        path.cubicTo(
            -half_w - 15, half_h * 0.5,
            -half_w - 12, -half_h,
            0, -half_h
        )
        path.closeSubpath()
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawPath(path)
        painter.restore()
    
    def _draw_highlight(self, painter, scale_x, scale_y):
        """绘制左上角高光 — 白色半透明椭圆，模拟果冻反光"""
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 55))  # 白色半透明
        hl_w = int(35 * scale_x)
        hl_h = int(22 * scale_y)
        hl_x = int(-BODY_WIDTH * scale_x * 0.28)
        hl_y = int(-BODY_HEIGHT * scale_y * 0.28)
        painter.rotate(-15)  # 稍微旋转让高光更自然
        painter.drawEllipse(hl_x, hl_y, hl_w, hl_h)
        painter.restore()
```

- [ ] **Step 2: 运行验证 — 看到蓝绿渐变史莱姆身体**

```bash
python desktop_pet.py
```

Expected: 屏幕右下角出现一个蓝绿渐变的水滴形身体，带投影和高光，静止不动

---

### Task 5: 五官渲染 — 眼睛、嘴巴及状态变体

**Files:**
- Modify: `D:/desktop_pet/desktop_pet.py` — 在 paintEvent 中添加五官绘制调用，添加对应方法

- [ ] **Step 1: 在 paintEvent 中添加五官绘制调用**

在 `self._draw_highlight(painter, scale_x, scale_y)` 之后、`painter.end()` 之前添加:

```python
        self._draw_eyes(painter, scale_x, scale_y)
        self._draw_mouth(painter, scale_x, scale_y)
```

- [ ] **Step 2: 添加眼睛绘制方法**

```python
    def _draw_eyes(self, painter, scale_x, scale_y):
        """绘制眼睛：
        - 正常：黑色实心圆
        - 眨眼：黑色横线
        - 抓起(X_X)：交叉十字线
        """
        painter.save()
        eye_spacing = int(25 * scale_x)  # 两眼间距
        eye_y = int(-BODY_HEIGHT * scale_y * 0.12)  # 眼睛垂直位置（身体上半部）
        left_x = -eye_spacing
        right_x = eye_spacing
        
        eye_pen = QPen(QColor(40, 40, 40), 2)  # 深灰色线条
        
        if self._state == PetState.GRABBED:
            # X_X 交叉眼
            painter.setPen(eye_pen)
            self._draw_x_eye(painter, left_x, eye_y, int(6 * scale_x))
            self._draw_x_eye(painter, right_x, eye_y, int(6 * scale_x))
        elif self._anim.is_blinking:
            # 眨眼 — 横线
            painter.setPen(QPen(QColor(40, 40, 40), 2))
            line_half = int(8 * scale_x)
            painter.drawLine(left_x - line_half, eye_y, left_x + line_half, eye_y)
            painter.drawLine(right_x - line_half, eye_y, right_x + line_half, eye_y)
        else:
            # 正常 — 实心圆（眼珠）
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(45, 45, 45))
            eye_r = int(6 * scale_x)
            painter.drawEllipse(QPoint(left_x, eye_y), eye_r, eye_r + 1)   # 略扁的椭圆眼
            painter.drawEllipse(QPoint(right_x, eye_y), eye_r, eye_r + 1)
        painter.restore()
    
    def _draw_x_eye(self, painter, cx, cy, size):
        """绘制单个 X 眼"""
        painter.drawLine(cx - size, cy - size, cx + size, cy + size)
        painter.drawLine(cx + size, cy - size, cx - size, cy + size)
```

- [ ] **Step 3: 添加嘴巴绘制方法**

```python
    def _draw_mouth(self, painter, scale_x, scale_y):
        """绘制嘴巴：
        - 正常：微笑弧线 (drawArc 下半弧)
        - 抓起：波浪线
        """
        painter.save()
        mouth_y = int(BODY_HEIGHT * scale_y * 0.08)  # 嘴巴垂直位置
        mouth_hw = int(18 * scale_x)  # 嘴巴半宽
        
        painter.setPen(QPen(QColor(55, 55, 55), 2))
        painter.setBrush(Qt.NoBrush)
        
        if self._state == PetState.GRABBED:
            # 波浪线 — 贝塞尔曲线
            path = QPainterPath()
            path.moveTo(-mouth_hw, mouth_y)
            path.cubicTo(
                -mouth_hw // 2, mouth_y + 7,
                mouth_hw // 2, mouth_y - 5,
                mouth_hw, mouth_y
            )
            painter.drawPath(path)
        else:
            # 微笑 — 弧线参数: (x, y, w, h, start_angle, span_angle)
            # start_angle=0 表示从3点钟方向开始，span_angle=180*16 表示下半弧
            arc_rect = (-mouth_hw, mouth_y - 6, mouth_hw * 2, 14)
            painter.drawArc(arc_rect, 0, 180 * 16)
        
        painter.restore()
```

- [ ] **Step 4: 运行验证 — 看到完整五官的史莱姆**

```bash
python desktop_pet.py
```

Expected: 蓝绿渐变史莱姆有眼睛（黑色实心圆）、微笑嘴巴，静止在屏幕右下角

---

### Task 6: Idle 动画 — 浮动、呼吸、眨眼

**Files:**
- Modify: `D:/desktop_pet/desktop_pet.py` — 添加 `_on_tick` 和 `_update_idle` 方法，完善状态机框架

- [ ] **Step 1: 添加动画更新框架和 Idle 逻辑**

在 DesktopPetWindow 类中添加以下方法（放在 `_setup_timer` 之后、`paintEvent` 之前）:

```python
    # ========================================================================
    # 动画状态机
    # ========================================================================
    
    def _on_tick(self):
        """每帧调用：更新动画参数并触发重绘"""
        self._state_timer_ms += FRAME_INTERVAL
        
        if self._state == PetState.IDLE:
            self._update_idle()
        elif self._state == PetState.WALK:
            self._update_walk()
        elif self._state == PetState.GRABBED:
            self._update_grabbed()
        
        self.update()  # 触发 paintEvent
    
    def _update_idle(self):
        """更新 Idle 动画参数：浮动、呼吸缩放、眨眼"""
        t = self._state_timer_ms
        anim = self._anim
        
        # 身体浮动: sin(2π * t / 2000) * 9px
        anim.float_offset_y = math.sin(t * 2 * math.pi / IDLE_FLOAT_PERIOD) * IDLE_FLOAT_AMPLITUDE
        
        # 呼吸缩放: 1.0 + sin(...) * 0.05
        anim.breath_scale = 1.0 + math.sin(t * 2 * math.pi / IDLE_FLOAT_PERIOD) * IDLE_BREATH_RANGE
        
        # 眨眼逻辑
        anim.blink_timer_ms += FRAME_INTERVAL
        
        if anim.is_blinking:
            # 闭眼持续 BLINK_DURATION ms 后睁开
            if anim.blink_timer_ms >= BLINK_DURATION:
                anim.is_blinking = False
                anim.blink_timer_ms = 0
                self._next_blink_ms = random.randint(BLINK_INTERVAL_MIN, BLINK_INTERVAL_MAX)
        else:
            # 等待下次眨眼时机
            if anim.blink_timer_ms >= self._next_blink_ms:
                anim.is_blinking = True
                anim.blink_timer_ms = 0
        
        # Walk 触发检查
        if self._state_timer_ms >= self._next_walk_ms:
            self._enter_walk()
    
    def _enter_walk(self):
        """进入 Walk 状态"""
        self._state = PetState.WALK
        self._state_timer_ms = 0
        
        anim = self._anim
        anim.walk_dir = random.choice([-1, 1])
        anim.walk_speed = random.randint(WALK_SPEED_MIN, WALK_SPEED_MAX)
        
        self._walk_duration_ms = random.randint(WALK_DURATION_MIN, WALK_DURATION_MAX)
    
    def _update_walk(self):
        """Walk 动画占位 — 下个任务实现"""
        pass
    
    def _update_grabbed(self):
        """Grabbed 动画占位 — 下下个任务实现"""
        pass
    
    def _enter_idle(self):
        """回到 Idle 状态，重置相关参数"""
        self._state = PetState.IDLE
        self._state_timer_ms = 0
        self._anim.reset_for_idle()
        self._next_blink_ms = random.randint(BLINK_INTERVAL_MIN, BLINK_INTERVAL_MAX)
        self._next_walk_ms = random.randint(WALK_INTERVAL_MIN, WALK_INTERVAL_MAX)
```

- [ ] **Step 2: 运行验证 — 史莱姆开始呼吸浮动**

```bash
python desktop_pet.py
```

Expected: 史莱姆上下浮动（正弦波）、身体微微缩放呼吸、每2-4秒眨眼一次。约3-8秒后尝试进入 Walk（但因为没有移动逻辑，外观不变）。按 Alt+F4 关闭。

---

### Task 7: Walk 动画 — 随机行走与边缘检测

**Files:**
- Modify: `D:/desktop_pet/desktop_pet.py` — 替换 `_update_walk` 占位方法

- [ ] **Step 1: 实现完整的 `_update_walk` 方法**

将 `_update_walk` 的 `pass` 替换为:

```python
    def _update_walk(self):
        """更新 Walk 动画：身体摇摆 + 压扁拉伸 + 水平移动 + 屏幕边缘检测"""
        t = self._state_timer_ms
        anim = self._anim
        
        # 到达行走时长上限 → 回到 Idle
        if t >= self._walk_duration_ms:
            self._enter_idle()
            return
        
        # 身体左右摇摆 X 偏移
        anim.walk_wobble_offset = math.sin(
            t * 2 * math.pi / WALK_WOBBLE_PERIOD
        ) * WALK_WOBBLE_AMPLITUDE
        
        # 压扁/拉伸形变: 宽缩放 * (1+sin)，高缩放 * (1/(1+sin))
        # 这样保持面积近似不变，产生Q弹的挤压效果
        squash_factor = math.sin(t * 2 * math.pi / WALK_SQUASH_PERIOD) * WALK_SQUASH_RANGE
        anim.walk_squash = 1.0 + squash_factor
        anim.breath_scale = 1.0 - squash_factor * 0.5  # 轻微参与呼吸缩放
        
        # 行走时的上下微浮动（比 Idle 更紧凑的节奏）
        anim.float_offset_y = math.sin(t * 2 * math.pi / 600) * 4
        
        # 水平移动
        dx = anim.walk_dir * anim.walk_speed
        new_x = self.x() + int(dx)
        
        # 屏幕边缘检测 — 碰到边缘就掉头
        screen = QApplication.primaryScreen().availableGeometry()
        if new_x < screen.left():
            new_x = screen.left()
            anim.walk_dir = 1   # 掉头向右
        elif new_x + WINDOW_WIDTH > screen.right():
            new_x = screen.right() - WINDOW_WIDTH
            anim.walk_dir = -1  # 掉头向左
        
        self.move(new_x, self.y())
```

- [ ] **Step 2: 更新 paintEvent 以支持 Walk 形变**

在 `paintEvent` 中，修改 scale_x/scale_y 的计算逻辑。找到:

```python
        scale_x = self._anim.breath_scale
        scale_y = self._anim.breath_scale
        
        # 应用动画 Y 偏移
        painter.translate(0, self._anim.float_offset_y)
```

替换为:

```python
        scale_x = self._anim.breath_scale
        scale_y = self._anim.breath_scale
        
        # Walk 状态的额外形变
        if self._state == PetState.WALK:
            scale_x *= self._anim.walk_squash
            scale_y *= 1.0 / max(self._anim.walk_squash, 0.5)
            # 应用行走摇摆 X 偏移
            painter.translate(self._anim.walk_wobble_offset, 0)
        
        # 应用动画 Y 偏移
        painter.translate(0, self._anim.float_offset_y)
```

- [ ] **Step 3: 运行验证 — 史莱姆开始走动**

```bash
python desktop_pet.py
```

Expected: 史莱姆先 Idle 浮动 3-8 秒，然后开始左右走动，碰到屏幕边缘掉头。走动时身体压扁拉伸、左右摇摆。走 2-5 秒后停下继续 Idle。循环往复。按 Alt+F4 关闭。

---

### Task 8: 鼠标交互 — 拖拽抓起与右键菜单

**Files:**
- Modify: `D:/desktop_pet/desktop_pet.py` — 替换 `_update_grabbed` 并添加鼠标事件方法

- [ ] **Step 1: 实现 `_update_grabbed` 和添加鼠标事件**

将 `_update_grabbed` 的 `pass` 替换为:

```python
    def _update_grabbed(self):
        """更新 Grabbed 动画：平滑过渡到抓起缩放"""
        anim = self._anim
        # 平滑插值到目标缩放
        anim.grab_scale += (GRAB_SCALE - anim.grab_scale) * 0.25
        # 抓起时禁用浮动
        anim.float_offset_y = 0
        anim.breath_scale = anim.grab_scale
```

在 `_setup_window` 之后添加鼠标事件方法:

```python
    # ========================================================================
    # 鼠标事件
    # ========================================================================
    
    def mousePressEvent(self, event):
        """鼠标按下：左键进入拖拽/抓起状态，右键弹出菜单"""
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_offset = event.pos()  # 记录点击位置相对于窗口左上角的偏移
            # 进入 GRABBED 状态
            self._state = PetState.GRABBED
            self._state_timer_ms = 0
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())
    
    def mouseMoveEvent(self, event):
        """鼠标移动：拖拽窗口跟随"""
        if self._dragging:
            # 新位置 = 全局鼠标坐标 - 点击偏移
            new_pos = event.globalPos() - self._drag_offset
            self.move(new_pos)
    
    def mouseReleaseEvent(self, event):
        """鼠标松开：退出抓起状态，回到 Idle"""
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._enter_idle()
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)
        
        exit_action = QAction("退出程序 (&Q)", self)
        exit_action.triggered.connect(QApplication.quit)
        menu.addAction(exit_action)
        
        menu.exec_(pos)
```

- [ ] **Step 2: 更新 paintEvent 以支持 Grabbed 缩放**

修改 paintEvent 中的 scale 计算，在现有逻辑之前添加 Grabbed 判断。找到:

```python
        scale_x = self._anim.breath_scale
        scale_y = self._anim.breath_scale
```

在这之前添加:

```python
        # Grabbed 状态使用独立的缩放参数
        if self._state == PetState.GRABBED:
            gs = self._anim.grab_scale
            painter.translate(0, 0)
            self._draw_shadow(painter, gs, gs)
            self._draw_body(painter, gs, gs)
            self._draw_highlight(painter, gs, gs)
            self._draw_eyes(painter, gs, gs)
            self._draw_mouth(painter, gs, gs)
            painter.end()
            return
```

- [ ] **Step 3: 运行验证 — 测试拖拽、抓起、右键菜单**

```bash
python desktop_pet.py
```

Expected:
- 左键拖拽：史莱姆缩成 70% 团状，眼睛变 X_X，跟随鼠标移动
- 松开左键：回到 Idle 状态（浮动 + 呼吸）
- 右键点击：弹出菜单，点击"退出程序"可关闭应用

---

### Task 9: 最终集成与测试

**Files:**
- Read: `D:/desktop_pet/desktop_pet.py` (完整文件检查)

- [ ] **Step 1: 确认完整文件结构正确**

```bash
python -c "import desktop_pet; print('Import OK')"
```

Expected: `Import OK`

- [ ] **Step 2: 完整功能测试**

按以下检查清单逐项验证:

| # | 测试项 | 预期 |
|---|--------|------|
| 1 | 启动 | 史莱姆出现在屏幕右下角，透明背景，无边框 |
| 2 | 置顶 | 切换到其他窗口后史莱姆仍可见 |
| 3 | Idle 浮动 | 身体上下浮动 8-10px，约2秒周期 |
| 4 | Idle 呼吸 | 身体微微缩放 |
| 5 | 眨眼 | 每 2-4 秒眨眼一次（眼睛变横线约 80ms） |
| 6 | Walk 触发 | 3-8 秒后开始走动 |
| 7 | Walk 移动 | 水平移动 3-5px/帧，身体压扁拉伸 |
| 8 | Walk 边缘掉头 | 碰到屏幕左右边缘后反向行走 |
| 9 | Walk 结束 | 2-5 秒后停下回到 Idle |
| 10| 左键拖拽 | 身体缩小 70%，眼睛 X_X，流畅跟随鼠标 |
| 11| 松开拖拽 | 回到 Idle 状态 |
| 12| 右键菜单 | 弹出菜单，点击"退出程序"关闭应用 |

- [ ] **Step 3: 如果任何测试项不通过，调试修复**

---

### Task 10: 打包说明文档

**Files:**
- Create: `D:/desktop_pet/README.md`

- [ ] **Step 1: 创建 README**

```markdown
# 桌面桌宠 - 蓝绿渐变果冻史莱姆

一个使用 PyQt5 + QPainter 矢量绘图构建的透明无边框桌面宠物应用。

## 环境要求

- Python 3.6+
- PyQt5

## 安装运行

```bash
pip install PyQt5
python desktop_pet.py
```

## 交互说明

| 操作 | 效果 |
|------|------|
| 左键拖拽 | 抓起宠物，可拖动到任意位置 |
| 右键点击 | 弹出菜单，可选择退出 |
| 什么也不做 | 宠物会在 Idle（浮动呼吸）和 Walk（左右走动）之间自动切换 |

## 打包为独立可执行文件

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "DesktopPet" desktop_pet.py
```

打包后的 `.exe` 文件在 `dist/` 目录下。

- Windows: `dist/DesktopPet.exe`
- macOS: `dist/DesktopPet.app`
```
```

- [ ] **Step 2: 验证 README 内容**

```bash
python -c "print(open('README.md').read()[:100])"
```
