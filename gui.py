#!/usr/bin/env python3
"""
暗黑破坏神游戏助手 - GUI界面

功能：
1. 实时显示OCR识别状态和结果
2. 显示任务指引、BOSS攻略、装备推荐
3. 语音交互：语音输入识别、语音播报回复
4. 支持暂停/继续、手动刷新、搜索
5. 可拖拽、置顶、半透明
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
    from voice_assistant import VoiceAssistant
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False


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

    def closeEvent(self, event):
        if hasattr(self, 'worker'):
            self.worker.stop()
        if self.voice_worker:
            self.voice_worker.stop()
        if self.voice_assistant:
            self.voice_assistant.stop_listening()
        event.accept()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
