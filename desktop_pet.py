#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""吉伊卡哇桌宠：保留本地关怀和限定散步，支持本地时间问候与外观。"""

import sys
import math
import random
import os
import time
import logging
from collections import deque
from enum import Enum
from care import CareClock, CareBubble, idle_seconds
from pet_menu import PetMenu
from theme import NAME, resource, ASSETS
from schedule import SettingsStore, Schedule

from PyQt5.QtWidgets import QApplication, QMainWindow, QAction
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPainter, QColor, QPixmap, QIcon

# ============================================================================
# 常量配置
# ============================================================================

# All resource paths are centralized in theme.py. The source folder and
# internal UsagiPet settings identity remain stable for launcher compatibility.

# 窗口尺寸
WINDOW_WIDTH = 120
WINDOW_HEIGHT = 120

# 贴图显示目标尺寸（无论原始图片多大，渲染时缩放到此范围）
TEXTURE_DISPLAY_W = 110
TEXTURE_DISPLAY_H = 110

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
WALK_DURATION_MIN = 8000
WALK_DURATION_MAX = 14000
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

    def __init__(self, store=None):
        super().__init__()
        self._store = store or SettingsStore()
        self._dev = not getattr(sys, 'frozen', False) and os.environ.get('CHIIKAWA_DEV') == '1'
        self._schedule = Schedule(self._store)
        if self._dev and '--preview-time' in sys.argv:
            from datetime import datetime
            self._schedule.preview = datetime.fromisoformat(sys.argv[sys.argv.index('--preview-time')+1])
        self._appearance = self._schedule.appearance()
        self._manual_sprite = None
        self._messages = deque()
        self._greeting_pending = None
        self._interacted = False
        self._settings_dialog = None
        self._fade_started = 0
        self._fade_from = None
        self._reminder_until = 0
        self._menu_open = False
        self._load_pixmap()
        self._last_pixmap = self._current_pixmap()
        self._setup_window()
        self._setup_state()
        self._setup_timer()
        self._anchor_x = self.x()
        self._walking_enabled = self._store.data['walking_enabled']
        self._care_enabled = self._store.data['care_enabled']
        self._care_clock = CareClock()
        self._care_bubble = CareBubble(self)
        self._care_bubble.dismissed.connect(self._bubble_finished)
        self._care_timer = QTimer(self)
        self._care_timer.timeout.connect(self._check_care)
        self._care_timer.start(10000)
        self.setWindowTitle(NAME + ' · 桌宠')
        self.setWindowIcon(QIcon(str(resource('normal'))))
        self._schedule_timer = QTimer(self)
        self._schedule_timer.timeout.connect(self._refresh_schedule)
        self._schedule_timer.start(1000)
        QTimer.singleShot(600, self._refresh_schedule)
        if self._dev and '--show-settings' in sys.argv:
            QTimer.singleShot(700, self._show_settings)
        if self._store.warning:
            QTimer.singleShot(800, lambda: self._queue_message(self._store.warning))
        if self._asset_warnings:
            QTimer.singleShot(1000, lambda: self._queue_message('；'.join(self._asset_warnings)))

    def _apply_settings(self):
        self._manual_sprite = None
        self._walking_enabled = self._store.data['walking_enabled']
        if self._care_enabled != self._store.data['care_enabled']:
            self._care_clock = CareClock()
        self._care_enabled = self._store.data['care_enabled']
        self._enter_idle()
        self._refresh_schedule()

    def _persist_toggle(self, key, enabled):
        self._store.data[key] = enabled
        try: self._store.save()
        except OSError as e: self._queue_message('设置保存失败：' + str(e))

    def _show_settings(self):
        from settings_ui import SettingsDialog
        if self._settings_dialog is not None and self._settings_dialog.isVisible():
            self._settings_dialog.raise_(); return
        self._enter_idle()
        self._settings_dialog = SettingsDialog(self)
        self._settings_dialog.show()

    def _refresh_schedule(self):
        current = self._schedule.appearance()
        if current != self._appearance:
            self._appearance = current
            self._manual_sprite = None
            self._enter_idle()
        self._update_visual_transition()
        # Replace deferred greeting with only the CURRENT period, never backlog.
        self._greeting_pending = self._schedule.greeting()
        self._drain_messages()

    def _update_visual_transition(self):
        pixmap = self._current_pixmap()
        if pixmap.cacheKey() != self._last_pixmap.cacheKey():
            self._fade_from = self._last_pixmap
            self._fade_started = time.monotonic()
            self._last_pixmap = pixmap

    def _queue_message(self, text, change_pose=True):
        if not change_pose:
            # Rapid picture changes keep the latest care line, while original
            # important reminders stay queued and are never overwritten.
            self._messages = deque((message, pose) for message, pose in self._messages if pose)
            if self._care_bubble.isVisible() and not self._reminder_until:
                self._care_bubble.present(text, self)
                return
        self._messages.append((text, change_pose))
        self._drain_messages()

    def _bubble_finished(self):
        self._reminder_until = 0
        self._update_visual_transition()
        QTimer.singleShot(50, self._drain_messages)

    def _drain_messages(self):
        if self._care_bubble.isVisible() or self._dragging or self._menu_open:
            return
        if self._messages:
            self._enter_idle()
            text, change_pose = self._messages.popleft()
            self._reminder_until = time.monotonic() + 10 if change_pose else 0
            self._update_visual_transition()
            self._care_bubble.present(text, self)
        elif self._greeting_pending and (self._appearance != 'sleep' or self._interacted):
            key, text = self._greeting_pending
            self._greeting_pending = None
            try: self._schedule.delivered(key)
            except OSError as e:
                logging.warning('Greeting record not saved: %s', e)
                return
            self._care_bubble.present(text, self)
        self._interacted = False

    def _check_care(self):
        due = self._care_clock.poll(idle_seconds())
        if due and self._care_enabled:
            self._show_care()

    def _show_care(self):
        self._queue_message(self._care_clock.next_message())

    def _toggle_walking(self, enabled):
        self._walking_enabled = enabled
        self._persist_toggle('walking_enabled', enabled)
        self._enter_idle()

    def _toggle_care(self, enabled):
        self._care_enabled = enabled
        self._persist_toggle('care_enabled', enabled)
        self._care_clock = CareClock()
        if not enabled:
            self._care_bubble.hide()

    def _load_pixmap(self):
        """All states load only normalized Chiikawa art from one directory."""
        self._asset_warnings = []
        self._pixmaps = {}
        for kind in ('normal', 'office', 'desktop', 'happy', 'late', 'late_scene', 'sleep'):
            path = ASSETS / (kind + '.png')
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                self._asset_warnings.append('吉伊卡哇素材缺失：' + path.name)
                pixmap = QPixmap(str(resource('normal')))
            if pixmap.isNull():
                raise RuntimeError('普通吉伊卡哇素材缺失，无法启动：' + str(resource('normal')))
            self._pixmaps[kind] = pixmap
        self._pixmap_idle = self._pixmaps['normal']
        # Keep state hooks compatible; no legacy GIFs are loaded.
        self._movie_walk = None
        self._movie_grabbed = None
        self._pixmap_walk2 = None

    def _sprite_kind(self, include_reminder=True):
        if include_reminder and time.monotonic() < self._reminder_until:
            return 'normal'
        if self._manual_sprite is not None:
            return self._manual_sprite
        kind = self._appearance
        if kind == 'late':
            variant = self._store.data['late_variant']
            if variant == 'rotate':
                kind = 'late' if self._schedule.now().date().toordinal() % 2 else 'late_scene'
            else:
                kind = variant if variant in ('late', 'late_scene') else 'late'
        return kind

    def _current_pixmap(self):
        return self._pixmaps.get(self._sprite_kind(), self._pixmap_idle)

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        self._dragging = False
        self._interacted = False
        self._enter_idle()
        daytime = ('normal', 'office', 'desktop', 'happy')
        allowed = daytime + ('late', 'late_scene') if self._appearance == 'late' else ('sleep',) if self._appearance == 'sleep' else daytime
        if len(allowed) > 1:
            # Reminder pose is temporary; cycle the underlying character choice.
            current = self._sprite_kind(include_reminder=False)
            self._manual_sprite = allowed[(allowed.index(current) + 1) % len(allowed)]
            self._update_visual_transition()
            self.update()
        self._queue_message(self._care_clock.next_message(), change_pose=False)
        event.accept()

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
            self._interacted = True
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
            screen = QApplication.screenAt(event.globalPos())
            geom = screen.availableGeometry() if screen else self._get_screen_geometry()
            if geom:
                x = max(geom.left(),
                        min(new_pos.x(), geom.right() - WINDOW_WIDTH + 1))
                y = max(geom.top(),
                        min(new_pos.y(), geom.bottom() - WINDOW_HEIGHT + 1))
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
            else:
                if self._appearance == 'sleep' and not self._greeting_pending:
                    self._queue_message('轻轻碰到你啦，我在好好休息，也陪着你。')
            self._drain_messages()

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        self._enter_idle()
        menu = self._build_menu()
        self._menu_open = True
        try:
            menu.exec_(pos)
        finally:
            self._menu_open = False
            menu.deleteLater()
            QTimer.singleShot(0, self._drain_messages)

    def _build_menu(self):
        menu = PetMenu(self, self._current_pixmap())
        care_action = menu.addAction("关怀提醒 · 30分钟")
        care_action.setCheckable(True)
        care_action.setChecked(self._care_enabled)
        care_action.triggered.connect(self._toggle_care)
        menu.addAction("一句暖心话 ♡").triggered.connect(self._show_care)
        menu.addSeparator()
        walk_action = menu.addAction("小步散步")
        walk_action.setCheckable(True)
        walk_action.setChecked(self._walking_enabled)
        walk_action.triggered.connect(self._toggle_walking)
        menu.addAction("陪伴与时间设置…").triggered.connect(self._show_settings)
        menu.addSeparator()
        exit_action = QAction("下次见～", menu)
        exit_action.triggered.connect(QApplication.quit)
        menu.addAction(exit_action)
        return menu

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

        if self._appearance == 'sleep':
            anim.float_offset_y = 0
            anim.breath_scale = 1
            return

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
        if self._walking_enabled and self._state_timer_ms >= self._next_walk_ms and not self._care_bubble.isVisible() and not self._menu_open and not (self._settings_dialog and self._settings_dialog.isVisible()):
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
        new_y = self.y()

        # 在固定活动范围内折返，不在边界原地踏步，也不逐次漂移。
        geom = self._get_screen_geometry()
        left = self._anchor_x - WALK_RADIUS
        right = self._anchor_x + WALK_RADIUS
        if geom:
            left = max(left, geom.left())
            right = min(right, geom.right() - WINDOW_WIDTH + 1)
            if left > right:
                left = right = max(geom.left(), min(self._anchor_x, geom.right() - WINDOW_WIDTH + 1))
            if new_y < geom.top():
                new_y = geom.top()
            elif new_y + WINDOW_HEIGHT > geom.bottom():
                new_y = geom.bottom() - WINDOW_HEIGHT

        if new_x <= left:
            new_x = left
            anim.walk_dir = 1
        elif new_x >= right:
            new_x = right
            anim.walk_dir = -1

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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        pixmap = self._current_pixmap()
        # One canvas/foot baseline for all assets. Uniform transform only;
        # original character proportions are never stretched or squashed.
        painter.translate(WINDOW_WIDTH / 2, 5 + 280 / 320 * TEXTURE_DISPLAY_H)
        scale = self._get_current_scale()
        if self._state == PetState.WALK:
            painter.rotate(math.sin(self._state_timer_ms * math.pi / 250) * 2)
        painter.translate(0, self._anim.float_offset_y)
        painter.scale(scale, scale)
        from PyQt5.QtCore import QRectF
        target = QRectF(-TEXTURE_DISPLAY_W / 2, -280 / 320 * TEXTURE_DISPLAY_H,
                        TEXTURE_DISPLAY_W, TEXTURE_DISPLAY_H)
        progress = min(1, max(0, (time.monotonic() - self._fade_started) / .3))
        if self._fade_from is not None and progress < 1:
            painter.setOpacity(1 - progress)
            painter.drawPixmap(target, self._fade_from, QRectF(self._fade_from.rect()))
            painter.setOpacity(progress)
        painter.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
        painter.end()


def main():
    """应用入口"""
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(resource('normal'))))
    app.setQuitOnLastWindowClosed(True)
    pet = DesktopPetWindow()
    pet.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
