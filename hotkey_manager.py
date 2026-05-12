#!/usr/bin/env python3
"""
全局快捷键管理器 - 在游戏中通过快捷键控制助手

功能：
1. 全局快捷键注册（即使游戏在前台也能响应）
2. 支持组合键（Ctrl+Alt+X 等）
3. 可配置的快捷键映射
4. 信号通知机制，与GUI解耦

默认快捷键：
  Ctrl+Alt+V  - 切换语音输入
  Ctrl+Alt+O  - 切换叠加层
  Ctrl+Alt+E  - 叠加层-装备标签
  Ctrl+Alt+S  - 叠加层-技能标签
  Ctrl+Alt+P  - 叠加层-巅峰标签
  Ctrl+Alt+M  - 叠加层-雇佣标签
  Ctrl+Alt+H  - 隐藏/显示主窗口
  Ctrl+Alt+R  - 刷新分析
"""

import logging
import threading

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

KEYBOARD_AVAILABLE = False
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    logger.warning("keyboard 库未安装，全局快捷键不可用。安装: pip install keyboard")


class HotkeyManager(QObject):
    """全局快捷键管理器"""

    voice_toggled = pyqtSignal()
    overlay_toggled = pyqtSignal()
    overlay_tab_requested = pyqtSignal(int)
    window_toggled = pyqtSignal()
    refresh_requested = pyqtSignal()
    damage_toggled = pyqtSignal()
    hotkey_pressed = pyqtSignal(str)

    DEFAULT_HOTKEYS = {
        'voice_toggle': 'ctrl+alt+v',
        'overlay_toggle': 'ctrl+alt+o',
        'overlay_equip': 'ctrl+alt+e',
        'overlay_skill': 'ctrl+alt+s',
        'overlay_paragon': 'ctrl+alt+p',
        'overlay_merc': 'ctrl+alt+m',
        'window_toggle': 'ctrl+alt+h',
        'refresh': 'ctrl+alt+r',
        'damage_toggle': 'ctrl+alt+d',
    }

    HOTKEY_LABELS = {
        'voice_toggle': '切换语音输入',
        'overlay_toggle': '切换叠加层',
        'overlay_equip': '叠加层-装备',
        'overlay_skill': '叠加层-技能',
        'overlay_paragon': '叠加层-巅峰',
        'overlay_merc': '叠加层-雇佣',
        'window_toggle': '隐藏/显示主窗口',
        'refresh': '刷新分析',
        'damage_toggle': '切换伤害监控',
    }

    HOTKEY_TAB_MAP = {
        'overlay_equip': 0,
        'overlay_skill': 1,
        'overlay_paragon': 2,
        'overlay_merc': 3,
    }

    def __init__(self, hotkeys=None, parent=None):
        super().__init__(parent)
        self.available = KEYBOARD_AVAILABLE
        self._registered = {}
        self._lock = threading.Lock()
        self._enabled = True

        self._hotkeys = dict(self.DEFAULT_HOTKEYS)
        if hotkeys:
            for key, value in hotkeys.items():
                if value and isinstance(value, str):
                    self._hotkeys[key] = value.lower().strip()

        if self.available:
            self._register_all()

    def _register_all(self):
        """注册所有快捷键"""
        if not self.available:
            return

        for action, key_combo in self._hotkeys.items():
            self._register_one(action, key_combo)

    def _register_one(self, action, key_combo):
        """注册单个快捷键"""
        if not self.available or not key_combo:
            return

        try:
            self._unregister_one(action)

            hook = keyboard.add_hotkey(
                key_combo,
                lambda a=action: self._on_hotkey(a),
                suppress=False,
            )
            with self._lock:
                self._registered[action] = hook
            logger.debug(f"快捷键注册: {key_combo} -> {action}")

        except Exception as e:
            logger.warning(f"快捷键注册失败 [{key_combo} -> {action}]: {e}")

    def _unregister_one(self, action):
        """注销单个快捷键"""
        with self._lock:
            hook = self._registered.pop(action, None)
        if hook and self.available:
            try:
                keyboard.remove_hotkey(hook)
            except Exception:
                pass

    def _on_hotkey(self, action):
        """快捷键触发回调"""
        if not self._enabled:
            return

        logger.info(f"快捷键触发: {action}")

        if action == 'voice_toggle':
            self.voice_toggled.emit()
        elif action == 'overlay_toggle':
            self.overlay_toggled.emit()
        elif action in self.HOTKEY_TAB_MAP:
            self.overlay_tab_requested.emit(self.HOTKEY_TAB_MAP[action])
        elif action == 'window_toggle':
            self.window_toggled.emit()
        elif action == 'refresh':
            self.refresh_requested.emit()
        elif action == 'damage_toggle':
            self.damage_toggled.emit()

        self.hotkey_pressed.emit(action)

    def update_hotkey(self, action, new_key_combo):
        """更新快捷键绑定"""
        if not new_key_combo:
            return

        new_key_combo = new_key_combo.lower().strip()
        old_key_combo = self._hotkeys.get(action)

        if old_key_combo == new_key_combo:
            return

        self._hotkeys[action] = new_key_combo
        self._register_one(action, new_key_combo)

    def enable(self):
        """启用快捷键"""
        self._enabled = True

    def disable(self):
        """禁用快捷键"""
        self._enabled = False

    def unregister_all(self):
        """注销所有快捷键"""
        if not self.available:
            return

        with self._lock:
            actions = list(self._registered.keys())

        for action in actions:
            self._unregister_one(action)

    def get_hotkey_info(self):
        """获取快捷键信息"""
        info = {}
        for action, key_combo in self._hotkeys.items():
            info[action] = {
                'key': key_combo,
                'label': self.HOTKEY_LABELS.get(action, action),
                'registered': action in self._registered,
            }
        return info

    def get_status(self):
        """获取快捷键管理器状态"""
        return {
            'available': self.available,
            'enabled': self._enabled,
            'registered_count': len(self._registered),
            'hotkeys': self._hotkeys,
        }

    def cleanup(self):
        """清理资源"""
        self.unregister_all()
