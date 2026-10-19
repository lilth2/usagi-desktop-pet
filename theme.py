"""Shared Chiikawa palette and resources (no legacy-character fallback)."""
import sys
from pathlib import Path

NAME = '吉伊卡哇'
BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
ASSETS = BASE / 'assets' / 'chiikawa' / 'processed'
INK = '#59464d'
PINK = '#f6dce5'
CREAM = '#fffaf2'
BORDER = '#d5b5bf'
DIALOG_STYLE = '''
QWidget { font-family:"Microsoft YaHei UI";font-size:12px; }
QDialog { background:#fffaf7; color:#59464d; }
QLabel, QCheckBox, QGroupBox { color:#59464d; }
QTabWidget::pane { border:1px solid #d5b5bf; border-radius:8px; }
QTabBar::tab { background:#fff4f2; color:#59464d; padding:8px 14px; }
QTabBar::tab:selected { background:#f6dce5; border-bottom:2px solid #a56a82; }
QPushButton { background:#f6dce5; color:#59464d; border:1px solid #c99dac;
 border-radius:6px; padding:7px 12px; }
QPushButton:hover { background:#edc6d5; }
QPushButton:focus, QLineEdit:focus, QTimeEdit:focus { border:2px solid #a56a82; }
QPushButton:disabled { color:#927e85; background:#f1e9e9; }
QLineEdit, QTimeEdit, QSpinBox, QComboBox, QTableWidget { background:#ffffff;
 color:#59464d; border:1px solid #d5b5bf; padding:4px; }
QTableWidget::item:selected { background:#f6dce5; color:#59464d; }
QHeaderView::section { background:#fff0f3; color:#59464d; padding:6px; }
'''


def resource(kind):
    path = ASSETS / f'{kind}.png'
    return path if path.is_file() else ASSETS / 'normal.png'

MENU_STYLE = '\n            QMenu {\n                background-color: #fffaf5; color: #59464d;\n                border: 1px solid #d5b5bf; border-radius: 10px;\n                padding: 5px 4px; font-family: "Microsoft YaHei UI";\n                font-size: 11px;\n            }\n            QMenu::item { padding: 6px 10px 6px 22px; margin: 1px 2px;\n                border-radius: 6px; background: transparent; }\n            QMenu::item:selected { background: #f6dce5; color: #59464d; }\n            QMenu::item:disabled { color:#9c8c91; }\n            QMenu::separator { height: 1px; background: #ead5db; margin: 4px 9px; }\n            QMenu::indicator { width: 10px; height: 10px; margin-left: 5px;\n                border: 1px solid #c29ca9; border-radius: 5px; background: #fffdf9; }\n            QMenu::indicator:checked { background: #c787a0; border: 1px solid #946378; }\n            QLabel { background: transparent; border: none; color: #59464d; }\n        '

BUBBLE_STYLE = 'background:transparent;color:#59464d;border:none;font-family:"Microsoft YaHei UI";font-size:12px;'
