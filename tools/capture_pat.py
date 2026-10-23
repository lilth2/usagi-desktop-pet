"""Capture the real 1.01 widgets with head-pat animation, using isolated data."""
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap,QPainter,QColor
from desktop_pet import DesktopPetWindow
from schedule import SettingsStore

app=QApplication([]);out=ROOT/'docs/v1.01';out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as temporary:
    p=DesktopPetWindow(SettingsStore(Path(temporary)/'settings.json'))
    p._timer.stop();p._schedule_timer.stop()
    p._schedule.now=lambda:datetime(2026,10,23,15)
    p._manual_sprite='happy';p._animation_started=100
    p.move(500,400);p.show();app.processEvents()
    with patch('desktop_pet.time.monotonic',return_value=100):
        p._finish_single_click(p._click_token)
    with patch('desktop_pet.time.monotonic',return_value=100.25):
        p._fade_started=0;p.update();app.processEvents()
        bubble=p._care_bubble
        bounds=p.frameGeometry().united(bubble.frameGeometry()).adjusted(-10,-10,10,10)
        canvas=QPixmap(bounds.size());canvas.fill(QColor('#f3f0ed'))
        painter=QPainter(canvas)
        for widget in (p,bubble):painter.drawPixmap(widget.pos()-bounds.topLeft(),widget.grab())
        painter.end();canvas.save(str(out/'head-pat.png'))
        p.grab().save(str(out/'heart-detail.png'))
    p.close();app.processEvents()
print(out)
