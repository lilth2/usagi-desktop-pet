"""Production-widget preview on a neutral background, no desktop capture."""
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap,QPainter,QColor
from desktop_pet import DesktopPetWindow
from schedule import SettingsStore

app=QApplication([])
out=ROOT/'docs/compact-bubble';out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as temporary:
    p=DesktopPetWindow(SettingsStore(Path(temporary)/'settings.json'))
    p._timer.stop();p._schedule_timer.stop()
    p._schedule.now=lambda:datetime(2026,10,19,15)
    p._store.data['animation_mode']='reduced'
    p._manual_sprite='happy';p.move(500,400);p.show();app.processEvents()
    p._show_care();app.processEvents();b=p._care_bubble
    b.grab().save(str(out/'bubble.png'))
    bounds=p.frameGeometry().united(b.frameGeometry()).adjusted(-10,-10,10,10)
    canvas=QPixmap(bounds.size());canvas.fill(QColor('#f3f0ed'))
    painter=QPainter(canvas)
    for widget in (p,b):painter.drawPixmap(widget.pos()-bounds.topLeft(),widget.grab())
    painter.end();canvas.save(str(out/'pet-and-bubble.png'))
    (out/'dimensions.json').write_text(json.dumps({'pet':[p.width(),p.height()],
        'bubble':[b.width(),b.height()],'tail':b._tail_side}),encoding='utf-8')
    p.close();app.processEvents()
print(out)
