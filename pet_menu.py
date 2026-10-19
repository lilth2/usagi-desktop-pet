"""Usagi-themed native popup, using the existing character artwork."""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainterPath, QRegion
from PyQt5.QtWidgets import QMenu, QWidgetAction, QWidget, QHBoxLayout, QVBoxLayout, QLabel


class PetMenu(QMenu):
    def __init__(self, parent, portrait):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet('''
            QMenu {
                background-color: #fff8df; color: #64452f;
                border: 1px solid #dcb878; border-radius: 10px;
                padding: 5px 4px; font-family: "Microsoft YaHei UI";
                font-size: 11px;
            }
            QMenu::item { padding: 6px 10px 6px 22px; margin: 1px 2px;
                border-radius: 6px; background: transparent; }
            QMenu::item:selected { background: #ffe2a3; color: #573d29; }
            QMenu::separator { height: 1px; background: #eedbb2; margin: 4px 9px; }
            QMenu::indicator { width: 10px; height: 10px; margin-left: 5px;
                border: 1px solid #cfac6a; border-radius: 5px; background: #fffdf5; }
            QMenu::indicator:checked { background: #efbb55; border: 1px solid #9b7036; }
            QLabel { background: transparent; border: none; color: #64452f; }
        ''')
        header = QWidget(self)
        row = QHBoxLayout(header)
        row.setContentsMargins(6, 2, 6, 3)
        row.setSpacing(4)
        picture = QLabel()
        picture.setPixmap(portrait.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        row.addWidget(picture)
        text = QVBoxLayout()
        text.setSpacing(1)
        title = QLabel("乌萨奇的小窝")
        title.setStyleSheet("font-size:12px;font-weight:600;")
        subtitle = QLabel("呀哈～陪着你 ♡")
        subtitle.setStyleSheet("font-size:10px;color:#99794e;")
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
