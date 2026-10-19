"""Native Qt integration tests (no system clock changes, isolated settings)."""
import os
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from PyQt5.QtCore import Qt,QPoint,QEvent
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication,QTabWidget,QDialogButtonBox
from desktop_pet import DesktopPetWindow,PetState,WALK_RADIUS
from schedule import SettingsStore,Schedule

APP=QApplication.instance() or QApplication([])


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=SettingsStore(Path(self.temp.name)/'settings.json')
        self.pet=DesktopPetWindow(self.store)
        self.pet._timer.stop();self.pet._schedule_timer.stop();self.pet._care_timer.stop()
        self.pet.show();APP.processEvents()
        self.current=datetime(2026,10,19,14,0)
        self.pet._schedule.now=lambda:self.current
        self.pet._refresh_schedule()
        self.pet._care_bubble.hide()

    def tearDown(self):
        for w in APP.topLevelWidgets():w.close()
        APP.processEvents();self.temp.cleanup()

    def test_transparent_topmost_assets_and_missing_fallback(self):
        self.assertTrue(self.pet.testAttribute(Qt.WA_TranslucentBackground))
        self.assertTrue(self.pet.windowFlags() & Qt.WindowStaysOnTopHint)
        self.assertEqual(self.pet.width(),120)
        for im in self.pet._pixmaps.values():self.assertEqual(im.width(),320)
        with tempfile.TemporaryDirectory() as t:
            from shutil import copyfile
            from theme import ASSETS
            copyfile(ASSETS/'normal.png',Path(t)/'normal.png')
            with patch('desktop_pet.ASSETS',Path(t)):
                self.pet._load_pixmap()
            self.assertEqual(len(self.pet._asset_warnings),6)
            self.assertFalse(self.pet._pixmaps['sleep'].isNull())

    def test_long_bounded_walk_reverses(self):
        self.pet._appearance='normal';self.pet._enter_walk();directions=set()
        for i in range(190):
            self.pet._state_timer_ms=i*40;self.pet._update_walk()
            directions.add(self.pet._anim.walk_dir)
            self.assertLessEqual(abs(self.pet.x()-self.pet._anchor_x),WALK_RADIUS)
        self.assertEqual(directions,{-1,1});self.assertEqual(self.pet._state,PetState.WALK)

    def test_double_click_cycles_allowed_art_and_resets_at_boundary(self):
        self.current=datetime(2026,10,19,18,0);self.pet._refresh_schedule()
        self.pet._care_bubble.hide()
        seen=set()
        for _ in range(6):
            QTest.mouseDClick(self.pet,Qt.LeftButton,pos=QPoint(60,60))
            QTest.mouseRelease(self.pet,Qt.LeftButton,pos=QPoint(60,60))
            seen.add(self.pet._sprite_kind(False))
            self.assertFalse(self.pet._dragging)
            chosen=self.pet._manual_sprite
            self.pet._refresh_schedule()
            self.assertEqual(self.pet._manual_sprite,chosen)
        self.assertEqual(seen,{'normal','office','desktop','happy','late','late_scene'})
        self.current=datetime(2026,10,19,23,0);self.pet._refresh_schedule()
        self.assertIsNone(self.pet._manual_sprite)
        self.pet._care_bubble.hide()
        QTest.mouseDClick(self.pet,Qt.LeftButton,pos=QPoint(60,60))
        self.assertIsNone(self.pet._manual_sprite)

    def test_daytime_double_click_uses_all_day_art_with_care(self):
        self.pet._messages.clear()
        self.pet._care_bubble.hide()
        seen=set()
        for _ in range(4):
            QTest.mouseDClick(self.pet,Qt.LeftButton,pos=QPoint(60,60))
            seen.add(self.pet._sprite_kind())
            self.assertTrue(self.pet._care_bubble.isVisible())
            self.assertIn(self.pet._care_bubble.text(),__import__('care').CARE_MESSAGES)
            self.pet._care_bubble.hide()
        self.assertEqual(seen,{'normal','office','desktop','happy'})

    def test_drag_updates_anchor_and_grab_scale(self):
        p=self.pet;initial=p.pos();local=QPoint(60,60);global_pos=p.mapToGlobal(local)
        QTest.mousePress(p,Qt.LeftButton,pos=local)
        for _ in range(20):p._update_grabbed()
        self.assertLess(p._anim.grab_scale,.72)
        event=QMouseEvent(QEvent.MouseMove,local,global_pos+QPoint(-40,-20),Qt.NoButton,Qt.LeftButton,Qt.NoModifier)
        APP.sendEvent(p,event)
        QTest.mouseRelease(p,Qt.LeftButton,pos=local)
        self.assertNotEqual(initial,p.pos());self.assertEqual(p._anchor_x,p.x())
        self.assertEqual(p._state,PetState.IDLE)

    def test_seventh_image_is_now_transparent_character(self):
        image=self.pet._pixmaps['late_scene'].toImage()
        opaque=[]
        for y in range(image.height()):
            for x in range(image.width()):
                if image.pixelColor(x,y).alpha():opaque.append((x,y))
        width=max(x for x,y in opaque)-min(x for x,y in opaque)+1
        height=max(y for x,y in opaque)-min(y for x,y in opaque)+1
        self.assertLess(width,220)
        self.assertGreater(height,width*.8)
        self.assertEqual(image.pixelColor(min(x for x,y in opaque),min(y for x,y in opaque)).alpha(),0)

    def test_switch_care_never_replaces_important_reminder(self):
        self.pet._queue_message('重要提醒：任务A在18:00完成。')
        for _ in range(4):QTest.mouseDClick(self.pet,Qt.LeftButton,pos=QPoint(60,60))
        self.assertEqual(self.pet._care_bubble.text(),'重要提醒：任务A在18:00完成。')
        self.assertEqual(len(self.pet._messages),1)
        self.pet._care_bubble.hide();self.pet._drain_messages()
        self.assertIn(self.pet._care_bubble.text(),__import__('care').CARE_MESSAGES)

    def test_sleep_stops_walk_but_delivers_original_reminder(self):
        self.current=datetime(2026,10,19,23,0);self.pet._refresh_schedule()
        self.assertEqual(self.pet._appearance,'sleep')
        self.pet._state_timer_ms=999999;self.pet._update_idle()
        self.assertEqual(self.pet._state,PetState.IDLE)
        self.pet._care_clock.last=time.monotonic()-30
        with patch('desktop_pet.idle_seconds',return_value=0):
            self.pet._care_clock.interval=30;self.pet._check_care()
        self.assertTrue(self.pet._care_bubble.isVisible())
        self.assertEqual(self.pet._current_pixmap().cacheKey(),self.pet._pixmaps['normal'].cacheKey())
        self.pet._care_bubble.hide()
        self.assertEqual(self.pet._current_pixmap().cacheKey(),self.pet._pixmaps['sleep'].cacheKey())

    def test_sleep_greeting_is_deferred_and_click_is_gentle(self):
        self.current=datetime(2026,10,19,23,0);self.pet._refresh_schedule()
        self.assertFalse(self.pet._care_bubble.isVisible())
        self.assertIsNotNone(self.pet._greeting_pending)
        QTest.mouseClick(self.pet,Qt.LeftButton,pos=QPoint(60,60))
        self.assertTrue(self.pet._care_bubble.isVisible())
        self.assertIn('晚上好',self.pet._care_bubble.text())
        self.assertEqual(self.pet._appearance,'sleep')

    def test_important_messages_queue_before_greeting(self):
        self.pet._care_bubble.hide();self.pet._menu_open=True
        self.current=datetime(2026,10,19,18,0);self.pet._refresh_schedule()
        self.pet._queue_message('任务A：18:00，错误原因：文件不存在。')
        self.pet._queue_message('任务B：18:05')
        self.pet._menu_open=False;self.pet._drain_messages()
        self.assertEqual(self.pet._care_bubble.text(),'任务A：18:00，错误原因：文件不存在。')
        self.pet._care_bubble.hide();self.pet._drain_messages()
        self.assertEqual(self.pet._care_bubble.text(),'任务B：18:05')
        self.pet._care_bubble.hide();self.pet._drain_messages()
        self.assertIn('晚上好',self.pet._care_bubble.text())

    def test_no_wrong_random_assets_and_resume_refresh(self):
        for h,m,expected in [(5,59,'sleep'),(6,0,'normal'),(12,30,'sleep'),(14,0,'normal'),(18,0,'late'),(23,0,'sleep')]:
            self.current=datetime(2026,10,19,h,m);self.pet._refresh_schedule()
            self.pet._care_bubble.hide();self.pet._reminder_until=0
            self.assertEqual(self.pet._appearance,expected)
            for _ in range(4):
                self.pet._enter_walk()
                if expected=='normal':self.assertEqual(self.pet._current_pixmap().cacheKey(),self.pet._pixmaps['normal'].cacheKey())
        self.current=datetime(2026,10,20,6,0);self.pet._refresh_schedule()
        self.assertEqual(self.pet._appearance,'normal')

    def test_menu_native_corners_and_keyboard_navigation(self):
        menu=self.pet._build_menu();menu.popup(QPoint(120,120));APP.processEvents()
        self.assertFalse(menu.mask().contains(QPoint(0,0)))
        actions=[a for a in menu.actions() if a.isCheckable()]
        self.assertEqual(len(actions),2)
        menu.setActiveAction(actions[0]);QTest.keyClick(menu,Qt.Key_Return)
        self.assertFalse(self.pet._care_enabled)
        self.assertFalse(SettingsStore(self.store.path).data['care_enabled'])

    def test_settings_save_custom_text_and_unknown_fields(self):
        clock=self.pet._care_clock
        clock.active=123
        self.store.data['legacy']={'keep':'完整保留'}
        self.pet._show_settings();APP.processEvents();d=self.pet._settings_dialog
        d.table.item(0,3).setText('早上好，自己的文案。')
        d.boxes['nap_enabled'].setChecked(False);d.save()
        self.assertEqual(d.result(),d.Accepted)
        data=SettingsStore(self.store.path).data
        self.assertEqual(data['legacy'],{'keep':'完整保留'})
        self.assertEqual(data['greetings'][0]['messages'],['早上好，自己的文案。'])
        self.assertFalse(data['nap_enabled'])
        self.assertIs(self.pet._care_clock,clock)
        self.assertEqual(clock.active,123)
        self.assertFalse(d.testAttribute(Qt.WA_QuitOnClose))

    def test_settings_long_text_resize_and_focus(self):
        self.pet._show_settings();APP.processEvents();d=self.pet._settings_dialog
        d.resize(400,320);tabs=d.findChild(QTabWidget);tabs.setCurrentIndex(2)
        d.table.item(0,3).setText('早上好。'+('很长的自定义文字，'*30))
        d.table.resizeRowsToContents();APP.processEvents()
        self.assertTrue(d.table.horizontalScrollBar().maximum()>0 or d.table.columnWidth(3)>0)
        d.table.setFocus();QTest.keyClick(d.table,Qt.Key_Tab)
        self.assertIsNotNone(APP.focusWidget())
        self.assertLessEqual(d.findChild(QDialogButtonBox).geometry().bottom(),d.height())

if __name__=='__main__':unittest.main()
