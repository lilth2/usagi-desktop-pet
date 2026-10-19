"""Capture real native Qt widgets using isolated data; never change OS time."""
import json
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PyQt5.QtCore import Qt,QPoint
from PyQt5.QtWidgets import QApplication,QTabWidget
from desktop_pet import DesktopPetWindow
from schedule import SettingsStore

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
app=QApplication([])
tag=os.environ.get('QT_SCALE_FACTOR','1').replace('.','_')
out=ROOT/'docs/chiikawa'/('scale-'+tag)
out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as temp:
    p=DesktopPetWindow(SettingsStore(Path(temp)/'settings.json'))
    p._timer.stop();p._schedule_timer.stop()
    p._store.data['greetings_enabled']=False
    p.show();app.processEvents()
    for name,iso,variant in [('normal','2026-10-19T14:00','late'),('office','2026-10-19T14:00','late'),('desktop','2026-10-19T14:00','late'),('happy','2026-10-19T14:00','late'),('late','2026-10-19T18:00','late'),('late-scene','2026-10-19T18:00','late_scene'),('sleep','2026-10-19T23:00','late')]:
        p._schedule.preview=datetime.fromisoformat(iso)
        p._store.data['late_variant']=variant
        p._refresh_schedule();p._manual_sprite=name.replace('-','_');p._fade_started=0;p.update();app.processEvents()
        p.grab().save(str(out/(name+'.png')))
    p._schedule.preview=datetime(2026,10,19,14,0);p._refresh_schedule()
    p._show_care();app.processEvents()
    p._care_bubble.grab().save(str(out/'reminder.png'))
    p._care_bubble.hide()
    menu=p._build_menu();menu.popup(QPoint(150,150));app.processEvents()
    menu.grab().save(str(out/'menu.png'))
    assert not menu.mask().contains(QPoint(0,0));menu.close()
    p._show_settings();app.processEvents();d=p._settings_dialog
    tabs=d.findChild(QTabWidget)
    for index,name in enumerate(('settings','appearance-settings','greeting-settings')):
        tabs.setCurrentIndex(index);app.processEvents();d.grab().save(str(out/(name+'.png')))
    d.resize(400,320);app.processEvents();d.grab().save(str(out/'settings-small.png'))
    (out/'display-info.json').write_text(json.dumps({'requested_scale':tag,'device_pixel_ratio':p.devicePixelRatioF(),'logical_pet':[p.width(),p.height()],'screens':[{'name':s.name(),'width':s.geometry().width(),'height':s.geometry().height()} for s in app.screens()]},indent=2),encoding='utf-8')
    d.close();p.close()
print('Native UI captures:',out)
