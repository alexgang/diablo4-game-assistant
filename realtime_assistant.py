#!/usr/bin/env python3
"""
实时游戏助手 - 整合所有模块

结合屏幕捕获、OCR识别、内容索引、网站数据爬虫
实现基于游戏窗口内容的智能辅助功能
"""

import sys
import os
import json
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from screen_capture import ScreenCapture
from game_data import GameDatabase
from game_detector import GameDetector
from content_indexer import ContentIndexer

try:
    from data_spider import DiabloDataSpider
    SPIDER_AVAILABLE = True
except ImportError:
    SPIDER_AVAILABLE = False

try:
    from ocr_recognizer import GameStateRecognizer
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class RealTimeAssistant:
    """实时游戏助手"""

    def __init__(self, use_web_data=False):
        self.screen_capture = ScreenCapture()
        self.game_db = GameDatabase()
        self.use_web_data = use_web_data

        self.web_data = None
        self.spider = None
        if use_web_data and SPIDER_AVAILABLE:
            self.spider = DiabloDataSpider()
            self.web_data = self.spider.get_cached_data()
            if not self.web_data:
                self.spider.update_local_database()
                self.web_data = self.spider.get_cached_data()
            print("已启用网站数据获取模式")

        self.indexer = ContentIndexer(game_db=self.game_db, web_data=self.web_data)

        self.recognizer = None
        if OCR_AVAILABLE:
            self.recognizer = GameStateRecognizer()
            print("已启用OCR文字识别模式")

        self.detector = GameDetector(use_web_data=use_web_data)
        print("已启用内容索引引擎")

    def analyze_screen_content(self, screen_text=None):
        """分析屏幕内容并返回智能推荐"""
        if screen_text is None:
            if self.recognizer:
                img = self.screen_capture.capture_full_screen()
                ocr_result = self.recognizer.analyze_image(img)
                screen_text = ocr_result.get('raw_text', '')
            else:
                screen_text = self.detector._get_screen_text_simulation()

        recommendations = self.indexer.get_context_recommendations(screen_text)

        return {
            'screen_text': screen_text,
            'recommendations': recommendations,
            'formatted': self.indexer.format_recommendations(recommendations),
        }

    def analyze_and_report(self):
        """分析并报告当前游戏状态"""
        print("\n" + "=" * 60)
        print("  暗黑破坏神实时游戏助手 - 智能内容索引")
        print("=" * 60)

        img = self.screen_capture.capture_full_screen()
        print("✓ 屏幕捕获完成")

        if self.recognizer:
            ocr_result = self.recognizer.analyze_image(img)
            screen_text = ocr_result.get('raw_text', '')
            print(f"✓ OCR识别完成")
            print(f"  识别文字: {screen_text[:50]}...")
        else:
            screen_text = self.detector._get_screen_text_simulation()
            print(f"✓ 模拟模式（演示用）")

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


def main():
    print("=" * 60)
    print("    暗黑破坏神实时游戏助手")
    print("=" * 60)

    use_web = '--web' in sys.argv
    if use_web:
        print("模式: 网站数据 + 本地数据库 + 内容索引")
    else:
        print("模式: 本地数据库 + 内容索引")

    assistant = RealTimeAssistant(use_web_data=use_web)

    if '--continuous' in sys.argv:
        assistant.continuous_monitor()
    elif '--search' in sys.argv:
        query = ' '.join([a for a in sys.argv[2:] if a != '--search'])
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
