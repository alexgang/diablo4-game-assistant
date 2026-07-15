#!/usr/bin/env python3
"""
OCR文字识别模块 - 从游戏画面中提取文字

支持引擎：
1. EasyOCR（默认，中文识别效果最好，实测准确率最高）
2. Tesseract（备选，需额外安装 Tesseract-OCR 软件）

自动检测可用引擎，按优先级选择。
"""

import os
import re
import json
import logging
import subprocess
import tempfile
import numpy as np

logger = logging.getLogger(__name__)


class GameOCR:
    """游戏画面OCR识别 - 多引擎支持"""

    ENGINES = ['easyocr', 'tesseract']

    def __init__(self, engine=None, lang='ch', device=None):
        self.lang = lang
        self.engine_name = None
        self.engine = None
        self.tesseract_cmd = None
        self._init_engine(engine)

    def _init_engine(self, preferred_engine=None):
        # 未显式指定引擎时,优先读 config.OCR_CONFIG['engine'](用户在 config 里的选择应生效)
        if not preferred_engine:
            try:
                from config import OCR_CONFIG
                cfg_engine = OCR_CONFIG.get('engine')
            except Exception:
                cfg_engine = None
            if cfg_engine and cfg_engine in self.ENGINES:
                preferred_engine = cfg_engine

        if preferred_engine:
            # 首选指定引擎,失败时回退到其余引擎(保持可用性)
            engines_to_try = [preferred_engine] + [e for e in self.ENGINES if e != preferred_engine]
        else:
            engines_to_try = self.ENGINES
        for eng in engines_to_try:
            if eng is None:
                continue
            try:
                if eng == 'easyocr':
                    self._init_easyocr()
                elif eng == 'tesseract':
                    self._init_tesseract()
                else:
                    continue
                if self.engine is not None:
                    self.engine_name = eng
                    logger.info(f"OCR引擎已启用: {eng}")
                    return
            except Exception as e:
                logger.debug(f"OCR引擎 {eng} 初始化失败: {e}")
                continue

        logger.warning("所有OCR引擎均不可用，将使用模拟模式")

    def _init_easyocr(self):
        import easyocr
        langs = ['ch_sim', 'en'] if self.lang == 'ch' else ['en']
        self.engine = easyocr.Reader(langs, gpu=False)

    def _init_tesseract(self):
        import pytesseract
        import subprocess

        tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'D:\Program Files\Tesseract-OCR\tesseract.exe',
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
        ]

        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                self.tesseract_cmd = path
                break

        if not self.tesseract_cmd:
            try:
                result = subprocess.run(
                    ['tesseract', '--version'],
                    capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    self.tesseract_cmd = 'tesseract'
            except Exception:
                pass

        if self.tesseract_cmd:
            self.engine = pytesseract
        else:
            raise Exception("未找到 Tesseract 可执行文件")

    @property
    def available(self):
        return self.engine is not None

    def preprocess_image(self, img, mode='auto'):
        """
        预处理图像以提高OCR识别率

        Args:
            img: BGR格式的numpy数组
            mode: 预处理模式
                - 'auto': 自动选择
                - 'dark': 暗色背景（游戏常见）
                - 'light': 亮色背景
                - 'high_contrast': 高对比度
                - 'none': 不处理
        """
        if mode == 'none':
            return img

        from PIL import Image
        import cv2

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        if mode == 'auto':
            mean_val = np.mean(gray)
            if mean_val < 80:
                mode = 'dark'
            elif mean_val > 180:
                mode = 'light'
            else:
                mode = 'high_contrast'

        if mode == 'dark':
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            denoised = cv2.medianBlur(binary, 3)
            return denoised

        elif mode == 'light':
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            denoised = cv2.medianBlur(binary, 3)
            return denoised

        elif mode == 'high_contrast':
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            thresh = cv2.adaptiveThreshold(
                enhanced, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11, 2
            )
            denoised = cv2.medianBlur(thresh, 3)
            return denoised

        return gray

    def extract_text(self, img, region=None, preprocess='auto'):
        """
        从图像中提取文字

        Args:
            img: BGR格式的numpy数组
            region: (x, y, w, h) 感兴趣区域
            preprocess: 预处理模式

        Returns:
            识别出的文字字符串
        """
        if not self.available:
            return self._get_simulation_text()

        import cv2

        if region:
            x, y, w, h = region
            x, y, w, h = max(0, x), max(0, y), max(1, w), max(1, h)
            img = img[y:y + h, x:x + w]

        # easyocr 自带预处理,喂原始彩色图效果最好;
        # 外部二值化/增强预处理只对 tesseract 有益(实测 easyocr 经预处理后反而读不出)
        if self.engine_name == 'easyocr':
            processed = img
        else:
            processed = self.preprocess_image(img, mode=preprocess)

        if self.engine_name == 'easyocr':
            return self._ocr_easyocr(processed)
        elif self.engine_name == 'tesseract':
            return self._ocr_tesseract(processed)

        return ''

    def extract_text_with_confidence(self, img, region=None, preprocess='auto'):
        """
        提取文字及置信度

        Returns:
            list of {'text': str, 'confidence': float, 'bbox': list}
        """
        if not self.available:
            return [{'text': self._get_simulation_text(), 'confidence': 0.0, 'bbox': []}]

        import cv2

        if region:
            x, y, w, h = region
            img = img[y:y + h, x:x + w]

        # easyocr 自带预处理,喂原始彩色图效果最好;
        # 外部二值化/增强预处理只对 tesseract 有益(实测 easyocr 经预处理后反而读不出)
        if self.engine_name == 'easyocr':
            processed = img
        else:
            processed = self.preprocess_image(img, mode=preprocess)

        if self.engine_name == 'easyocr':
            return self._ocr_easyocr_detail(processed)
        elif self.engine_name == 'tesseract':
            return self._ocr_tesseract_detail(processed)

        return []

    def _ocr_easyocr(self, img):
        try:
            from PIL import Image
            if len(img.shape) == 2:
                pil_img = Image.fromarray(img)
            else:
                import cv2
                pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            results = self.engine.readtext(np.array(pil_img))
            texts = [r[1] for r in results if r[1]]
            return ' '.join(texts)
        except Exception as e:
            logger.error(f"EasyOCR识别失败: {e}")
            return ''

    def _ocr_easyocr_detail(self, img):
        try:
            from PIL import Image
            if len(img.shape) == 2:
                pil_img = Image.fromarray(img)
            else:
                import cv2
                pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            results = self.engine.readtext(np.array(pil_img))
            details = []
            for r in results:
                details.append({
                    'text': r[1],
                    'confidence': float(r[2]),
                    'bbox': r[0],
                })
            return details
        except Exception as e:
            logger.error(f"EasyOCR识别失败: {e}")
            return []

    def _ocr_tesseract(self, img):
        try:
            from PIL import Image
            pil_img = Image.fromarray(img)
            config = r'--oem 3 --psm 6'
            text = self.engine.image_to_string(pil_img, lang='chi_sim+eng', config=config)
            return text.strip()
        except Exception as e:
            logger.error(f"Tesseract识别失败: {e}")
            return ''

    def _ocr_tesseract_detail(self, img):
        try:
            from PIL import Image
            pil_img = Image.fromarray(img)
            config = r'--oem 3 --psm 6'
            data = self.engine.image_to_data(pil_img, lang='chi_sim+eng', config=config, output_type=self.engine.Output.DICT)
            details = []
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])
                if text and conf > 30:
                    details.append({
                        'text': text,
                        'confidence': conf / 100.0,
                        'bbox': [
                            data['left'][i], data['top'][i],
                            data['left'][i] + data['width'][i],
                            data['top'][i] + data['height'][i]
                        ],
                    })
            return details
        except Exception as e:
            logger.error(f"Tesseract识别失败: {e}")
            return []

    @staticmethod
    def postprocess_text(text):
        """
        OCR文本后处理 - 清理和规范化识别结果

        - 去除多余空白
        - 修正常见OCR错误
        - 过滤无意义片段
        """
        if not text:
            return ''

        text = re.sub(r'\s+', ' ', text).strip()

        corrections = {
            '安达利尔': ['安达利尔', '安达利爾', '安达利尔'],
            '都瑞尔': ['都瑞尔', '都瑞爾'],
            '墨菲斯托': ['墨菲斯托', '墨菲斯托'],
            '暗黑破坏神': ['暗黑破坏神', '暗黑破壞神'],
            '巴尔': ['巴尔', '巴爾'],
            '迪亚波罗': ['迪亚波罗', '迪亞波羅'],
        }
        for correct, variants in corrections.items():
            for variant in variants:
                text = text.replace(variant, correct)

        noise_patterns = [
            r'[^\u4e00-\u9fff\w\s·\-—,.;:!?()（）\[\]【】/\\|+]',
            r'\b[a-z]{1,2}\b',
        ]
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text)

        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def extract_quest_text(self, img):
        quest_region = (100, 50, 400, 100)
        text = self.extract_text(img, region=quest_region, preprocess='dark')
        return self.postprocess_text(text)

    def extract_location_text(self, img):
        location_region = (50, 50, 200, 50)
        text = self.extract_text(img, region=location_region, preprocess='dark')
        return self.postprocess_text(text)

    def extract_boss_name(self, img):
        boss_region = (400, 300, 800, 100)
        text = self.extract_text(img, region=boss_region, preprocess='dark')
        return self.postprocess_text(text)

    def extract_skill_text(self, img):
        skill_region = (600, 800, 700, 200)
        text = self.extract_text(img, region=skill_region, preprocess='dark')
        return self.postprocess_text(text)

    def extract_item_text(self, img):
        item_region = (800, 200, 400, 600)
        text = self.extract_text(img, region=item_region, preprocess='dark')
        return self.postprocess_text(text)

    def full_screen_analysis(self, img):
        """全屏文字分析 - 返回各区域识别结果"""
        result = {
            'quest': self.extract_quest_text(img),
            'location': self.extract_location_text(img),
            'boss': self.extract_boss_name(img),
            'skill': self.extract_skill_text(img),
            'item': self.extract_item_text(img),
        }
        all_texts = [v for v in result.values() if v]
        result['full_text'] = ' '.join(all_texts)
        result['engine'] = self.engine_name or 'simulation'
        return result

    def _get_simulation_text(self):
        import random
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
            "巴尔",
            "野蛮人 旋风斩",
            "术士 开荒",
            "暗金 护符",
        ]
        return random.choice(simulation_texts)


