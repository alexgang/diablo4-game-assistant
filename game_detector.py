#!/usr/bin/env python3
"""
游戏状态检测器 - 集成OCR和内容索引引擎

功能：
1. 屏幕捕获 -> OCR文字识别 -> 内容索引匹配
2. 检测当前任务、BOSS、位置、职业
3. 提供上下文感知的智能推荐
"""

import cv2
import numpy as np
import json
import os
import logging
import time

from screen_capture import ScreenCapture
from game_data import GameDatabase
from content_indexer import ContentIndexer

logger = logging.getLogger(__name__)


class GameDetector:
    """游戏状态检测器 - 集成OCR和内容索引引擎"""

    def __init__(self, use_web_data=False, use_ocr=True, ocr_engine=None):
        self.screen_capture = ScreenCapture()
        self.game_db = GameDatabase()
        self.current_quest = None
        self.current_boss = None
        self.current_location = None
        self.current_class = None

        web_data = None
        if use_web_data:
            cache_path = os.path.join(os.path.dirname(__file__), 'cache', 'web_data.json')
            if os.path.exists(cache_path):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    web_data = json.load(f)

        self.indexer = ContentIndexer(game_db=self.game_db, web_data=web_data)

        self.ocr_recognizer = None
        self.ocr_available = False
        if use_ocr:
            try:
                from ocr_recognizer import GameStateRecognizer
                self.ocr_recognizer = GameStateRecognizer(ocr_engine=ocr_engine)
                self.ocr_available = self.ocr_recognizer.ocr.available
                if self.ocr_available:
                    logger.info(f"OCR已启用，引擎: {self.ocr_recognizer.ocr.engine_name}")
                else:
                    logger.warning("OCR引擎不可用，使用模拟模式")
            except ImportError as e:
                logger.warning(f"OCR模块导入失败: {e}，使用模拟模式")

        self.last_ocr_text = ''
        self.last_ocr_time = 0
        self.ocr_cache_ttl = 2.0

    def get_screen_text(self):
        """
        获取当前屏幕文字 - 优先使用OCR，回退到模拟模式

        Returns:
            str: 识别出的屏幕文字
        """
        if self.ocr_available:
            try:
                img = self.screen_capture.capture_full_screen()
                ocr_result = self.ocr_recognizer.analyze_image(img)
                text = ocr_result.get('raw_text', '')

                if text and len(text.strip()) > 1:
                    self.last_ocr_text = text
                    self.last_ocr_time = time.time()
                    self._update_ocr_state(ocr_result)
                    return text

            except Exception as e:
                logger.error(f"OCR识别失败: {e}")

        return self._get_simulation_text()

    def get_screen_text_fast(self):
        """
        快速获取屏幕文字 - 使用缓存避免频繁OCR

        Returns:
            str: 识别出的屏幕文字
        """
        if time.time() - self.last_ocr_time < self.ocr_cache_ttl and self.last_ocr_text:
            return self.last_ocr_text
        return self.get_screen_text()

    def _update_ocr_state(self, ocr_result):
        """从OCR结果更新当前状态"""
        if ocr_result.get('quest'):
            self.current_quest = ocr_result['quest']
        if ocr_result.get('location'):
            self.current_location = ocr_result['location']
        if ocr_result.get('class'):
            self.current_class = ocr_result['class']

    def detect_from_screen_text(self, screen_text):
        """根据屏幕文字检测游戏状态并返回相关推荐"""
        recommendations = self.indexer.get_context_recommendations(screen_text)
        self._update_state_from_recommendations(recommendations)
        return recommendations

    def _update_state_from_recommendations(self, recommendations):
        """从推荐结果更新当前状态"""
        if recommendations['quest_hints']:
            top_quest = recommendations['quest_hints'][0]
            self.current_quest = top_quest.get('name')

        if recommendations['boss_tips']:
            top_boss = recommendations['boss_tips'][0]
            self.current_boss = top_boss.get('name')

    def detect_quest(self):
        """检测当前任务"""
        screen_text = self.get_screen_text()
        recommendations = self.detect_from_screen_text(screen_text)

        if recommendations['quest_hints']:
            quest = recommendations['quest_hints'][0]
            return {
                'name': quest['name'],
                'location': quest['location'],
                'guide': quest['guide'],
            }
        return None

    def detect_boss(self):
        """检测BOSS"""
        screen_text = self.get_screen_text()
        recommendations = self.detect_from_screen_text(screen_text)

        if recommendations['boss_tips']:
            boss = recommendations['boss_tips'][0]
            return {
                'name': boss['name'],
                'weakness': boss['weakness'],
                'skills': boss['skills'],
                'guide': boss['guide'],
            }
        return None

    def detect_location(self):
        """检测当前位置"""
        img = self.screen_capture.capture_full_screen()
        minimap_region = {'top': 0, 'left': 0, 'width': 200, 'height': 200}
        minimap_img = self.screen_capture.capture_region(minimap_region)
        avg_color = cv2.mean(minimap_img)[:3]

        if avg_color[2] > 150:
            self.current_location = "洞穴"
        elif avg_color[1] > 100:
            self.current_location = "森林"
        elif avg_color[2] > 100 and avg_color[0] > 100:
            self.current_location = "沙漠"
        else:
            self.current_location = "未知"

        return self.current_location

    def get_current_guide(self):
        """获取当前指引"""
        screen_text = self.get_screen_text_fast()
        recommendations = self.detect_from_screen_text(screen_text)

        guide = {}

        if recommendations['quest_hints']:
            guide['quest'] = recommendations['quest_hints'][0]

        if recommendations['boss_tips']:
            guide['boss'] = recommendations['boss_tips'][0]

        if recommendations['build_guides']:
            guide['build'] = recommendations['build_guides'][0]

        if recommendations['web_guides']:
            guide['web_guides'] = recommendations['web_guides']

        if recommendations['equipment_suggestions']:
            guide['equipment'] = recommendations['equipment_suggestions'][:3]

        if recommendations['boss_schedule']:
            guide['events'] = recommendations['boss_schedule']

        if recommendations['skill_info']:
            guide['skills'] = recommendations['skill_info'][:5]

        if recommendations['build_details']:
            guide['build_details'] = recommendations['build_details'][:3]

        guide['location'] = self.current_location or '未知'
        guide['ocr_text'] = self.last_ocr_text
        guide['ocr_engine'] = self.ocr_recognizer.ocr.engine_name if self.ocr_recognizer else 'none'

        return guide

    def analyze_game_state(self):
        """分析游戏状态"""
        screen_text = self.get_screen_text()
        recommendations = self.detect_from_screen_text(screen_text)

        result = {
            'status': 'analyzing',
            'screen_text': screen_text,
            'recommendations': recommendations,
            'formatted': self.indexer.format_recommendations(recommendations),
            'ocr_engine': self.ocr_recognizer.ocr.engine_name if self.ocr_recognizer else 'simulation',
        }

        return result

    def capture_and_analyze(self):
        """捕获并分析当前画面"""
        img = self.screen_capture.capture_full_screen()
        analysis = self.analyze_game_state()
        return img, analysis

    def _get_simulation_text(self):
        """模拟获取屏幕文字（OCR不可用时的回退方案）"""
        import random
        simulation_texts = [
            "杀死安达利尔 地下墓穴",
            "寻找凯恩之书 遗忘之塔",
            "击败都瑞尔 塔拉夏的古墓",
            "库拉斯特海港 墨菲斯托",
            "混沌要塞 暗黑破坏神",
            "世界之石要塞 巴尔",
            "野蛮人 旋风斩 开荒",
            "女巫 暴风雪 冰封球",
            "术士 恐惧之爪 开荒",
            "暗金 护符 德鲁伊",
        ]
        return random.choice(simulation_texts)
