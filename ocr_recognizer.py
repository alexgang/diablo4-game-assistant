#!/usr/bin/env python3
"""
OCR文字识别模块 - 从游戏画面中提取文字

使用Tesseract OCR识别游戏中的文字，
实现真正的实时游戏状态检测。

如果没有安装Tesseract，会自动使用模拟模式。
"""

import cv2
import numpy as np
from PIL import Image
import os
import random


class GameOCR:
    """游戏画面OCR识别"""

    def __init__(self):
        self.custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789一-龥'
        
        # 检查 tesseract 是否可用
        self.tesseract_available = False
        try:
            import pytesseract
            import subprocess
            import os
            
            # 尝试设置Tesseract路径（Windows）
            tesseract_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                r'D:\Program Files\Tesseract-OCR\tesseract.exe',
            ]
            
            # 首先检查是否设置了路径
            found = False
            for path in tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    found = True
                    break
            
            # 尝试运行 tesseract 检查是否可用
            if found:
                subprocess.run(
                    [pytesseract.pytesseract.tesseract_cmd, '--version'],
                    capture_output=True,
                    timeout=5
                )
                self.tesseract_available = True
                print("✓ Tesseract OCR 已启用")
            else:
                raise Exception("未找到 Tesseract 可执行文件")
        except Exception as e:
            self.tesseract_available = False
            print(f"提示: Tesseract OCR 不可用 ({str(e)})，将使用模拟模式")

    def preprocess_image(self, img):
        """预处理图像以提高识别率"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        thresh = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )

        denoised = cv2.medianBlur(thresh, 3)
        return denoised

    def extract_text(self, img, region=None):
        """从图像中提取文字"""
        if not self.tesseract_available:
            # 模拟返回一些游戏相关的文字
            return self._get_simulation_text()

        try:
            import pytesseract
        except ImportError:
            return self._get_simulation_text()

        if region:
            x, y, w, h = region
            img = img[y:y+h, x:x+w]

        processed = self.preprocess_image(img)
        pil_img = Image.fromarray(processed)

        text = pytesseract.image_to_string(
            pil_img,
            lang='chi_sim+eng',
            config=self.custom_config
        )

        return text.strip()

    def _get_simulation_text(self):
        """返回模拟的游戏文字（用于演示）"""
        simulation_texts = [
            "杀死安达利尔",
            "任务：寻找凯恩之书",
            "罗格营地",
            "埋骨之地",
            "地下墓穴",
            "击败都瑞尔",
            "塔拉夏的古墓",
            "库拉斯特海港",
            "憎恨的囚牢",
            "墨菲斯托",
            "暗黑破坏神",
            "世界之石要塞",
            "巴尔"
        ]
        return random.choice(simulation_texts)

    def extract_quest_text(self, img):
        """提取任务相关文字"""
        quest_region = (100, 50, 400, 100)
        return self.extract_text(img, quest_region)

    def extract_location_text(self, img):
        """提取位置相关文字"""
        location_region = (50, 50, 200, 50)
        return self.extract_text(img, location_region)

    def extract_boss_name(self, img):
        """提取BOSS名称"""
        boss_region = (400, 300, 800, 100)
        return self.extract_text(img, boss_region)

    def full_screen_analysis(self, img):
        """全屏文字分析"""
        result = {
            'quest': self.extract_quest_text(img),
            'location': self.extract_location_text(img),
            'boss': self.extract_boss_name(img)
        }
        return result


class GameStateRecognizer:
    """游戏状态识别器 - 基于OCR"""

    def __init__(self):
        self.ocr = GameOCR()

        self.quest_keywords = {
            '安达利尔': 'andariel',
            '都瑞尔': 'duriel',
            '墨菲斯托': 'mephisto',
            '暗黑破坏神': 'diablo',
            '巴尔': 'baal',
            '迪卡凯恩': 'q1',
            '血鸟': 'q2',
            '凯恩之书': 'q3',
            '赫拉迪克': 'q5'
        }

        self.location_keywords = {
            '罗格营地': 'act1',
            '邪恶洞穴': 'act1_dungeon',
            '冰冷之原': 'act1_outside',
            '埋骨之地': 'act1_crypt',
            '修道院': 'act1_monastery',
            '鲁·高因': 'act2',
            '库拉斯特': 'act3',
            '群魔堡垒': 'act4',
            '哈洛加斯': 'act5'
        }

    def recognize_quest(self, text):
        """识别任务"""
        for keyword, quest_id in self.quest_keywords.items():
            if keyword in text:
                return quest_id
        return None

    def recognize_location(self, text):
        """识别位置"""
        for keyword, location_id in self.location_keywords.items():
            if keyword in text:
                return location_id
        return None

    def analyze_image(self, img):
        """分析游戏画面"""
        text = self.ocr.extract_text(img)

        result = {
            'raw_text': text,
            'quest': self.recognize_quest(text),
            'location': self.recognize_location(text)
        }

        return result


if __name__ == "__main__":
    print("OCR模块测试")
    print("注意：需要安装 Tesseract OCR 和 pytesseract")