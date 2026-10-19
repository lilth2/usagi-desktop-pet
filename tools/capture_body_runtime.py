"""Capture the real desktop renderer in all three animation modes."""
import sys
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
from io import BytesIO
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PyQt5.QtCore import QBuffer,QIODevice,QPoint
from PyQt5.QtWidgets import QApplication
from desktop_pet import DesktopPetWindow,PetState
from schedule import SettingsStore

app=QApplication([])
doc=ROOT/'docs/body-animation';doc.mkdir(exist_ok=True)

def grab(widget):
    buffer=QBuffer();buffer.open(QIODevice.WriteOnly);widget.grab().save(buffer,'PNG')
    return Image.open(BytesIO(bytes(buffer.data()))).convert('RGBA')

with tempfile.TemporaryDirectory() as temp:
    p=DesktopPetWindow(SettingsStore(Path(temp)/'settings.json'))
    for timer in (p._timer,p._care_timer,p._schedule_timer):timer.stop()
    p._store.data['greetings_enabled']=False
    p._schedule.preview=datetime(2026,10,19,14,0)
    p._refresh_schedule();p._manual_sprite='happy';p._fade_started=0
    p._animation_started=100;p._gesture_started=100;p._gesture_clip='happy'
    p.show();app.processEvents()
    frames=[]
    for index in range(32):
        elapsed=index/31*1.6
        frame=Image.new('RGB',(360,140),'#fff9f3')
        for col,mode in enumerate(('whole','body','reduced')):
            p._store.data['animation_mode']=mode
            p._state=PetState.IDLE;p._state_timer_ms=int(elapsed*1000);p._update_idle()
            with patch('desktop_pet.time.monotonic',return_value=100+elapsed):
                p.update();app.processEvents();image=grab(p)
            frame.paste(image,(col*120,20),image)
            ImageDraw.Draw(frame).text((col*120+8,3),mode,fill='#59464d')
            if index==16:image.save(doc/f'runtime-{mode}.png')
        frames.append(frame)
    frames[0].save(doc/'runtime-three-modes.gif',save_all=True,append_images=frames[1:],duration=50,loop=0,disposal=2)
    p._store.data['animation_mode']='body'
    p._show_settings();app.processEvents();p._settings_dialog.grab().save(str(doc/'runtime-settings.png'))
    p._settings_dialog.close()
    menu=p._build_menu();menu.popup(QPoint(100,100));app.processEvents();menu.grab().save(str(doc/'runtime-menu.png'));menu.close()
    p._show_care();app.processEvents();p._care_bubble.grab().save(str(doc/'runtime-care.png'))
    p.close()
print('Native runtime captures:',doc)
