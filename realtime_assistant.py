#!/usr/bin/env python3
"""
实时游戏助手 - 整合所有模块

结合屏幕捕获、OCR识别、内容索引、网站数据爬虫、语音交互
实现基于游戏窗口内容的智能辅助功能

流程：
1. 屏幕捕获 -> OCR文字识别 -> 内容索引匹配 -> 智能推荐
2. 语音输入 -> 意图识别 -> 数据库搜索 -> 屏幕提示 + 语音回复
"""

import sys
import os
import json
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from screen_capture import ScreenCapture
from game_data import GameDatabase
from game_detector import GameDetector
from content_indexer import ContentIndexer

try:
    from sdk_client import GamingAssistantSDK
    from config import SDK_CONFIG
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

logger = logging.getLogger(__name__)

try:
    from data_spider import DiabloDataSpider
    SPIDER_AVAILABLE = True
except ImportError:
    SPIDER_AVAILABLE = False

try:
    from ocr_recognizer import GameOCR, GameStateRecognizer
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    from voice_assistant import VoiceAssistant
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

try:
    from overlay import OverlayPanel
    OVERLAY_AVAILABLE = True
except ImportError:
    OVERLAY_AVAILABLE = False


class RealTimeAssistant:
    """实时游戏助手"""

    def __init__(self, use_web_data=False, use_ocr=True, ocr_engine=None,
                 use_voice=True, stt_engine='google', tts_engine='auto',
                 use_sdk=True, instance_id='default'):
        self.screen_capture = ScreenCapture()
        self.game_db = GameDatabase()
        self.use_web_data = use_web_data
        self.use_ocr = use_ocr
        self.use_voice = use_voice

        self.web_data = None
        self.spider = None
        if use_web_data and SPIDER_AVAILABLE:
            self.spider = DiabloDataSpider()
            self.web_data = self.spider.get_cached_data()
            if not self.web_data:
                self.spider.update_local_database()
                self.web_data = self.spider.get_cached_data()
            logger.info("已启用网站数据获取模式")

        self.indexer = ContentIndexer(game_db=self.game_db, web_data=self.web_data)

        self.ocr = None
        self.ocr_recognizer = None
        if use_ocr and OCR_AVAILABLE:
            try:
                self.ocr_recognizer = GameStateRecognizer(ocr_engine=ocr_engine)
                self.ocr = self.ocr_recognizer.ocr
                if self.ocr.available:
                    logger.info(f"已启用OCR文字识别模式，引擎: {self.ocr.engine_name}")
                else:
                    logger.warning("OCR引擎不可用，使用模拟模式")
            except Exception as e:
                logger.warning(f"OCR初始化失败: {e}")

        self.detector = GameDetector(use_web_data=use_web_data, use_ocr=use_ocr, ocr_engine=ocr_engine)
        logger.info("已启用内容索引引擎")

        self.voice = None
        if use_voice and VOICE_AVAILABLE:
            try:
                self.voice = VoiceAssistant(
                    content_indexer=self.indexer,
                    stt_engine=stt_engine,
                    tts_engine=tts_engine,
                )
                status = self.voice.get_status()
                if status['stt_available'] or status['tts_available']:
                    logger.info(f"语音助手已启用 (识别: {status['stt_engine']}, 播报: {status['tts_engine']})")
                else:
                    logger.warning("语音引擎不可用")
            except Exception as e:
                logger.warning(f"语音助手初始化失败: {e}")

        self.last_ocr_text = ''
        self.last_analysis_time = 0
        self.last_voice_result = None

        self.overlay = None
        self.overlay_visible = False

        self.sdk = None
        self.sdk_available = False
        if use_sdk and SDK_AVAILABLE:
            try:
                sdk = GamingAssistantSDK()
                if sdk.check_server():
                    sdk.init_all(instance_id)
                    self.sdk = sdk
                    self.sdk_available = True
                    logger.info("SDK服务已启用")
                else:
                    logger.warning("SDK服务不可用，使用本地模式")
            except Exception as e:
                logger.warning(f"SDK初始化失败: {e}")

    def analyze_screen_content(self, screen_text=None):
        """分析屏幕内容并返回智能推荐"""
        if screen_text is None:
            result = self.detector.capture_and_query()
            self.last_ocr_text = result.get('ocr_text', '')
            return result

        self.last_ocr_text = screen_text
        return self.detector.analyze_game_state()

    def analyze_and_report(self):
        """分析并报告当前游戏状态"""
        print("\n" + "=" * 60)
        print("  暗黑破坏神实时游戏助手 - 智能内容索引")
        print("=" * 60)

        result = self.detector.capture_and_query()
        self.last_ocr_text = result.get('ocr_text', '')

        ocr_text = result.get('ocr_text', '')
        scene_info = result.get('scene_info', [])
        engine_label = result.get('ocr_engine', 'simulation')

        print(f"✓ 画面分析完成 (引擎: {engine_label})")
        if ocr_text:
            print(f"  OCR文字: {ocr_text[:80]}...")
        if scene_info:
            for s in scene_info[:3]:
                print(f"  场景: {s.get('scene_id', '')} (置信度: {s.get('score', 0):.0%})")

        knowledge_answer = result.get('knowledge_answer', '')
        if knowledge_answer:
            print(f"\n🤖 SDK推荐: {knowledge_answer[:200]}")

        formatted = result.get('formatted', '')
        if formatted:
            print(f"\n{formatted}")

        print("=" * 60)
        return result

    def voice_query(self, timeout=5, phrase_time_limit=10):
        """
        语音查询：听 -> 识别意图 -> 搜索 -> 回复

        Returns:
            dict: 语音查询结果
        """
        if not self.voice:
            return {
                'text': '',
                'intent': 'none',
                'query': '',
                'results': [],
                'response': '语音助手不可用',
                'spoken': False,
            }

        result = self.voice.process_voice(timeout=timeout, phrase_time_limit=phrase_time_limit)
        self.last_voice_result = result
        return result

    def text_query(self, text):
        """文字查询（可用于手动输入）"""
        if self.sdk_available:
            try:
                answer = self.sdk.knowledge_query(
                    self.detector.instance_id,
                    text,
                    knowledge_id=self.detector.knowledge_id,
                )
                if answer and answer.strip():
                    return {
                        'text': text,
                        'intent': 'sdk_query',
                        'query': text,
                        'results': [],
                        'response': answer.strip(),
                        'spoken': False,
                        'source': 'sdk',
                    }
            except Exception as e:
                logger.warning(f"SDK文字查询失败，回退到本地搜索: {e}")

        if self.voice:
            result = self.voice.process_text(text)
            self.last_voice_result = result
            return result

        results = self.indexer.search(text, top_n=5)
        return {
            'text': text,
            'intent': 'general_search',
            'query': text,
            'results': results,
            'response': self._format_text_response(results),
            'spoken': False,
        }

    def _format_text_response(self, results):
        """格式化文字查询结果"""
        if not results:
            return f'未找到相关信息'
        top = results[0]
        name = top['data'].get('name', top['data'].get('title', ''))
        return f'找到: {name}'

    def speak(self, text, blocking=False):
        """语音播报"""
        if self.voice and self.voice.voice_output.available:
            self.voice.voice_output.speak(text, blocking=blocking)

    def start_voice_listening(self, wake_word=None, callback=None):
        """启动语音持续监听"""
        if self.voice:
            self.voice.start_continuous_listening(wake_word=wake_word, callback=callback)

    def stop_voice_listening(self):
        """停止语音监听"""
        if self.voice:
            self.voice.stop_listening()

    def continuous_monitor(self, interval=5):
        """持续监控游戏状态"""
        print(f"\n开始持续监控（每 {interval} 秒更新一次）")
        print("按 Ctrl+C 停止\n")

        try:
            while True:
                self.analyze_and_report()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n监控已停止")

    def search(self, query, top_n=5):
        """手动搜索游戏内容"""
        return self.detector.search(query, top_n=top_n)

    def update_web_data(self):
        """手动更新网站数据"""
        if self.spider:
            self.spider.update_local_database()
            self.web_data = self.spider.get_cached_data()
            self.indexer.reload_web_data(self.web_data)
            self.detector.indexer.reload_web_data(self.web_data)
            if self.voice:
                self.voice.set_indexer(self.indexer)
            print("网站数据已更新")
        else:
            print("网站爬虫不可用")

    def show_overlay(self, class_name=None, build_data=None):
        """显示叠加层"""
        if not OVERLAY_AVAILABLE:
            logger.warning("叠加层模块不可用")
            return False

        if not self.overlay:
            self.overlay = OverlayPanel(opacity=0.85)

        if build_data:
            self.overlay.update_from_build(class_name, build_data)
        elif self.web_data:
            self._update_overlay_with_web_data(class_name)

        self.overlay.show_at_game_position()
        self.overlay_visible = True
        return True

    def hide_overlay(self):
        """隐藏叠加层"""
        if self.overlay:
            self.overlay.hide()
            self.overlay_visible = False

    def toggle_overlay(self):
        """切换叠加层"""
        if self.overlay_visible:
            self.hide_overlay()
        else:
            self.show_overlay()

    def update_overlay(self, class_name=None, build_data=None, equipment=None,
                       skills=None, paragon=None, mercenary=None):
        """更新叠加层内容"""
        if not self.overlay:
            return

        if build_data:
            self.overlay.update_from_build(class_name, build_data)
            return

        if equipment:
            self.overlay.update_equipment(class_name, {'equipment': equipment, 'title': '装备推荐'})
        if skills:
            self.overlay.update_skills(class_name, {'skills': skills})
        if paragon:
            self.overlay.update_paragon(class_name, paragon)
        if mercenary:
            self.overlay.update_mercenary(class_name, mercenary)

    def _update_overlay_with_web_data(self, class_name=None):
        """用网站数据更新叠加层"""
        if not self.web_data or not self.overlay:
            return

        build_details = self.web_data.get('build_details', [])
        if build_details:
            top_build = build_details[0]
            self.overlay.update_from_build(class_name, top_build)
            return

        equipment = self.web_data.get('unique_items', [])
        if equipment:
            self.overlay.update_equipment(class_name, {'equipment': equipment[:10], 'title': '装备推荐'})

        web_skills = self.web_data.get('skills', [])
        if web_skills:
            skill_names = [s.get('name', '') for s in web_skills[:15] if s.get('name')]
            self.overlay.update_skills(class_name, {'skills': skill_names})

    def get_ocr_status(self):
        """获取OCR引擎状态"""
        if self.ocr and self.ocr.available:
            return {
                'available': True,
                'engine': self.ocr.engine_name,
                'last_text': self.last_ocr_text[:100] if self.last_ocr_text else '',
            }
        return {
            'available': False,
            'engine': 'none',
            'last_text': '',
        }

    def get_voice_status(self):
        """获取语音助手状态"""
        if self.voice:
            return self.voice.get_status()
        return {
            'stt_available': False,
            'stt_engine': 'none',
            'tts_available': False,
            'tts_engine': 'none',
            'is_listening': False,
            'is_speaking': False,
            'last_query': None,
            'last_intent': None,
        }

    def get_sdk_status(self):
        """获取SDK服务状态"""
        return {
            'available': self.sdk_available,
            'server_url': SDK_CONFIG['server_url'],
        }


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    print("=" * 60)
    print("    暗黑破坏神实时游戏助手")
    print("=" * 60)

    use_web = '--web' in sys.argv
    use_ocr = '--no-ocr' not in sys.argv
    use_voice = '--no-voice' not in sys.argv
    ocr_engine = None
    stt_engine = 'google'
    tts_engine = 'auto'

    for arg in sys.argv:
        if arg.startswith('--ocr='):
            ocr_engine = arg.split('=')[1]
        elif arg.startswith('--stt='):
            stt_engine = arg.split('=')[1]
        elif arg.startswith('--tts='):
            tts_engine = arg.split('=')[1]

    mode_parts = []
    if use_web:
        mode_parts.append("网站数据")
    mode_parts.append("本地数据库")
    mode_parts.append("内容索引")
    if use_ocr:
        mode_parts.append("OCR识别")
    else:
        mode_parts.append("模拟模式")
    if use_voice:
        mode_parts.append("语音交互")
    print(f"模式: {' + '.join(mode_parts)}")

    assistant = RealTimeAssistant(
        use_web_data=use_web,
        use_ocr=use_ocr,
        ocr_engine=ocr_engine,
        use_voice=use_voice,
        stt_engine=stt_engine,
        tts_engine=tts_engine,
    )

    ocr_status = assistant.get_ocr_status()
    if ocr_status['available']:
        print(f"OCR引擎: {ocr_status['engine']}")
    else:
        print("OCR引擎: 不可用（模拟模式）")

    voice_status = assistant.get_voice_status()
    if voice_status['stt_available']:
        print(f"语音识别: {voice_status['stt_engine']}")
    else:
        print("语音识别: 不可用")
    if voice_status['tts_available']:
        print(f"语音播报: {voice_status['tts_engine']}")
    else:
        print("语音播报: 不可用")

    if '--continuous' in sys.argv:
        assistant.continuous_monitor()
    elif '--voice' in sys.argv:
        print("\n语音交互模式 - 请说话...")
        while True:
            try:
                result = assistant.voice_query()
                if result['text']:
                    print(f"\n🎤 识别: {result['text']}")
                    print(f"🎯 意图: {result['intent']} | 关键词: {result['query']}")
                    print(f"💬 回复: {result['response']}")
                    if result['results']:
                        for r in result['results'][:3]:
                            print(f"  [{r['category']}] {r['score']:.0%} - {r['data'].get('name', r['data'].get('title', ''))}")
                else:
                    print(".", end='', flush=True)
            except KeyboardInterrupt:
                print("\n语音模式已退出")
                break
    elif '--search' in sys.argv:
        query = ' '.join([a for a in sys.argv[2:] if a != '--search' and not a.startswith('--')])
        if query:
            results = assistant.search(query)
            for r in results:
                print(f"  [{r['category']}] (相关度: {r['score']:.0%}) {r['data']}")
        else:
            print("请输入搜索关键词")
    else:
        assistant.analyze_and_report()


if __name__ == "__main__":
    main()
