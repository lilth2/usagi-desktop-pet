import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from PyQt5.QtWidgets import QApplication
from body_animation import BodyAnimations
from desktop_pet import DesktopPetWindow,PetState
from schedule import SettingsStore,validate
from tools.author_body_animation import field
from theme import ASSETS

APP=QApplication.instance() or QApplication([])
ROOT=Path(__file__).resolve().parents[1]


class BodyAssetTests(unittest.TestCase):
    def test_four_extractions_are_real_alpha(self):
        for kind in ('office','desktop','happy','late_scene'):
            with self.subTest(kind=kind):
                im=Image.open(ASSETS/(kind+'.png'))
                self.assertEqual(im.mode,'RGBA');self.assertEqual(im.size,(320,320))
                alpha=np.asarray(im)[:,:,3]
                self.assertEqual(int(alpha[0,0]),0)
                self.assertGreater(int((alpha==255).sum()),1000)
                self.assertGreater(int((alpha==0).sum()),40000)
                self.assertEqual(im.getbbox()[3],280)

    def test_gesture_endpoints_and_facial_features(self):
        for kind in ('office','desktop','happy','late_scene'):
            with self.subTest(kind=kind):
                folder=ROOT/'assets/chiikawa/animation_sources'/kind
                rig=json.loads((folder/'rig.json').read_text(encoding='utf-8'))
                atlas=Image.open(ASSETS/'animations'/f'{kind}-happy.png')
                first=np.asarray(atlas.crop((0,0,320,320)))
                peak=np.asarray(atlas.crop((0,640,320,960)))
                last=np.asarray(atlas.crop((2240,960,2560,1280)))
                self.assertTrue(np.array_equal(first,last))
                self.assertGreater(int(np.any(first!=peak,axis=2).sum()),50)
                x,y,w,h=rig['face'];x0,x1=int(x-w*.35),int(x+w*.35);y0,y1=int(y-h*.35),int(y+h*.35)
                self.assertTrue(np.array_equal(first[y0:y1,x0:x1],peak[y0:y1,x0:x1]))

    def test_local_mesh_has_no_foldovers(self):
        for kind in ('office','desktop','happy','late_scene'):
            rig=json.loads((ROOT/'assets/chiikawa/animation_sources'/kind/'rig.json').read_text(encoding='utf-8'))
            for clip in ('idle','interact','happy'):
                for phase in (np.pi/2,np.pi,3*np.pi/2):
                    dx,dy=field(rig,phase,clip)
                    dxx=np.gradient(dx,axis=1);dxy=np.gradient(dx,axis=0)
                    dyx=np.gradient(dy,axis=1);dyy=np.gradient(dy,axis=0)
                    determinant=(1-dxx)*(1-dyy)-dxy*dyx
                    self.assertGreater(float(determinant.min()),.2,(kind,clip,phase))

    def test_only_suitable_pose_has_step_animation(self):
        manifest=json.loads((ASSETS/'animations/manifest.json').read_text())
        self.assertIn('walk',manifest['normal'])
        for kind in ('office','desktop','happy','late_scene','sleep','late'):
            self.assertNotIn('walk',manifest[kind])
        self.assertEqual(set(manifest['sleep']),{'idle'})

    def test_atlas_cache_is_bounded_and_missing_is_safe(self):
        player=BodyAnimations()
        for kind in ('office','happy','desktop','late_scene'):
            self.assertFalse(player.frame(kind,'idle',.2).isNull())
        self.assertLessEqual(len(player.cache),2)
        self.assertIsNone(player.frame('missing','idle',0))

    def test_idle_loop_has_no_large_reset(self):
        atlas=Image.open(ASSETS/'animations/happy-idle.png')
        frames=[np.asarray(atlas.crop(((i%8)*320,(i//8)*320,(i%8+1)*320,(i//8+1)*320)),dtype=float) for i in range(32)]
        adjacent=[np.abs(frames[i+1]-frames[i]).mean() for i in range(31)]
        self.assertLessEqual(np.abs(frames[0]-frames[-1]).mean(),max(adjacent)*1.5)


class BodyRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.pet=DesktopPetWindow(SettingsStore(Path(self.temp.name)/'settings.json'))
        for t in (self.pet._timer,self.pet._schedule_timer,self.pet._care_timer):t.stop()

    def tearDown(self):
        self.pet.close();APP.processEvents();self.temp.cleanup()

    def test_three_modes_keep_window_and_reminder(self):
        p=self.pet
        for mode in ('whole','body','reduced'):
            p._store.data['animation_mode']=mode
            self.assertEqual((p.width(),p.height()),(120,120))
            self.assertFalse(p._body_frame().isNull())
            if mode!='body':self.assertEqual(p._body_frame().cacheKey(),p._current_pixmap().cacheKey())
        p._appearance='normal';p._state_timer_ms=999999;p._update_idle()
        self.assertEqual(p._state,PetState.IDLE)
        p._show_care();self.assertTrue(p._care_bubble.isVisible())

    def test_gesture_drives_real_frame_and_keeps_position(self):
        p=self.pet;p._manual_sprite='happy';p._store.data['animation_mode']='body'
        p._gesture_started=100;p._gesture_clip='happy';position=p.pos()
        with patch('desktop_pet.time.monotonic',return_value=100):first=p._body_frame().toImage()
        with patch('desktop_pet.time.monotonic',return_value=100.8):peak=p._body_frame().toImage()
        self.assertNotEqual(first,peak);self.assertEqual(p.pos(),position)

    def test_mode_persists_with_existing_fields(self):
        p=self.pet;p._store.data['custom_history']=['保留'];p._store.data['animation_mode']='reduced';p._store.save()
        restored=SettingsStore(p._store.path)
        self.assertEqual(restored.data['animation_mode'],'reduced')
        self.assertEqual(restored.data['custom_history'],['保留'])

    def test_mode_setting_keeps_selected_photo(self):
        from datetime import datetime
        p=self.pet;p._schedule.preview=datetime(2026,10,19,14,0);p._refresh_schedule()
        p._manual_sprite='office';p._show_settings();APP.processEvents()
        d=p._settings_dialog;d.animation_mode.setCurrentIndex(d.animation_mode.findData('reduced'));d.save()
        self.assertEqual(p._manual_sprite,'office')
        self.assertEqual(p._store.data['animation_mode'],'reduced')
        d.close()

if __name__=='__main__':unittest.main()
