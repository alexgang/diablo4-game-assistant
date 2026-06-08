#!/usr/bin/env python3
"""
游戏场景助手窗口 - 独立的小窗口，根据 Vision 识别结果自动切换 Tab

特点：
- 独立小窗口（不依赖主 GUI 布局）
- 4个 Tab：战斗 / 装备 / 技能 / 地图
- 5秒/次自动 Vision 截图识别
- 自动切换到对应 Tab 并高亮提示
- 可拖拽、置顶、不抢焦点
"""

import os
import sys
import time
import logging
import threading

import cv2
import numpy as np

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QTextEdit,
    QPushButton, QFrame, QCheckBox, QApplication,
)
from PyQt5.QtGui import QFont, QColor, QPalette
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize

from scene_classifier import SceneCategory, classify_scene, get_category_display_name, get_category_color

logger = logging.getLogger(__name__)


def _get_screen_scale():
    import ctypes
    user32 = ctypes.windll.user32
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    return max(1.0, min(screen_w / 1920, screen_h / 1080))


SCREEN_SCALE = _get_screen_scale()


def _fs(base_size):
    return max(int(base_size * SCREEN_SCALE), base_size + 2)


def _ff(family, base_size, weight=QFont.Normal):
    return QFont(family, _fs(base_size), weight)


class SceneTipText(QTextEdit):
    """带提示信息的文本框"""

    def __init__(self, title, color="#ffd700"):
        super().__init__()
        self.setReadOnly(True)
        self.title = title
        self.color = color
        self.setStyleSheet(
            f"background-color: rgba(0,0,0,0.3); color: #e0e0e0; "
            f"border: none; font-size: {_fs(13)}px;"
        )

    def set_placeholder(self, text):
        self.setPlainText(f"[{self.title}]\n\n{text}")


class SceneVisionWorker(QThread):
    """后台 Vision 场景识别线程 - 5秒/次"""
    scene_detected = pyqtSignal(dict)

    def __init__(self, game_detector, interval=5.0):
        super().__init__()
        self.detector = game_detector
        self.interval = interval
        self._running = True

    def run(self):
        while self._running:
            try:
                result = self._detect_scene()
                if result:
                    self.scene_detected.emit(result)
            except Exception as e:
                logger.error(f"Vision 场景识别失败: {e}")
            for _ in range(int(self.interval * 10)):
                if not self._running:
                    return
                self.msleep(100)

    def _detect_scene(self):
        """检测当前场景"""
        if not self.detector or not self.detector.sdk_available:
            return None
        try:
            tmp_path = self.detector._get_temp_image_path()
            if not tmp_path:
                return None
            results = self.detector.sdk.vision_query(
                self.detector.instance_id,
                tmp_path,
                topk=1,
                mode='accurate',
            )
            if not results:
                return None
            top = results[0]
            scene_id = top.get('scene_id', '')
            score = top.get('score', 0)
            picture_id = top.get('picture_id', '')
            if score < 0.5:
                return None
            category = classify_scene(scene_id)
            return {
                'scene_id': scene_id,
                'picture_id': picture_id,
                'score': score,
                'category': category,
            }
        except Exception as e:
            logger.error(f"Vision 查询失败: {e}")
            return None

    def stop(self):
        self._running = False
        self.wait()


