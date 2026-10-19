#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桌面桌宠 - 乌萨奇 (Usagi)
使用 PyQt5 + QPixmap/QMovie 贴图渲染的透明无边框桌面宠物应用

运行方式:
    pip install PyQt5
    python desktop_pet.py

图片文件（放到同目录下）:
    usagi_idle.png     — Idle 状态（必需）
    usagi_walk1.gif    — Walk 动画（可选，无则用 idle）
    usagi_walk2.png    — Walk 帧2（可选）
    usagi_grabbed.gif  — 抓起状态（可选，无则缩放 idle）

打包方式:
    pip install pyinstaller
    pyinstaller --onefile --windowed --add-data "usagi_idle.png;." ... desktop_pet.py
"""

import sys
import math
import random
import os
from enum import Enum
from chat import ChatWindow
from care import CareClock, CareBubble, idle_seconds

from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QAction
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPainter, QColor, QPixmap, QMovie

# ============================================================================
# 常量配置
# ============================================================================

# 贴图文件路径（支持 PyInstaller 打包后的临时目录）
if getattr(sys, 'frozen', False):
    _BASE = sys._MEIPASS           # PyInstaller --onefile 解压临时目录
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))
PIXMAP_IDLE = os.path.join(_BASE, "usagi_idle.png")
PIXMAP_WALK_GIF = os.path.join(_BASE, "usagi_walk1.gif")
PIXMAP_WALK2 = os.path.join(_BASE, "usagi_walk2.png")
PIXMAP_GRABBED_GIF = os.path.join(_BASE, "usagi_grabbed.gif")

# 窗口尺寸
WINDOW_WIDTH = 120
WINDOW_HEIGHT = 120

# 贴图显示目标尺寸（无论原始图片多大，渲染时缩放到此范围）
TEXTURE_DISPLAY_W = 90
TEXTURE_DISPLAY_H = 90

# 动画帧间隔 (ms)，约 25 FPS
FRAME_INTERVAL = 40

# Idle 动画参数
IDLE_FLOAT_PERIOD = 2000       # 浮动周期 ms
IDLE_FLOAT_AMPLITUDE = 4       # 浮动幅度 px
IDLE_BREATH_RANGE = 0.05       # 呼吸缩放范围 ±5%

# 眨眼参数（贴图模式下仅维持计时，不实际绘制眨眼效果）
BLINK_INTERVAL_MIN = 2000
BLINK_INTERVAL_MAX = 4000
BLINK_DURATION = 80

# Walk 动画参数
WALK_INTERVAL_MIN = 15000
WALK_INTERVAL_MAX = 30000
WALK_DURATION_MIN = 600
WALK_DURATION_MAX = 1200
WALK_SPEED_MIN = 1
WALK_SPEED_MAX = 1
WALK_RADIUS = 30              # 相对启动/最后拖放位置，最多左右各 30px
WALK_WOBBLE_PERIOD = 500       # 行走身体摇摆周期 ms
WALK_WOBBLE_AMPLITUDE = 3      # 行走身体摇摆幅度 px
WALK_SQUASH_PERIOD = 250       # 行走压扁/拉伸周期 ms
WALK_SQUASH_RANGE = 0.1        # 行走压扁范围

# 抓起状态参数
GRAB_SCALE = 0.7               # 抓起时缩放比例

# 宠物在窗口中的绘制中心
BODY_CENTER_X = WINDOW_WIDTH // 2   # 100
BODY_CENTER_Y = WINDOW_HEIGHT // 2  # 100

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
    """保存每帧动画所需的所有动态数据"""

    def __init__(self):
        # Idle 动画
        self.float_offset_y = 0.0      # 身体浮动 Y 偏移
        self.breath_scale = 1.0        # 呼吸缩放因子

        # 眨眼（贴图模式下仅计时，不影响渲染）
        self.is_blinking = False
        self.blink_timer_ms = 0

        # Walk 动画
        self.walk_dir = 1              # 行走方向: 1=右, -1=左
        self.walk_speed = 4            # 行走速度 px/帧
        self.walk_wobble_offset = 0.0  # 行走身体左右摇摆 X 偏移
        self.walk_squash = 1.0         # 行走压扁/拉伸因子

        # Grabbed 动画
        self.grab_scale = 1.0          # 抓起缩放 (1.0 → GRAB_SCALE 平滑过渡)

    def reset_for_idle(self):
        """复位到 Idle 默认值"""
        self.float_offset_y = 0.0
        self.breath_scale = 1.0
        self.walk_wobble_offset = 0.0
        self.walk_squash = 1.0
        self.walk_dir = 1
        self.is_blinking = False
        self.blink_timer_ms = 0
        self.grab_scale = 1.0


# ============================================================================
# 桌宠主窗口
# ============================================================================

class DesktopPetWindow(QMainWindow):
    """透明无边框桌宠窗口，负责贴图加载、状态机、事件处理和渲染"""

    def __init__(self):
        super().__init__()
        self._chat = None
        self._load_pixmap()
        self._setup_window()
        self._setup_state()
        self._setup_timer()
        self._anchor_x = self.x()
        self._walking_enabled = True
        self._care_enabled = True
        self._care_clock = CareClock()
        self._care_bubble = CareBubble(self)
        self._care_timer = QTimer(self)
        self._care_timer.timeout.connect(self._check_care)
        self._care_timer.start(10000)

    def _check_care(self):
        due = self._care_clock.poll(idle_seconds())
        if due and self._care_enabled and not self._dragging:
            self._show_care()

    def _show_care(self):
        self._enter_idle()
        self._care_bubble.present(self._care_clock.next_message(), self)

    def _toggle_walking(self, enabled):
        self._walking_enabled = enabled
        self._enter_idle()

    def _toggle_care(self, enabled):
        self._care_enabled = enabled
        self._care_clock = CareClock()
        if not enabled:
            self._care_bubble.hide()

    def _load_pixmap(self):
        """加载所有贴图资源：Idle (PNG)、Walk (GIF/PNG)、Grabbed (GIF)"""
        self._pixmap_idle = None
        self._movie_walk = None
        self._pixmap_walk2 = None
        self._movie_grabbed = None

        # --- Idle 贴图（必需） ---
        if os.path.exists(PIXMAP_IDLE):
            self._pixmap_idle = QPixmap(PIXMAP_IDLE)
        else:
            self._pixmap_idle = self._create_placeholder("Idle")

        # --- Walk GIF ---
        if os.path.exists(PIXMAP_WALK_GIF):
            self._movie_walk = QMovie(PIXMAP_WALK_GIF)
            self._movie_walk.setCacheMode(QMovie.CacheAll)
        elif os.path.exists(PIXMAP_WALK2):
            self._pixmap_walk2 = QPixmap(PIXMAP_WALK2)

        # --- Grabbed GIF ---
        if os.path.exists(PIXMAP_GRABBED_GIF):
            self._movie_grabbed = QMovie(PIXMAP_GRABBED_GIF)
            self._movie_grabbed.setCacheMode(QMovie.CacheAll)

    def _create_placeholder(self, label):
        """创建占位贴图"""
        pm = QPixmap(TEXTURE_DISPLAY_W, TEXTURE_DISPLAY_H)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 200, 100))
        painter.drawEllipse(5, 5, TEXTURE_DISPLAY_W - 10, TEXTURE_DISPLAY_H - 10)
        painter.setPen(QColor(100, 50, 0))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(pm.rect(), Qt.AlignCenter, f"请放置\nusagi_{label}.png")
        painter.end()
        print(f"警告: 未找到 {label} 贴图，使用占位图")
        return pm

    def _current_pixmap(self):
        """返回当前状态下应渲染的 QPixmap"""
        if self._state == PetState.WALK:
            if self._movie_walk is not None:
                return self._movie_walk.currentPixmap()
            if self._pixmap_walk2 is not None:
                return self._pixmap_walk2
        elif self._state == PetState.GRABBED:
            if self._movie_grabbed is not None:
                return self._movie_grabbed.currentPixmap()
        # Idle 或 fallback
        return self._pixmap_idle

    def _setup_window(self):
        """配置透明无边框置顶窗口"""
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        if sys.platform == 'win32':
            flags |= Qt.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # 定位到屏幕右下角（留 50px 边距）
        geom = self._get_screen_geometry()
        if geom:
            self.move(
                geom.right() - WINDOW_WIDTH - 50,
                geom.bottom() - WINDOW_HEIGHT - 50
            )

        # 拖拽相关变量
        self._dragging = False
        self._drag_offset = QPoint()

    # ========================================================================
    # 鼠标事件
    # ========================================================================

    def mousePressEvent(self, event):
        """鼠标按下：左键进入拖拽/抓起状态，右键弹出菜单"""
        if event.button() == Qt.LeftButton:
            self._care_bubble.hide()
            self._press_global = event.globalPos()
            self._did_drag = False
            self._dragging = True
            self._drag_offset = event.pos()
            # 停止 Walk GIF，启动 Grabbed GIF
            if self._movie_walk is not None:
                self._movie_walk.stop()
            if self._movie_grabbed is not None:
                self._movie_grabbed.start()
            self._state = PetState.GRABBED
            self._state_timer_ms = 0
        elif event.button() == Qt.RightButton:
            if self._dragging:
                self._dragging = False
                self._enter_idle()
            self._show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        """鼠标移动：拖拽窗口跟随，并限制不超出屏幕边界"""
        if self._dragging:
            if (event.globalPos() - self._press_global).manhattanLength() < QApplication.startDragDistance() and not self._did_drag:
                return
            self._did_drag = True
            new_pos = event.globalPos() - self._drag_offset
            geom = self._get_screen_geometry()
            if geom:
                x = max(geom.left() - WINDOW_WIDTH + 30,
                        min(new_pos.x(), geom.right() - 30))
                y = max(geom.top() - WINDOW_HEIGHT + 30,
                        min(new_pos.y(), geom.bottom() - 30))
                new_pos.setX(x)
                new_pos.setY(y)
            self.move(new_pos)

    def mouseReleaseEvent(self, event):
        """鼠标松开：退出抓起状态，回到 Idle"""
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._enter_idle()
            if self._did_drag:
                self._anchor_x = self.x()
            if not self._did_drag:
                self._show_chat()

    def _show_chat(self):
        if self._chat is None:
            self._chat = ChatWindow(self)
        self._chat.show()
        self._chat.raise_()
        self._chat.activateWindow()
        self._chat.input.setFocus()

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)
        chat_action = menu.addAction("聊聊天")
        chat_action.triggered.connect(self._show_chat)
        care_action = menu.addAction("自动关怀（持续使用30分钟）")
        care_action.setCheckable(True)
        care_action.setChecked(self._care_enabled)
        care_action.triggered.connect(self._toggle_care)
        menu.addAction("看看关怀提醒").triggered.connect(self._show_care)
        walk_action = menu.addAction("小范围走动")
        walk_action.setCheckable(True)
        walk_action.setChecked(self._walking_enabled)
        walk_action.triggered.connect(self._toggle_walking)
        exit_action = QAction("退出程序 (&Q)", self)
        exit_action.triggered.connect(QApplication.quit)
        menu.addAction(exit_action)
        menu.exec_(pos)

    def _get_screen_geometry(self):
        """获取当前窗口所在屏幕的可用几何区域"""
        screen = QApplication.screenAt(self.geometry().center())
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return None
        return screen.availableGeometry()

    def _setup_state(self):
        """初始化状态机变量"""
        self._state = PetState.IDLE
        self._anim = AnimationData()
        self._state_timer_ms = 0
        self._next_blink_ms = random.randint(BLINK_INTERVAL_MIN, BLINK_INTERVAL_MAX)
        self._next_walk_ms = random.randint(WALK_INTERVAL_MIN, WALK_INTERVAL_MAX)
        self._walk_duration_ms = 0

    def _setup_timer(self):
        """启动动画驱动定时器"""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(FRAME_INTERVAL)

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

        self.update()

    def _update_idle(self):
        """更新 Idle 动画参数：浮动、呼吸缩放"""
        t = self._state_timer_ms
        anim = self._anim

        # 身体浮动
        anim.float_offset_y = math.sin(t * 2 * math.pi / IDLE_FLOAT_PERIOD) * IDLE_FLOAT_AMPLITUDE
        # 呼吸缩放
        anim.breath_scale = 1.0 + math.sin(t * 2 * math.pi / IDLE_FLOAT_PERIOD) * IDLE_BREATH_RANGE

        # 眨眼计时（仅维持节奏，贴图模式下不改变渲染）
        anim.blink_timer_ms += FRAME_INTERVAL
        if anim.is_blinking:
            if anim.blink_timer_ms >= BLINK_DURATION:
                anim.is_blinking = False
                anim.blink_timer_ms = 0
                self._next_blink_ms = random.randint(BLINK_INTERVAL_MIN, BLINK_INTERVAL_MAX)
        else:
            if anim.blink_timer_ms >= self._next_blink_ms:
                anim.is_blinking = True
                anim.blink_timer_ms = 0

        # Walk 触发
        if self._walking_enabled and self._state_timer_ms >= self._next_walk_ms and not self._care_bubble.isVisible() and not (self._chat and self._chat.isVisible()):
            self._enter_walk()

    def _enter_walk(self):
        """进入 Walk 状态"""
        self._state = PetState.WALK
        self._state_timer_ms = 0
        anim = self._anim
        anim.walk_dir = random.choice([-1, 1])
        anim.walk_speed = random.randint(WALK_SPEED_MIN, WALK_SPEED_MAX)
        self._walk_duration_ms = random.randint(WALK_DURATION_MIN, WALK_DURATION_MAX)
        # 启动 Walk GIF 动画
        if self._movie_walk is not None:
            self._movie_walk.start()

    def _update_walk(self):
        """更新 Walk 动画：摇摆 + 压扁拉伸 + 水平移动 + 屏幕边缘检测"""
        t = self._state_timer_ms
        anim = self._anim

        if t >= self._walk_duration_ms:
            self._enter_idle()
            return

        # 左右摇摆
        anim.walk_wobble_offset = math.sin(
            t * 2 * math.pi / WALK_WOBBLE_PERIOD
        ) * WALK_WOBBLE_AMPLITUDE

        # 压扁/拉伸
        squash_factor = math.sin(t * 2 * math.pi / WALK_SQUASH_PERIOD) * WALK_SQUASH_RANGE
        anim.walk_squash = 1.0 + squash_factor
        anim.breath_scale = 1.0 - squash_factor * 0.5

        # 上下微浮动
        anim.float_offset_y = math.sin(t * 2 * math.pi / 600) * 4

        # 水平移动
        dx = anim.walk_dir * anim.walk_speed
        new_x = self.x() + int(dx)
        new_x = max(self._anchor_x - WALK_RADIUS, min(new_x, self._anchor_x + WALK_RADIUS))
        new_y = self.y()

        # 屏幕边缘检测
        geom = self._get_screen_geometry()
        if geom:
            if new_x < geom.left():
                new_x = geom.left()
                anim.walk_dir = 1
            elif new_x + WINDOW_WIDTH > geom.right():
                new_x = geom.right() - WINDOW_WIDTH
                anim.walk_dir = -1
            if new_y < geom.top():
                new_y = geom.top()
            elif new_y + WINDOW_HEIGHT > geom.bottom():
                new_y = geom.bottom() - WINDOW_HEIGHT

        self.move(new_x, new_y)

    def _update_grabbed(self):
        """更新 Grabbed 动画：平滑过渡到抓起缩放"""
        anim = self._anim
        anim.grab_scale += (GRAB_SCALE - anim.grab_scale) * 0.25
        anim.float_offset_y = 0
        anim.breath_scale = anim.grab_scale

    def _enter_idle(self):
        """回到 Idle 状态"""
        # 停止 Walk GIF
        if self._movie_walk is not None:
            self._movie_walk.stop()
        # 停止 Grabbed GIF
        if self._movie_grabbed is not None:
            self._movie_grabbed.stop()
        self._state = PetState.IDLE
        self._state_timer_ms = 0
        self._anim.reset_for_idle()
        self._next_blink_ms = random.randint(BLINK_INTERVAL_MIN, BLINK_INTERVAL_MAX)
        self._next_walk_ms = random.randint(WALK_INTERVAL_MIN, WALK_INTERVAL_MAX)

    # ========================================================================
    # 渲染系统（贴图模式）
    # ========================================================================

    def _get_current_scale(self):
        """获取当前帧的等效缩放因子（供 _draw_shadow 和 paintEvent 使用）"""
        if self._state == PetState.GRABBED:
            return self._anim.grab_scale
        return self._anim.breath_scale

    def paintEvent(self, event):
        """渲染入口：以贴图为中心应用缩放和位移动画"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        scale = self._get_current_scale()

        # 平移到窗口中心
        painter.translate(BODY_CENTER_X, BODY_CENTER_Y)

        # Walk 状态的额外形变
        if self._state == PetState.WALK:
            sx = scale * self._anim.walk_squash
            sy = scale / self._anim.walk_squash
            painter.translate(self._anim.walk_wobble_offset, 0)
        else:
            sx = scale
            sy = scale

        # Y 轴浮动偏移
        painter.translate(0, self._anim.float_offset_y)

        # --- 绘制底部投影 ---
        self._draw_shadow(painter, sx, sy)

        # --- 绘制贴图 ---
        pixmap = self._current_pixmap()
        if pixmap is not None and not pixmap.isNull():
            pw = pixmap.width()
            ph = pixmap.height()
            # 贴图原始尺寸 → 显示尺寸的缩放比
            ds_x = TEXTURE_DISPLAY_W / pw if pw > 0 else 1.0
            ds_y = TEXTURE_DISPLAY_H / ph if ph > 0 else 1.0
            painter.save()
            # 先缩放贴图到显示尺寸，再叠加动画缩放
            painter.scale(sx * ds_x, sy * ds_y)
            painter.drawPixmap(-pw // 2, -ph // 2, pixmap)
            painter.restore()

        painter.end()

    def _draw_shadow(self, painter, scale_x, scale_y):
        """绘制底部投影 — 半透明深色椭圆（贴图底部）"""
        shadow_w = int(TEXTURE_DISPLAY_W * scale_x * 0.7)
        shadow_h = 10
        # 投影在贴图底部偏下
        shadow_y = int(TEXTURE_DISPLAY_H * scale_y * 0.38)
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 35))
        painter.drawEllipse(-shadow_w // 2, shadow_y, shadow_w, shadow_h)
        painter.restore()


def main():
    """应用入口"""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    pet = DesktopPetWindow()
    pet.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
