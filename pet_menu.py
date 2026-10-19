"""Compact Chiikawa popup, using the current character artwork."""
from theme import MENU_STYLE
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainterPath, QRegion
from PyQt5.QtWidgets import QMenu, QWidgetAction, QWidget, QHBoxLayout, QVBoxLayout, QLabel


class PetMenu(QMenu):
    def __init__(self, parent, portrait):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(MENU_STYLE)
        header = QWidget(self)
        row = QHBoxLayout(header)
        row.setContentsMargins(6, 2, 6, 3)
        row.setSpacing(4)
        picture = QLabel()
        picture.setPixmap(portrait.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        row.addWidget(picture)
        text = QVBoxLayout()
        text.setSpacing(1)
        title = QLabel("吉伊卡哇的小窝")
        title.setStyleSheet("font-size:12px;font-weight:600;")
        subtitle = QLabel("轻轻地，陪着你 ♡")
        subtitle.setStyleSheet("font-size:10px;color:#846670;")
        text.addWidget(title)
        text.addWidget(subtitle)
        row.addLayout(text)
        action = QWidgetAction(self)
        action.setDefaultWidget(header)
        self.addAction(action)
        self.addSeparator()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Clip the native popup window too: stylesheet rounding alone can leave
        # opaque black corners on Windows popup surfaces.
        outline = QPainterPath()
        from PyQt5.QtCore import QRectF
        outline.addRoundedRect(QRectF(self.rect()), 10, 10)
        self.setMask(QRegion(outline.toFillPolygon().toPolygon()))
