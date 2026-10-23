"""Native gesture arbitration and the 1.01 head-pat response."""
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from PyQt5.QtCore import Qt,QPoint,QEvent
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication
from desktop_pet import DesktopPetWindow
from schedule import SettingsStore

APP=QApplication.instance() or QApplication([])


class PatTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.pet=DesktopPetWindow(SettingsStore(Path(self.temp.name)/'settings.json'))
        self.pet._timer.stop();self.pet._schedule_timer.stop()
        self.pet._schedule.now=lambda:datetime(2026,10,23,15)
        self.pet.show();APP.processEvents();self.pet._refresh_schedule()
        self.pet._care_bubble.hide()

    def tearDown(self):
        self.pet.close();APP.processEvents();self.temp.cleanup()

    def wait_for_single(self):QTest.qWait(APP.doubleClickInterval()+150)

    def test_single_click_exact_copy_heart_animation_and_independent_clock(self):
        p=self.pet
        before=(p._sprite_kind(),p.pos(),p._schedule.text_step,p._schedule.next_due,
                dict(p._schedule.interaction_steps))
        QTest.mouseClick(p,Qt.LeftButton,pos=QPoint(60,60))
        self.assertIsNone(p._pat_started)
        self.wait_for_single()
        self.assertIsNotNone(p._pat_started)
        self.assertEqual(p._gesture_clip,'interact')
        self.assertEqual(p._care_bubble.text(),'收到你的摸摸啦。')
        self.assertTrue(p._care_bubble.isVisible())
        self.assertEqual((p._sprite_kind(),p.pos(),p._schedule.text_step,p._schedule.next_due,
                          dict(p._schedule.interaction_steps)),before)

    def test_double_click_cancels_single_pat(self):
        p=self.pet
        QTest.mouseClick(p,Qt.LeftButton,pos=QPoint(60,60))
        QTest.mouseDClick(p,Qt.LeftButton,pos=QPoint(60,60))
        QTest.mouseRelease(p,Qt.LeftButton,pos=QPoint(60,60))
        self.wait_for_single()
        self.assertIsNone(p._pat_started)
        self.assertNotEqual(p._care_bubble.text(),'收到你的摸摸啦。')

    def test_drag_does_not_pat_and_cancels_an_earlier_click(self):
        p=self.pet;local=QPoint(60,60)
        QTest.mouseClick(p,Qt.LeftButton,pos=local)
        QTest.mousePress(p,Qt.LeftButton,pos=local)
        event=QMouseEvent(QEvent.MouseMove,local,p.mapToGlobal(local)+QPoint(-40,-20),
                          Qt.NoButton,Qt.LeftButton,Qt.NoModifier)
        APP.sendEvent(p,event);QTest.mouseRelease(p,Qt.LeftButton,pos=local)
        self.wait_for_single()
        self.assertIsNone(p._pat_started)
        self.assertFalse(p._care_bubble.isVisible())

    def test_pat_does_not_replace_important_reminder(self):
        p=self.pet;p._queue_message('重要任务：18:00完成。')
        QTest.mouseClick(p,Qt.LeftButton,pos=QPoint(60,60));self.wait_for_single()
        self.assertEqual(p._care_bubble.text(),'重要任务：18:00完成。')
        self.assertEqual(p._interaction_pending,'收到你的摸摸啦。')
        p._care_bubble.hide();p._drain_messages()
        self.assertEqual(p._care_bubble.text(),'收到你的摸摸啦。')

    def test_reduced_mode_has_static_heart_and_expires(self):
        p=self.pet;p._store.data['animation_mode']='reduced';p._fade_started=0
        p._pat_started=None;before=p.grab().toImage()
        p._pat_started=100
        with patch('desktop_pet.time.monotonic',return_value=100.2):first=p.grab().toImage()
        with patch('desktop_pet.time.monotonic',return_value=100.6):second=p.grab().toImage()
        with patch('desktop_pet.time.monotonic',return_value=101.2):expired=p.grab().toImage()
        self.assertNotEqual(first,before)
        self.assertEqual(first,second)
        self.assertEqual(expired,before)

    def test_bubble_close_never_pats(self):
        p=self.pet;p._show_care()
        QTest.mouseClick(p._care_bubble.close_button,Qt.LeftButton)
        self.wait_for_single()
        self.assertIsNone(p._pat_started)
        self.assertFalse(p._care_bubble.isVisible())


if __name__=='__main__':unittest.main()
