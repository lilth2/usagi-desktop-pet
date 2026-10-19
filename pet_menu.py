"""Usagi-themed native popup, using the existing character artwork."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMenu, QWidgetAction, QWidget, QHBoxLayout, QVBoxLayout, QLabel


class PetMenu(QMenu):
    def __init__(self, parent, portrait):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet('''
            QMenu {
                background-color: #fff8df; color: #64452f;
                border: 2px solid #dcb878; border-radius: 18px;
                padding: 10px 8px; font-family: "Microsoft YaHei UI";
                font-size: 13px;
            }
            QMenu::item { padding: 12px 16px 12px 30px; margin: 3px 4px;
                border-radius: 11px; background: transparent; }
            QMenu::item:selected { background: #ffe2a3; color: #573d29; }
            QMenu::separator { height: 1px; background: #eedbb2; margin: 7px 14px; }
            QMenu::indicator { width: 14px; height: 14px; margin-left: 8px;
                border: 1px solid #cfac6a; border-radius: 7px; background: #fffdf5; }
            QMenu::indicator:checked { background: #efbb55; border: 2px solid #9b7036; }
            QLabel { background: transparent; border: none; color: #64452f; }
        ''')
        header = QWidget(self)
        row = QHBoxLayout(header)
        row.setContentsMargins(12, 4, 14, 8)
        picture = QLabel()
        picture.setPixmap(portrait.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        row.addWidget(picture)
        text = QVBoxLayout()
        title = QLabel("呀哈！乌萨奇的小窝")
        title.setStyleSheet("font-size:15px;font-weight:600;")
        subtitle = QLabel("慢慢走，也陪你好好休息 ♡")
        subtitle.setStyleSheet("font-size:11px;color:#99794e;")
        text.addWidget(title)
        text.addWidget(subtitle)
        row.addLayout(text)
        action = QWidgetAction(self)
        action.setDefaultWidget(header)
        self.addAction(action)
        self.addSeparator()
