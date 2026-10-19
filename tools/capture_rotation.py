"""Capture production Qt widgets and trace only non-private selection state."""
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QTabWidget
from desktop_pet import DesktopPetWindow
from schedule import SettingsStore

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
app = QApplication([])
out = ROOT / 'docs/rotation'
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as temporary:
    pet = DesktopPetWindow(SettingsStore(Path(temporary) / 'settings.json'))
    pet._timer.stop(); pet._schedule_timer.stop()
    pet._schedule.now = lambda: datetime(2026, 10, 19, 15)
    pet._manual_sprite = 'office'
    pet.show(); app.processEvents()
    with patch('time.monotonic', return_value=100) as clock:
        pet._refresh_schedule(); pet._fade_started = 0; app.processEvents()
        pet.grab().save(str(out / 'pet-before-close.png'))
        pet._care_bubble.grab().save(str(out / 'greeting-primary.png'))
        trace = [{'event': 'startup', 'asset': pet._sprite_kind(),
                  'text_step': pet._schedule.text_step, 'next_due': pet._schedule.next_due}]
        pet._care_bubble.dismiss_by_user(); app.processEvents()
        pet.grab().save(str(out / 'pet-after-close.png'))
        trace.append({'event': 'user-close', 'asset': pet._sprite_kind(),
                      'text_step': pet._schedule.text_step, 'next_due': pet._schedule.next_due})
        clock.return_value = 400
        pet._refresh_schedule(); pet._fade_started = 0; app.processEvents()
        pet.grab().save(str(out / 'pet-periodic.png'))
        pet._care_bubble.grab().save(str(out / 'greeting-auxiliary.png'))
        trace.append({'event': 'periodic', 'asset': pet._sprite_kind(),
                      'text_step': pet._schedule.text_step, 'next_due': pet._schedule.next_due})
        pet._show_settings(); app.processEvents()
        dialog = pet._settings_dialog
        dialog.resize(960, 650)
        dialog.findChild(QTabWidget).setCurrentIndex(2)
        app.processEvents()
        dialog.grab().save(str(out / 'greeting-settings.png'))
        dialog.close()
    pet.close(); app.processEvents()
    (out / 'native-state-trace.json').write_text(json.dumps(trace, indent=2), encoding='utf-8')
print(out)
