#!/usr/bin/env python3
"""
暗黑破坏神游戏助手 - GUI界面

功能：
1. 实时显示OCR识别状态和结果
2. 显示任务指引、BOSS攻略、装备推荐
3. 语音交互：语音输入识别、语音播报回复
4. 支持暂停/继续、手动刷新、搜索
5. 可拖拽、置顶、半透明
6. 游戏叠加层：装备/技能/巅峰/雇佣半透明显示
"""

import sys
import logging

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QFrame, QScrollArea, QLineEdit,
)
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread

from game_detector import GameDetector

logger = logging.getLogger(__name__)

try:
    from overlay import OverlayPanel
    OVERLAY_AVAILABLE = True
except ImportError:
    OVERLAY_AVAILABLE = False

try:
    from voice_assistant import VoiceAssistant
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

try:
    from hotkey_manager import HotkeyManager
    HOTKEY_AVAILABLE = True
except ImportError:
    HOTKEY_AVAILABLE = False

try:
    from damage_analyzer import DamageMonitor, DamageLogParser, DamageStatistics, BuildComparator
    DAMAGE_AVAILABLE = True
except ImportError:
    DAMAGE_AVAILABLE = False


class AnalysisWorker(QThread):
    """后台分析线程"""
    result_ready = pyqtSignal(dict)

    def __init__(self, detector):
        super().__init__()
        self.detector = detector
        self._running = True

    def run(self):
        while self._running:
            try:
                analysis = self.detector.analyze_game_state()
                self.result_ready.emit(analysis)
            except Exception as e:
                logger.error(f"分析失败: {e}")
            self.msleep(2000)

    def stop(self):
        self._running = False
        self.wait()


class VoiceWorker(QThread):
    """语音识别后台线程"""
    voice_result = pyqtSignal(dict)

    def __init__(self, voice_assistant):
        super().__init__()
        self.voice_assistant = voice_assistant
        self._running = True

    def run(self):
        while self._running:
            try:
                result = self.voice_assistant.process_voice(timeout=3, phrase_time_limit=8)
                if result and result.get('text'):
                    self.voice_result.emit(result)
            except Exception as e:
                logger.error(f"语音识别失败: {e}")
            self.msleep(500)

    def stop(self):
        self._running = False
        self.wait()


