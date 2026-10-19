"""Regressions for independent image/text/bubble/scheduler state."""
import copy
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from PyQt5.QtCore import Qt, QPoint, QEvent
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from companion_config import CORE_MESSAGES, CARE_MESSAGES, ImageRotation
from schedule import Schedule, SettingsStore, DEFAULTS, validate
from desktop_pet import DesktopPetWindow

APP = QApplication.instance() or QApplication([])


class RotationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'settings.json'
        self.store = SettingsStore(self.path)
        self.schedule = Schedule(self.store)

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_originals_and_alternating_auxiliary(self):
        expected = [
            '早上好呀 新的一天，我陪着你。',
            '中午好～ 睡醒也要记得好好吃饭。',
            '下午好呀～ 除了上课健身也要注意安全。',
            "晚上好哦～今天辛苦咯，I'm here 随时都在。",
        ]
        for hour, g, original in zip((8, 11, 15, 19), self.store.data['greetings'], expected):
            self.assertEqual(g['primary'], original)
            messages = []
            for _ in range(10):
                key, text = self.schedule.greeting(datetime(2026, 10, 19, hour))
                messages.append(text)
                self.schedule.delivered(key)
            self.assertEqual(messages[::2], [original] * 5)
            auxiliary = messages[1::2]
            self.assertTrue(all(a != b for a, b in zip(auxiliary, auxiliary[1:])))
            self.assertEqual(messages[1], g['messages'][0])
            self.assertEqual(messages[3], g['messages'][1])

    def test_cross_midnight_keeps_same_night_text_progress(self):
        key,text=self.schedule.greeting(datetime(2026,10,19,23,55))
        self.schedule.delivered(key)
        key_after,text_after=self.schedule.greeting(datetime(2026,10,20,0,0))
        self.assertEqual(key,key_after)
        self.assertEqual(text_after,self.store.data['greetings'][3]['messages'][0])

    def test_no_auxiliary_and_period_entry_reset(self):
        g = self.store.data['greetings'][0]
        g['messages'] = []
        validate(self.store.data)
        for _ in range(3):
            key, text = self.schedule.greeting(datetime(2026, 10, 19, 8))
            self.assertEqual(text, CORE_MESSAGES['morning'])
            self.schedule.delivered(key)
        self.assertEqual(self.schedule.greeting(datetime(2026, 10, 19, 11))[1], CORE_MESSAGES['noon'])

    def test_legacy_copy_migration_preserves_every_line_and_unknown_data(self):
        raw = copy.deepcopy(DEFAULTS)
        raw.pop('greeting_copy_version')
        for g in raw['greetings']:
            g.pop('primary')
            g['messages'] = ['自定义原文  空格也保留']
        raw['history'] = ['任务A，不得加入随机池']
        self.path.write_text(json.dumps(raw, ensure_ascii=False), encoding='utf-8')
        migrated = SettingsStore(self.path)
        self.assertFalse(migrated.warning)
        for g in migrated.data['greetings']:
            self.assertEqual(g['messages'][0], '自定义原文  空格也保留')
            self.assertEqual(g['primary'], CORE_MESSAGES[g['id']])
        pool = [text for g in migrated.data['greetings'] for text in g['messages']]
        self.assertTrue(set(CARE_MESSAGES).issubset(pool))
        self.assertNotIn(raw['history'][0], pool)
        self.assertEqual(migrated.data['history'], raw['history'])
        self.assertEqual(json.loads(self.path.read_text(encoding='utf-8')), raw)
        migrated.save()
        self.assertEqual(SettingsStore(self.path).data, migrated.data)
        self.assertEqual(json.loads(self.path.with_suffix('.json.bak').read_text(encoding='utf-8')), raw)

    def test_one_two_and_all_asset_rounds(self):
        for count in (1, 2, 4, 6, 7):
            allowed = tuple(str(i) for i in range(count))
            rotation = ImageRotation()
            current = None
            result = []
            for _ in range(count * 4):
                current = rotation.next(allowed, current)
                result.append(current)
            for start in range(0, len(result), count):
                self.assertEqual(set(result[start:start+count]), set(allowed))
            if count > 1:
                self.assertTrue(all(a != b for a, b in zip(result, result[1:])))

    def test_initial_image_still_follows_time(self):
        for hour,minute,expected in ((8,0,'normal'),(12,45,'sleep'),(23,30,'sleep'),(19,0,'late_scene')):
            self.schedule.preview=datetime(2026,10,19,hour,minute)
            self.store.data['late_variant']='late_scene'
            self.assertEqual(self.schedule.initial_asset(),expected)

    def test_allowed_assets_all_boundaries(self):
        for stamp, expected in [
            ('05:59', {'sleep'}), ('06:00', {'normal','office','desktop','happy'}),
            ('11:00', {'normal','office','desktop','happy'}), ('12:30', {'sleep'}),
            ('14:00', {'normal','office','desktop','happy'}),
            ('18:00', {'normal','office','desktop','happy','late','late_scene'}),
            ('23:00', {'sleep'}), ('00:00', {'sleep'}),
        ]:
            self.assertEqual(set(self.schedule.allowed_assets(datetime.fromisoformat('2026-10-19T'+stamp))), expected)

    def test_single_clock_resume_does_not_catch_up_or_reset_on_delivery(self):
        self.assertEqual(self.schedule.poll(100), 'startup')
        due = self.schedule.next_due
        key, _ = self.schedule.greeting(datetime(2026,10,19,8))
        self.schedule.delivered(key)
        self.assertEqual(self.schedule.next_due, due)
        self.assertIsNone(self.schedule.poll(399))
        self.assertEqual(self.schedule.poll(3600), 'periodic')
        self.assertIsNone(self.schedule.poll(3600))
        self.assertEqual(self.schedule.next_due, 3900)


class NativeRotationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.p = DesktopPetWindow(SettingsStore(Path(self.temp.name)/'settings.json'))
        self.p._timer.stop(); self.p._schedule_timer.stop()
        self.clock = patch('time.monotonic', return_value=100)
        self.mock_clock = self.clock.start()
        self.current = datetime(2026,10,19,15)
        self.p._schedule.now = lambda: self.current
        self.p._manual_sprite = 'normal'
        self.p.show(); APP.processEvents()
        self.p._refresh_schedule()

    def tearDown(self):
        self.p.close(); APP.processEvents()
        self.clock.stop(); self.temp.cleanup()

    def double_click(self, widget=None):
        QTest.mouseDClick(widget or self.p, Qt.LeftButton, pos=QPoint(20,20))
        QTest.mouseRelease(widget or self.p, Qt.LeftButton, pos=QPoint(20,20))

    def test_double_click_traverses_rounds_without_advancing_text_or_clock(self):
        p = self.p
        original = (p._schedule.text_step, p._schedule.next_due, p._care_bubble.text())
        result = []
        for _ in range(21):
            self.double_click()
            result.append(p._sprite_kind())
        for offset in range(0,21,7):
            self.assertEqual(set(result[offset:offset+7]), set(p._pixmaps))
        self.assertTrue(all(a!=b for a,b in zip(result,result[1:])))
        self.assertEqual((p._schedule.text_step, p._schedule.next_due, p._care_bubble.text()), original)

    def test_user_close_preserves_art_animation_text_index_and_deadline(self):
        p = self.p
        p._advance_image('double-click')
        p._start_gesture('happy')
        before = (p._sprite_kind(), p._state, p._gesture_started, p._gesture_clip,
                  p._schedule.text_step, p._schedule.auxiliary_index, p._schedule.next_due,
                  p._fade_started, list(p._image_rotation.remaining))
        before_pixels=p.grab().toImage()
        QTest.mouseClick(p._care_bubble.close_button, Qt.LeftButton)
        self.assertEqual(p.grab().toImage(),before_pixels)
        for _ in range(5): p._refresh_schedule()
        self.assertFalse(p._care_bubble.isVisible())
        after = (p._sprite_kind(), p._state, p._gesture_started, p._gesture_clip,
                 p._schedule.text_step, p._schedule.auxiliary_index, p._schedule.next_due,
                 p._fade_started, list(p._image_rotation.remaining))
        self.assertEqual(before, after)
        self.mock_clock.return_value = 400
        p._refresh_schedule()
        self.assertNotEqual(p._sprite_kind(), before[0])
        self.assertTrue(p._care_bubble.isVisible())
        self.assertEqual(p._care_bubble.text(), p._store.data['greetings'][2]['messages'][0])
        self.assertEqual(p._schedule.next_due, 700)

    def test_bubble_click_double_click_and_drag_do_not_reach_pet(self):
        p = self.p; before = (p._sprite_kind(), p._schedule.text_step, p._schedule.next_due)
        for widget in (p._care_bubble, p._care_bubble.label, p._care_bubble.scroll.viewport()):
            QTest.mouseClick(widget, Qt.LeftButton, pos=QPoint(10,10))
            self.double_click(widget)
            QTest.mousePress(widget, Qt.LeftButton, pos=QPoint(10,10))
            QTest.mouseMove(widget, QPoint(20,20))
            QTest.mouseRelease(widget, Qt.LeftButton, pos=QPoint(20,20))
        self.assertEqual((p._sprite_kind(), p._schedule.text_step, p._schedule.next_due), before)

    def test_time_boundary_does_not_override_user_image(self):
        p=self.p;p._manual_sprite='late_scene'
        for current in (datetime(2026,10,19,18),datetime(2026,10,19,23),datetime(2026,10,20,6)):
            self.current=current;p._refresh_schedule()
            self.assertEqual(p._sprite_kind(),'late_scene')

    def test_timeout_and_important_reminder_never_replace_base_art(self):
        p = self.p;p._manual_sprite='office'
        p._care_bubble.hide()
        p._queue_message('重要任务：18:00，错误原因：文件不存在。')
        self.assertEqual(p._sprite_kind(),'office')
        p._care_bubble.timer.timeout.emit()
        self.assertEqual(p._sprite_kind(),'office')
        self.assertFalse(p._care_bubble.isVisible())

    def test_double_click_after_drag_is_ignored(self):
        p=self.p;local=QPoint(60,60);global_pos=p.mapToGlobal(local)
        QTest.mousePress(p,Qt.LeftButton,pos=local)
        event=QMouseEvent(QEvent.MouseMove,local,global_pos+QPoint(-40,-20),Qt.NoButton,Qt.LeftButton,Qt.NoModifier)
        APP.sendEvent(p,event);QTest.mouseRelease(p,Qt.LeftButton,pos=local)
        before=p._sprite_kind();self.double_click()
        self.assertEqual(p._sprite_kind(),before)

    def test_settings_menu_and_single_click_keep_base_image(self):
        p=self.p;p._manual_sprite='office';before=p._schedule.next_due
        QTest.mouseClick(p,Qt.LeftButton,pos=QPoint(60,60))
        self.assertEqual(p._sprite_kind(),'office')
        menu=p._build_menu();menu.popup(QPoint(100,100));APP.processEvents();menu.close()
        p._show_settings();APP.processEvents();p._settings_dialog.save()
        self.assertEqual(p._sprite_kind(),'office')
        self.assertEqual(p._schedule.next_due,before)

    def test_real_click_then_double_click_does_not_deliver_sleep_greeting(self):
        p=self.p;p._care_bubble.hide()
        self.current=datetime(2026,10,19,23)
        self.mock_clock.return_value=400;p._refresh_schedule()
        self.assertIsNotNone(p._greeting_pending)
        before=(p._schedule.text_step,p._schedule.next_due)
        QTest.mouseClick(p,Qt.LeftButton,pos=QPoint(60,60))
        self.double_click()
        QTest.qWait(APP.doubleClickInterval()+150)
        self.assertFalse(p._care_bubble.isVisible())
        self.assertEqual((p._schedule.text_step,p._schedule.next_due),before)
        self.assertIn(p._sprite_kind(),p._pixmaps)

    def test_pending_greeting_does_not_resurface_on_close(self):
        p=self.p;p._care_bubble.hide();p._queue_message('重要任务：18:00完成。')
        self.mock_clock.return_value=400;p._refresh_schedule()
        self.assertIsNotNone(p._greeting_pending)
        before=(p._schedule.text_step,p._schedule.next_due,p._sprite_kind())
        QTest.mouseClick(p._care_bubble.close_button,Qt.LeftButton)
        for _ in range(4):p._refresh_schedule()
        self.assertFalse(p._care_bubble.isVisible())
        self.assertEqual((p._schedule.text_step,p._schedule.next_due,p._sprite_kind()),before)

    def test_periodic_rotation_during_reminder_keeps_one_current_greeting(self):
        p=self.p;p._care_bubble.hide();p._queue_message('重要任务：18:00完成。')
        for tick in (400,700,1000):
            self.mock_clock.return_value=tick;p._refresh_schedule()
            self.assertEqual(p._care_bubble.text(),'重要任务：18:00完成。')
            self.assertIsNotNone(p._greeting_pending)
        # Timeout is allowed to drain queued messages on the regular scheduler;
        # unlike an explicit user dismissal it does not suppress pending text.
        p._care_bubble.hide();p._refresh_schedule()
        self.assertEqual(p._care_bubble.text(),p._store.data['greetings'][2]['messages'][0])
        self.assertEqual(p._schedule.text_step,2)
        self.assertEqual(p._schedule.next_due,1300)

    def test_periodic_at_night_traverses_all_seven(self):
        p=self.p;self.current=datetime(2026,10,19,23,30)
        seen=[]
        for tick in range(400,2500,300):
            self.mock_clock.return_value=tick;p._refresh_schedule()
            seen.append(p._sprite_kind());p._care_bubble.hide()
        self.assertEqual(set(seen),set(p._pixmaps))

    def test_night_and_nap_double_click_use_all_seven(self):
        p=self.p
        for current in (datetime(2026,10,19,12,45),datetime(2026,10,19,19),datetime(2026,10,19,23,30)):
            self.current=current;p._refresh_schedule();seen=[]
            for _ in range(14):
                self.double_click();seen.append(p._sprite_kind())
            for offset in (0,7):
                self.assertEqual(set(seen[offset:offset+7]),set(p._pixmaps))



if __name__ == '__main__':
    unittest.main()
