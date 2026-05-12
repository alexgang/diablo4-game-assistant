import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import HOTKEY_CONFIG


class TestHotkeyConfig:
    def test_hotkey_config_exists(self):
        assert isinstance(HOTKEY_CONFIG, dict)

    def test_hotkey_config_enabled(self):
        assert 'enabled' in HOTKEY_CONFIG
        assert HOTKEY_CONFIG['enabled'] is True

    def test_hotkey_bindings_exist(self):
        assert 'bindings' in HOTKEY_CONFIG
        assert isinstance(HOTKEY_CONFIG['bindings'], dict)

    def test_hotkey_bindings_voice_toggle(self):
        bindings = HOTKEY_CONFIG['bindings']
        assert 'voice_toggle' in bindings
        assert isinstance(bindings['voice_toggle'], str)

    def test_hotkey_bindings_overlay_toggle(self):
        bindings = HOTKEY_CONFIG['bindings']
        assert 'overlay_toggle' in bindings
        assert isinstance(bindings['overlay_toggle'], str)

    def test_hotkey_bindings_window_toggle(self):
        bindings = HOTKEY_CONFIG['bindings']
        assert 'window_toggle' in bindings
        assert isinstance(bindings['window_toggle'], str)

    def test_hotkey_bindings_format(self):
        bindings = HOTKEY_CONFIG['bindings']
        for action, key in bindings.items():
            assert isinstance(key, str)
            assert len(key) > 0


class TestHotkeyManagerDefaults:
    def test_default_hotkeys_defined(self):
        from hotkey_manager import HotkeyManager
        assert isinstance(HotkeyManager.DEFAULT_HOTKEYS, dict)
        assert len(HotkeyManager.DEFAULT_HOTKEYS) > 0

    def test_default_hotkey_actions(self):
        from hotkey_manager import HotkeyManager
        expected_actions = [
            'voice_toggle', 'overlay_toggle', 'overlay_equip',
            'overlay_skill', 'overlay_paragon', 'overlay_merc',
            'window_toggle', 'refresh',
        ]
        for action in expected_actions:
            assert action in HotkeyManager.DEFAULT_HOTKEYS

    def test_hotkey_labels_defined(self):
        from hotkey_manager import HotkeyManager
        assert isinstance(HotkeyManager.HOTKEY_LABELS, dict)
        for action in HotkeyManager.DEFAULT_HOTKEYS:
            assert action in HotkeyManager.HOTKEY_LABELS

    def test_tab_map_defined(self):
        from hotkey_manager import HotkeyManager
        assert isinstance(HotkeyManager.HOTKEY_TAB_MAP, dict)
        assert 'overlay_equip' in HotkeyManager.HOTKEY_TAB_MAP
        assert HotkeyManager.HOTKEY_TAB_MAP['overlay_equip'] == 0
        assert HotkeyManager.HOTKEY_TAB_MAP['overlay_skill'] == 1
        assert HotkeyManager.HOTKEY_TAB_MAP['overlay_paragon'] == 2
        assert HotkeyManager.HOTKEY_TAB_MAP['overlay_merc'] == 3


class TestHotkeyManagerInit:
    def test_init_without_keyboard(self):
        from hotkey_manager import HotkeyManager, KEYBOARD_AVAILABLE
        mgr = HotkeyManager()
        if not KEYBOARD_AVAILABLE:
            assert mgr.available is False
        else:
            assert mgr.available is True
            mgr.cleanup()

    def test_init_with_custom_hotkeys(self):
        from hotkey_manager import HotkeyManager
        custom = {'voice_toggle': 'ctrl+shift+v'}
        mgr = HotkeyManager(hotkeys=custom)
        assert mgr._hotkeys['voice_toggle'] == 'ctrl+shift+v'
        mgr.cleanup()

    def test_get_status(self):
        from hotkey_manager import HotkeyManager
        mgr = HotkeyManager()
        status = mgr.get_status()
        assert 'available' in status
        assert 'enabled' in status
        assert 'hotkeys' in status
        mgr.cleanup()

    def test_get_hotkey_info(self):
        from hotkey_manager import HotkeyManager
        mgr = HotkeyManager()
        info = mgr.get_hotkey_info()
        assert isinstance(info, dict)
        assert 'voice_toggle' in info
        assert 'key' in info['voice_toggle']
        assert 'label' in info['voice_toggle']
        mgr.cleanup()

    def test_enable_disable(self):
        from hotkey_manager import HotkeyManager
        mgr = HotkeyManager()
        mgr.disable()
        assert mgr._enabled is False
        mgr.enable()
        assert mgr._enabled is True
        mgr.cleanup()

    def test_update_hotkey(self):
        from hotkey_manager import HotkeyManager
        mgr = HotkeyManager()
        mgr.update_hotkey('voice_toggle', 'ctrl+shift+v')
        assert mgr._hotkeys['voice_toggle'] == 'ctrl+shift+v'
        mgr.cleanup()
