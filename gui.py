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
import os
import logging
import ctypes

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QFrame, QScrollArea, QLineEdit,
    QTabWidget, QCheckBox, QComboBox, QGridLayout, QMessageBox,
    QAction, QInputDialog,
)
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread

from game_detector import GameDetector
from scene_classifier import SceneCategory, classify_scene, get_category_display_name, get_category_color
from class_recommender import (
    D4Class, CLASS_NAMES, detect_class_from_text,
    get_class_display_name, get_class_color, get_class_icon,
    DEFAULT_BUILDS,
)


logger = logging.getLogger(__name__)


def _get_screen_scale():
    user32 = ctypes.windll.user32
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    ref_w, ref_h = 1920, 1080
    scale = max(screen_w / ref_w, screen_h / ref_h)
    try:
        dc = user32.GetDC(None)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)
        user32.ReleaseDC(None, dc)
        if dpi > 96:
            scale *= dpi / 96
    except Exception:
        pass
    return max(1.0, min(scale, 3.0))


SCREEN_SCALE = _get_screen_scale()


def _fs(base_size):
    return max(int(base_size * SCREEN_SCALE), base_size + 2)


def _ff(family, base_size, weight=QFont.Normal):
    return QFont(family, _fs(base_size), weight)

try:
    from web_overlay import WebOverlay, WEB_AVAILABLE as _WEB_OK
except ImportError:
    WebOverlay = None
    _WEB_OK = False

if _WEB_OK and WebOverlay is not None:
    GraphicalOverlay = None
    OverlayPanel = None
    OVERLAY_AVAILABLE = True
else:
    try:
        from graphical_overlay import GraphicalOverlay
        OVERLAY_AVAILABLE = True
    except ImportError:
        try:
            from overlay import OverlayPanel
            GraphicalOverlay = None
            OVERLAY_AVAILABLE = True
        except ImportError:
            GraphicalOverlay = None
            OverlayPanel = None
            OVERLAY_AVAILABLE = False

try:
    from voice_assistant import VoiceAssistant
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

try:
    from quest_guide_webview import QuestGuideWebView
    QUEST_GUIDE_AVAILABLE = True
except ImportError:
    QuestGuideWebView = None
    QUEST_GUIDE_AVAILABLE = False

try:
    from quest_guide_config import (
        SIDE_QUESTS, MAIN_QUESTS, BEGINNER_GUIDES, SEASON_GUIDES,
        search_guide, GAMERSKY_D4_HOME,
    )
    QUEST_CONFIG_OK = True
except ImportError:
    QUEST_CONFIG_OK = False
    SIDE_QUESTS = {}
    MAIN_QUESTS = {}
    BEGINNER_GUIDES = {}
    SEASON_GUIDES = {}

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


class SceneVisionWorker(QThread):
    """后台 Vision 场景识别定时器线程

    关键设计：**本线程只做 5 秒一次的定时通知，不碰 dxcam、不碰截图**
    实际的截图+Vision 查询放在主线程的 _do_scene_detect() 里执行。
    这样可以保证 dxcam 实例只在主线程被一个消费者使用，彻底避免多实例冲突导致的死机。
    """
    # 请求主线程执行一次场景检测
    request_detect = pyqtSignal()
    # 场景识别结果（由主线程发出，但这里也保留一个信号以便外部使用）
    scene_detected = pyqtSignal(dict)

    def __init__(self, interval=5.0):
        super().__init__()
        self.interval = interval
        self._running = True

    def run(self):
        # 先 sleep 3 秒让 GUI+主程序完全初始化完成
        self.msleep(3000)
        logger.info("SceneVisionWorker 启动 (只做定时通知)")
        cycle = 0
        while self._running:
            cycle += 1
            # 只发一个信号，通知主线程去做实际的检测
            logger.info(f"[Vision-Timer #{cycle}] 触发主线程检测")
            self.request_detect.emit()
            # 等待 interval 秒（可响应 stop）
            for _ in range(int(self.interval * 10)):
                if not self._running:
                    return
                self.msleep(100)

    def stop(self):
        self._running = False
        self.wait(1000)