class GameWindowDetector:
    """游戏窗口检测 - 自动定位游戏窗口区域"""

    D4_WINDOW_PATTERNS = {
        'quest_area': {'x_ratio': 0.0, 'y_ratio': 0.0, 'w_ratio': 0.25, 'h_ratio': 0.1},
        'location_area': {'x_ratio': 0.0, 'y_ratio': 0.9, 'w_ratio': 0.15, 'h_ratio': 0.05},
        'boss_area': {'x_ratio': 0.25, 'y_ratio': 0.15, 'w_ratio': 0.5, 'h_ratio': 0.08},
        'skill_bar': {'x_ratio': 0.3, 'y_ratio': 0.85, 'w_ratio': 0.4, 'h_ratio': 0.12},
        'item_tooltip': {'x_ratio': 0.5, 'y_ratio': 0.1, 'w_ratio': 0.25, 'h_ratio': 0.5},
        'chat_area': {'x_ratio': 0.0, 'y_ratio': 0.5, 'w_ratio': 0.25, 'h_ratio': 0.4},
        'minimap': {'x_ratio': 0.85, 'y_ratio': 0.0, 'w_ratio': 0.15, 'h_ratio': 0.15},
    }

    @classmethod
    def get_region(cls, img_shape, area_name):
        """根据图像尺寸和区域名称计算像素坐标"""
        if area_name not in cls.D4_WINDOW_PATTERNS:
            return None
        pattern = cls.D4_WINDOW_PATTERNS[area_name]
        h, w = img_shape[:2]
        x = int(w * pattern['x_ratio'])
        y = int(h * pattern['y_ratio'])
        rw = int(w * pattern['w_ratio'])
        rh = int(h * pattern['h_ratio'])
        return (x, y, rw, rh)

    @classmethod
    def get_all_regions(cls, img_shape):
        """获取所有检测区域"""
        regions = {}
        for name in cls.D4_WINDOW_PATTERNS:
            regions[name] = cls.get_region(img_shape, name)
        return regions


