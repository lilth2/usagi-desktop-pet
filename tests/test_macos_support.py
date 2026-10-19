import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from care import idle_seconds, _mac_idle_reader
from schedule import SettingsStore


class MacSupportTests(unittest.TestCase):
    def test_native_idle_api_binding_and_valid_value(self):
        _mac_idle_reader.cache_clear()
        reader=MagicMock(return_value=12.5)
        library=MagicMock(CGEventSourceSecondsSinceLastEventType=reader)
        with patch('care.sys.platform','darwin'),patch('care.ctypes.CDLL',return_value=library):
            self.assertEqual(idle_seconds(),12.5)
            reader.assert_called_once_with(0,0xffffffff)
            self.assertEqual(len(reader.argtypes),2)
        _mac_idle_reader.cache_clear()

    def test_unavailable_or_invalid_idle_value_does_not_crash(self):
        for value in (-1,float('nan'),float('inf')):
            with patch('care.sys.platform','darwin'),patch('care._mac_idle_reader',return_value=lambda *_:value):
                self.assertIsNone(idle_seconds())
        with patch('care.sys.platform','darwin'),patch('care._mac_idle_reader',side_effect=OSError('missing')):
            self.assertIsNone(idle_seconds())

    def test_new_mac_config_uses_application_support(self):
        with tempfile.TemporaryDirectory() as temporary:
            home=Path(temporary)
            with patch('schedule.sys.platform','darwin'),patch('schedule.Path.home',return_value=home):
                store=SettingsStore()
                self.assertEqual(store.path,home/'Library'/'Application Support'/'ChiikawaPet'/'settings.json')
                store.save()
                self.assertTrue(store.path.exists())

    def test_legacy_mac_config_stays_in_place(self):
        with tempfile.TemporaryDirectory() as temporary:
            home=Path(temporary);legacy=home/'UsagiPet'/'settings.json'
            original=SettingsStore(legacy);original.data['custom-history']=['keep'];original.save()
            with patch('schedule.sys.platform','darwin'),patch('schedule.Path.home',return_value=home):
                store=SettingsStore()
                self.assertEqual(store.path,legacy)
                self.assertEqual(store.data['custom-history'],['keep'])


if __name__=='__main__':unittest.main()