class SceneAssistantWindow(QWidget):
    """游戏场景助手窗口 - 根据 Vision 自动切换 Tab"""

    scene_category_signal = pyqtSignal(object, str, float)

    def __init__(self, game_detector, parent=None):
        super().__init__(parent, Qt.Window)
        self.detector = game_detector
        self.current_category = SceneCategory.UNKNOWN
        self.auto_switch = True
        self._tab_highlight_timer = None

        self._init_ui()
        self._start_vision_worker()

    def _init_ui(self):
        self.setWindowTitle("🎮 场景助手")
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        width = int(380 * SCREEN_SCALE)
        height = int(540 * SCREEN_SCALE)
        self.setFixedSize(width, height)

        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - width - 20
        y = 100
        self.move(x, y)

        self.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 30, 0.92);
                color: #e0e0e0;
            }
            QTabWidget::pane {
                border: 1px solid rgba(139, 0, 0, 0.4);
                background-color: rgba(0, 0, 0, 0.3);
            }
            QTabBar::tab {
                background-color: rgba(40, 40, 50, 0.8);
                color: #aaa;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 60px;
            }
            QTabBar::tab:selected {
                background-color: rgba(139, 0, 0, 0.6);
                color: #fff;
                font-weight: bold;
            }
            QTabBar::tab:!selected:hover {
                background-color: rgba(60, 60, 70, 0.8);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("🎮 智能场景助手")
        title.setFont(_ff('Microsoft YaHei', 13, QFont.Bold))
        title.setStyleSheet("color: #ff6b35; background: transparent;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.status_label = QLabel("识别中...")
        self.status_label.setFont(_ff('Microsoft YaHei', 10))
        self.status_label.setStyleSheet("color: #4ade80; background: transparent;")
        header_layout.addWidget(self.status_label)

        self.auto_switch_check = QCheckBox("自动切换")
        self.auto_switch_check.setChecked(True)
        self.auto_switch_check.setFont(_ff('Microsoft YaHei', 10))
        self.auto_switch_check.setStyleSheet("color: #ccc; background: transparent;")
        self.auto_switch_check.toggled.connect(self._on_auto_switch_toggle)
        header_layout.addWidget(self.auto_switch_check)

        layout.addWidget(header)

        self.scene_info_label = QLabel("当前场景: --")
        self.scene_info_label.setFont(_ff('Microsoft YaHei', 11))
        self.scene_info_label.setStyleSheet("color: #9b59b6; background: transparent; padding: 4px;")
        self.scene_info_label.setWordWrap(True)
        layout.addWidget(self.scene_info_label)

        self.tabs = QTabWidget()
        self.tabs.setFont(_ff('Microsoft YaHei', 11))
        self._create_tabs()
        layout.addWidget(self.tabs)

        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.refresh_btn = QPushButton("🔄 立即识别")
        self.refresh_btn.setStyleSheet(
            "background-color: #0066cc; color: white; border: none; "
            f"border-radius: 3px; padding: 5px 10px; font-size: {_fs(11)}px;"
        )
        self.refresh_btn.clicked.connect(self._manual_detect)
        bottom_layout.addWidget(self.refresh_btn)

        self.ocr_btn = QPushButton("📝 OCR 文字")
        self.ocr_btn.setStyleSheet(
            "background-color: #2d5a27; color: white; border: none; "
            f"border-radius: 3px; padding: 5px 10px; font-size: {_fs(11)}px;"
        )
        self.ocr_btn.setCheckable(True)
        self.ocr_btn.setChecked(True)
        self.ocr_btn.clicked.connect(self._toggle_ocr)
        bottom_layout.addWidget(self.ocr_btn)

        self.voice_btn = QPushButton("🎤 语音")
        self.voice_btn.setStyleSheet(
            "background-color: #9b59b6; color: white; border: none; "
            f"border-radius: 3px; padding: 5px 10px; font-size: {_fs(11)}px;"
        )
        bottom_layout.addWidget(self.voice_btn)

        bottom_layout.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(int(28 * SCREEN_SCALE), int(28 * SCREEN_SCALE))
        self.close_btn.setStyleSheet(
            "color: #ff6b35; background: transparent; border: none; "
            f"font-size: {_fs(14)}px; font-weight: bold;"
        )
        self.close_btn.clicked.connect(self.hide)
        bottom_layout.addWidget(self.close_btn)

        layout.addWidget(bottom)

    def _create_tabs(self):
        """创建4个 Tab"""
        # Tab 0: 战斗 (默认)
        self.tab_combat = QWidget()
        combat_layout = QVBoxLayout(self.tab_combat)
        combat_layout.setContentsMargins(6, 6, 6, 6)
        self.combat_info = SceneTipText("战斗信息", "#e74c3c")
        self.combat_info.set_placeholder("检测到战斗场景时，会显示：\n• 当前怪物信息\n• BOSS 攻略\n• DPS 统计\n• 战斗建议")
        combat_layout.addWidget(self.combat_info)
        self.tabs.addTab(self.tab_combat, "⚔ 战斗")

        # Tab 1: 装备
        self.tab_equipment = QWidget()
        equip_layout = QVBoxLayout(self.tab_equipment)
        equip_layout.setContentsMargins(6, 6, 6, 6)
        self.equip_info = SceneTipText("装备/物品", "#ff6b35")
        self.equip_info.set_placeholder("检测到装备/物品界面时，会显示：\n• 物品词条说明\n• 装备对比建议\n• Code of Power 推荐\n• 装备精工/强化建议")
        equip_layout.addWidget(self.equip_info)
        self.tabs.addTab(self.tab_equipment, "🛡 装备")

        # Tab 2: 技能
        self.tab_skill = QWidget()
        skill_layout = QVBoxLayout(self.tab_skill)
        skill_layout.setContentsMargins(6, 6, 6, 6)
        self.skill_info = SceneTipText("技能/天赋", "#9b59b6")
        self.skill_info.set_placeholder("检测到技能/天赋界面时，会显示：\n• 当前职业 BD 推荐\n• 技能加点方案\n• 巅峰盘建议\n• 技能搭配说明")
        skill_layout.addWidget(self.skill_info)
        self.tabs.addTab(self.tab_skill, "🔮 技能")

        # Tab 3: 地图
        self.tab_map = QWidget()
        map_layout = QVBoxLayout(self.tab_map)
        map_layout.setContentsMargins(6, 6, 6, 6)
        self.map_info = SceneTipText("地图/任务", "#3498db")
        self.map_info.set_placeholder("检测到地图/任务界面时，会显示：\n• 当前位置\n• 任务追踪\n• 地下城推荐\n• BOSS 召唤时间表")
        map_layout.addWidget(self.map_info)
        self.tabs.addTab(self.tab_map, "🗺 地图")

    def _start_vision_worker(self):
        """启动后台 Vision 识别线程（5秒/次）"""
        if not self.detector or not self.detector.sdk_available:
            self.status_label.setText("SDK未连接")
            self.status_label.setStyleSheet("color: #e74c3c; background: transparent;")
            return

        self.vision_worker = SceneVisionWorker(self.detector, interval=5.0)
        self.vision_worker.scene_detected.connect(self._on_scene_detected)
        self.vision_worker.start()

    def _on_scene_detected(self, result):
        """Vision 识别结果回调"""
        category = result['category']
        scene_id = result['scene_id']
        score = result['score']

        display_name = get_category_display_name(category)
        color = get_category_color(category)
        self.status_label.setText(f"✓ {display_name}")
        self.status_label.setStyleSheet(f"color: {color}; background: transparent;")

        score_pct = f"{score * 100:.0f}%"
        self.scene_info_label.setText(
            f"场景: <b style='color:{color};'>{scene_id}</b><br>"
            f"类别: <b style='color:{color};'>{display_name}</b>  置信度: <b>{score_pct}</b>"
        )
        self.scene_info_label.setTextFormat(Qt.RichText)

        if self.auto_switch and category != self.current_category:
            self._switch_to_category(category)

        self.current_category = category

    def _switch_to_category(self, category):
        """切换到指定类别 Tab"""
        tab_index_map = {
            SceneCategory.COMBAT: 0,
            SceneCategory.EQUIPMENT: 1,
            SceneCategory.SKILL: 2,
            SceneCategory.MAP: 3,
            SceneCategory.UNKNOWN: 0,
        }
        index = tab_index_map.get(category, 0)
        self.tabs.setCurrentIndex(index)

        color = get_category_color(category)
        self.tabs.tabBar().setStyleSheet(
            f"QTabBar::tab:selected {{ background-color: {color}; color: #fff; font-weight: bold; }}"
        )

        QApplication.beep() if hasattr(QApplication, 'beep') else None

    def _on_auto_switch_toggle(self, checked):
        self.auto_switch = checked
        if checked:
            self.auto_switch_check.setText("自动切换")
        else:
            self.auto_switch_check.setText("手动模式")

    def _manual_detect(self):
        """手动触发识别"""
        if not self.vision_worker:
            return
        result = self.vision_worker._detect_scene()
        if result:
            self._on_scene_detected(result)
        else:
            self.status_label.setText("未识别到场景")
            self.status_label.setStyleSheet("color: #aaa; background: transparent;")

    def _toggle_ocr(self, checked):
        """切换 OCR 显示"""
        if not self.detector:
            return
        if checked:
            self.detector.use_ocr = True
        else:
            self.detector.use_ocr = False

    def closeEvent(self, event):
        if self.vision_worker:
            self.vision_worker.stop()
        event.accept()


if __name__ == "__main__":
    from game_detector import GameDetector
    detector = GameDetector()
    app = QApplication(sys.argv)
    window = SceneAssistantWindow(detector)
    window.show()
    sys.exit(app.exec_())