class GameStateRecognizer:
    """游戏状态识别器 - 基于OCR"""

    def __init__(self, ocr_engine=None):
        self.ocr = GameOCR(engine=ocr_engine)
        self.window_detector = GameWindowDetector()

        self.quest_keywords = {
            '安达利尔': 'andariel', '都瑞尔': 'duriel', '墨菲斯托': 'mephisto',
            '暗黑破坏神': 'diablo', '巴尔': 'baal', '迪卡凯恩': 'q1',
            '血鸟': 'q2', '凯恩之书': 'q3', '赫拉迪克': 'q5',
        }

        self.location_keywords = {
            '罗格营地': 'act1', '邪恶洞穴': 'act1_dungeon',
            '冰冷之原': 'act1_outside', '埋骨之地': 'act1_crypt',
            '修道院': 'act1_monastery', '鲁·高因': 'act2',
            '库拉斯特': 'act3', '群魔堡垒': 'act4', '哈洛加斯': 'act5',
        }

        self.class_keywords = {
            '野蛮人': 'barbarian', '巫师': 'sorcerer', '德鲁伊': 'druid',
            '游侠': 'rogue', '死灵法师': 'necromancer',
            '圣骑士': 'paladin', 'paladin': 'paladin', '术士': 'warlock',
        }

    def recognize_quest(self, text):
        for keyword, quest_id in self.quest_keywords.items():
            if keyword in text:
                return quest_id
        return None

    def recognize_location(self, text):
        for keyword, location_id in self.location_keywords.items():
            if keyword in text:
                return location_id
        return None

    def recognize_class(self, text):
        for keyword, class_id in self.class_keywords.items():
            if keyword in text:
                return class_id
        return None

    def analyze_image(self, img):
        """分析游戏画面 - 智能区域检测"""
        regions = self.window_detector.get_all_regions(img.shape)

        region_texts = {}
        for name, region in regions.items():
            if region:
                text = self.ocr.extract_text(img, region=region, preprocess='dark')
                region_texts[name] = GameOCR.postprocess_text(text)

        full_text = ' '.join(v for v in region_texts.values() if v)

        result = {
            'raw_text': full_text,
            'quest': self.recognize_quest(full_text),
            'location': self.recognize_location(full_text),
            'class': self.recognize_class(full_text),
            'regions': region_texts,
            'engine': self.ocr.engine_name or 'simulation',
        }

        return result

    def analyze_image_full(self, img):
        """全屏OCR分析（不分区）"""
        text = self.ocr.extract_text(img, preprocess='auto')
        text = GameOCR.postprocess_text(text)

        result = {
            'raw_text': text,
            'quest': self.recognize_quest(text),
            'location': self.recognize_location(text),
            'class': self.recognize_class(text),
            'engine': self.ocr.engine_name or 'simulation',
        }

        return result


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    print("=" * 50)
    print("  OCR模块测试")
    print("=" * 50)

    ocr = GameOCR()
    print(f"\n当前引擎: {ocr.engine_name or '模拟模式'}")
    print(f"可用状态: {'可用' if ocr.available else '不可用'}")

    if len(sys.argv) > 1:
        import cv2
        img_path = sys.argv[1]
        if os.path.exists(img_path):
            img = cv2.imread(img_path)
            print(f"\n图像尺寸: {img.shape}")

            text = ocr.extract_text(img)
            print(f"\n识别结果:\n{text}")

            print("\n--- 详细结果 ---")
            details = ocr.extract_text_with_confidence(img)
            for d in details:
                print(f"  [{d['confidence']:.1%}] {d['text']}")

            print("\n--- 区域分析 ---")
            recognizer = GameStateRecognizer()
            result = recognizer.analyze_image(img)
            for k, v in result.items():
                if k != 'regions':
                    print(f"  {k}: {v}")
                else:
                    for rk, rv in v.items():
                        if rv:
                            print(f"  区域[{rk}]: {rv}")
        else:
            print(f"文件不存在: {img_path}")
    else:
        print("\n用法: python ocr_recognizer.py <图片路径>")
        print("不提供图片时仅显示引擎状态")
