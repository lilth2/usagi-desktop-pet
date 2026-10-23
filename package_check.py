"""Optional packaged-app check; isolated config, never touches user settings."""
import json
import platform
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt, QPointF, QTimer
from PyQt5.QtGui import QMouseEvent


def run(app):
    from desktop_pet import DesktopPetWindow
    from schedule import SettingsStore
    from care import idle_seconds
    output=Path(sys.argv[sys.argv.index('--package-check')+1]).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=tempfile.TemporaryDirectory()
    pet=DesktopPetWindow(SettingsStore(Path(temporary.name)/'settings.json'))
    pet._timer.stop();pet._schedule_timer.stop()
    pet._schedule.now=lambda:datetime(2026,10,19,15)
    pet._manual_sprite='normal'
    app.setQuitOnLastWindowClosed(False)
    pet.show()
    result={'platform':platform.platform(),'architecture':platform.machine(),'success':False}
    def check():
        try:
            assert len(pet._pixmaps)==7 and all(not p.isNull() for p in pet._pixmaps.values())
            pet._refresh_schedule()
            deadline=pet._schedule.next_due
            step=pet._schedule.text_step
            seen=[]
            for _ in range(7):
                event=QMouseEvent(QMouseEvent.MouseButtonDblClick,QPointF(60,60),Qt.LeftButton,Qt.LeftButton,Qt.NoModifier)
                app.sendEvent(pet,event)
                seen.append(pet._sprite_kind())
                assert not pet._body_frame().isNull()
            assert set(seen)==set(pet._pixmaps)
            assert pet._care_bubble.active and pet._care_bubble.isVisible()
            assert pet._care_bubble.width()<=168
            before=(pet._sprite_kind(),pet._schedule.next_due,pet._schedule.text_step)
            pet._care_bubble.close_button.click()
            assert before==(pet._sprite_kind(),pet._schedule.next_due,pet._schedule.text_step)
            assert deadline==pet._schedule.next_due and step==pet._schedule.text_step
            pet._store.data['animation_mode']='reduced'
            pet._fade_started=0
            before_pat=pet.grab().toImage()
            pet._finish_single_click(pet._click_token)
            assert pet._care_bubble.text()=='收到你的摸摸啦。'
            assert pet._pat_started is not None
            assert pet.grab().toImage()!=before_pat
            assert deadline==pet._schedule.next_due and step==pet._schedule.text_step
            pet._show_settings()
            assert pet._settings_dialog.isVisible()
            pet._settings_dialog.close()
            idle=idle_seconds()
            if sys.platform in ('win32','darwin'):
                assert idle is not None and idle>=0,'OS idle-time API unavailable'
            result.update(success=True,images=seen,independent_clock=True,pat_response=True,
                          close_keeps_art=True,settings_open=True,idle_api_available=idle is not None,
                          bubble_size=[pet._care_bubble.width(),pet._care_bubble.height()])
        except Exception:
            result['error']=traceback.format_exc()
        finally:
            output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            pet.close();temporary.cleanup()
            app.exit(0 if result['success'] else 1)
    QTimer.singleShot(1200,check)
    return app.exec_()
