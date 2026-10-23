"""Verify real painted character/heart pixels never intersect the bubble."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QRegion
from PyQt5.QtCore import QPoint
from desktop_pet import DesktopPetWindow
from schedule import SettingsStore

APP=QApplication.instance() or QApplication([])


class BubbleSpacingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.p=DesktopPetWindow(SettingsStore(Path(self.temp.name)/'settings.json'))
        self.p._timer.stop();self.p._schedule_timer.stop()
        self.p._schedule.now=lambda:datetime(2026,10,23,15)
        self.p._animation_started=100;self.p._gesture_started=100
        self.p._fade_started=0;self.p._manual_sprite='happy'
        self.p.move(500,400);self.p.show();APP.processEvents()

    def tearDown(self):
        self.p.close();APP.processEvents();self.temp.cleanup()

    def assert_no_overlap(self):
        p=self.p;b=p._care_bubble
        body=QRegion(p.grab().mask()).translated(p.pos())
        bubble=b.mask().translated(b.pos())
        self.assertTrue(body.intersected(bubble).isEmpty(),(p._sprite_kind(),b._tail_side))
        self.assertTrue(p.screen().availableGeometry().contains(b.frameGeometry()))

    def test_all_seven_poses_with_body_and_whole_motion(self):
        p=self.p;p._anim.breath_scale=1.05;p._anim.float_offset_y=-4
        for kind in p._pixmaps:
            p._manual_sprite=kind
            for phase in (.1,.4,.8,1.2):
                with self.subTest(kind=kind,phase=phase),patch('desktop_pet.time.monotonic',return_value=100+phase):
                    p._care_bubble.present('收到你的摸摸啦。',p)
                    self.assert_no_overlap()

    def test_corners_long_text_and_pat_heart(self):
        p=self.p;area=p.screen().availableGeometry()
        p._pat_started=100
        for point in (area.topLeft(),QPoint(area.right()-120,area.top()),
                      QPoint(area.left(),area.bottom()-120),QPoint(area.right()-120,area.bottom()-120)):
            p.move(point)
            with patch('desktop_pet.time.monotonic',return_value=100.25):
                for text in ('收到你的摸摸啦。','长文本提醒。'*100):
                    p._care_bubble.present(text,p)
                    self.assert_no_overlap()

    def test_crossfade_protects_outgoing_character(self):
        p=self.p;p._manual_sprite='sleep';p._fade_from=p._pixmaps['happy'];p._fade_started=100
        with patch('desktop_pet.time.monotonic',return_value=100.1):
            p._care_bubble.present('收到你的摸摸啦。',p)
            self.assert_no_overlap()

    def test_breathing_does_not_move_bubble_and_distance_stays_small(self):
        p=self.p;positions=[]
        for phase in (.1,.4,.8):
            with patch('desktop_pet.time.monotonic',return_value=100+phase):
                p._care_bubble.present('收到你的摸摸啦。',p)
                positions.append(p._care_bubble.pos())
        self.assertTrue(all(point==positions[0] for point in positions))
        p._store.data['animation_mode']='reduced'
        bounds=QRegion(p.grab().mask()).boundingRect().translated(p.pos())
        self.assertGreaterEqual(bounds.left()-p._care_bubble.geometry().right(),5)
        self.assertLessEqual(bounds.left()-p._care_bubble.geometry().right(),16)


if __name__=='__main__':unittest.main()
