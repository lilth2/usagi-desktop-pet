import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from schedule import SettingsStore, Schedule, DEFAULTS, contains, validate
from care import CareClock, CARE_MESSAGES


class SchedulingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'settings.json'
        self.store=SettingsStore(self.path)
        self.schedule=Schedule(self.store)

    def tearDown(self):self.temp.cleanup()

    def at(self,time):return datetime.fromisoformat('2026-10-19T'+time)

    def test_required_boundaries(self):
        cases=[('05:59','sleep','晚上好'),('06:00','normal','早上好'),('11:00','normal','中午好'),('12:30','sleep','中午好'),('14:00','normal','下午好'),('18:00','late','晚上好'),('23:00','sleep','晚上好'),('00:00','sleep','晚上好')]
        for t,appearance,greeting in cases:
            with self.subTest(time=t):
                self.assertEqual(self.schedule.appearance(self.at(t)),appearance)
                self.assertIn(greeting,self.schedule.greeting(self.at(t))[1])

    def test_entire_day_no_forbidden_appearance(self):
        for minute in range(1440):
            t=datetime(2026,10,19,minute//60,minute%60)
            a=self.schedule.appearance(t)
            if a=='late':self.assertTrue(minute>=1080 or minute<360)
            if a=='sleep':self.assertTrue(minute>=1380 or minute<360 or 750<=minute<840)

    def test_inclusive_start_exclusive_end(self):
        self.assertTrue(contains(1380,'23:00','06:00'))
        self.assertTrue(contains(0,'23:00','06:00'))
        self.assertFalse(contains(360,'23:00','06:00'))
        self.assertFalse(contains(840,'12:30','14:00'))

    def test_periodic_interval_restart_and_no_repeat(self):
        self.assertEqual(self.schedule.poll(100),'startup')
        key,msg=self.schedule.greeting(self.at('06:00'));self.schedule.delivered(key)
        self.assertIsNone(self.schedule.poll(399))
        self.assertEqual(self.schedule.poll(400),'periodic')
        self.assertNotEqual(msg,self.schedule.greeting(self.at('06:05'))[1])
        self.assertEqual(Schedule(SettingsStore(self.path)).poll(900),'startup')

    def test_dnd_cross_midnight_and_resume_current_only(self):
        self.store.data['dnd_enabled']=True
        self.assertIsNone(self.schedule.greeting(self.at('23:00')))
        self.assertIsNone(self.schedule.greeting(self.at('05:59')))
        self.assertIn('早上好',self.schedule.greeting(self.at('06:00'))[1])

    def test_wake_only_current_period(self):
        self.schedule.greeting(self.at('06:00'))
        key,msg=self.schedule.greeting(self.at('18:00'))
        self.assertIn('晚上好',msg);self.assertTrue(key.endswith('evening'))
        self.assertEqual(self.store.data['greeted'],{})

    def test_timezone_change_recomputes(self):
        instant=datetime(2026,10,19,0,0,tzinfo=timezone.utc)
        self.assertEqual(self.schedule.appearance(instant.astimezone(timezone(timedelta(hours=11)))),'normal')
        self.assertEqual(self.schedule.appearance(instant.astimezone(timezone(timedelta(hours=-1)))),'sleep')

    def test_edit_configuration_and_disable(self):
        self.store.data['nap_start']='13:00';self.store.data['nap_end']='13:30'
        self.assertEqual(self.schedule.appearance(self.at('12:30')),'normal')
        self.store.data['nap_enabled']=False
        self.assertEqual(self.schedule.appearance(self.at('13:00')),'normal')
        self.store.data['appearance_enabled']=False
        self.assertEqual(self.schedule.appearance(self.at('23:00')),'normal')
        self.store.data['greetings_enabled']=False
        self.assertIsNone(self.schedule.greeting(self.at('06:00')))

    def test_no_overlapping_greeting_config(self):
        bad=copy.deepcopy(DEFAULTS);bad['greetings'][0]['end']='12:00'
        with self.assertRaises(ValueError):validate(bad)

    def test_night_assets_cannot_be_configured_for_day(self):
        bad=copy.deepcopy(DEFAULTS);bad['sleep_end']='12:00'
        with self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(DEFAULTS);bad['evening_start']='14:00'
        with self.assertRaises(ValueError):validate(bad)

    def test_preserve_unknown_fields_and_custom_text(self):
        self.store.data['legacy_history']=[{'text':'不要修改'}]
        self.store.data['greetings'][0]['messages']=['早上好，我自己写的文案。']
        self.store.save();self.store.data['walking_enabled']=False;self.store.save()
        reloaded=SettingsStore(self.path)
        self.assertEqual(reloaded.data['legacy_history'],[{'text':'不要修改'}])
        self.assertEqual(reloaded.data['greetings'][0]['messages'],['早上好，我自己写的文案。'])
        self.assertTrue(self.path.with_suffix('.json.bak').exists())

    def test_corrupt_config_is_never_overwritten(self):
        self.path.write_text('{BROKEN',encoding='utf-8');store=SettingsStore(self.path)
        self.assertTrue(store.warning)
        with self.assertRaises(OSError):store.save()
        self.assertEqual(self.path.read_text(),'{BROKEN')

    def test_preview_does_not_persist(self):
        self.schedule.preview=self.at('06:00');key,_=self.schedule.greeting();self.schedule.delivered(key)
        self.assertIsNotNone(self.schedule.greeting())
        self.assertFalse(self.path.exists());self.assertEqual(self.store.data['greeted'],{})

    def test_original_care_timing_and_shuffle(self):
        clock=CareClock(interval=30,rest=20);clock.last=0
        self.assertFalse(clock.poll(0,10));self.assertFalse(clock.poll(0,20));self.assertTrue(clock.poll(0,30))
        self.assertFalse(clock.poll(25,40));self.assertEqual(clock.active,0)
        self.assertFalse(clock.poll(0,200));self.assertEqual(clock.active,0)
        self.assertEqual(len(CARE_MESSAGES),10)

if __name__=='__main__':unittest.main()
