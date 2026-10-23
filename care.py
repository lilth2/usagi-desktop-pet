"""Local activity timing. Reads only time since last input, never input contents."""
import ctypes
import sys
import time
from functools import lru_cache

from theme import CREAM, INK, BORDER, BUBBLE_STYLE
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRectF, QEvent, QRect
from PyQt5.QtGui import QPainterPath, QRegion, QPainter, QColor, QPen
from PyQt5.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea, QApplication

from companion_config import CARE_MESSAGES


@lru_cache(maxsize=1)
def _mac_idle_reader():
    library=ctypes.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
    reader=library.CGEventSourceSecondsSinceLastEventType
    reader.argtypes=[ctypes.c_int32,ctypes.c_uint32]
    reader.restype=ctypes.c_double
    return reader


def idle_seconds():
    if sys.platform == 'darwin':
        try:
            value=_mac_idle_reader()(0,0xffffffff)
            return value if 0<=value<float('inf') else None
        except (OSError,AttributeError):
            return None
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
        self.important=False
        self._tail_side='bottom'
        self._tail_coordinate=80
        self._anchor_bounds={}
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        if sys.platform == 'darwin':
            self.setAttribute(Qt.WA_MacAlwaysShowToolWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setWindowTitle('吉伊卡哇 · 关怀')
        self.setStyleSheet(BUBBLE_STYLE)
        layout=QVBoxLayout(self);layout.setContentsMargins(15,13,26,13);layout.setSpacing(0)
        self.close_button=QPushButton('×',self);self.close_button.setFixedSize(16,16)
        self.close_button.setStyleSheet('QPushButton {padding:0;color:#92717d;border:none;border-radius:8px;} QPushButton:hover {background:#f6dce5;color:#59464d;}')
        self.close_button.setToolTip('关闭气泡');self.close_button.setFocusPolicy(Qt.NoFocus)
        self.close_button.clicked.connect(self.dismiss_by_user)
        self.label=QLabel();self.label.setWordWrap(True);self.label.setTextFormat(Qt.PlainText)
        self.label.setStyleSheet('background: transparent; border: none; font-size:11px;')
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setWidget(self.label)
        self.scroll.setFocusPolicy(Qt.NoFocus);self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setStyleSheet('QScrollArea {background:transparent;border:none;} QScrollBar:vertical {width:7px;background:#fff5f4;} QScrollBar::handle:vertical {background:#d9b5c4;min-height:14px;border-radius:3px;} QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}')
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

    def _bubble_path(self):
        body=QRectF(self.rect()).adjusted(6.5,6.5,-6.5,-6.5)
        path=QPainterPath();path.addRoundedRect(body,9,9)
        tail=QPainterPath();side=self._tail_side
        if side in ('bottom','top'):
            anchor=max(body.left()+13,min(self._tail_coordinate,body.right()-13))
            edge=body.bottom() if side=='bottom' else body.top()
            tip=self.height()-.7 if side=='bottom' else .7
            tail.moveTo(anchor-5,edge);tail.lineTo(anchor,tip);tail.lineTo(anchor+5,edge)
        else:
            anchor=max(body.top()+12,min(self._tail_coordinate,body.bottom()-12))
            edge=body.left() if side=='left' else body.right()
            tip=.7 if side=='left' else self.width()-.7
            tail.moveTo(edge,anchor-5);tail.lineTo(tip,anchor);tail.lineTo(edge,anchor+5)
        tail.closeSubpath()
        return path.united(tail)

    def _update_outline(self):
        self.close_button.move(self.width()-25,9)
        self.close_button.raise_()
        self.setMask(QRegion(self._bubble_path().toFillPolygon().toPolygon()))
        self.update()

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(CREAM));painter.setPen(QPen(QColor(BORDER),1))
        painter.drawPath(self._bubble_path())

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._update_outline()

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
        area=screen.availableGeometry();rect=self.pet.frameGeometry();gap=4
        # Static alpha bounds keep the tail near the visible character, without
        # following the small per-frame breathing/sway deformation.
        pixmap=self.pet._current_pixmap();key=pixmap.cacheKey()
        if key not in self._anchor_bounds:
            mask=pixmap.mask()
            self._anchor_bounds[key]=QRegion(mask).boundingRect() if not mask.isNull() else pixmap.rect()
        visible=self._anchor_bounds[key]
        scale=(self.pet.width()-10)/pixmap.width()
        rect=QRect(self.pet.x()+5+round(visible.x()*scale),
                   self.pet.y()+5+round(visible.y()*scale),
                   max(1,round(visible.width()*scale)),max(1,round(visible.height()*scale)))
        # Reserve a fixed motion envelope rather than chasing each animation
        # frame. Include the outgoing image while the character crossfades.
        outgoing=getattr(self.pet,'_fade_from',None)
        if outgoing is not None and time.monotonic()-self.pet._fade_started<.3:
            old_key=outgoing.cacheKey()
            if old_key not in self._anchor_bounds:
                mask=outgoing.mask()
                self._anchor_bounds[old_key]=QRegion(mask).boundingRect() if not mask.isNull() else outgoing.rect()
            old=self._anchor_bounds[old_key]
            old_scale=(self.pet.width()-10)/outgoing.width()
            old_rect=QRect(self.pet.x()+5+round(old.x()*old_scale),
                           self.pet.y()+5+round(old.y()*old_scale),
                           max(1,round(old.width()*old_scale)),max(1,round(old.height()*old_scale)))
            rect=rect.united(old_rect)
        rect=rect.adjusted(-8,-8,8,8)
        maximum=min(round(self.pet.width()*1.4),180,max(80,area.width()-16))
        natural=self.label.fontMetrics().horizontalAdvance(self.label.text())+50
        width=max(min(108,maximum),min(maximum,natural))
        text_width=max(35,width-49)
        self.label.setFixedWidth(text_width)
        height=min(max(46,self.label.heightForWidth(text_width)+28),136,max(46,area.height()-16))
        self.resize(width,height)
        candidates=[QRect(rect.left()-width-gap,rect.top()-height//4,width,height),
                    QRect(rect.right()+gap,rect.top()-height//4,width,height),
                    QRect(rect.center().x()-width//2,rect.top()-height-gap,width,height),
                    QRect(rect.center().x()-width//2,rect.bottom()+gap,width,height)]
        # Slide side bubbles vertically, and top/bottom bubbles horizontally,
        # without sliding either into the character's protected area.
        for index,candidate in enumerate(candidates):
            if index<2:
                candidate.moveTop(max(area.top(),min(candidate.top(),area.bottom()-height+1)))
            else:
                candidate.moveLeft(max(area.left(),min(candidate.left(),area.right()-width+1)))
        # All coordinates are Qt logical desktop coordinates (also on mixed-DPI monitors).
        target=next((r for r in candidates if area.contains(r)),None)
        if target is None:
            fitted=[]
            for r in candidates:
                r.moveLeft(max(area.left(),min(r.left(),area.right()-width+1)))
                r.moveTop(max(area.top(),min(r.top(),area.bottom()-height+1)))
                overlap=r.intersected(rect);fitted.append((overlap.width()*overlap.height(),r))
            target=min(fitted,key=lambda item:item[0])[1]
        if target.bottom() < rect.top():
            self._tail_side='bottom';self._tail_coordinate=rect.center().x()-target.x()
        elif target.top() > rect.bottom():
            self._tail_side='top';self._tail_coordinate=rect.center().x()-target.x()
        elif target.left() > rect.right():
            self._tail_side='left';self._tail_coordinate=rect.center().y()-target.y()
        else:
            self._tail_side='right';self._tail_coordinate=rect.center().y()-target.y()
        self.move(target.topLeft());self._update_outline()
        if self.suspended:
            self.suspended=False;self.show();self.timer.start(self.remaining)

    def present(self,text,pet,important=False):
        self.important=important
        self.label.setText(text);self.scroll.verticalScrollBar().setValue(0)
        self.active=True;self.suspended=False
        self.follow();self.show();self.timer.start(8000)
        self.follow()
