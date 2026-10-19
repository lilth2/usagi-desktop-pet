"""Local activity timing. Reads only time since last input, never input contents."""
import ctypes
import random
import sys
import time

from theme import CREAM, INK, BORDER, BUBBLE_STYLE
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRectF
from PyQt5.QtGui import QPainterPath, QRegion, QPainter, QColor, QPen
from PyQt5.QtWidgets import QLabel

CARE_MESSAGES = (
    "忙了好一会儿，看看远处，让眼睛歇一歇吧。",
    "起来走两步，伸伸肩膀，我在这里等你。",
    "喝口水吧～照顾好自己也是今天很重要的事。",
    "辛苦啦，不必一直绷着。慢慢呼吸，给自己一点空隙。",
    "如果今天有点难，也没关系。你可以按自己的节奏来。",
    "手腕和脖子还舒服吗？换个姿势，放松一下吧。",
    "事情做不完也可以先休息，你的感受同样值得被照顾。",
    "送你一个小小的抱抱。愿你这一刻能轻松一点。",
    "专注了这么久，已经很努力啦。给自己几分钟休息吧。",
    "别忘了按时吃饭。忙碌的时候，也要对自己温柔一点。",
)


def idle_seconds():
    if sys.platform != "win32":
        return None
    class LastInput(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint32)]
    info = LastInput()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return None
    return ((ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xffffffff) / 1000


class CareClock:
    def __init__(self, interval=30 * 60, rest=5 * 60):
        self.interval, self.rest = interval, rest
        self.active = 0
        self.last = time.monotonic()
        self.messages = []

    def poll(self, idle, now=None):
        now = time.monotonic() if now is None else now
        elapsed = max(0, now - self.last)
        self.last = now
        # A sleep/resume gap must not count as continuous computer use.
        if idle is None or idle >= self.rest or elapsed > 60:
            self.active = 0
            return False
        self.active += elapsed
        if self.active >= self.interval:
            self.active = 0
            return True
        return False

    def next_message(self):
        if not self.messages:
            self.messages = list(CARE_MESSAGES)
            random.shuffle(self.messages)
        return self.messages.pop()


class CareBubble(QLabel):
    dismissed = pyqtSignal()
    def __init__(self, parent):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setWordWrap(True)
        self.setWindowTitle('吉伊卡哇 · 关怀')
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(230)
        self.setMargin(10)
        self.setTextFormat(Qt.PlainText)
        self.setStyleSheet(BUBBLE_STYLE)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(CREAM))
        painter.setPen(QPen(QColor(BORDER),1))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5,.5,-.5,-.5),10,10)
        painter.end()
        super().paintEvent(event)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        path=QPainterPath();path.addRoundedRect(QRectF(self.rect()),10,10)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def hideEvent(self,event):
        self.timer.stop()
        super().hideEvent(event)
        self.dismissed.emit()

    def present(self, text, pet):
        self.setText(text)
        self.adjustSize()
        area = pet._get_screen_geometry()
        if area:
            x = max(area.left(), min(pet.x(), area.right() - self.width() + 1))
            y = pet.y() - self.height() - 8
            if y < area.top():
                y = pet.y() + pet.height() + 8
            y = max(area.top(), min(y, area.bottom() - self.height() + 1))
            self.move(x, y)
        self.show()
        self.timer.start(10000)
