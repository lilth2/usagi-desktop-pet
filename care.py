"""Local activity timing. Reads only time since last input, never input contents."""
import ctypes
import sys
import time

from theme import CREAM, INK, BORDER, BUBBLE_STYLE
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRectF, QEvent, QRect
from PyQt5.QtGui import QPainterPath, QRegion, QPainter, QColor, QPen
from PyQt5.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea, QApplication

from companion_config import CARE_MESSAGES


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



class CareBubble(QWidget):
    dismissed = pyqtSignal()
    user_closed = pyqtSignal()
    def __init__(self, parent):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.pet=parent
        self.active=False
        self.suspended=False
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setWindowTitle('吉伊卡哇 · 关怀')
        self.setStyleSheet(BUBBLE_STYLE)
        layout=QVBoxLayout(self);layout.setContentsMargins(10,4,10,10);layout.setSpacing(0)
        row=QHBoxLayout();row.addStretch()
        self.close_button=QPushButton('×');self.close_button.setFixedSize(24,22)
        self.close_button.setToolTip('关闭气泡');self.close_button.setFocusPolicy(Qt.NoFocus)
        self.close_button.clicked.connect(self.dismiss_by_user);row.addWidget(self.close_button);layout.addLayout(row)
        self.label=QLabel();self.label.setWordWrap(True);self.label.setTextFormat(Qt.PlainText)
        self.label.setStyleSheet('background: transparent; border: none;')
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setWidget(self.label)
        self.scroll.setFocusPolicy(Qt.NoFocus);self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);layout.addWidget(self.scroll)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.hide)
        parent.installEventFilter(self)
        self.follow_timer=QTimer(self);self.follow_timer.timeout.connect(self.follow);self.follow_timer.start(50)

    def text(self):return self.label.text()

    def dismiss_by_user(self):
        self.user_closed.emit()
        self.hide()

    def mousePressEvent(self,event):event.accept()
    def mouseReleaseEvent(self,event):event.accept()
    def mouseDoubleClickEvent(self,event):event.accept()
    def mouseMoveEvent(self,event):event.accept()

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(CREAM));painter.setPen(QPen(QColor(BORDER),1))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5,.5,-.5,-.5),10,10)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        path=QPainterPath();path.addRoundedRect(QRectF(self.rect()),10,10)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def hide(self):
        self.active=False;self.suspended=False;self.timer.stop()
        super().hide()

    def hideEvent(self,event):
        super().hideEvent(event)
        if not self.suspended:
            self.active=False;self.timer.stop();self.dismissed.emit()

    def eventFilter(self,obj,event):
        if event.type() in (QEvent.Move,QEvent.Resize,QEvent.Show,QEvent.Hide,QEvent.WindowStateChange):
            self.follow()
        return False

    def follow(self):
        if not self.active:return
        if not self.pet.isVisible() or self.pet.isMinimized() or getattr(self.pet,'_menu_open',False):
            if not self.suspended:
                self.remaining=max(1,self.timer.remainingTime());self.timer.stop();self.suspended=True
                super().hide()
            return
        screen=QApplication.screenAt(self.pet.frameGeometry().center()) or self.pet.screen()
        area=screen.availableGeometry();rect=self.pet.frameGeometry();gap=8
        width=min(260,max(80,area.width()-16));self.label.setFixedWidth(max(40,width-40))
        height=min(max(80,self.label.heightForWidth(width-40)+40),240,max(60,area.height()-16))
        self.resize(width,height)
        candidates=[QRect(rect.center().x()-width//2,rect.top()-height-gap,width,height),
                    QRect(rect.right()+gap,rect.center().y()-height//2,width,height),
                    QRect(rect.left()-width-gap,rect.center().y()-height//2,width,height),
                    QRect(rect.center().x()-width//2,rect.bottom()+gap,width,height)]
        # All coordinates are Qt logical desktop coordinates (also on mixed-DPI monitors).
        target=next((r for r in candidates if area.contains(r)),None)
        if target is None:
            fitted=[]
            for r in candidates:
                r.moveLeft(max(area.left(),min(r.left(),area.right()-width+1)))
                r.moveTop(max(area.top(),min(r.top(),area.bottom()-height+1)))
                overlap=r.intersected(rect);fitted.append((overlap.width()*overlap.height(),r))
            target=min(fitted,key=lambda item:item[0])[1]
        self.move(target.topLeft())
        if self.suspended:
            self.suspended=False;self.show();self.timer.start(self.remaining)

    def present(self,text,pet):
        self.label.setText(text);self.scroll.verticalScrollBar().setValue(0)
        self.active=True;self.suspended=False
        self.follow();self.show();self.timer.start(8000)
        self.follow()