class GuideWidget(QWidget):
    """指引显示组件"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(4)

        self.title_label = QLabel("游戏指引")
        self.title_label.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        self.title_label.setStyleSheet("color: #ff6b35;")
        layout.addWidget(self.title_label)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #8b0000;")
        layout.addWidget(line)

        self.ocr_status_group = QWidget()
        ocr_layout = QVBoxLayout()
        ocr_layout.setSpacing(2)
        self.ocr_status_title = QLabel("OCR状态")
        self.ocr_status_title.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        self.ocr_status_title.setStyleSheet("color: #00bfff;")
        ocr_layout.addWidget(self.ocr_status_title)
        self.ocr_engine_label = QLabel("引擎: 检测中...")
        self.ocr_engine_label.setStyleSheet("color: #aaa;")
        ocr_layout.addWidget(self.ocr_engine_label)
        self.ocr_text_label = QLabel("识别文字: --")
        self.ocr_text_label.setWordWrap(True)
        self.ocr_text_label.setStyleSheet("color: #ccc; font-size: 11px;")
        ocr_layout.addWidget(self.ocr_text_label)
        self.ocr_status_group.setLayout(ocr_layout)
        layout.addWidget(self.ocr_status_group)

        self.voice_status_group = QWidget()
        voice_layout = QVBoxLayout()
        voice_layout.setSpacing(2)
        self.voice_status_title = QLabel("语音助手")
        self.voice_status_title.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        self.voice_status_title.setStyleSheet("color: #9b59b6;")
        voice_layout.addWidget(self.voice_status_title)
        self.voice_stt_label = QLabel("识别: 检测中...")
        self.voice_stt_label.setStyleSheet("color: #aaa; font-size: 11px;")
        voice_layout.addWidget(self.voice_stt_label)
        self.voice_tts_label = QLabel("播报: 检测中...")
        self.voice_tts_label.setStyleSheet("color: #aaa; font-size: 11px;")
        voice_layout.addWidget(self.voice_tts_label)
        self.voice_last_label = QLabel("最近查询: --")
        self.voice_last_label.setWordWrap(True)
        self.voice_last_label.setStyleSheet("color: #ccc; font-size: 11px;")
        voice_layout.addWidget(self.voice_last_label)
        self.voice_response_label = QLabel("回复: --")
        self.voice_response_label.setWordWrap(True)
        self.voice_response_label.setStyleSheet("color: #4ade80; font-size: 11px;")
        voice_layout.addWidget(self.voice_response_label)
        self.voice_status_group.setLayout(voice_layout)
        layout.addWidget(self.voice_status_group)

        self.damage_group = QWidget()
        dmg_layout = QVBoxLayout()
        dmg_layout.setSpacing(2)
        self.damage_title = QLabel("⚔️ 伤害分析")
        self.damage_title.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        self.damage_title.setStyleSheet("color: #e74c3c;")
        dmg_layout.addWidget(self.damage_title)
        self.damage_dps_label = QLabel("DPS: --")
        self.damage_dps_label.setStyleSheet("color: #ff6b35; font-size: 12px; font-weight: bold;")
        dmg_layout.addWidget(self.damage_dps_label)
        self.damage_crit_label = QLabel("暴击率: --")
        self.damage_crit_label.setStyleSheet("color: #f1c40f; font-size: 11px;")
        dmg_layout.addWidget(self.damage_crit_label)
        self.damage_tier_label = QLabel("评级: --")
        self.damage_tier_label.setStyleSheet("color: #aaa; font-size: 11px;")
        dmg_layout.addWidget(self.damage_tier_label)
        self.damage_skill_label = QLabel("主力技能: --")
        self.damage_skill_label.setStyleSheet("color: #4ade80; font-size: 11px;")
        dmg_layout.addWidget(self.damage_skill_label)
        self.damage_advice_label = QLabel("建议: --")
        self.damage_advice_label.setWordWrap(True)
        self.damage_advice_label.setStyleSheet("color: #ccc; font-size: 11px;")
        dmg_layout.addWidget(self.damage_advice_label)
        self.damage_group.setLayout(dmg_layout)
        self.damage_group.hide()
        layout.addWidget(self.damage_group)

        self.quest_group = QWidget()
        quest_layout = QVBoxLayout()
        quest_layout.setSpacing(2)
        self.quest_title = QLabel("当前任务")
        self.quest_title.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        self.quest_title.setStyleSheet("color: #ffd700;")
        quest_layout.addWidget(self.quest_title)
        self.quest_content = QTextEdit()
        self.quest_content.setReadOnly(True)
        self.quest_content.setMaximumHeight(80)
        self.quest_content.setStyleSheet("background-color: rgba(0,0,0,0.5); color: #e0e0e0; border: none; font-size: 12px;")
        quest_layout.addWidget(self.quest_content)
        self.quest_group.setLayout(quest_layout)
        layout.addWidget(self.quest_group)

        self.boss_group = QWidget()
        boss_layout = QVBoxLayout()
        boss_layout.setSpacing(2)
        self.boss_title = QLabel("BOSS信息")
        self.boss_title.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        self.boss_title.setStyleSheet("color: #ff6b35;")
        boss_layout.addWidget(self.boss_title)
        self.boss_content = QTextEdit()
        self.boss_content.setReadOnly(True)
        self.boss_content.setMaximumHeight(80)
        self.boss_content.setStyleSheet("background-color: rgba(0,0,0,0.5); color: #e0e0e0; border: none; font-size: 12px;")
        boss_layout.addWidget(self.boss_content)
        self.boss_group.setLayout(boss_layout)
        layout.addWidget(self.boss_group)

        self.recommend_group = QWidget()
        recommend_layout = QVBoxLayout()
        recommend_layout.setSpacing(2)
        self.recommend_title = QLabel("推荐建议")
        self.recommend_title.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        self.recommend_title.setStyleSheet("color: #4ade80;")
        recommend_layout.addWidget(self.recommend_title)
        self.recommend_content = QTextEdit()
        self.recommend_content.setReadOnly(True)
        self.recommend_content.setMaximumHeight(200)
        self.recommend_content.setStyleSheet("background-color: rgba(0,0,0,0.5); color: #e0e0e0; border: none; font-size: 11px;")
        recommend_layout.addWidget(self.recommend_content)
        self.recommend_group.setLayout(recommend_layout)
        layout.addWidget(self.recommend_group)

        self.setLayout(layout)

    def update_guide(self, analysis):
        """更新指引内容"""
        if not isinstance(analysis, dict):
            return

        ocr_engine = analysis.get('ocr_engine', 'simulation')
        screen_text = analysis.get('screen_text', '')

        if ocr_engine and ocr_engine != 'simulation':
            self.ocr_engine_label.setText(f"引擎: {ocr_engine}")
            self.ocr_engine_label.setStyleSheet("color: #4ade80;")
        else:
            self.ocr_engine_label.setText("引擎: 模拟模式")
            self.ocr_engine_label.setStyleSheet("color: #ff6b35;")

        if screen_text:
            display_text = screen_text[:80] + ('...' if len(screen_text) > 80 else '')
            self.ocr_text_label.setText(f"识别: {display_text}")
        else:
            self.ocr_text_label.setText("识别: (无文字)")

        recommendations = analysis.get('recommendations', {})

        if recommendations.get('quest_hints'):
            quest = recommendations['quest_hints'][0]
            content = f"名称: {quest['name']}\n地点: {quest['location']}\n指引: {quest['guide']}"
            self.quest_content.setPlainText(content)
            self.quest_group.show()
        else:
            self.quest_group.hide()

        if recommendations.get('boss_tips'):
            boss = recommendations['boss_tips'][0]
            content = f"名称: {boss['name']}\n弱点: {', '.join(boss['weakness'])}\n技能: {', '.join(boss['skills'])}\n攻略: {boss['guide']}"
            self.boss_content.setPlainText(content)
            self.boss_group.show()
        else:
            self.boss_group.hide()

        formatted = analysis.get('formatted', '')
        if formatted:
            self.recommend_content.setPlainText(formatted)
            self.recommend_group.show()
        else:
            self.recommend_group.hide()

    def update_voice_result(self, result):
        """更新语音查询结果"""
        if not isinstance(result, dict):
            return

        text = result.get('text', '')
        intent = result.get('intent', '')
        query = result.get('query', '')
        response = result.get('response', '')

        if text:
            self.voice_last_label.setText(f"查询: {text}")
        if response:
            self.voice_response_label.setText(f"回复: {response}")

        if result.get('results'):
            lines = []
            for r in result['results'][:5]:
                cat = r['category']
                score = r['score']
                data = r['data']
                name = data.get('name', data.get('title', ''))
                lines.append(f"[{cat}] {score:.0%} {name}")
            self.recommend_content.setPlainText('\n'.join(lines))
            self.recommend_group.show()

    def update_damage_report(self, report):
        """更新伤害分析报告"""
        if not isinstance(report, dict):
            return

        summary = report.get('summary', {})
        comparison = report.get('comparison', {})

        dps = summary.get('dps', 0)
        crit_rate = summary.get('crit_rate', 0)
        top_skill = summary.get('top_skill', '--')

        self.damage_dps_label.setText(f"DPS: {dps:,.0f}")

        dps_eval = comparison.get('dps_evaluation', {})
        if dps_eval:
            tier = dps_eval.get('tier', '--')
            label = dps_eval.get('label', '')
            color = dps_eval.get('color', '#aaa')
            self.damage_tier_label.setText(f"评级: {tier}（{label}）")
            self.damage_tier_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")

        self.damage_crit_label.setText(f"暴击率: {crit_rate:.1f}%")
        self.damage_skill_label.setText(f"主力技能: {top_skill}")

        recommendations = comparison.get('recommendations', [])
        if recommendations:
            advice_lines = []
            for rec in recommendations:
                msg = rec.get('message', '')
                advice_lines.append(f"• {msg}")
                for s in rec.get('suggestions', [])[:2]:
                    advice_lines.append(f"  → {s}")
            self.damage_advice_label.setText('\n'.join(advice_lines))
        else:
            self.damage_advice_label.setText("暂无建议")

        self.damage_group.show()


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self, use_web_data=False, ocr_engine=None, stt_engine='google', tts_engine='auto'):
        super().__init__()
        self.detector = GameDetector(use_web_data=use_web_data, use_ocr=True, ocr_engine=ocr_engine)
        self.stt_engine = stt_engine
        self.tts_engine = tts_engine

        self.voice_assistant = None
        self.voice_worker = None
        self.is_voice_listening = False

        self.overlay_panel = None
        self.overlay_visible = False

        self.hotkey_manager = None

        self.damage_monitor = None
        self.is_damage_monitoring = False

        if VOICE_AVAILABLE:
            try:
                self.voice_assistant = VoiceAssistant(
                    content_indexer=self.detector.indexer,
                    stt_engine=stt_engine,
                    tts_engine=tts_engine,
                )
            except Exception as e:
                logger.warning(f"语音助手初始化失败: {e}")

        self.init_ui()
        self.start_analysis()
        self._update_voice_status_display()
        self._init_hotkeys()

    def init_ui(self):
        self.setWindowTitle("暗黑破坏神游戏助手")
        self.setGeometry(100, 100, 340, 700)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        self.setWindowOpacity(0.92)
        palette = QPalette()
        palette.setColor(QPalette.Background, QColor(20, 20, 40))
        self.setPalette(palette)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(4)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setSpacing(8)

        self.title_label = QLabel("暗黑破坏神助手")
        self.title_label.setFont(QFont('Microsoft YaHei', 12, QFont.Bold))
        self.title_label.setStyleSheet("color: #ff6b35;")
        header_layout.addWidget(self.title_label)

        ocr_status = self.detector.ocr_recognizer.ocr.engine_name if self.detector.ocr_recognizer else 'none'
        ocr_color = '#4ade80' if ocr_status and ocr_status != 'none' else '#ff6b35'
        self.ocr_indicator = QLabel(f"OCR: {ocr_status or 'N/A'}")
        self.ocr_indicator.setFont(QFont('Microsoft YaHei', 9))
        self.ocr_indicator.setStyleSheet(f"color: {ocr_color};")
        header_layout.addWidget(self.ocr_indicator)

        voice_status = self.voice_assistant.get_status() if self.voice_assistant else {}
        stt = voice_status.get('stt_engine', 'none')
        tts = voice_status.get('tts_engine', 'none')
        voice_color = '#9b59b6' if (stt != 'none' or tts != 'none') else '#666'
        self.voice_indicator = QLabel(f"Voice: {stt}/{tts}")
        self.voice_indicator.setFont(QFont('Microsoft YaHei', 8))
        self.voice_indicator.setStyleSheet(f"color: {voice_color};")
        header_layout.addWidget(self.voice_indicator)

        hotkey_color = '#e67e22' if HOTKEY_AVAILABLE else '#666'
        self.hotkey_indicator = QLabel("⌨" if HOTKEY_AVAILABLE else "")
        self.hotkey_indicator.setFont(QFont('Microsoft YaHei', 9))
        self.hotkey_indicator.setStyleSheet(f"color: {hotkey_color};")
        self.hotkey_indicator.setToolTip(self._get_hotkey_tooltip() if HOTKEY_AVAILABLE else "")
        header_layout.addWidget(self.hotkey_indicator)

        header_layout.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet("color: #ff6b35; background: transparent; border: none; font-size: 14px;")
        self.close_btn.clicked.connect(self.close)
        header_layout.addWidget(self.close_btn)

        layout.addWidget(header)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #8b0000;")
        layout.addWidget(line)

        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setSpacing(4)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索游戏内容...")
        self.search_input.setStyleSheet(
            "background-color: rgba(0,0,0,0.5); color: #e0e0e0; border: 1px solid #444; "
            "border-radius: 3px; padding: 4px 8px; font-size: 12px;"
        )
        self.search_input.returnPressed.connect(self.manual_search)
        search_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("搜索")
        self.search_btn.setStyleSheet(
            "background-color: #0066cc; color: white; border: none; "
            "border-radius: 3px; padding: 4px 10px; font-size: 12px;"
        )
        self.search_btn.clicked.connect(self.manual_search)
        search_layout.addWidget(self.search_btn)
        layout.addWidget(search_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.guide_widget = GuideWidget()
        scroll_area.setWidget(self.guide_widget)
        layout.addWidget(scroll_area)

        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        control_layout.setSpacing(4)

        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setStyleSheet(
            "background-color: #8b0000; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
        )
        self.pause_btn.clicked.connect(self.toggle_pause)
        control_layout.addWidget(self.pause_btn)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setStyleSheet(
            "background-color: #0066cc; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
        )
        self.refresh_btn.clicked.connect(self.manual_refresh)
        control_layout.addWidget(self.refresh_btn)

        self.ocr_toggle_btn = QPushButton("OCR: 开")
        self.ocr_toggle_btn.setStyleSheet(
            "background-color: #2d5a27; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
        )
        self.ocr_toggle_btn.clicked.connect(self.toggle_ocr)
        control_layout.addWidget(self.ocr_toggle_btn)

        layout.addWidget(control_widget)

        voice_control_widget = QWidget()
        voice_control_layout = QHBoxLayout(voice_control_widget)
        voice_control_layout.setSpacing(4)

        self.voice_listen_btn = QPushButton("🎤 语音输入")
        self.voice_listen_btn.setStyleSheet(
            "background-color: #9b59b6; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
        )
        self.voice_listen_btn.clicked.connect(self.toggle_voice_listening)
        voice_control_layout.addWidget(self.voice_listen_btn)

        self.voice_speak_btn = QPushButton("🔊 朗读结果")
        self.voice_speak_btn.setStyleSheet(
            "background-color: #2d5a27; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
        )
        self.voice_speak_btn.clicked.connect(self.speak_current_result)
        voice_control_layout.addWidget(self.voice_speak_btn)

        self.voice_stop_btn = QPushButton("⏹ 停止朗读")
        self.voice_stop_btn.setStyleSheet(
            "background-color: #666; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
        )
        self.voice_stop_btn.clicked.connect(self.stop_speaking)
        voice_control_layout.addWidget(self.voice_stop_btn)

        layout.addWidget(voice_control_widget)

        overlay_control_widget = QWidget()
        overlay_control_layout = QHBoxLayout(overlay_control_widget)
        overlay_control_layout.setSpacing(4)

        self.overlay_toggle_btn = QPushButton("📋 叠加层")
        self.overlay_toggle_btn.setStyleSheet(
            "background-color: #e67e22; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
        )
        self.overlay_toggle_btn.clicked.connect(self.toggle_overlay)
        overlay_control_layout.addWidget(self.overlay_toggle_btn)

        self.overlay_equip_btn = QPushButton("⚔️ 装备")
        self.overlay_equip_btn.setStyleSheet(
            "background-color: #2c3e50; color: #bf642f; border: 1px solid #bf642f; "
            "border-radius: 3px; padding: 4px 8px; font-size: 11px;"
        )
        self.overlay_equip_btn.clicked.connect(lambda: self._show_overlay_tab(0))
        overlay_control_layout.addWidget(self.overlay_equip_btn)

        self.overlay_skill_btn = QPushButton("🔮 技能")
        self.overlay_skill_btn.setStyleSheet(
            "background-color: #2c3e50; color: #4ade80; border: 1px solid #4ade80; "
            "border-radius: 3px; padding: 4px 8px; font-size: 11px;"
        )
        self.overlay_skill_btn.clicked.connect(lambda: self._show_overlay_tab(1))
        overlay_control_layout.addWidget(self.overlay_skill_btn)

        self.overlay_paragon_btn = QPushButton("🌟 巅峰")
        self.overlay_paragon_btn.setStyleSheet(
            "background-color: #2c3e50; color: #f1c40f; border: 1px solid #f1c40f; "
            "border-radius: 3px; padding: 4px 8px; font-size: 11px;"
        )
        self.overlay_paragon_btn.clicked.connect(lambda: self._show_overlay_tab(2))
        overlay_control_layout.addWidget(self.overlay_paragon_btn)

        self.overlay_merc_btn = QPushButton("🗡️ 雇佣")
        self.overlay_merc_btn.setStyleSheet(
            "background-color: #2c3e50; color: #9b59b6; border: 1px solid #9b59b6; "
            "border-radius: 3px; padding: 4px 8px; font-size: 11px;"
        )
        self.overlay_merc_btn.clicked.connect(lambda: self._show_overlay_tab(3))
        overlay_control_layout.addWidget(self.overlay_merc_btn)

        layout.addWidget(overlay_control_widget)

        damage_control_widget = QWidget()
        damage_control_layout = QHBoxLayout(damage_control_widget)
        damage_control_layout.setSpacing(4)

        self.damage_monitor_btn = QPushButton("⚔️ 伤害监控")
        self.damage_monitor_btn.setStyleSheet(
            "background-color: #c0392b; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
        )
        self.damage_monitor_btn.clicked.connect(self.toggle_damage_monitor)
        damage_control_layout.addWidget(self.damage_monitor_btn)

        self.damage_reset_btn = QPushButton("🔄 重置")
        self.damage_reset_btn.setStyleSheet(
            "background-color: #2c3e50; color: #e74c3c; border: 1px solid #e74c3c; "
            "border-radius: 3px; padding: 4px 8px; font-size: 11px;"
        )
        self.damage_reset_btn.clicked.connect(self.reset_damage_stats)
        damage_control_layout.addWidget(self.damage_reset_btn)

        self.damage_feed_btn = QPushButton("📝 输入日志")
        self.damage_feed_btn.setStyleSheet(
            "background-color: #2c3e50; color: #f39c12; border: 1px solid #f39c12; "
            "border-radius: 3px; padding: 4px 8px; font-size: 11px;"
        )
        self.damage_feed_btn.clicked.connect(self._feed_damage_log)
        damage_control_layout.addWidget(self.damage_feed_btn)

        layout.addWidget(damage_control_widget)

        self.dragging = False
        self.drag_position = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def start_analysis(self):
        """开始定时分析"""
        self.is_paused = False
        self.worker = AnalysisWorker(self.detector)
        self.worker.result_ready.connect(self.update_guide)
        self.worker.start()

    def toggle_pause(self):
        """暂停/继续分析"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.setText("继续")
            self.worker.stop()
        else:
            self.pause_btn.setText("暂停")
            self.worker = AnalysisWorker(self.detector)
            self.worker.result_ready.connect(self.update_guide)
            self.worker.start()

    def manual_refresh(self):
        """手动刷新"""
        try:
            analysis = self.detector.analyze_game_state()
            self.update_guide(analysis)
        except Exception as e:
            logger.error(f"刷新失败: {e}")

    def toggle_ocr(self):
        """切换OCR开关"""
        self.detector.ocr_available = not self.detector.ocr_available
        if self.detector.ocr_available:
            self.ocr_toggle_btn.setText("OCR: 开")
            self.ocr_toggle_btn.setStyleSheet(
                "background-color: #2d5a27; color: white; border: none; "
                "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
            )
        else:
            self.ocr_toggle_btn.setText("OCR: 关")
            self.ocr_toggle_btn.setStyleSheet(
                "background-color: #666; color: white; border: none; "
                "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
            )

    def toggle_voice_listening(self):
        """切换语音监听"""
        if not self.voice_assistant:
            self.voice_listen_btn.setText("🎤 不可用")
            return

        if self.is_voice_listening:
            self._stop_voice_listening()
        else:
            self._start_voice_listening()

    def _start_voice_listening(self):
        """启动语音监听"""
        if not self.voice_assistant or not self.voice_assistant.voice_input.available:
            self.voice_listen_btn.setText("🎤 麦克风不可用")
            self.voice_listen_btn.setStyleSheet(
                "background-color: #666; color: white; border: none; "
                "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
            )
            return

        self.is_voice_listening = True
        self.voice_listen_btn.setText("🎤 监听中...")
        self.voice_listen_btn.setStyleSheet(
            "background-color: #c0392b; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
        )

        self.voice_worker = VoiceWorker(self.voice_assistant)
        self.voice_worker.voice_result.connect(self._on_voice_result)
        self.voice_worker.start()

    def _stop_voice_listening(self):
        """停止语音监听"""
        self.is_voice_listening = False
        self.voice_listen_btn.setText("🎤 语音输入")
        self.voice_listen_btn.setStyleSheet(
            "background-color: #9b59b6; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
        )

        if self.voice_worker:
            self.voice_worker.stop()
            self.voice_worker = None

    def _on_voice_result(self, result):
        """处理语音识别结果"""
        self.guide_widget.update_voice_result(result)

        if result.get('spoken'):
            self.voice_speak_btn.setText("🔊 播报中...")
            QTimer.singleShot(3000, lambda: self.voice_speak_btn.setText("🔊 朗读结果"))

    def speak_current_result(self):
        """朗读当前推荐结果"""
        if not self.voice_assistant or not self.voice_assistant.voice_output.available:
            return

        text = self.guide_widget.recommend_content.toPlainText()
        if text:
            self.voice_assistant.voice_output.speak(text, blocking=False)
            self.voice_speak_btn.setText("🔊 播报中...")
            QTimer.singleShot(5000, lambda: self.voice_speak_btn.setText("🔊 朗读结果"))

    def stop_speaking(self):
        """停止朗读"""
        if self.voice_assistant:
            self.voice_assistant.voice_output.stop()
            self.voice_speak_btn.setText("🔊 朗读结果")

    def manual_search(self):
        """手动搜索"""
        query = self.search_input.text().strip()
        if not query:
            return

        if self.voice_assistant:
            result = self.voice_assistant.process_text(query)
            self.guide_widget.update_voice_result(result)
            if result.get('spoken'):
                self.voice_speak_btn.setText("🔊 播报中...")
                QTimer.singleShot(3000, lambda: self.voice_speak_btn.setText("🔊 朗读结果"))
            return

        results = self.detector.indexer.search(query, top_n=10)
        if results:
            formatted_lines = [f"搜索: {query}\n"]
            for r in results:
                cat = r['category']
                score = r['score']
                data = r['data']
                if cat == 'quests':
                    formatted_lines.append(f"📋 [{score:.0%}] {data.get('name','')} - {data.get('location','')}")
                elif cat == 'bosses':
                    formatted_lines.append(f"👹 [{score:.0%}] {data.get('name','')} 弱点: {', '.join(data.get('weakness',[]))}")
                elif cat == 'equipment':
                    formatted_lines.append(f"⚔️ [{score:.0%}] {data.get('name','')} [{data.get('rarity','')}]")
                elif cat == 'web_skills':
                    formatted_lines.append(f"🔮 [{score:.0%}] {data.get('name','')} [{data.get('class','')}]")
                elif cat == 'skills':
                    name = data.get('name', '')
                    skills = data.get('skills', {})
                    builds = data.get('builds', {})
                    line = f"🔮 [{score:.0%}] {name}"
                    if skills:
                        skill_cats = list(skills.keys())[:3]
                        line += f" | 技能: {', '.join(skill_cats)}"
                    if builds:
                        build_names = list(builds.keys())[:2]
                        line += f" | 加点: {', '.join(build_names)}"
                    formatted_lines.append(line)
                elif cat == 'build_details':
                    formatted_lines.append(f"📖 [{score:.0%}] {data.get('title','')}")
                elif cat == 'guides':
                    formatted_lines.append(f"🌐 [{score:.0%}] {data.get('title','')}")
                else:
                    formatted_lines.append(f"[{cat}] [{score:.0%}] {data}")

            analysis = {
                'ocr_engine': 'search',
                'screen_text': query,
                'recommendations': {},
                'formatted': '\n'.join(formatted_lines),
            }
            self.update_guide(analysis)
            self._update_overlay_from_search(results)
        else:
            self.guide_widget.recommend_content.setPlainText(f"未找到与 '{query}' 相关的内容")

    def _update_voice_status_display(self):
        """更新语音状态显示"""
        if not self.voice_assistant:
            self.guide_widget.voice_stt_label.setText("识别: 不可用")
            self.guide_widget.voice_stt_label.setStyleSheet("color: #ff6b35; font-size: 11px;")
            self.guide_widget.voice_tts_label.setText("播报: 不可用")
            self.guide_widget.voice_tts_label.setStyleSheet("color: #ff6b35; font-size: 11px;")
            return

        status = self.voice_assistant.get_status()
        if status['stt_available']:
            self.guide_widget.voice_stt_label.setText(f"识别: {status['stt_engine']}")
            self.guide_widget.voice_stt_label.setStyleSheet("color: #4ade80; font-size: 11px;")
        else:
            self.guide_widget.voice_stt_label.setText("识别: 不可用")
            self.guide_widget.voice_stt_label.setStyleSheet("color: #ff6b35; font-size: 11px;")

        if status['tts_available']:
            self.guide_widget.voice_tts_label.setText(f"播报: {status['tts_engine']}")
            self.guide_widget.voice_tts_label.setStyleSheet("color: #4ade80; font-size: 11px;")
        else:
            self.guide_widget.voice_tts_label.setText("播报: 不可用")
            self.guide_widget.voice_tts_label.setStyleSheet("color: #ff6b35; font-size: 11px;")

    def update_guide(self, analysis):
        """更新指引内容"""
        if not self.is_paused:
            self.guide_widget.update_guide(analysis)
            self._update_overlay_from_analysis(analysis)

    def toggle_overlay(self):
        """切换叠加层显示"""
        if not OVERLAY_AVAILABLE:
            self.overlay_toggle_btn.setText("📋 不可用")
            return

        if self.overlay_visible and self.overlay_panel:
            self.overlay_panel.hide()
            self.overlay_visible = False
            self.overlay_toggle_btn.setText("📋 叠加层")
            self.overlay_toggle_btn.setStyleSheet(
                "background-color: #e67e22; color: white; border: none; "
                "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
            )
        else:
            if not self.overlay_panel:
                self.overlay_panel = OverlayPanel(opacity=0.85)
                self.overlay_panel.closed.connect(self._on_overlay_closed)
            self.overlay_panel.show_at_game_position()
            self.overlay_visible = True
            self.overlay_toggle_btn.setText("📋 隐藏叠加")
            self.overlay_toggle_btn.setStyleSheet(
                "background-color: #c0392b; color: white; border: none; "
                "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
            )

    def _show_overlay_tab(self, tab_index):
        """显示叠加层并切换到指定标签"""
        if not OVERLAY_AVAILABLE:
            return

        if not self.overlay_panel:
            self.overlay_panel = OverlayPanel(opacity=0.85)
            self.overlay_panel.closed.connect(self._on_overlay_closed)

        self.overlay_panel._tab_widget.setCurrentIndex(tab_index)

        if not self.overlay_visible:
            self.overlay_panel.show_at_game_position()
            self.overlay_visible = True
            self.overlay_toggle_btn.setText("📋 隐藏叠加")
            self.overlay_toggle_btn.setStyleSheet(
                "background-color: #c0392b; color: white; border: none; "
                "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
            )

    def _on_overlay_closed(self):
        """叠加层关闭回调"""
        self.overlay_visible = False
        self.overlay_toggle_btn.setText("📋 叠加层")
        self.overlay_toggle_btn.setStyleSheet(
            "background-color: #e67e22; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
        )

    def _update_overlay_from_analysis(self, analysis):
        """从分析结果更新叠加层"""
        if not self.overlay_panel or not self.overlay_visible:
            return

        recommendations = analysis.get('recommendations', {})
        class_name = analysis.get('class_name')

        build_details = recommendations.get('build_details', [])
        if build_details:
            top_build = build_details[0]
            self.overlay_panel.update_from_build(class_name, top_build)
            return

        equip_suggestions = recommendations.get('equipment_suggestions', [])
        skill_info = recommendations.get('skill_info', [])

        if equip_suggestions:
            equip_data = {
                'equipment': [s for s in equip_suggestions],
                'title': '装备推荐',
            }
            self.overlay_panel.update_equipment(class_name, equip_data)

        if skill_info:
            self.overlay_panel.update_skills(class_name, {'skills': skill_info})

    def _update_overlay_from_search(self, results, class_name=None):
        """从搜索结果更新叠加层"""
        if not self.overlay_panel:
            return
        self.overlay_panel.update_from_search_results(results, class_name)

    def _init_hotkeys(self):
        """初始化全局快捷键"""
        if not HOTKEY_AVAILABLE:
            logger.info("全局快捷键不可用（keyboard 库未安装）")
            return

        try:
            from config import HOTKEY_CONFIG
            hotkeys = HOTKEY_CONFIG.get('bindings', {})
        except ImportError:
            hotkeys = {}

        self.hotkey_manager = HotkeyManager(hotkeys=hotkeys)

        self.hotkey_manager.voice_toggled.connect(self._on_hotkey_voice)
        self.hotkey_manager.overlay_toggled.connect(self._on_hotkey_overlay)
        self.hotkey_manager.overlay_tab_requested.connect(self._on_hotkey_overlay_tab)
        self.hotkey_manager.window_toggled.connect(self._on_hotkey_window)
        self.hotkey_manager.refresh_requested.connect(self._on_hotkey_refresh)
        self.hotkey_manager.damage_toggled.connect(self._on_hotkey_damage)
        self.hotkey_manager.hotkey_pressed.connect(self._on_hotkey_pressed)

        status = self.hotkey_manager.get_status()
        if status['available']:
            logger.info(f"全局快捷键已启用，已注册 {status['registered_count']} 个快捷键")
        else:
            logger.warning("全局快捷键初始化失败")

    def _get_hotkey_tooltip(self):
        """获取快捷键提示文本"""
        if not self.hotkey_manager:
            from hotkey_manager import HotkeyManager
            mgr = HotkeyManager.__new__(HotkeyManager)
            mgr._hotkeys = HotkeyManager.DEFAULT_HOTKEYS
        else:
            mgr = self.hotkey_manager

        lines = ["快捷键列表:"]
        for action, key in mgr._hotkeys.items():
            label = mgr.HOTKEY_LABELS.get(action, action)
            lines.append(f"  {key.upper()} - {label}")
        return '\n'.join(lines)

    def _on_hotkey_voice(self):
        """快捷键：切换语音输入"""
        self.toggle_voice_listening()

    def _on_hotkey_overlay(self):
        """快捷键：切换叠加层"""
        self.toggle_overlay()

    def _on_hotkey_overlay_tab(self, tab_index):
        """快捷键：叠加层标签页"""
        self._show_overlay_tab(tab_index)

    def _on_hotkey_window(self):
        """快捷键：隐藏/显示主窗口"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()

    def _on_hotkey_refresh(self):
        """快捷键：刷新分析"""
        self.manual_refresh()

    def _on_hotkey_damage(self):
        """快捷键：切换伤害监控"""
        self.toggle_damage_monitor()

    def _on_hotkey_pressed(self, action):
        """快捷键触发反馈"""
        if self.hotkey_manager:
            key = self.hotkey_manager._hotkeys.get(action, '')
            label = self.hotkey_manager.HOTKEY_LABELS.get(action, action)
            self.hotkey_indicator.setStyleSheet("color: #ff6b35; font-size: 12px;")
            QTimer.singleShot(300, lambda: self.hotkey_indicator.setStyleSheet(
                "color: #e67e22; font-size: 9px;"
            ))

    def toggle_damage_monitor(self):
        """切换伤害监控"""
        if not DAMAGE_AVAILABLE:
            self.damage_monitor_btn.setText("⚔️ 不可用")
            return

        if self.is_damage_monitoring:
            self._stop_damage_monitor()
        else:
            self._start_damage_monitor()

    def _start_damage_monitor(self):
        """启动伤害监控"""
        if not DAMAGE_AVAILABLE:
            return

        if not self.damage_monitor:
            ocr_rec = self.detector.ocr_recognizer if hasattr(self.detector, 'ocr_recognizer') else None
            self.damage_monitor = DamageMonitor(
                ocr_recognizer=ocr_rec,
                content_indexer=self.detector.indexer,
            )

        self.damage_monitor.start_monitoring(callback=self._on_damage_update)
        self.is_damage_monitoring = True
        self.damage_monitor_btn.setText("⚔️ 监控中...")
        self.damage_monitor_btn.setStyleSheet(
            "background-color: #e74c3c; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
        )
        self.guide_widget.damage_group.show()

    def _stop_damage_monitor(self):
        """停止伤害监控"""
        if self.damage_monitor:
            self.damage_monitor.stop_monitoring()
        self.is_damage_monitoring = False
        self.damage_monitor_btn.setText("⚔️ 伤害监控")
        self.damage_monitor_btn.setStyleSheet(
            "background-color: #c0392b; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: 12px;"
        )

    def reset_damage_stats(self):
        """重置伤害统计"""
        if self.damage_monitor:
            self.damage_monitor.reset()
            self.guide_widget.damage_dps_label.setText("DPS: --")
            self.guide_widget.damage_crit_label.setText("暴击率: --")
            self.guide_widget.damage_tier_label.setText("评级: --")
            self.guide_widget.damage_skill_label.setText("主力技能: --")
            self.guide_widget.damage_advice_label.setText("建议: --")

    def _on_damage_update(self, report):
        """伤害数据更新回调"""
        self.guide_widget.update_damage_report(report)
        if self.overlay_panel and self.overlay_visible:
            self._update_overlay_damage(report)

    def _feed_damage_log(self):
        """手动输入伤害日志"""
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getMultiLineText(
            self, "输入战斗日志",
            "粘贴D4高级战斗日志文本：",
            "",
        )
        if ok and text.strip():
            if not self.damage_monitor and DAMAGE_AVAILABLE:
                self.damage_monitor = DamageMonitor(
                    content_indexer=self.detector.indexer,
                )
            if self.damage_monitor:
                events = self.damage_monitor.feed_log_text(text)
                if events:
                    report = self.damage_monitor.get_report()
                    self.guide_widget.update_damage_report(report)
                    if self.overlay_panel and self.overlay_visible:
                        self._update_overlay_damage(report)
                else:
                    self.guide_widget.damage_advice_label.setText("未识别到伤害数据，请检查日志格式")

    def _update_overlay_damage(self, report):
        """更新叠加层伤害数据"""
        if not self.overlay_panel:
            return

        summary = report.get('summary', {})
        comparison = report.get('comparison', {})

        skill_breakdown = summary.get('skill_breakdown', {})
        if skill_breakdown:
            equip_data = {
                'equipment': [],
                'title': f"伤害统计 DPS:{summary.get('dps', 0):,.0f}",
            }
            for skill, data in skill_breakdown.items():
                equip_data['equipment'].append({
                    'name': f"{skill} ({data['percentage']}%)",
                    'slot': f"avg:{data['avg_damage']:,.0f} max:{data['max_damage']:,.0f}",
                    'rarity': '暗金' if data['percentage'] > 30 else '传奇',
                })
            self.overlay_panel.update_equipment(
                report.get('player_class', ''), equip_data
            )

        recommendations = comparison.get('recommendations', [])
        if recommendations:
            advice_skills = []
            for rec in recommendations:
                advice_skills.append(rec.get('message', ''))
                for s in rec.get('suggestions', [])[:2]:
                    advice_skills.append(f"  → {s}")
            self.overlay_panel.update_skills(
                report.get('player_class', ''),
                {'skills': advice_skills},
            )

    def closeEvent(self, event):
        if hasattr(self, 'worker'):
            self.worker.stop()
        if self.voice_worker:
            self.voice_worker.stop()
        if self.voice_assistant:
            self.voice_assistant.stop_listening()
        if self.overlay_panel:
            self.overlay_panel.close()
        if self.hotkey_manager:
            self.hotkey_manager.cleanup()
        if self.damage_monitor:
            self.damage_monitor.stop_monitoring()
        event.accept()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
