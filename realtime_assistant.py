#!/usr/bin/env python3
"""
实时游戏助手 - 整合所有模块

结合屏幕捕获、OCR识别、内容索引、网站数据爬虫
实现基于游戏窗口内容的智能辅助功能

流程：屏幕捕获 -> OCR文字识别 -> 内容索引匹配 -> 智能推荐
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


class RealTimeAssistant:
    """实时游戏助手"""

    def __init__(self, use_web_data=False, use_ocr=True, ocr_engine=None):
        self.screen_capture = ScreenCapture()
        self.game_db = GameDatabase()
        self.use_web_data = use_web_data
        self.use_ocr = use_ocr

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

        self.last_ocr_text = ''
        self.last_analysis_time = 0

    def analyze_screen_content(self, screen_text=None):
        """分析屏幕内容并返回智能推荐"""
        if screen_text is None:
            screen_text = self.detector.get_screen_text()

        self.last_ocr_text = screen_text
        recommendations = self.indexer.get_context_recommendations(screen_text)

        return {
            'screen_text': screen_text,
            'recommendations': recommendations,
            'formatted': self.indexer.format_recommendations(recommendations),
            'ocr_engine': self.ocr.engine_name if self.ocr and self.ocr.available else 'simulation',
        }

    def analyze_and_report(self):
        """分析并报告当前游戏状态"""
        print("\n" + "=" * 60)
        print("  暗黑破坏神实时游戏助手 - 智能内容索引")
        print("=" * 60)

        img = self.screen_capture.capture_full_screen()
        print("✓ 屏幕捕获完成")

        if self.ocr_recognizer and self.ocr and self.ocr.available:
            ocr_result = self.ocr_recognizer.analyze_image(img)
            screen_text = ocr_result.get('raw_text', '')
            engine = ocr_result.get('engine', 'unknown')
            print(f"✓ OCR识别完成 (引擎: {engine})")
            if screen_text:
                print(f"  识别文字: {screen_text[:80]}...")
            else:
                print("  未识别到文字，使用模拟模式")
                screen_text = self.detector._get_simulation_text()
        else:
            screen_text = self.detector._get_simulation_text()
            print("✓ 模拟模式（演示用）")

        result = self.analyze_screen_content(screen_text)

        print(f"\n📝 屏幕内容: {screen_text}")
        print(f"\n{result['formatted']}")

        print("=" * 60)
        return result

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
        results = self.indexer.search(query, top_n=top_n)
        return results

    def update_web_data(self):
        """手动更新网站数据"""
        if self.spider:
            self.spider.update_local_database()
            self.web_data = self.spider.get_cached_data()
            self.indexer.reload_web_data(self.web_data)
            self.detector.indexer.reload_web_data(self.web_data)
            print("网站数据已更新")
        else:
            print("网站爬虫不可用")

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


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    print("=" * 60)
    print("    暗黑破坏神实时游戏助手")
    print("=" * 60)

    use_web = '--web' in sys.argv
    use_ocr = '--no-ocr' not in sys.argv
    ocr_engine = None

    for arg in sys.argv:
        if arg.startswith('--ocr='):
            ocr_engine = arg.split('=')[1]

    mode_parts = []
    if use_web:
        mode_parts.append("网站数据")
    mode_parts.append("本地数据库")
    mode_parts.append("内容索引")
    if use_ocr:
        mode_parts.append("OCR识别")
    else:
        mode_parts.append("模拟模式")
    print(f"模式: {' + '.join(mode_parts)}")

    assistant = RealTimeAssistant(use_web_data=use_web, use_ocr=use_ocr, ocr_engine=ocr_engine)

    ocr_status = assistant.get_ocr_status()
    if ocr_status['available']:
        print(f"OCR引擎: {ocr_status['engine']}")
    else:
        print("OCR引擎: 不可用（模拟模式）")

    if '--continuous' in sys.argv:
        assistant.continuous_monitor()
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