class BuildFetcherThread(QThread):
    """后台抓取BD攻略图片线程"""
    finished_ok = pyqtSignal(list)

    def __init__(self, fetcher, class_type):
        super().__init__()
        self.fetcher = fetcher
        self.class_type = class_type

    def run(self):
        try:
            builds = self.fetcher.get_or_fetch_builds(self.class_type)
            self.finished_ok.emit(builds)
        except Exception as e:
            logger.error(f"抓取BD失败: {e}")
            self.finished_ok.emit([])


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
        self.setStyleSheet("background-color: transparent;")

        self.title_label = QLabel("游戏指引")
        self.title_label.setFont(_ff('Microsoft YaHei', 16, QFont.Bold))
        self.title_label.setStyleSheet("color: #ff6b35; background-color: transparent;")
        layout.addWidget(self.title_label)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: rgba(139,0,0,0.5);")
        layout.addWidget(line)

        self.ocr_status_group = QWidget()
        self.ocr_status_group.setStyleSheet("background-color: transparent;")
        ocr_layout = QVBoxLayout()
        ocr_layout.setSpacing(2)
        self.ocr_status_title = QLabel("画面识别")
        self.ocr_status_title.setFont(_ff('Microsoft YaHei', 13, QFont.Bold))
        self.ocr_status_title.setStyleSheet("color: #00bfff; background-color: transparent;")
        ocr_layout.addWidget(self.ocr_status_title)
        self.ocr_engine_label = QLabel("引擎: 检测中...")
        self.ocr_engine_label.setStyleSheet("color: #aaa; background-color: transparent;")
        ocr_layout.addWidget(self.ocr_engine_label)
        self.ocr_text_label = QLabel("OCR文字: --")
        self.ocr_text_label.setWordWrap(True)
        self.ocr_text_label.setStyleSheet(f"color: #ccc; font-size: {_fs(13)}px; background-color: transparent;")
        ocr_layout.addWidget(self.ocr_text_label)
        self.vision_scene_label = QLabel("场景: --")
        self.vision_scene_label.setWordWrap(True)
        self.vision_scene_label.setStyleSheet(f"color: #9b59b6; font-size: {_fs(13)}px; background-color: transparent;")
        ocr_layout.addWidget(self.vision_scene_label)
        self.ocr_status_group.setLayout(ocr_layout)
        layout.addWidget(self.ocr_status_group)

        self.voice_status_group = QWidget()
        self.voice_status_group.setStyleSheet("background-color: transparent;")
        voice_layout = QVBoxLayout()
        voice_layout.setSpacing(2)
        self.voice_status_title = QLabel("语音助手")
        self.voice_status_title.setFont(_ff('Microsoft YaHei', 13, QFont.Bold))
        self.voice_status_title.setStyleSheet("color: #9b59b6; background-color: transparent;")
        voice_layout.addWidget(self.voice_status_title)
        self.voice_stt_label = QLabel("识别: 检测中...")
        self.voice_stt_label.setStyleSheet(f"color: #aaa; font-size: {_fs(13)}px; background-color: transparent;")
        voice_layout.addWidget(self.voice_stt_label)
        self.voice_tts_label = QLabel("播报: 检测中...")
        self.voice_tts_label.setStyleSheet(f"color: #aaa; font-size: {_fs(13)}px; background-color: transparent;")
        voice_layout.addWidget(self.voice_tts_label)
        self.voice_last_label = QLabel("最近查询: --")
        self.voice_last_label.setWordWrap(True)
        self.voice_last_label.setStyleSheet(f"color: #ccc; font-size: {_fs(13)}px; background-color: transparent;")
        voice_layout.addWidget(self.voice_last_label)
        self.voice_response_label = QLabel("回复: --")
        self.voice_response_label.setWordWrap(True)
        self.voice_response_label.setStyleSheet(f"color: #4ade80; font-size: {_fs(13)}px; background-color: transparent;")
        voice_layout.addWidget(self.voice_response_label)
        self.voice_status_group.setLayout(voice_layout)
        layout.addWidget(self.voice_status_group)

        self.damage_group = QWidget()
        self.damage_group.setStyleSheet("background-color: transparent;")
        dmg_layout = QVBoxLayout()
        dmg_layout.setSpacing(2)
        self.damage_title = QLabel("⚔️ 伤害分析")
        self.damage_title.setFont(_ff('Microsoft YaHei', 13, QFont.Bold))
        self.damage_title.setStyleSheet("color: #e74c3c; background-color: transparent;")
        dmg_layout.addWidget(self.damage_title)
        self.damage_dps_label = QLabel("DPS: --")
        self.damage_dps_label.setStyleSheet(f"color: #ff6b35; font-size: {_fs(16)}px; font-weight: bold; background-color: transparent;")
        dmg_layout.addWidget(self.damage_dps_label)
        self.damage_crit_label = QLabel("暴击率: --")
        self.damage_crit_label.setStyleSheet(f"color: #f1c40f; font-size: {_fs(13)}px; background-color: transparent;")
        dmg_layout.addWidget(self.damage_crit_label)
        self.damage_tier_label = QLabel("评级: --")
        self.damage_tier_label.setStyleSheet(f"color: #aaa; font-size: {_fs(13)}px; background-color: transparent;")
        dmg_layout.addWidget(self.damage_tier_label)
        self.damage_skill_label = QLabel("主力技能: --")
        self.damage_skill_label.setStyleSheet(f"color: #4ade80; font-size: {_fs(13)}px; background-color: transparent;")
        dmg_layout.addWidget(self.damage_skill_label)
        self.damage_advice_label = QLabel("建议: --")
        self.damage_advice_label.setWordWrap(True)
        self.damage_advice_label.setStyleSheet(f"color: #ccc; font-size: {_fs(13)}px; background-color: transparent;")
        dmg_layout.addWidget(self.damage_advice_label)
        self.damage_group.setLayout(dmg_layout)
        self.damage_group.hide()
        layout.addWidget(self.damage_group)

        self.quest_group = QWidget()
        self.quest_group.setStyleSheet("background-color: transparent;")
        quest_layout = QVBoxLayout()
        quest_layout.setSpacing(2)
        self.quest_title = QLabel("当前任务")
        self.quest_title.setFont(_ff('Microsoft YaHei', 13, QFont.Bold))
        self.quest_title.setStyleSheet("color: #ffd700; background-color: transparent;")
        quest_layout.addWidget(self.quest_title)
        self.quest_content = QTextEdit()
        self.quest_content.setReadOnly(True)
        self.quest_content.setMaximumHeight(80)
        self.quest_content.setStyleSheet(f"background-color: rgba(0,0,0,0.3); color: #e0e0e0; border: none; font-size: {_fs(16)}px;")
        quest_layout.addWidget(self.quest_content)
        self.quest_group.setLayout(quest_layout)
        layout.addWidget(self.quest_group)

        self.boss_group = QWidget()
        self.boss_group.setStyleSheet("background-color: transparent;")
        boss_layout = QVBoxLayout()
        boss_layout.setSpacing(2)
        self.boss_title = QLabel("BOSS信息")
        self.boss_title.setFont(_ff('Microsoft YaHei', 13, QFont.Bold))
        self.boss_title.setStyleSheet("color: #ff6b35; background-color: transparent;")
        boss_layout.addWidget(self.boss_title)
        self.boss_content = QTextEdit()
        self.boss_content.setReadOnly(True)
        self.boss_content.setMaximumHeight(80)
        self.boss_content.setStyleSheet(f"background-color: rgba(0,0,0,0.3); color: #e0e0e0; border: none; font-size: {_fs(16)}px;")
        boss_layout.addWidget(self.boss_content)
        self.boss_group.setLayout(boss_layout)
        layout.addWidget(self.boss_group)

        self.recommend_group = QWidget()
        self.recommend_group.setStyleSheet("background-color: transparent;")
        recommend_layout = QVBoxLayout()
        recommend_layout.setSpacing(2)
        self.recommend_title = QLabel("推荐建议")
        self.recommend_title.setFont(_ff('Microsoft YaHei', 13, QFont.Bold))
        self.recommend_title.setStyleSheet("color: #4ade80; background-color: transparent;")
        recommend_layout.addWidget(self.recommend_title)
        self.recommend_content = QTextEdit()
        self.recommend_content.setReadOnly(True)
        self.recommend_content.setMaximumHeight(200)
        self.recommend_content.setStyleSheet(f"background-color: rgba(0,0,0,0.3); color: #e0e0e0; border: none; font-size: {_fs(13)}px;")
        recommend_layout.addWidget(self.recommend_content)
        self.recommend_group.setLayout(recommend_layout)
        layout.addWidget(self.recommend_group)

        self.setLayout(layout)

    def update_guide(self, analysis):
        """更新指引内容"""
        if not isinstance(analysis, dict):
            return

        ocr_engine = analysis.get('ocr_engine', 'simulation')
        ocr_text = analysis.get('ocr_text', '') or analysis.get('screen_text', '')
        scene_info = analysis.get('scene_info', [])
        scene_context = analysis.get('scene_context', '')
        knowledge_answer = analysis.get('knowledge_answer', '')

        if 'sdk' in ocr_engine and 'ocr' in ocr_engine:
            self.ocr_engine_label.setText(f"引擎: {ocr_engine}")
            self.ocr_engine_label.setStyleSheet("color: #4ade80; background-color: transparent;")
        elif 'sdk' in ocr_engine:
            self.ocr_engine_label.setText("引擎: SDK (Intel)")
            self.ocr_engine_label.setStyleSheet("color: #4ade80; background-color: transparent;")
        elif ocr_engine and ocr_engine != 'simulation':
            self.ocr_engine_label.setText(f"引擎: {ocr_engine}")
            self.ocr_engine_label.setStyleSheet("color: #4ade80; background-color: transparent;")
        else:
            self.ocr_engine_label.setText("引擎: 模拟模式")
            self.ocr_engine_label.setStyleSheet("color: #ff6b35; background-color: transparent;")

        if ocr_text:
            display_text = ocr_text[:80] + ('...' if len(ocr_text) > 80 else '')
            self.ocr_text_label.setText(f"OCR: {display_text}")
        else:
            self.ocr_text_label.setText("OCR: (无文字)")

        if scene_info:
            scene_parts = []
            for s in scene_info[:3]:
                sid = s.get('scene_id', '')
                score = s.get('score', 0)
                scene_parts.append(f"{sid}({score:.0%})")
            self.vision_scene_label.setText(f"场景: {', '.join(scene_parts)}")
            self.vision_scene_label.setStyleSheet(f"color: #9b59b6; font-size: {_fs(13)}px; background-color: transparent;")
        elif scene_context:
            self.vision_scene_label.setText(f"场景: {scene_context[:60]}")
            self.vision_scene_label.setStyleSheet(f"color: #9b59b6; font-size: {_fs(13)}px; background-color: transparent;")
        else:
            self.vision_scene_label.setText("场景: 未识别")
            self.vision_scene_label.setStyleSheet(f"color: #666; font-size: {_fs(13)}px; background-color: transparent;")

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
            self.damage_tier_label.setStyleSheet(f"color: {color}; font-size: {_fs(16)}px; font-weight: bold;")

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

    def __init__(self, use_web_data=False, use_ocr=True, ocr_engine=None, stt_engine='google', tts_engine='auto'):
        super().__init__()
        self.detector = GameDetector(use_web_data=use_web_data, use_ocr=use_ocr, ocr_engine=ocr_engine)
        self.stt_engine = stt_engine
        self.tts_engine = tts_engine

        self.voice_assistant = None
        self.voice_worker = None
        self.is_voice_listening = False

        self.overlay_panel = None
        self.overlay_visible = False
        self.skill_webview = None          # 内嵌技能Tab的d2core构筑网页器(lazy)
        self._skill_web_class = None       # 内嵌webview当前已加载的职业(防重复reload)

        self.hotkey_manager = None

        self.damage_monitor = None
        self.is_damage_monitoring = False

        self.current_scene_category = SceneCategory.UNKNOWN
        self.scene_vision_worker = None
        self.scene_query_path = None

        # 职业推荐系统
        self.current_class = None  # 当前角色职业 (D4Class)
        self.class_builds_cache = {}  # 职业BD缓存 {D4Class: [ClassBuildGuide]}
        self._class_locked_by_user = False  # 用户是否手动锁定了职业

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
        self._start_scene_vision_worker()

    def init_ui(self):
        self.setWindowTitle("暗黑破坏神游戏助手")
        win_w = int(560 * SCREEN_SCALE)
        win_h = int(820 * SCREEN_SCALE)
        self.setGeometry(100, 100, win_w, win_h)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        self.setWindowOpacity(0.85)
        self.setAttribute(Qt.WA_TranslucentBackground)

        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: rgba(20, 20, 40, 200);")
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(4)

        header = QWidget()
        header.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setSpacing(8)

        self.title_label = QLabel("暗黑破坏神助手")
        self.title_label.setFont(_ff('Microsoft YaHei', 16, QFont.Bold))
        self.title_label.setStyleSheet("color: #ff6b35; background-color: transparent;")
        header_layout.addWidget(self.title_label)

        engine_label = self.detector._get_engine_label()
        ocr_color = '#4ade80' if 'simulation' not in engine_label else '#ff6b35'
        self.ocr_indicator = QLabel(f"引擎: {engine_label}")
        self.ocr_indicator.setFont(_ff('Microsoft YaHei', 11))
        self.ocr_indicator.setStyleSheet(f"color: {ocr_color}; background-color: transparent;")
        header_layout.addWidget(self.ocr_indicator)

        voice_status = self.voice_assistant.get_status() if self.voice_assistant else {}
        stt = voice_status.get('stt_engine', 'none')
        tts = voice_status.get('tts_engine', 'none')
        voice_color = '#9b59b6' if (stt != 'none' or tts != 'none') else '#666'
        self.voice_indicator = QLabel(f"Voice: {stt}/{tts}")
        self.voice_indicator.setFont(_ff('Microsoft YaHei', 10))
        self.voice_indicator.setStyleSheet(f"color: {voice_color}; background-color: transparent;")
        header_layout.addWidget(self.voice_indicator)

        hotkey_color = '#e67e22' if HOTKEY_AVAILABLE else '#666'
        self.hotkey_indicator = QLabel("⌨" if HOTKEY_AVAILABLE else "")
        self.hotkey_indicator.setFont(_ff('Microsoft YaHei', 11))
        self.hotkey_indicator.setStyleSheet(f"color: {hotkey_color}; background-color: transparent;")
        self.hotkey_indicator.setToolTip(self._get_hotkey_tooltip() if HOTKEY_AVAILABLE else "")
        header_layout.addWidget(self.hotkey_indicator)

        self.sdk_indicator = QLabel("SDK")
        self.sdk_indicator.setFont(_ff('Microsoft YaHei', 11))
        if self.detector.sdk_available:
            self.sdk_indicator.setStyleSheet("color: #4ade80; font-weight: bold; background-color: transparent;")
        else:
            self.sdk_indicator.setStyleSheet("color: #666; background-color: transparent;")
        header_layout.addWidget(self.sdk_indicator)

        header_layout.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(int(24 * SCREEN_SCALE), int(24 * SCREEN_SCALE))
        self.close_btn.setStyleSheet(f"color: #ff6b35; background: transparent; border: none; font-size: {_fs(16)}px;")
        self.close_btn.clicked.connect(self.close)
        header_layout.addWidget(self.close_btn)

        # 让 header 上的所有 QLabel 对鼠标事件透明(包括后面 insertWidget 加进来的 scene_info_label)
        # 这样点击 header 空白区域 / 标签文字时,事件能传到 header 控件本身,
        # 由事件过滤器接管实现窗口拖动(close_btn 仍能正常点击)
        for child in header.findChildren(QLabel):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        # header 作为窗口拖动手柄
        self._drag_handle = header
        header.installEventFilter(self)
        header.setMouseTracking(True)

        layout.addWidget(header)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: rgba(139,0,0,0.5);")
        layout.addWidget(line)

        # === 保留创建但不加入布局的控件（其他方法仍会引用这些对象）===
        # 搜索控件（通过菜单触发搜索）
        search_widget = QWidget()
        search_widget.setStyleSheet("background-color: transparent;")
        search_layout = QHBoxLayout(search_widget)
        search_layout.setSpacing(4)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索游戏内容...")
        self.search_input.setStyleSheet(
            "background-color: rgba(0,0,0,0.3); color: #e0e0e0; border: 1px solid rgba(68,68,68,0.5); "
            "border-radius: 3px; padding: 4px 8px; font-size: {_fs(16)}px;"
        )
        self.search_input.returnPressed.connect(self.manual_search)
        search_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("搜索")
        self.search_btn.setStyleSheet(
            "background-color: rgba(0,102,204,0.7); color: white; border: none; "
            "border-radius: 3px; padding: 4px 10px; font-size: {_fs(16)}px;"
        )
        self.search_btn.clicked.connect(self.manual_search)
        search_layout.addWidget(self.search_btn)
        # search_widget 不加入布局，搜索通过菜单触发

        # 场景信息标签放到 header 右侧（替代原来单独的 scene_status_widget 行）
        self.scene_info_label = QLabel("当前场景: -- (识别中...)")
        self.scene_info_label.setFont(_ff('Microsoft YaHei', 10))
        self.scene_info_label.setStyleSheet("color: #9b59b6; background-color: transparent;")
        # 同样对鼠标事件透明,避免拦截 header 拖动
        self.scene_info_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        header_layout.insertWidget(header_layout.indexOf(self.close_btn), self.scene_info_label)

        # 自动切Tab复选框（保留为 QCheckBox，其他代码用 isChecked()；通过菜单 action 同步状态）
        self.auto_switch_check = QCheckBox("自动切Tab")
        self.auto_switch_check.setChecked(True)
        self.auto_switch_check.setFont(_ff('Microsoft YaHei', 9))
        self.auto_switch_check.setStyleSheet("color: #ccc; background-color: transparent;")

        # 场景识别按钮（保留创建，不加入布局）
        self.scene_refresh_btn = QPushButton("识别")
        self.scene_refresh_btn.setStyleSheet(
            "background-color: #0066cc; color: white; border: none; "
            f"border-radius: 3px; padding: 3px 8px; font-size: {_fs(10)}px;"
        )
        self.scene_refresh_btn.clicked.connect(self._manual_scene_detect)

        # 控制按钮（保留创建，不加入布局）
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setStyleSheet(
            "background-color: #8b0000; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
        )
        self.pause_btn.clicked.connect(self.toggle_pause)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setStyleSheet(
            "background-color: #0066cc; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
        )
        self.refresh_btn.clicked.connect(self.manual_refresh)

        self.ocr_toggle_btn = QPushButton("OCR: 开")
        self.ocr_toggle_btn.setStyleSheet(
            "background-color: #2d5a27; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
        )
        self.ocr_toggle_btn.clicked.connect(self.toggle_ocr)

        # 语音按钮（保留创建，不加入布局）
        self.voice_listen_btn = QPushButton("🎤 语音输入")
        self.voice_listen_btn.setStyleSheet(
            "background-color: #9b59b6; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
        )
        self.voice_listen_btn.clicked.connect(self.toggle_voice_listening)

        self.voice_speak_btn = QPushButton("🔊 朗读结果")
        self.voice_speak_btn.setStyleSheet(
            "background-color: #2d5a27; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
        )
        self.voice_speak_btn.clicked.connect(self.speak_current_result)

        self.voice_stop_btn = QPushButton("⏹ 停止朗读")
        self.voice_stop_btn.setStyleSheet(
            "background-color: #666; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
        )
        self.voice_stop_btn.clicked.connect(self.stop_speaking)

        # 叠加层按钮（保留创建，不加入布局）
        self.overlay_toggle_btn = QPushButton("📋 叠加层")
        self.overlay_toggle_btn.setStyleSheet(
            "background-color: #e67e22; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
        )
        self.overlay_toggle_btn.clicked.connect(self.toggle_overlay)

        self.overlay_equip_btn = QPushButton("⚔️ 装备")
        self.overlay_equip_btn.setStyleSheet(
            "background-color: #2c3e50; color: #bf642f; border: 1px solid #bf642f; "
            "border-radius: 3px; padding: 4px 8px; font-size: {_fs(13)}px;"
        )
        self.overlay_equip_btn.clicked.connect(lambda: self._show_overlay_tab(0))

        self.overlay_skill_btn = QPushButton("🔮 技能")
        self.overlay_skill_btn.setStyleSheet(
            "background-color: #2c3e50; color: #4ade80; border: 1px solid #4ade80; "
            "border-radius: 3px; padding: 4px 8px; font-size: {_fs(13)}px;"
        )
        self.overlay_skill_btn.clicked.connect(lambda: self._show_overlay_tab(1))

        self.overlay_paragon_btn = QPushButton("🌟 巅峰")
        self.overlay_paragon_btn.setStyleSheet(
            "background-color: #2c3e50; color: #f1c40f; border: 1px solid #f1c40f; "
            "border-radius: 3px; padding: 4px 8px; font-size: {_fs(13)}px;"
        )
        self.overlay_paragon_btn.clicked.connect(lambda: self._show_overlay_tab(2))

        self.overlay_merc_btn = QPushButton("🗡️ 雇佣")
        self.overlay_merc_btn.setStyleSheet(
            "background-color: #2c3e50; color: #9b59b6; border: 1px solid #9b59b6; "
            "border-radius: 3px; padding: 4px 8px; font-size: {_fs(13)}px;"
        )
        self.overlay_merc_btn.clicked.connect(lambda: self._show_overlay_tab(3))

        # 伤害监控按钮（保留创建，不加入布局）
        self.damage_monitor_btn = QPushButton("⚔️ 伤害监控")
        self.damage_monitor_btn.setStyleSheet(
            "background-color: #c0392b; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
        )
        self.damage_monitor_btn.clicked.connect(self.toggle_damage_monitor)

        self.damage_reset_btn = QPushButton("🔄 重置")
        self.damage_reset_btn.setStyleSheet(
            "background-color: #2c3e50; color: #e74c3c; border: 1px solid #e74c3c; "
            "border-radius: 3px; padding: 4px 8px; font-size: {_fs(13)}px;"
        )
        self.damage_reset_btn.clicked.connect(self.reset_damage_stats)

        self.damage_feed_btn = QPushButton("📝 输入日志")
        self.damage_feed_btn.setStyleSheet(
            "background-color: #2c3e50; color: #f39c12; border: 1px solid #f39c12; "
            "border-radius: 3px; padding: 4px 8px; font-size: {_fs(13)}px;"
        )
        self.damage_feed_btn.clicked.connect(self._feed_damage_log)

        # guide_widget 保留创建（其他代码可能引用），不加入布局
        self.guide_widget = GuideWidget()

        # === 菜单栏（替代底部所有按钮行）===
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: rgba(20, 20, 40, 200);
                color: #ccc;
                border-bottom: 1px solid rgba(139, 0, 0, 0.4);
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 12px;
            }
            QMenuBar::item:selected {
                background-color: rgba(139, 0, 0, 0.6);
                color: #fff;
            }
            QMenu {
                background-color: rgba(30, 30, 50, 240);
                color: #ccc;
                border: 1px solid rgba(139, 0, 0, 0.4);
            }
            QMenu::item:selected {
                background-color: rgba(139, 0, 0, 0.6);
                color: #fff;
            }
        """)

        # 场景菜单
        menu_scene = menubar.addMenu("场景")
        self._auto_switch_action = QAction("自动切Tab", self)
        self._auto_switch_action.setCheckable(True)
        self._auto_switch_action.setChecked(self.auto_switch_check.isChecked())
        self._auto_switch_action.triggered.connect(
            lambda: self.auto_switch_check.setChecked(self._auto_switch_action.isChecked())
        )
        menu_scene.addAction(self._auto_switch_action)
        menu_scene.addAction("手动识别", self._manual_scene_detect)

        # 控制菜单
        menu_control = menubar.addMenu("控制")
        self._pause_action = QAction("暂停/继续", self)
        self._pause_action.triggered.connect(self.toggle_pause)
        menu_control.addAction(self._pause_action)
        menu_control.addAction("刷新", self.manual_refresh)
        self._ocr_action = QAction("OCR: 开", self)
        self._ocr_action.triggered.connect(self.toggle_ocr)
        menu_control.addAction(self._ocr_action)

        # 语音菜单
        menu_voice = menubar.addMenu("语音")
        menu_voice.addAction("语音输入", self.toggle_voice_listening)
        menu_voice.addAction("朗读结果", self.speak_current_result)
        menu_voice.addAction("停止朗读", self.stop_speaking)

        # 叠加层菜单
        menu_overlay = menubar.addMenu("叠加层")
        menu_overlay.addAction("叠加层开关", self.toggle_overlay)
        menu_overlay.addAction("装备", lambda: self._show_overlay_tab(0))
        menu_overlay.addAction("技能", lambda: self._show_overlay_tab(1))
        menu_overlay.addAction("巅峰", lambda: self._show_overlay_tab(2))
        menu_overlay.addAction("雇佣", lambda: self._show_overlay_tab(3))

        # 伤害菜单
        menu_damage = menubar.addMenu("伤害")
        menu_damage.addAction("伤害监控", self.toggle_damage_monitor)
        menu_damage.addAction("重置", self.reset_damage_stats)
        menu_damage.addAction("输入日志", self._feed_damage_log)

        # 搜索菜单
        menu_search = menubar.addMenu("搜索")
        search_action = menu_search.addAction("🔍 搜索游戏内容")
        search_action.triggered.connect(self._menu_search)

        # 攻略菜单(游民星空图文攻略)
        menu_guide = menubar.addMenu("攻略")
        # 支线任务子菜单(按区域)
        menu_side = menu_guide.addMenu("📋 支线任务")
        for name in SIDE_QUESTS:
            menu_side.addAction(name, lambda n=name: self._load_quest_guide(n))
        # 主线/DLC子菜单
        menu_main = menu_guide.addMenu("⚔ 主线/DLC")
        for name in MAIN_QUESTS:
            menu_main.addAction(name, lambda n=name: self._load_quest_guide(n))
        # 新手指南子菜单
        menu_beginner = menu_guide.addMenu("🎓 新手指南")
        for name in BEGINNER_GUIDES:
            menu_beginner.addAction(name, lambda n=name: self._load_quest_guide(n))
        # 赛季攻略子菜单
        menu_season = menu_guide.addMenu("🏆 赛季攻略")
        for name in SEASON_GUIDES:
            menu_season.addAction(name, lambda n=name: self._load_quest_guide(n))
        menu_guide.addSeparator()
        menu_guide.addAction("🔍 搜索攻略", self._menu_search_guide)
        menu_guide.addAction("🏠 攻略首页", lambda: self._load_quest_guide_url(GAMERSKY_D4_HOME))
        menu_guide.addAction("◀ 后退", self._guide_go_back)
        menu_guide.addAction("▶ 前进", self._guide_go_forward)

        # === Tabs（保留创建所有 tab 内容，隐藏 Tab 栏，最大化展示区域）===
        self.tabs = QTabWidget()
        self.tabs.setFont(_ff('Microsoft YaHei', 10, QFont.Bold))
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(139, 0, 0, 0.4);
                background-color: rgba(0, 0, 0, 0.3);
            }
            QTabBar::tab {
                background-color: rgba(40, 40, 50, 0.8);
                color: #aaa;
                padding: 6px 10px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 50px;
            }
            QTabBar::tab:selected {
                background-color: rgba(139, 0, 0, 0.6);
                color: #fff;
            }
            QTabBar::tab:!selected:hover {
                background-color: rgba(60, 60, 70, 0.8);
            }
        """)
        self._create_scene_tabs()
        self.tabs.tabBar().hide()
        layout.addWidget(self.tabs, 1)

        # 默认显示攻略 Tab(index=5),并预加载攻略网页
        if self.tabs.count() > 5:
            self.tabs.setCurrentIndex(5)
            self._ensure_guide_webview()

        self.dragging = False
        self.drag_position = None

    def _menu_search(self):
        """通过菜单触发搜索弹窗"""
        text, ok = QInputDialog.getText(self, "搜索", "输入搜索内容:")
        if ok and text:
            self.search_input.setText(text)
            self.manual_search()

    # ============ 任务图文攻略相关方法 ============

    def _ensure_guide_webview(self):
        """懒加载攻略网页组件。首次调用时创建并替换占位符。"""
        if self._guide_webview is not None:
            return self._guide_webview
        if not QUEST_GUIDE_AVAILABLE or QuestGuideWebView is None:
            logger.warning("QuestGuideWebView 模块不可用")
            return None
        # 移除占位符
        if self._guide_web_placeholder is not None:
            self._guide_web_placeholder.setParent(None)
            self._guide_web_placeholder.deleteLater()
            self._guide_web_placeholder = None
        # 创建嵌入式攻略网页
        self._guide_webview = QuestGuideWebView(self.tab_guide)
        # 找到 guide_layout 并添加(布局在 _create_scene_tabs 里创建)
        layout = self.tab_guide.layout()
        if layout is not None:
            layout.addWidget(self._guide_webview, 1)
        logger.info("QuestGuideWebView 已创建")
        return self._guide_webview

    def _switch_to_guide_tab(self):
        """切换到攻略 Tab(index=5)"""
        if self.tabs.count() > 5:
            self.tabs.setCurrentIndex(5)

    def _load_quest_guide(self, name):
        """按名称加载攻略并切换到攻略 Tab"""
        wv = self._ensure_guide_webview()
        if wv is None:
            QMessageBox.warning(self, "不可用", "攻略网页组件不可用,请检查 PyQtWebEngine 安装")
            return
        ok = wv.load_guide(name)
        if ok:
            self.guide_top_bar.setText(f"📖 攻略: {name}")
            self._switch_to_guide_tab()
        else:
            QMessageBox.warning(self, "未找到", f"找不到攻略: {name}")

    def _load_quest_guide_url(self, url):
        """按 URL 加载攻略并切换到攻略 Tab"""
        wv = self._ensure_guide_webview()
        if wv is None:
            QMessageBox.warning(self, "不可用", "攻略网页组件不可用,请检查 PyQtWebEngine 安装")
            return
        wv.load_url(url)
        self.guide_top_bar.setText("📖 攻略: 游民星空")
        self._switch_to_guide_tab()

    def _menu_search_guide(self):
        """通过菜单搜索攻略弹窗"""
        text, ok = QInputDialog.getText(self, "搜索攻略", "输入任务名/区域名/关键词:")
        if not ok or not text:
            return
        wv = self._ensure_guide_webview()
        if wv is None:
            QMessageBox.warning(self, "不可用", "攻略网页组件不可用")
            return
        results = search_guide(text)
        if results:
            name, info = results[0]
            wv.load_url(info['url'])
            self.guide_top_bar.setText(f"📖 攻略: {name}")
            self._switch_to_guide_tab()
            if len(results) > 1:
                QMessageBox.information(
                    self, "找到多个匹配",
                    f"共 {len(results)} 个匹配,已加载第一个:\n{name}\n\n其他匹配: " +
                    "、".join(n for n, _ in results[1:5])
                )
        else:
            QMessageBox.information(self, "无结果", f"未找到匹配 '{text}' 的攻略\n已加载专区首页")
            wv.go_home()
            self._switch_to_guide_tab()

    def _guide_go_back(self):
        """攻略网页后退"""
        if self._guide_webview is not None:
            self._guide_webview.go_back()

    def _guide_go_forward(self):
        """攻略网页前进"""
        if self._guide_webview is not None:
            self._guide_webview.go_forward()

    def _create_scene_tabs(self):
        """创建场景 Tab：战斗 / 装备 / 技能 / 地图"""

        def make_textedit(placeholder, color):
            te = QTextEdit()
            te.setReadOnly(True)
            te.setStyleSheet(
                f"background-color: rgba(0,0,0,0.3); color: #e0e0e0; border: none; "
                f"font-size: {_fs(12)}px;"
            )
            te.setPlainText(placeholder)
            return te

        # ============== Tab 0: 战斗 ==============
        self.tab_combat = QWidget()
        combat_layout = QVBoxLayout(self.tab_combat)
        combat_layout.setContentsMargins(4, 4, 4, 4)
        # 顶部：当前职业信息
        self.combat_class_bar = QLabel("⚔ 职业: 等待识别")
        self.combat_class_bar.setStyleSheet(
            "color: #fff; background-color: rgba(231,76,60,0.3); "
            "padding: 6px; font-weight: bold; font-size: 13px; "
            "border-radius: 4px;"
        )
        combat_layout.addWidget(self.combat_class_bar)
        # BD推荐
        self.combat_info = make_textedit(
            "⚔ 战斗信息\n\n"
            "• 当前怪物信息\n"
            "• BOSS 攻略\n"
            "• DPS 统计\n"
            "• 战斗建议\n\n"
            "请先在右上角选择职业...",
            '#e74c3c',
        )
        combat_layout.addWidget(self.combat_info)
        self.tabs.addTab(self.tab_combat, "⚔ 战斗")

        # ============== Tab 1: 装备 ==============
        self.tab_equipment = QWidget()
        equip_layout = QVBoxLayout(self.tab_equipment)
        equip_layout.setContentsMargins(4, 4, 4, 4)
        # 职业选择下拉框
        equip_class_row = QHBoxLayout()
        equip_class_label = QLabel("🛡 当前职业:")
        equip_class_label.setStyleSheet("color: #fff; font-weight: bold; font-size: 12px;")
        self.equip_class_combo = QComboBox()
        self.equip_class_combo.setStyleSheet(
            "QComboBox { background-color: rgba(255,255,255,0.1); color: #fff; "
            "padding: 4px 8px; border: 1px solid #555; border-radius: 3px; }"
            "QComboBox::drop-down { border: none; }"
        )
        self.equip_class_combo.addItem("❓ 自动识别", None)
        for cls in D4Class:
            info = CLASS_NAMES[cls]
            self.equip_class_combo.addItem(f"{info['icon']} {info['zh']}", cls)
        self.equip_class_combo.currentIndexChanged.connect(self._on_class_changed)
        equip_class_row.addWidget(equip_class_label)
        equip_class_row.addWidget(self.equip_class_combo, 1)
        equip_class_row.addStretch()
        equip_layout.addLayout(equip_class_row)
        # 装备推荐显示
        self.equip_info = make_textedit(
            "🛡 装备/物品\n\n"
            "• 物品词条说明\n"
            "• 装备对比建议\n"
            "• Code of Power 推荐\n"
            "• 装备精工/强化建议\n\n"
            "请先选择职业...",
            '#ff6b35',
        )
        equip_layout.addWidget(self.equip_info)
        self.tabs.addTab(self.tab_equipment, "🛡 装备")

        # ============== Tab 2: 技能 ==============
        self.tab_skill = QWidget()
        skill_layout = QVBoxLayout(self.tab_skill)
        skill_layout.setContentsMargins(4, 4, 4, 4)
        # 职业显示栏
        self.skill_class_bar = QLabel("🔮 职业: 等待识别")
        self.skill_class_bar.setStyleSheet(
            "color: #fff; background-color: rgba(155,89,182,0.3); "
            "padding: 6px; font-weight: bold; font-size: 13px; "
            "border-radius: 4px;"
        )
        skill_layout.addWidget(self.skill_class_bar)
        # BD选择 + 刷新按钮
        skill_bd_row = QHBoxLayout()
        skill_bd_label = QLabel("📋 推荐BD:")
        skill_bd_label.setStyleSheet("color: #fff; font-weight: bold; font-size: 12px;")
        self.skill_bd_combo = QComboBox()
        self.skill_bd_combo.setStyleSheet(
            "QComboBox { background-color: rgba(255,255,255,0.1); color: #fff; "
            "padding: 4px 8px; border: 1px solid #555; border-radius: 3px; }"
        )
        self.skill_bd_combo.currentIndexChanged.connect(self._on_bd_changed)
        self.skill_refresh_btn = QPushButton("🔄 刷新推荐")
        self.skill_refresh_btn.setStyleSheet(
            "QPushButton { background-color: rgba(155,89,182,0.5); color: #fff; "
            "border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; }"
            "QPushButton:hover { background-color: rgba(155,89,182,0.8); }"
        )
        self.skill_refresh_btn.clicked.connect(self._refresh_build_images)
        skill_bd_row.addWidget(skill_bd_label)
        skill_bd_row.addWidget(self.skill_bd_combo, 1)
        skill_bd_row.addWidget(self.skill_refresh_btn)
        skill_layout.addLayout(skill_bd_row)
        # 旧的截图区控件保留(隐藏),避免大量旧引用报错;实际用内嵌网页构筑器
        self.skill_scroll = QScrollArea()
        self.skill_scroll.setWidgetResizable(True)
        self.skill_content = QWidget()
        self.skill_content_layout = QVBoxLayout(self.skill_content)
        self.skill_text = QLabel("请先选择职业和BD...")
        self.skill_text.setWordWrap(True)
        self.skill_content_layout.addWidget(self.skill_text)
        self.skill_content_layout.addStretch()
        self.skill_scroll.setWidget(self.skill_content)
        self.skill_scroll.hide()   # 不显示,改用内嵌网页

        # 内嵌 d2core 构筑网页器容器(webview lazy 创建后插入)
        self.skill_web_container = QWidget()
        self.skill_web_layout = QVBoxLayout(self.skill_web_container)
        self.skill_web_layout.setContentsMargins(0, 0, 0, 0)
        self._skill_web_placeholder = QLabel("识别职业后将自动加载暗黑核构筑器…")
        self._skill_web_placeholder.setStyleSheet("color: #999; padding: 20px; font-size: 12px;")
        self._skill_web_placeholder.setAlignment(Qt.AlignCenter)
        self.skill_web_layout.addWidget(self._skill_web_placeholder)
        skill_layout.addWidget(self.skill_web_container, 1)
        self.tabs.addTab(self.tab_skill, "🔮 技能")

        # ============== Tab 2.5: 巅峰（Paragon Board）==============
        self.tab_peak = QWidget()
        peak_layout = QVBoxLayout(self.tab_peak)
        peak_layout.setContentsMargins(4, 4, 4, 4)
        # 职业显示栏
        self.peak_class_bar = QLabel("🏆 职业: 等待识别")
        self.peak_class_bar.setStyleSheet(
            "color: #000; background-color: rgba(241,196,15,0.3); "
            "padding: 6px; font-weight: bold; font-size: 13px; "
            "border-radius: 4px;"
        )
        peak_layout.addWidget(self.peak_class_bar)
        # BD选择 + 刷新按钮
        peak_bd_row = QHBoxLayout()
        peak_bd_label = QLabel("📋 推荐BD:")
        peak_bd_label.setStyleSheet("color: #fff; font-weight: bold; font-size: 12px;")
        self.peak_bd_combo = QComboBox()
        self.peak_bd_combo.setStyleSheet(
            "QComboBox { background-color: rgba(255,255,255,0.1); color: #fff; "
            "padding: 4px 8px; border: 1px solid #555; border-radius: 3px; }"
        )
        self.peak_bd_combo.currentIndexChanged.connect(self._on_peak_bd_changed)
        self.peak_refresh_btn = QPushButton("🔄 刷新推荐")
        self.peak_refresh_btn.setStyleSheet(
            "QPushButton { background-color: rgba(241,196,15,0.5); color: #000; "
            "border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; font-weight: bold; }"
            "QPushButton:hover { background-color: rgba(241,196,15,0.8); }"
        )
        self.peak_refresh_btn.clicked.connect(self._refresh_build_images)
        peak_bd_row.addWidget(peak_bd_label)
        peak_bd_row.addWidget(self.peak_bd_combo, 1)
        peak_bd_row.addWidget(self.peak_refresh_btn)
        peak_layout.addLayout(peak_bd_row)
        # 巅峰盘/雕文推荐内容（嵌入图片）
        self.peak_scroll = QScrollArea()
        self.peak_scroll.setWidgetResizable(True)
        self.peak_scroll.setStyleSheet("background-color: rgba(0,0,0,0.3); border: none;")
        self.peak_content = QWidget()
        self.peak_content_layout = QVBoxLayout(self.peak_content)
        self.peak_content_layout.setContentsMargins(8, 8, 8, 8)
        self.peak_text = QLabel(
            "🏆 巅峰盘 / 雕文推荐\n\n"
            "• 根据当前职业自动加载网上推荐的巅峰盘加点图\n"
            "• 显示各雕文放置位置和加点路线\n\n"
            "请先选择职业和BD..."
        )
        self.peak_text.setStyleSheet("color: #e0e0e0; font-size: 12px;")
        self.peak_text.setWordWrap(True)
        self.peak_content_layout.addWidget(self.peak_text)
        self.peak_content_layout.addStretch()
        self.peak_scroll.setWidget(self.peak_content)
        peak_layout.addWidget(self.peak_scroll)
        self.tabs.addTab(self.tab_peak, "🏆 巅峰")

        # ============== Tab 3: 地图 ==============
        self.tab_map = QWidget()
        map_layout = QVBoxLayout(self.tab_map)
        map_layout.setContentsMargins(4, 4, 4, 4)
        # 职业显示
        self.map_class_bar = QLabel("🗺 职业: 等待识别")
        self.map_class_bar.setStyleSheet(
            "color: #fff; background-color: rgba(52,152,219,0.3); "
            "padding: 6px; font-weight: bold; font-size: 13px; "
            "border-radius: 4px;"
        )
        map_layout.addWidget(self.map_class_bar)
        self.map_info = make_textedit(
            "🗺 地图/任务\n\n"
            "• 当前位置\n"
            "• 任务追踪\n"
            "• 地下城推荐\n"
            "• BOSS 召唤时间表\n\n"
            "等待 Vision 识别地图场景...",
            '#3498db',
        )
        map_layout.addWidget(self.map_info)
        self.tabs.addTab(self.tab_map, "🗺 地图")

        # ============== Tab 5: 攻略（游民星空图文攻略）==============
        self.tab_guide = QWidget()
        guide_layout = QVBoxLayout(self.tab_guide)
        guide_layout.setContentsMargins(0, 0, 0, 0)
        guide_layout.setSpacing(0)
        # 攻略顶部信息栏
        self.guide_top_bar = QLabel("📖 任务图文攻略 - 游民星空")
        self.guide_top_bar.setStyleSheet(
            "color: #ff6b35; background-color: rgba(20,20,40,200); "
            "padding: 4px 8px; font-weight: bold; font-size: 12px; "
            "border-bottom: 1px solid rgba(139,0,0,0.4);"
        )
        guide_layout.addWidget(self.guide_top_bar)
        # 嵌入式攻略网页(lazy 创建)
        self._guide_webview = None
        self._guide_web_placeholder = QLabel(
            "📖 任务图文攻略\n\n"
            "通过菜单「攻略」选择分类:\n"
            "  • 支线任务(按区域)\n"
            "  • 主线/DLC流程\n"
            "  • 新手指南\n"
            "  • 赛季攻略\n\n"
            "或通过菜单「搜索」输入任务名查找"
        )
        self._guide_web_placeholder.setAlignment(Qt.AlignCenter)
        self._guide_web_placeholder.setStyleSheet(
            "color: #999; padding: 40px; font-size: 13px; "
            "background-color: rgba(0,0,0,0.3);"
        )
        guide_layout.addWidget(self._guide_web_placeholder, 1)
        self.tabs.addTab(self.tab_guide, "📖 攻略")

    def _start_scene_vision_worker(self):
        """启动后台 Vision 场景识别（5秒/次）

        新设计：worker 只做定时器，实际截图+Vision 查询放在主线程 _do_scene_detect()
        避免多线程 dxcam 实例冲突导致死机。
        """
        if not self.detector or not self.detector.sdk_available:
            self.scene_info_label.setText("当前场景: SDK未连接")
            return

        self.scene_vision_worker = SceneVisionWorker(interval=5.0)
        self.scene_vision_worker.request_detect.connect(self._do_scene_detect)
        self.scene_vision_worker.start()
        logger.info("SceneVisionWorker 启动完成")

    def _orb_template_match(self, frame):
        """
        ORB 模板匹配（SDK NPU 兜底）

        D4 动态游戏画面用 SDK NPU 不稳定（细节哈希/embedding 敏感）
        改用 OpenCV ORB 特征点匹配，对画面内容变化更鲁棒

        Args:
            frame: 已缩放到 1920 宽的 BGR 画面

        Returns:
            列表 [{'scene_id', 'picture_id', 'score', 'mode': 'orb'}]
        """
        import cv2
        import os
        if frame is None or frame.size == 0:
            return []
        templates = [
            ('my_equipment', 'my_equipment_pic', 'game_screenshots/my_equipment_realtime2.png'),
            ('my_paragon', 'my_paragon_pic', 'game_screenshots/my_paragon_realtime.png'),
            ('my_skill', 'my_skill_pic', 'game_screenshots/my_skill_realtime.png'),
            ('my_map', 'my_map_pic', 'game_screenshots/my_map_realtime.png'),
        ]
        orb = cv2.ORB_create(nfeatures=2000)
        kp_curr, des_curr = orb.detectAndCompute(frame, None)
        if des_curr is None:
            return []
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        scores = []
        for scene_id, pic_id, tpl_path in templates:
            if not os.path.exists(tpl_path):
                continue
            tpl = cv2.imread(tpl_path)
            if tpl is None:
                continue
            kp_tpl, des_tpl = orb.detectAndCompute(tpl, None)
            if des_tpl is None:
                continue
            matches = bf.match(des_tpl, des_curr)
            if not matches:
                continue
            good = [m for m in matches if m.distance < 50]
            score = len(good) / max(len(matches), 1)
            logger.info(
                f'ORB {scene_id}: total={len(matches)} good={len(good)} score={score:.3f}'
            )
            scores.append((score, scene_id, pic_id, len(good)))

        if not scores:
            return []

        # 按得分排序(高→低)
        scores.sort(key=lambda x: x[0], reverse=True)
        top = scores[0]

        # 过滤条件1: 最高分必须 > 0.55 且 good match >= 30
        if top[0] <= 0.55 or top[3] < 30:
            logger.info(
                f'ORB 兜底: 最高分 {top[0]:.3f} (good={top[3]}) 未达阈值(>0.55, good>=30),不返回'
            )
            return []

        # 过滤条件2: 最高分和次高分差距必须 > 0.12(避免相似界面误判)
        if len(scores) > 1:
            second = scores[1]
            gap = top[0] - second[0]
            if gap < 0.12:
                logger.info(
                    f'ORB 兜底: 最高分 {top[0]:.3f}({top[1]}) 与次高分 {second[0]:.3f}({second[1]}) '
                    f'差距 {gap:.3f} < 0.12, 无法可靠区分,不返回'
                )
                return []

        return [{
            'scene_id': top[1],
            'picture_id': top[2],
            'score': top[0],
            'mode': 'orb',
        }]

    def _do_scene_detect(self):
        """主线程执行一次场景检测（截图+缩放+Vision 查询）

        截图流程：
        1. 优先用 sc._dxcam（已绑定游戏所在显示器2，region 修复后能截 3440x1440）
        2. 回退到 mss 截取游戏所在显示器
        3. 缩放到 1920 宽度 → Vision 查询
        """
        if not self.detector or not self.detector.sdk_available:
            return

        try:
            import cv2
            import os

            sc = self.detector.screen_capture
            mon = sc.game_monitor
            frame = None

            # 方式1: 使用 sc._dxcam（绑定到游戏所在显示器，修复后能截完整 3440x1440）
            if sc._dxcam is not None:
                try:
                    raw = sc._dxcam.grab()
                    if raw is None:
                        raw = sc._dxcam.get_frame()
                    if raw is not None and raw.size > 0:
                        frame = raw
                        logger.info(f"[Vision] dxcam 截图: shape={frame.shape}, mean={frame.mean():.1f}")
                except Exception as e:
                    logger.debug(f"dxcam 截图失败: {e}")

            # 方式2: mss 截取游戏所在显示器（包含其他窗口可能遮挡的内容）
            if frame is None and mon:
                try:
                    import mss
                    import numpy as np
                    with mss.MSS() as sct:
                        sct_img = sct.grab(mon)
                        frame = np.array(sct_img)
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    logger.info(f"[Vision] mss 截图: shape={frame.shape}, mean={frame.mean():.1f}")
                except Exception as e:
                    logger.debug(f"mss 截图失败: {e}")

            # 方式3: 回退到 ScreenCapture 自带方法
            if frame is None or frame.size == 0:
                frame = sc.capture_full_screen(max_size=0)
                if frame is not None:
                    logger.info(f"[Vision] capture_full_screen: shape={frame.shape}")

            if frame is None or frame.size == 0:
                logger.info("Vision 检测: 截图失败（可能游戏窗口未找到）")
                return

            # 保存原始分辨率 frame 供 QuestOCR 使用(缩放后中文文字会模糊,OCR 识别效果差)
            original_frame = frame

            # 2. 缩放到 1920 宽度（保持宽高比），实测 1920 宽度匹配得分 0.999+
            VISION_TARGET_WIDTH = 1920
            h, w = frame.shape[:2]
            if w > VISION_TARGET_WIDTH:
                scale = VISION_TARGET_WIDTH / w
                frame = cv2.resize(
                    frame, (VISION_TARGET_WIDTH, int(h * scale)),
                    interpolation=cv2.INTER_AREA,
                )

            # 3. 保存临时文件供 Vision 查询
            tmp_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'game_screenshots', '_scene_query_temp.png'
            )
            os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
            cv2.imwrite(tmp_path, frame)

            # 4. Vision 查询（优先 accurate 模式，因为索引是用 accurate 建的）
            # threshold=-1 不限，topk=5 返回多候选以便 client 端二次过滤
            results = []
            try:
                results = self.detector.sdk.vision_query(
                    self.detector.instance_id,
                    tmp_path,
                    topk=5,
                    threshold=-1,
                    threshold_2=-1,
                    mode='accurate',
                )
                if not results:
                    results = self.detector.sdk.vision_query(
                        self.detector.instance_id,
                        tmp_path,
                        topk=5,
                        threshold=-1,
                        threshold_2=-1,
                        mode='basic',
                    )
            except Exception as ve:
                # Vision 查询异常(instance 未 build/服务不可用),走 ORB 兜底
                logger.warning(f"[Vision] SDK查询异常,走ORB兜底: {ve}")
                results = []
            logger.info(f"[Vision] SDK查询结果: {results[:3] if results else '空'}")
            if not results:
                # 兜底：ORB 模板匹配（更适合 D4 动态画面）
                results = self._orb_template_match(frame)
                logger.info(f"[Vision] ORB兜底结果: {results[:3] if results else '空'}")
            if not results:
                # 调试：查询失败时保存截图，便于排查截到的内容是什么
                import time as _t
                debug_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    'game_screenshots',
                    f'_debug_no_match_{int(_t.time())}.png',
                )
                cv2.imwrite(debug_path, frame)
                logger.info(f"[Vision] 调试截图已保存: {debug_path}")
                logger.info("Vision 查询: 无匹配结果")
                self.scene_info_label.setText("当前场景: -- (未识别)")
                self.scene_info_label.setStyleSheet("color: #aaa; background-color: transparent;")

                # 场景未识别 -> 隐藏窗口到后台(不干扰玩家游戏)
                self.current_scene_category = SceneCategory.UNKNOWN
                self._switch_to_category(SceneCategory.UNKNOWN)
                return

            # 5. 选择得分最高且 >= 0.3 的匹配
            for top in results:
                scene_id = top.get('scene_id', '')
                score = top.get('score', 0)
                if score >= 0.3:
                    picture_id = top.get('picture_id', '')
                    category = classify_scene(scene_id)
                    logger.info(
                        f"✓ Vision: {scene_id} ({score*100:.0f}%) -> {category.value}"
                    )
                    self._on_scene_detected({
                        'scene_id': scene_id,
                        'picture_id': picture_id,
                        'score': score,
                        'category': category,
                    })
                    return

            logger.info("Vision 查询: 匹配得分均 < 0.3")
            self.scene_info_label.setText("当前场景: -- (未识别)")
            self.scene_info_label.setStyleSheet("color: #aaa; background-color: transparent;")
            # 场景未识别 -> 隐藏窗口到后台(不干扰玩家游戏)
            self.current_scene_category = SceneCategory.UNKNOWN
            self._switch_to_category(SceneCategory.UNKNOWN)

        except Exception as e:
            logger.error(f"Vision 主线程检测异常: {e}")

    def _try_ocr_quest_guide(self, frame):
        """OCR 识别游戏右侧任务追踪面板的任务名,匹配到攻略则自动加载

        D4 右侧任务追踪面板位置(MCP 实测 2560x1600):
          x=2200 y=380 w=320 h=130 (任务名在上部,描述在下部)
          比例: x=86% y=24% w=12.5% h=8%
        适当扩大边距确保完整覆盖不同任务文本
        """
        if not self.detector or not self.detector.ocr_available:
            return
        try:
            import cv2
            import time as _t
            # 节流:10 秒内不重复 OCR(避免频繁识别)
            if _t.time() - getattr(self, '_last_quest_ocr_time', 0) < 10:
                return
            self._last_quest_ocr_time = _t.time()

            h, w = frame.shape[:2]
            # 右侧任务追踪面板区域(按比例,MCP 实测 2560x1600)
            # 实测: x=2200-2520 y=380-510 (含任务名+描述)
            # 比例: x=86%-98% y=24%-32%,适当扩大边距
            x1 = int(w * 0.84)
            y1 = int(h * 0.22)
            x2 = int(w * 0.99)
            y2 = int(h * 0.36)
            quest_region = frame[y1:y2, x1:x2]
            if quest_region.size == 0:
                return

            logger.info(f"[QuestOCR] 开始识别右侧任务面板,区域 shape={quest_region.shape}")

            # OCR 识别:尝试多种预处理,取识别到文字的那个
            text = ''
            for preprocess in ['dark', 'high_contrast', 'auto']:
                try:
                    t = self.detector.ocr.extract_text(quest_region, preprocess=preprocess)
                    t = t.strip()
                    if t and len(t) >= 2:
                        text = t
                        logger.info(f"[QuestOCR] preprocess={preprocess} 识别到文字: '{text}'")
                        break
                    else:
                        logger.info(f"[QuestOCR] preprocess={preprocess} 无有效文字: '{t}'")
                except Exception as oe:
                    logger.warning(f"[QuestOCR] preprocess={preprocess} 异常: {oe}")

            text = text.strip()
            logger.info(f"[QuestOCR] 最终识别文字: '{text}'")

            if not text or len(text) < 2:
                return

            # 匹配攻略关键词
            from quest_guide_config import search_guide
            results = search_guide(text)
            if results:
                name, info = results[0]
                # 避免重复加载同一个攻略
                last_loaded = getattr(self, '_last_loaded_quest', None)
                if last_loaded == name:
                    return
                self._last_loaded_quest = name
                logger.info(f"[QuestOCR] 任务 '{text}' 匹配攻略: {name}")
                # 自动加载攻略(不切换 Tab,只在攻略顶部栏提示)
                wv = self._ensure_guide_webview()
                if wv is not None:
                    wv.load_url(info['url'])
                    self.guide_top_bar.setText(
                        f"📖 攻略: {name} (任务识别: {text[:20]})"
                    )
                    self.guide_top_bar.setStyleSheet(
                        "color: #4ade80; background-color: rgba(20,40,20,200); "
                        "padding: 4px 8px; font-weight: bold; font-size: 12px; "
                        "border-bottom: 1px solid rgba(0,139,0,0.4);"
                    )
            else:
                logger.info(f"[QuestOCR] 文字 '{text}' 未匹配到攻略库,调用在线搜索+LLM汇总")
                # 避免重复在线搜索同样的文字
                last_online = getattr(self, '_last_online_search', None)
                if last_online == text:
                    return
                self._last_online_search = text
                # 游民星空攻略库未匹配,启动后台 Bing 搜索 + 智谱 GLM 汇总
                wv = self._ensure_guide_webview()
                if wv is not None:
                    wv.search_online(text)
                    # 显示"搜索中"状态(橙色),搜索完成后由定时器更新为结果
                    self.guide_top_bar.setText(
                        f"🔍 搜索中: {text[:20]} (Bing + GLM 汇总中...)"
                    )
                    self.guide_top_bar.setStyleSheet(
                        "color: #ffa500; background-color: rgba(50,35,15,200); "
                        "padding: 4px 8px; font-weight: bold; font-size: 12px; "
                        "border-bottom: 1px solid rgba(200,120,0,0.4);"
                    )
                    # 启动定时器检查搜索结果(每 1.5 秒检查一次,最多 20 秒)
                    self._check_online_result_text = text
                    self._online_check_count = 0
                    if not hasattr(self, '_online_check_timer'):
                        from PyQt5.QtCore import QTimer as _QTimer
                        self._online_check_timer = _QTimer()
                        self._online_check_timer.timeout.connect(
                            self._check_online_search_result
                        )
                    self._online_check_timer.start(1500)
        except Exception as e:
            logger.warning(f"QuestOCR 异常: {e}", exc_info=True)

    def _check_online_search_result(self):
        """定时检查在线搜索结果,更新顶部栏提示"""
        self._online_check_count += 1
        # 超时(20 秒)则停止检查
        if self._online_check_count > 14:
            self._online_check_timer.stop()
            return

        wv = getattr(self, '_guide_webview', None)
        if wv is None:
            self._online_check_timer.stop()
            return

        # 检查 webview 是否已加载新 URL(搜索完成的标志)
        summary = getattr(wv, '_online_summary', None)
        title = getattr(wv, '_online_title', None)
        text = getattr(self, '_check_online_result_text', '')

        if summary is not None and title is not None:
            # 搜索完成,显示 LLM 汇总结果(蓝色)
            self.guide_top_bar.setText(
                f"🔍 LLM 汇总: {title[:30]} | {summary[:30]} (任务: {text[:15]})"
            )
            self.guide_top_bar.setStyleSheet(
                "color: #00bfff; background-color: rgba(20,30,50,200); "
                "padding: 4px 8px; font-weight: bold; font-size: 12px; "
                "border-bottom: 1px solid rgba(0,100,200,0.4);"
            )
            self._online_check_timer.stop()
            # 清除标记,避免下次误判
            wv._online_summary = None
            wv._online_title = None

    def _on_scene_detected(self, result):
        """Vision 场景识别结果回调"""
        category = result['category']
        scene_id = result['scene_id']
        score = result['score']

        display_name = get_category_display_name(category)
        color = get_category_color(category)
        score_pct = f"{score * 100:.0f}%"

        self.scene_info_label.setText(
            f"场景: {scene_id} | {display_name} ({score_pct})"
        )
        self.scene_info_label.setStyleSheet(f"color: {color}; background-color: transparent;")

        if self.auto_switch_check.isChecked() and category != self.current_scene_category:
            logger.info(f"自动切换条件满足: checked={self.auto_switch_check.isChecked()}, category变化={category.value} != {self.current_scene_category.value}")
            self._switch_to_category(category)

        self.current_scene_category = category

        # 装备/技能/巅峰界面 -> 确保技能Tab的内嵌构筑网页器已创建并加载当前职业
        # (改为内嵌,不再弹独立 WebOverlay 窗口)
        is_target_scene = category in (
            SceneCategory.EQUIPMENT, SceneCategory.SKILL, SceneCategory.PEAK,
        )
        if is_target_scene and self.current_class is not None:
            QTimer.singleShot(0, lambda: self._sync_overlay_with_class(self.current_class))

        # 触发职业 OCR 识别（仅在用户未锁定职业时）
        if not self._class_locked_by_user:
            self._trigger_class_ocr()

    def _switch_to_category(self, category):
        """切换到指定类别 Tab。装备/技能/巅峰 都映射到技能Tab(内嵌构筑网页),
        并驱动网页内部 tab 跟随游戏画面:
          装备->总览, 技能树->技能, 巅峰->巅峰
        未识别场景时隐藏窗口,不影响玩家游戏;可通过 Ctrl+Alt+H 重新显示"""
        # 未识别场景 -> 隐藏窗口(后台运行,不干扰玩家)
        if category == SceneCategory.UNKNOWN:
            if self.isVisible():
                logger.info(f"🔄 场景未识别,隐藏窗口到后台 (从 {self.current_scene_category.value})")
                self.hide()
            return

        # 其他场景 -> 确保窗口可见(从后台恢复)
        if not self.isVisible():
            self.show()
            self.activateWindow()
            logger.info(f"🔄 场景已识别,恢复窗口显示 ({category.value})")

        tab_index_map = {
            SceneCategory.COMBAT: 0,
            SceneCategory.EQUIPMENT: 2,
            SceneCategory.SKILL: 2,
            SceneCategory.PEAK: 2,
            SceneCategory.MAP: 4,
        }
        index = tab_index_map.get(category, 0)
        logger.info(f"🔄 Tab 切换: {self.current_scene_category.value} -> {category.value} (index={index})")
        self.tabs.setCurrentIndex(index)

        # 游戏画面在装备/技能树/巅峰界面 -> 网页内部自动切到对应tab
        inner_tab_map = {
            SceneCategory.EQUIPMENT: 'overview',
            SceneCategory.SKILL: 'skill',
            SceneCategory.PEAK: 'peak',
        }
        if category in inner_tab_map:
            wv = self._ensure_skill_webview()
            if wv is not None:
                wv.switch_inner_tab(inner_tab_map[category])

        # 地图场景:切换到攻略Tab并触发 QuestOCR 自动匹配任务攻略
        if category == SceneCategory.MAP:
            # 切到攻略 Tab(index 5)
            self.tabs.setCurrentIndex(5)
            self.guide_top_bar.setText("📖 任务图文攻略 - 识别到地图场景")
            self.guide_top_bar.setStyleSheet(
                "color: #4ade80; background-color: rgba(20,20,40,200); "
                "padding: 4px 8px; font-weight: bold; font-size: 12px; "
                "border-bottom: 1px solid rgba(139,0,0,0.4);"
            )
            # 地图场景触发 QuestOCR:识别右侧任务面板,自动加载攻略
            # 从 detector 获取最新帧
            if self.detector and hasattr(self.detector, '_cached_img'):
                frame = self.detector._cached_img
                if frame is not None and frame.size > 0:
                    logger.info("🗺️ 地图场景:触发 QuestOCR 识别任务面板")
                    self._try_ocr_quest_guide(frame)
        else:
            self.guide_top_bar.setText("📖 任务图文攻略 - 游民星空")
            self.guide_top_bar.setStyleSheet(
                "color: #ff6b35; background-color: rgba(20,20,40,200); "
                "padding: 4px 8px; font-weight: bold; font-size: 12px; "
                "border-bottom: 1px solid rgba(139,0,0,0.4);"
            )

        color = get_category_color(category)
        self.tabs.tabBar().setStyleSheet(
            f"QTabBar::tab:selected {{ background-color: {color}; color: #fff; font-weight: bold; }}"
        )

    def _manual_scene_detect(self):
        """手动触发场景识别（直接在主线程执行）"""
        self._do_scene_detect()

    def _on_class_changed(self, index):
        """用户从下拉框选择职业"""
        cls = self.equip_class_combo.currentData()
        if cls is None:
            self._class_locked_by_user = False
            self.current_class = None
            logger.info("职业选择: 切回自动识别模式")
        else:
            self._class_locked_by_user = True
            self.current_class = cls
            logger.info(f"职业选择: 用户手动选择 {get_class_display_name(cls)}")
        self._refresh_class_info()
        # 同步刷新 WebOverlay（如果已打开）—— 用户手动切职业时也自动换推荐
        if isinstance(self.overlay_panel, WebOverlay) and self.current_class is not None:
            self.overlay_panel.refresh_builds_for_class(self.current_class)
            if self.overlay_visible:
                self.overlay_panel.load_class_recommendation(self.current_class)

    def _on_bd_changed(self, index):
        """用户选择具体BD"""
        if index < 0:
            return
        bd_index = self.skill_bd_combo.currentData()
        if bd_index is None or self.current_class is None:
            return
        builds = self.class_builds_cache.get(self.current_class, [])
        if 0 <= bd_index < len(builds):
            self._show_build_images(builds[bd_index])

    def _on_peak_bd_changed(self, index):
        """用户选择巅峰Tab的具体BD：仅显示该BD的 paragon 巅峰图"""
        if index < 0:
            return
        bd_index = self.peak_bd_combo.currentData()
        if bd_index is None or self.current_class is None:
            return
        builds = self.class_builds_cache.get(self.current_class, [])
        if 0 <= bd_index < len(builds):
            self._show_peak_images(builds[bd_index])

    def _refresh_class_info(self):
        """刷新所有Tab中的职业信息显示"""
        if self.current_class is None:
            text = '❓ 等待识别职业...'
            color = '#888'
        else:
            text = f"{get_class_icon(self.current_class)} 职业: {get_class_display_name(self.current_class)}"
            color = get_class_color(self.current_class)

        if hasattr(self, 'combat_class_bar'):
            self.combat_class_bar.setText(text)
            self.combat_class_bar.setStyleSheet(
                f"color: #fff; background-color: {color}33; "
                f"padding: 6px; font-weight: bold; font-size: 13px; "
                f"border-radius: 4px;"
            )
        if hasattr(self, 'skill_class_bar'):
            self.skill_class_bar.setText(text)
            self.skill_class_bar.setStyleSheet(
                f"color: #fff; background-color: {color}33; "
                f"padding: 6px; font-weight: bold; font-size: 13px; "
                f"border-radius: 4px;"
            )
        if hasattr(self, 'peak_class_bar'):
            self.peak_class_bar.setText(text)
            self.peak_class_bar.setStyleSheet(
                f"color: #000; background-color: {color}55; "
                f"padding: 6px; font-weight: bold; font-size: 13px; "
                f"border-radius: 4px;"
            )
        if hasattr(self, 'map_class_bar'):
            self.map_class_bar.setText(text)
            self.map_class_bar.setStyleSheet(
                f"color: #fff; background-color: {color}33; "
                f"padding: 6px; font-weight: bold; font-size: 13px; "
                f"border-radius: 4px;"
            )

        # 更新BD下拉框
        self._update_bd_combo()
        self._update_peak_bd_combo()

    def _update_bd_combo(self):
        """更新BD下拉框内容"""
        self.skill_bd_combo.blockSignals(True)
        self.skill_bd_combo.clear()
        self.skill_bd_combo.addItem("请选择BD...", None)
        if self.current_class:
            builds = self.class_builds_cache.get(self.current_class, [])
            # 如果还没缓存，加载
            if not builds:
                builds = DEFAULT_BUILDS.get(self.current_class, [])
                self.class_builds_cache[self.current_class] = builds
            for i, build in enumerate(builds):
                self.skill_bd_combo.addItem(
                    f"{build.build_name} ({build.season})",
                    i,
                )
        self.skill_bd_combo.blockSignals(False)
        # 识别到职业后自动选中第一个 BD 并展示构筑图(index 1 = 第一个真实BD,index 0是"请选择")
        if self.current_class and self.skill_bd_combo.count() > 1:
            self.skill_bd_combo.setCurrentIndex(1)

    def _update_peak_bd_combo(self):
        """更新巅峰Tab的BD下拉框（与技能Tab共享同一份缓存）"""
        self.peak_bd_combo.blockSignals(True)
        self.peak_bd_combo.clear()
        self.peak_bd_combo.addItem("请选择BD...", None)
        if self.current_class:
            builds = self.class_builds_cache.get(self.current_class, [])
            if not builds:
                builds = DEFAULT_BUILDS.get(self.current_class, [])
                self.class_builds_cache[self.current_class] = builds
            for i, build in enumerate(builds):
                self.peak_bd_combo.addItem(
                    f"{build.build_name} ({build.season})",
                    i,
                )
        self.peak_bd_combo.blockSignals(False)
        # 识别到职业后自动选中第一个 BD 并展示巅峰图
        if self.current_class and self.peak_bd_combo.count() > 1:
            self.peak_bd_combo.setCurrentIndex(1)

    def _popup_full_image(self, path):
        """弹出独立窗口显示构筑原图(可滚动查看大图)"""
        try:
            from PyQt5.QtWidgets import QDialog, QScrollArea, QVBoxLayout, QLabel as _QL
            if not os.path.exists(path):
                return
            dlg = QDialog(self)
            dlg.setWindowTitle("构筑大图 - 滚动查看")
            dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowStaysOnTopHint)
            dlg.resize(1000, 900)
            lay = QVBoxLayout(dlg)
            lay.setContentsMargins(0, 0, 0, 0)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            lbl = _QL()
            pm = QPixmap(path)
            # 大图按宽度960显示,高度自适应,可上下滚动
            if pm.width() > 960:
                pm = pm.scaledToWidth(960, Qt.SmoothTransformation)
            lbl.setPixmap(pm)
            scroll.setWidget(lbl)
            lay.addWidget(scroll)
            dlg.show()
            self._build_img_dialog = dlg  # 保持引用防止被GC
        except Exception as e:
            logger.debug(f"弹出大图失败: {e}")

    def _show_build_images(self, build):
        """在技能Tab中显示BD推荐图片"""
        # 清空原内容（除了 skill_text）
        while self.skill_content_layout.count() > 1:
            item = self.skill_content_layout.takeAt(0)
            if item.widget() and item.widget() != self.skill_text:
                item.widget().deleteLater()

        # 更新标题
        self.skill_text.setText(
            f"<h3 style='color:{get_class_color(self.current_class)};'>"
            f"{get_class_icon(self.current_class)} {build.build_name}</h3>"
            f"<p style='color:#aaa;'>赛季: {build.season} | 来源: {build.source_url[:50]}...</p>"
            f"<p style='color:#fff;'>📊 推荐内容:</p>"
        )

        # 嵌入图片
        if not build.image_paths:
            placeholder = QLabel(
                "📥 攻略图片未抓取\n\n"
                "点击'刷新推荐'按钮可在线抓取最新攻略..."
            )
            placeholder.setStyleSheet("color: #888; padding: 20px; font-size: 12px;")
            placeholder.setAlignment(Qt.AlignCenter)
            self.skill_content_layout.insertWidget(1, placeholder)
            return

        labels = {
            'main': '🎯 主推荐',
            'skills': '⚡ 技能加点',
            'gear': '🛡 装备词条',
            'paragon': '🏔 巅峰加点',
        }

        for key, path in build.image_paths.items():
            if not os.path.exists(path):
                continue
            # 图片标题
            title = QLabel(labels.get(key, key))
            title.setStyleSheet(
                "color: #fff; font-weight: bold; font-size: 12px; "
                "padding: 4px; background-color: rgba(155,89,182,0.3); "
                "border-radius: 3px;"
            )
            self.skill_content_layout.insertWidget(
                self.skill_content_layout.count() - 1, title
            )
            # 图片（适配窗口宽度，点击可弹出原图大窗口）
            img_label = QLabel()
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                # 按当前窗口可用宽度缩放（窗口宽 - 边距）
                target_w = max(self.width() - 60, 480)
                shown = pixmap
                if pixmap.width() > target_w:
                    shown = pixmap.scaledToWidth(target_w, Qt.SmoothTransformation)
                img_label.setPixmap(shown)
                img_label.setStyleSheet("padding: 4px; background-color: rgba(0,0,0,0.5);")
                img_label.setCursor(Qt.PointingHandCursor)
                img_label.setToolTip("点击查看大图")
                # 点击弹出原图大窗口
                img_label.mousePressEvent = (
                    lambda ev, p=path: self._popup_full_image(p)
                )
                self.skill_content_layout.insertWidget(
                    self.skill_content_layout.count() - 1, img_label
                )

    def _show_peak_images(self, build):
        """在巅峰Tab中显示该BD的巅峰/雕文推荐图片（仅 paragon 类别）"""
        # 清空原内容（除了 peak_text 和 stretch）
        while self.peak_content_layout.count() > 2:
            item = self.peak_content_layout.takeAt(0)
            if item.widget() and item.widget() != self.peak_text:
                item.widget().deleteLater()

        # 更新标题
        self.peak_text.setText(
            f"<h3 style='color:{get_class_color(self.current_class)};'>"
            f"{get_class_icon(self.current_class)} {build.build_name} - 巅峰盘</h3>"
            f"<p style='color:#aaa;'>赛季: {build.season} | 来源: {build.source_url[:50]}...</p>"
            f"<p style='color:#fff;'>📊 巅峰推荐内容:</p>"
        )

        paragon_path = build.image_paths.get('paragon')
        if not paragon_path or not os.path.exists(paragon_path):
            placeholder = QLabel(
                "📥 巅峰盘图片未抓取\n\n"
                "请先在'技能'或'巅峰'Tab点击'🔄 刷新推荐'按钮\n"
                "在线抓取该职业的最新巅峰加点图..."
            )
            placeholder.setStyleSheet("color: #888; padding: 20px; font-size: 12px;")
            placeholder.setAlignment(Qt.AlignCenter)
            self.peak_content_layout.insertWidget(1, placeholder)
            return

        # 显示巅峰图（标题 + 图片）
        title = QLabel("🏔 巅峰盘 / 雕文加点")
        title.setStyleSheet(
            "color: #000; font-weight: bold; font-size: 13px; "
            "padding: 6px; background-color: rgba(241,196,15,0.4); "
            "border-radius: 3px;"
        )
        self.peak_content_layout.insertWidget(
            self.peak_content_layout.count() - 1, title
        )

        img_label = QLabel()
        pixmap = QPixmap(paragon_path)
        if not pixmap.isNull():
            target_w = 500
            if pixmap.width() > target_w:
                pixmap = pixmap.scaledToWidth(target_w, Qt.SmoothTransformation)
            img_label.setPixmap(pixmap)
            img_label.setStyleSheet("padding: 4px; background-color: rgba(0,0,0,0.5);")
            self.peak_content_layout.insertWidget(
                self.peak_content_layout.count() - 1, img_label
            )
        else:
            err_label = QLabel(f"⚠️ 图片加载失败: {paragon_path}")
            err_label.setStyleSheet("color: #e74c3c; padding: 8px;")
            self.peak_content_layout.insertWidget(
                self.peak_content_layout.count() - 1, err_label
            )

    def _set_class_from_ocr(self, ocr_text: str):
        """从OCR文本中识别职业（仅在用户未锁定时）"""
        if self._class_locked_by_user:
            return
        new_class = detect_class_from_text(ocr_text)
        if new_class is not None and new_class != self.current_class:
            self.current_class = new_class
            logger.info(
                f"OCR 识别职业: {get_class_display_name(new_class)} "
                f"(来自文本: {ocr_text[:30]})"
            )
            # 同步下拉框
            for i in range(self.equip_class_combo.count()):
                if self.equip_class_combo.itemData(i) == new_class:
                    self.equip_class_combo.blockSignals(True)
                    self.equip_class_combo.setCurrentIndex(i)
                    self.equip_class_combo.blockSignals(False)
                    break
            self._refresh_class_info()

    def _trigger_class_ocr(self):
        """触发一次职业 OCR 识别（异步，不阻塞主线程）"""
        # 用 QTimer.singleShot 在 0ms 延迟后启动后台任务
        # 这里用 detector 已有的 OCR 能力
        QTimer.singleShot(0, self._do_class_ocr)

    def _do_class_ocr(self):
        """执行职业自动识别（多策略：图标匹配 → 右侧面板属性 OCR → 全屏关键词 OCR 兜底）"""
        logger.info("触发职业自动识别")
        try:
            import cv2
            sc = self.detector.screen_capture if self.detector else None
            if sc is None:
                return
            frame = None
            if sc._dxcam is not None:
                try:
                    raw = sc._dxcam.grab()
                    if raw is None:
                        raw = sc._dxcam.get_frame()
                    if raw is not None and raw.size > 0:
                        frame = raw
                except Exception:
                    pass
            if frame is None:
                import mss
                import numpy as np
                mon = sc.game_monitor
                if mon:
                    try:
                        with mss.MSS() as sct:
                            sct_img = sct.grab(mon)
                            frame = np.array(sct_img)
                            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    except Exception:
                        pass
            if frame is None or frame.size == 0:
                frame = sc.capture_full_screen(max_size=0)
            if frame is None or frame.size == 0:
                return

            from class_icon_detector import (
                ClassIconDetector,
                crop_right_panel,
                detect_class_from_attributes,
            )

            # ===== 策略0: 角色名 OCR → 职业映射（最可靠，本机已知角色）=====
            # 角色选择界面/游戏内若能 OCR 到已知角色名，直接定职业。
            if self.detector.ocr:
                try:
                    from class_recommender import detect_class_from_character_name
                    import cv2 as _cv2
                    _h, _w = frame.shape[:2]
                    _small = _cv2.resize(frame, (max(_w // 2, 960), max(_h // 2, 540)),
                                         interpolation=_cv2.INTER_AREA)
                    _name_text = self.detector.ocr.extract_text(_small) or ""
                    name_cls, ambiguous = detect_class_from_character_name(_name_text)
                    if name_cls is not None and not ambiguous:
                        logger.info(f"角色名映射命中 -> {name_cls.value}")
                        self._set_class_directly(name_cls, source='char_name')
                        return
                    if name_cls is not None and ambiguous:
                        logger.info(f"角色名重名命中({name_cls.value}),交由图标/属性消歧")
                except Exception as e:
                    logger.debug(f"角色名映射失败: {e}")

            # ===== 策略1: 职业图标识别（主） =====
            if not hasattr(self, '_class_icon_detector'):
                self._class_icon_detector = ClassIconDetector(
                    sdk=self.detector.sdk if self.detector.sdk_available else None,
                    instance_id=self.detector.instance_id,
                )
            cls = self._class_icon_detector.detect_class(frame)
            if cls is not None:
                source = getattr(self._class_icon_detector, 'last_detect_source', None) or 'icon'
                self._set_class_directly(cls, source=source)
                return

            # ===== 策略2: 右侧面板主属性 OCR（辅，识别力量/敏捷/智力等） =====
            if self.detector.ocr:
                right_panel = crop_right_panel(frame, ratio=0.45)
                if right_panel is not None:
                    try:
                        panel_text = self.detector.ocr.extract_text(right_panel)
                        if panel_text:
                            logger.info(f"右侧面板 OCR: {panel_text[:160]}")
                            cls = detect_class_from_attributes(panel_text)
                            if cls is not None:
                                self._set_class_directly(cls, source='attribute_ocr')
                                return
                    except Exception as e:
                        logger.debug(f"右侧面板 OCR 失败: {e}")

            # ===== 策略3: 顶部 + 全屏 OCR 兜底（识别技能/职业关键词） =====
            if self.detector.ocr:
                h, w = frame.shape[:2]
                # 3a) 顶部区域（包含标题、Tab、角色名等）
                top_region = frame[:h // 4, :]
                try:
                    top_text = self.detector.ocr.extract_text(top_region)
                    if top_text:
                        logger.info(f"顶部 OCR 文本: {top_text[:120]}")
                        cls = detect_class_from_text(top_text)
                        if cls is not None:
                            self._set_class_directly(cls, source='top_ocr')
                            return
                except Exception as e:
                    logger.debug(f"顶部 OCR 失败: {e}")
                # 3b) 中央区域（主要内容区，装备/技能描述）
                center_region = frame[h // 5: h * 4 // 5, w // 6: w * 5 // 6]
                try:
                    center_text = self.detector.ocr.extract_text(center_region)
                    if center_text:
                        logger.info(f"中央区域 OCR: {center_text[:120]}")
                        cls = detect_class_from_text(center_text)
                        if cls is not None:
                            self._set_class_directly(cls, source='center_ocr')
                            return
                except Exception as e:
                    logger.debug(f"中央区域 OCR 失败: {e}")
                # 3c) 全屏兜底（低分辨率缩放到一半，提高 OCR 速度和识别率）
                try:
                    import numpy as _np
                    small_h, small_w = max(h // 2, 540), max(w // 2, 960)
                    small = cv2.resize(frame, (small_w, small_h), interpolation=cv2.INTER_AREA)
                    full_text = self.detector.ocr.extract_text(small)
                    if full_text:
                        logger.info(f"全屏 OCR: {full_text[:200]}")
                        cls = detect_class_from_text(full_text)
                        if cls is not None:
                            self._set_class_directly(cls, source='full_ocr')
                            return
                except Exception as e:
                    logger.debug(f"全屏 OCR 失败: {e}")

            logger.info("所有职业识别策略都未命中，保持未识别状态")
        except Exception as e:
            logger.warning(f"职业自动识别失败: {e}", exc_info=True)

    def _ensure_skill_webview(self):
        """在技能Tab里 lazy 创建内嵌 d2core 构筑网页器(WebOverlay embedded模式)"""
        if self.skill_webview is not None:
            return self.skill_webview
        if not OVERLAY_AVAILABLE or WebOverlay is None:
            return None
        try:
            self.skill_webview = WebOverlay(parent=self.skill_web_container, embedded=True)
            # 移除占位提示,插入 webview
            if getattr(self, '_skill_web_placeholder', None):
                self._skill_web_placeholder.hide()
                self.skill_web_layout.removeWidget(self._skill_web_placeholder)
            self.skill_web_layout.addWidget(self.skill_webview)
            self.skill_webview.show()
            logger.info("技能Tab内嵌构筑网页器已创建")
        except Exception as e:
            logger.error(f"创建内嵌构筑网页器失败: {e}", exc_info=True)
            self.skill_webview = None
        return self.skill_webview

    def _sync_overlay_with_class(self, cls):
        """识别到职业 -> 内嵌技能Tab的构筑网页器加载对应职业构筑。
        仅在职业变化时才重载,避免反复 reload 把用户切的内部tab刷回总览。"""
        try:
            wv = self._ensure_skill_webview()
            if wv is not None and cls is not None:
                if cls != self._skill_web_class:
                    wv.refresh_builds_for_class(cls)
                    self._skill_web_class = cls
                    logger.info(f"内嵌构筑器已加载职业: {cls.value}")
                # 职业未变 -> 不重载,保留用户当前查看的内部tab
        except Exception as e:
            logger.error(f"同步内嵌构筑器失败: {e}", exc_info=True)

    def _set_class_directly(self, cls, source: str = 'unknown'):
        """根据图标/属性识别结果直接设置职业（绕过 OCR 关键词匹配）"""
        if self._class_locked_by_user:
            return
        from class_recommender import get_class_display_name
        # 职业没变,但构筑网页窗口已被关闭/隐藏 -> 重新显示(不重新加载,避免闪烁)
        if cls == self.current_class and cls is not None:
            try:
                if self.overlay_panel and not self.overlay_panel.isVisible():
                    self.overlay_panel.show_at_game_position()
                    self.overlay_visible = True
                    logger.info("构筑窗口被隐藏,已重新显示")
            except Exception:
                pass
        if cls != self.current_class:
            self.current_class = cls
            logger.info(
                f"自动识别职业: {get_class_display_name(cls)} (来源: {source})"
            )
            for i in range(self.equip_class_combo.count()):
                if self.equip_class_combo.itemData(i) == cls:
                    self.equip_class_combo.blockSignals(True)
                    self.equip_class_combo.setCurrentIndex(i)
                    self.equip_class_combo.blockSignals(False)
                    break
            self._refresh_class_info()
            # 识别到职业后自动切到"技能"Tab,让构筑图立即可见(index 2)
            try:
                self.tabs.setCurrentIndex(2)
            except Exception:
                pass
            # 同步刷新 WebOverlay（不管是否可见都加载，这样打开时立即显示对应推荐）
            self._sync_overlay_with_class(cls)

            # 自动采集技能栏模板(程序自动采集策略)
            # 当通过其他策略(角色名/OCR/右上角图标)识别到职业时,
            # 保存当前技能栏截图作为模板,供后续技能栏识别使用
            if source != 'skill_bar':
                self._auto_collect_skill_bar_template(cls)

    def _auto_collect_skill_bar_template(self, cls):
        """自动采集技能栏模板(程序自动采集策略)

        当通过其他策略识别到职业时,保存当前技能栏截图作为模板。
        后续即使其他策略失效(如切换角色后角色名变化),
        技能栏模板匹配仍能工作。
        """
        try:
            if not hasattr(self, '_class_icon_detector'):
                return
            # 从 detector 获取当前缓存帧(避免重复截屏)
            frame = None
            if self.detector and hasattr(self.detector, '_cached_img'):
                frame = self.detector._cached_img
            if frame is None or frame.size == 0:
                return
            # 节流:同一职业 60 秒内只采集一次(避免频繁写文件)
            cache_key = f'_last_skill_bar_collect_{cls.value}'
            import time as _t
            last = getattr(self, cache_key, 0)
            if _t.time() - last < 60:
                return
            self._class_icon_detector.save_skill_bar_template(frame, cls)
            setattr(self, cache_key, _t.time())
        except Exception as e:
            logger.debug(f"自动采集技能栏模板失败: {e}")

    def _refresh_build_images(self):
        """在线抓取最新BD攻略图片（异步）"""
        if not self.current_class:
            QMessageBox.information(self, "提示", "请先选择职业")
            return
        self.skill_refresh_btn.setEnabled(False)
        self.skill_refresh_btn.setText("⏳ 抓取中...")
        # 启动后台线程
        from build_guide_fetcher import BuildGuideFetcher
        self._build_fetcher_thread = BuildFetcherThread(
            BuildGuideFetcher(), self.current_class
        )
        self._build_fetcher_thread.finished_ok.connect(self._on_fetch_finished)
        self._build_fetcher_thread.start()

    def _on_fetch_finished(self, builds):
        """抓取完成回调"""
        self.skill_refresh_btn.setEnabled(True)
        self.skill_refresh_btn.setText("🔄 刷新推荐")
        if self.current_class:
            self.class_builds_cache[self.current_class] = builds
            self._update_bd_combo()
            QMessageBox.information(
                self, "完成",
                f"已抓取 {len(builds)} 个BD的图片！\n请从下拉框选择具体BD查看。"
            )

    def eventFilter(self, obj, event):
        """让 header 区域成为窗口拖动手柄。

        UI 重构后窗口被 QTabWidget + WebEngine 占满,主窗口的 mousePressEvent
        永远不会被触发。改为在 header 上安装事件过滤器,header 上的 QLabel
        都设置了 WA_TransparentForMouseEvents,所以点击 header 任意位置都能
        拖动整个窗口(close_btn 是 QPushButton,仍能正常响应点击)。
        """
        if obj is getattr(self, '_drag_handle', None):
            etype = event.type()
            if etype == event.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.dragging = True
                    self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                    event.accept()
                    return True
            elif etype == event.MouseMove:
                if self.dragging:
                    self.move(event.globalPos() - self.drag_position)
                    event.accept()
                    return True
            elif etype == event.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    self.dragging = False
                    event.accept()
                    return True
        return super().eventFilter(obj, event)

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
            if hasattr(self, "_pause_action"):
                self._pause_action.setText("▶ 继续")
            self.worker.stop()
        else:
            self.pause_btn.setText("暂停")
            if hasattr(self, "_pause_action"):
                self._pause_action.setText("⏸ 暂停/继续")
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
                "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
            )
            if hasattr(self, "_ocr_action"):
                self._ocr_action.setText("OCR: 开")
        else:
            self.ocr_toggle_btn.setText("OCR: 关")
            self.ocr_toggle_btn.setStyleSheet(
                "background-color: #666; color: white; border: none; "
                "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
            )
            if hasattr(self, "_ocr_action"):
                self._ocr_action.setText("OCR: 关")

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
                "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
            )
            return

        self.is_voice_listening = True
        self.voice_listen_btn.setText("🎤 监听中...")
        self.voice_listen_btn.setStyleSheet(
            "background-color: #c0392b; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
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
            "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
        )

        if self.voice_worker:
            self.voice_worker.stop()
            self.voice_worker = None

    def _on_voice_result(self, result):
        """处理语音识别结果"""
        self.guide_widget.update_voice_result(result)

        # 语音查询任务攻略:识别文字包含攻略/任务相关关键词时,自动搜索并切换到攻略 Tab
        text = result.get('text', '')
        if text:
            quest_keywords = [
                '攻略', '任务', '支线', '主线', 'dlc', '剧情',
                '破碎', '索格伦', '干燥', '凯吉斯坦', '哈维泽', '三神教',
                '奶牛', '地狱狂潮', '声望', '低语', '秘语',
                '新手', '入门', '快捷键', '属性', '增伤', '技能树',
                '调谐石', '协调石', '战争计划', '暗金', '套装', '魔盒',
                '创世', '编年史',
            ]
            text_lower = text.lower()
            if any(kw in text_lower for kw in quest_keywords):
                # 尝试搜索攻略
                results = search_guide(text)
                if results:
                    name, info = results[0]
                    wv = self._ensure_guide_webview()
                    if wv is not None:
                        wv.load_url(info['url'])
                        self.guide_top_bar.setText(f"📖 攻略: {name} (语音触发)")
                        self._switch_to_guide_tab()
                        logger.info(f"语音触发攻略: '{text}' → {name}")

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
            self.guide_widget.voice_stt_label.setStyleSheet(f"color: #ff6b35; font-size: {_fs(13)}px;")
            self.guide_widget.voice_tts_label.setText("播报: 不可用")
            self.guide_widget.voice_tts_label.setStyleSheet(f"color: #ff6b35; font-size: {_fs(13)}px;")
            return

        status = self.voice_assistant.get_status()
        if status['stt_available']:
            self.guide_widget.voice_stt_label.setText(f"识别: {status['stt_engine']}")
            self.guide_widget.voice_stt_label.setStyleSheet(f"color: #4ade80; font-size: {_fs(13)}px;")
        else:
            self.guide_widget.voice_stt_label.setText("识别: 不可用")
            self.guide_widget.voice_stt_label.setStyleSheet(f"color: #ff6b35; font-size: {_fs(13)}px;")

        if status['tts_available']:
            self.guide_widget.voice_tts_label.setText(f"播报: {status['tts_engine']}")
            self.guide_widget.voice_tts_label.setStyleSheet(f"color: #4ade80; font-size: {_fs(13)}px;")
        else:
            self.guide_widget.voice_tts_label.setText("播报: 不可用")
            self.guide_widget.voice_tts_label.setStyleSheet(f"color: #ff6b35; font-size: {_fs(13)}px;")

    def update_guide(self, analysis):
        """更新指引内容"""
        if not self.is_paused:
            self.guide_widget.update_guide(analysis)
            self._update_overlay_from_analysis(analysis)
            self._update_sdk_status()

    def _update_sdk_status(self):
        """更新SDK状态指示器"""
        engine_label = self.detector._get_engine_label()
        if 'simulation' not in engine_label:
            self.sdk_indicator.setStyleSheet("color: #4ade80; font-weight: bold; background-color: transparent;")
            self.ocr_indicator.setText(f"引擎: {engine_label}")
            self.ocr_indicator.setStyleSheet("color: #4ade80; background-color: transparent;")
        else:
            self.sdk_indicator.setStyleSheet("color: #666; background-color: transparent;")
            self.ocr_indicator.setText(f"引擎: {engine_label}")
            self.ocr_indicator.setStyleSheet("color: #ff6b35; background-color: transparent;")

    def _create_overlay_if_needed(self):
        """异步创建 WebOverlay（如果还没创建）
        创建完成后：
        1) 若 current_class 已知 → 直接加载该职业推荐构筑
        2) 若 current_class 未知 → 触发 OCR + 右侧面板属性识别 + 图标匹配
        3) 无论识别成功与否，都设置兜底 build
        """
        if self.overlay_panel is not None:
            return
        if WebOverlay is None:
            return
        try:
            logger.info("开始创建 WebOverlay（异步）...")
            self.overlay_panel = self._create_overlay_panel()
            logger.info("WebOverlay 创建成功")
            # 立即根据当前职业刷新 + 加载推荐
            if self.current_class is not None and isinstance(self.overlay_panel, WebOverlay):
                self._sync_overlay_with_class(self.current_class)
                logger.info(f"WebOverlay 已自动加载: {self.current_class.value}")
            else:
                # current_class 还没识别，触发一次职业识别；识别完成后 set_class_directly
                # 里会再次调用 _sync_overlay_with_class 同步 build
                logger.info("WebOverlay 已创建，current_class 尚未识别，触发职业识别")
                self._trigger_class_ocr()
                # 兜底：如果 OCR 也没识别出，就刷新到默认下拉（让至少有 build 可选）
                QTimer.singleShot(
                    3000,
                    self._ensure_overlay_has_build,
                )
        except Exception as e:
            logger.error(f"WebOverlay 创建失败: {e}")

    def _ensure_overlay_has_build(self):
        """确保 WebOverlay 至少有一组 build 可选（兜底策略）"""
        try:
            if not isinstance(self.overlay_panel, WebOverlay):
                return
            if self.current_class is not None:
                self._sync_overlay_with_class(self.current_class)
                logger.info(f"兜底: WebOverlay 已使用 {self.current_class.value} 职业")
            else:
                # 仍未识别职业，仅刷新通用下拉（让用户可以手动选）
                logger.info("兜底: WebOverlay 仍未识别职业，刷新为通用下拉")
        except Exception as e:
            logger.error(f"确保 WebOverlay 有 build 时出错: {e}")

    def _create_overlay_panel(self):
        if WebOverlay is not None:
            panel = WebOverlay(opacity=0.85)
        elif GraphicalOverlay is not None:
            panel = GraphicalOverlay(opacity=0.85)
            try:
                from screen_capture import ScreenCapture
                panel.init_capture(ScreenCapture())
            except Exception:
                panel.init_capture()
        elif OverlayPanel is not None:
            panel = OverlayPanel(opacity=0.85)
        else:
            return None
        panel.closed.connect(self._on_overlay_closed)
        return panel

    def toggle_overlay(self):
        if not OVERLAY_AVAILABLE:
            self.overlay_toggle_btn.setText("📋 不可用")
            return

        if self.overlay_visible and self.overlay_panel:
            self.overlay_panel.hide()
            self.overlay_visible = False
            self.overlay_toggle_btn.setText("📋 叠加层")
            self.overlay_toggle_btn.setStyleSheet(
                "background-color: #e67e22; color: white; border: none; "
                "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
            )
        else:
            if not self.overlay_panel:
                self.overlay_panel = self._create_overlay_panel()
            if self.overlay_panel:
                self.overlay_panel.show_at_game_position()
                self.overlay_visible = True
                self.overlay_toggle_btn.setText("📋 隐藏叠加")
                self.overlay_toggle_btn.setStyleSheet(
                    "background-color: #c0392b; color: white; border: none; "
                    "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
                )

    def _show_overlay_tab(self, tab_index):
        if not OVERLAY_AVAILABLE:
            return

        if not self.overlay_panel:
            self.overlay_panel = self._create_overlay_panel()

        if self.overlay_panel:
            if isinstance(self.overlay_panel, WebOverlay):
                # 自动加载当前职业对应的推荐构筑（无需用户手工选）
                if self.current_class is not None:
                    self.overlay_panel.refresh_builds_for_class(self.current_class)
                    self.overlay_panel.load_class_recommendation(self.current_class)
            elif isinstance(self.overlay_panel, GraphicalOverlay):
                panel_names = ['skill', 'paragon', 'equipment']
                if 0 <= tab_index < len(panel_names):
                    self.overlay_panel.show_panel(panel_names[tab_index])
            elif hasattr(self.overlay_panel, '_tab_widget'):
                self.overlay_panel._tab_widget.setCurrentIndex(tab_index)

            if not self.overlay_visible:
                self.overlay_panel.show_at_game_position()
                self.overlay_visible = True
                self.overlay_toggle_btn.setText("📋 隐藏叠加")
                self.overlay_toggle_btn.setStyleSheet(
                    "background-color: #c0392b; color: white; border: none; "
                    "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
                )

    def _on_overlay_closed(self):
        """叠加层关闭回调"""
        self.overlay_visible = False
        self.overlay_toggle_btn.setText("📋 叠加层")
        self.overlay_toggle_btn.setStyleSheet(
            "background-color: #e67e22; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
        )

    def _update_overlay_from_analysis(self, analysis):
        """从分析结果更新叠加层"""
        if not self.overlay_panel or not self.overlay_visible:
            return

        if isinstance(self.overlay_panel, WebOverlay):
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
        if isinstance(self.overlay_panel, WebOverlay):
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
            self.hotkey_indicator.setStyleSheet(f"color: #ff6b35; font-size: {_fs(16)}px;")
            QTimer.singleShot(300, lambda: self.hotkey_indicator.setStyleSheet(
                "color: #e67e22; font-size: {_fs(11)}px;"
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
            self.damage_monitor = DamageMonitor(
                content_indexer=self.detector.indexer,
            )

        self.damage_monitor.start_monitoring(callback=self._on_damage_update)
        self.is_damage_monitoring = True
        self.damage_monitor_btn.setText("⚔️ 监控中...")
        self.damage_monitor_btn.setStyleSheet(
            "background-color: #e74c3c; color: white; border: none; "
            "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
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
            "border-radius: 3px; padding: 5px 10px; font-size: {_fs(16)}px;"
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

        if isinstance(self.overlay_panel, WebOverlay):
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
        if self.scene_vision_worker:
            self.scene_vision_worker.stop()
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
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
