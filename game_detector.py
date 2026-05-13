#!/usr/bin/env python3
"""
游戏状态检测器 - 集成Intel Gaming Assistant SDK

功能：
1. 屏幕捕获 -> SDK Vision识别 -> Knowledge RAG推荐
2. 检测当前任务、BOSS、位置、职业
3. 提供上下文感知的智能推荐
4. SDK不可用时回退到本地模拟模式
"""

import json
import logging
import os
import tempfile
import time

from screen_capture import ScreenCapture
from game_data import GameDatabase
from content_indexer import ContentIndexer
from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG

logger = logging.getLogger(__name__)


class GameDetector:
    """游戏状态检测器 - 集成Intel Gaming Assistant SDK"""

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

        self.instance_id = SDK_CONFIG['instance_id']
        self.knowledge_id = SDK_CONFIG['knowledge']['knowledge_id']

        self.sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
        self.sdk_available = False
        try:
            if self.sdk.check_server():
                self.sdk.init_all(self.instance_id)
                self.sdk_available = True
                logger.info(f"SDK已连接并初始化, instance_id={self.instance_id}")
            else:
                logger.warning("SDK服务不可用，使用本地模式")
        except Exception as e:
            logger.warning(f"SDK初始化失败: {e}，使用本地模式")
            self.sdk_available = False

        self.last_ocr_text = ''
        self.last_ocr_time = 0
        self.ocr_cache_ttl = 2.0

    def get_screen_text(self):
        """
        获取当前屏幕文字 - 优先使用SDK Vision，回退到模拟模式

        Returns:
            str: 识别出的屏幕文字
        """
        if self.sdk_available:
            try:
                img = self.screen_capture.capture_full_screen()
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp_path = tmp.name
                try:
                    import cv2
                    cv2.imwrite(tmp_path, img)
                    vision_results = self.sdk.vision_query(
                        self.instance_id,
                        tmp_path,
                        topk=SDK_CONFIG['vision']['topk'],
                        mode=SDK_CONFIG['vision']['mode'],
                    )
                    if vision_results:
                        scene_parts = []
                        for vr in vision_results:
                            scene_id = vr.get('scene_id', '')
                            picture_id = vr.get('picture_id', '')
                            score = vr.get('score', 0)
                            scene_parts.append(f"场景:{scene_id} 画面:{picture_id} 置信度:{score:.2f}")
                        text = '; '.join(scene_parts)
                        if text.strip():
                            self.last_ocr_text = text
                            self.last_ocr_time = time.time()
                            return text
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            except Exception as e:
                logger.error(f"SDK Vision识别失败: {e}")

        return self._get_simulation_text()

    def get_screen_text_fast(self):
        """
        快速获取屏幕文字 - 使用缓存避免频繁识别

        Returns:
            str: 识别出的屏幕文字
        """
        if time.time() - self.last_ocr_time < self.ocr_cache_ttl and self.last_ocr_text:
            return self.last_ocr_text
        return self.get_screen_text()

    def detect_from_screen_text(self, screen_text):
        """根据屏幕文字检测游戏状态并返回相关推荐"""
        if self.sdk_available:
            try:
                answer = self.sdk.knowledge_query(
                    self.instance_id,
                    screen_text,
                    knowledge_id=self.knowledge_id,
                )
                recommendations = self._parse_knowledge_answer(answer, screen_text)
                self._update_state_from_recommendations(recommendations)
                return recommendations
            except Exception as e:
                logger.error(f"SDK Knowledge查询失败，回退本地: {e}")

        recommendations = self.indexer.get_context_recommendations(screen_text)
        self._update_state_from_recommendations(recommendations)
        return recommendations

    def _parse_knowledge_answer(self, answer, screen_text):
        """将SDK Knowledge返回的文本解析为推荐结构"""
        recommendations = {
            'quest_hints': [],
            'boss_tips': [],
            'build_guides': [],
            'equipment_suggestions': [],
            'web_guides': [],
            'boss_schedule': [],
            'skill_info': [],
            'build_details': [],
        }

        local_recs = self.indexer.get_context_recommendations(screen_text)
        for key in recommendations:
            recommendations[key] = local_recs.get(key, [])

        if answer and answer.strip():
            recommendations['quest_hints'].insert(0, {
                'name': 'SDK推荐',
                'location': '',
                'guide': answer.strip(),
                'act': 'SDK',
                'relevance': 1.0,
            })

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
        if self.sdk_available:
            try:
                screen_text = self.get_screen_text()
                answer = self.sdk.knowledge_query(
                    self.instance_id,
                    f"当前任务指引: {screen_text}",
                    knowledge_id=self.knowledge_id,
                )
                if answer and answer.strip():
                    return {
                        'name': 'SDK任务识别',
                        'location': '',
                        'guide': answer.strip(),
                    }
            except Exception as e:
                logger.error(f"SDK任务查询失败，回退本地: {e}")

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
        if self.sdk_available:
            try:
                screen_text = self.get_screen_text()
                answer = self.sdk.knowledge_query(
                    self.instance_id,
                    f"BOSS攻略: {screen_text}",
                    knowledge_id=self.knowledge_id,
                )
                if answer and answer.strip():
                    return {
                        'name': 'SDK BOSS识别',
                        'weakness': [],
                        'skills': [],
                        'guide': answer.strip(),
                    }
            except Exception as e:
                logger.error(f"SDK BOSS查询失败，回退本地: {e}")

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
        if self.sdk_available:
            try:
                img = self.screen_capture.capture_full_screen()
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp_path = tmp.name
                try:
                    import cv2
                    cv2.imwrite(tmp_path, img)
                    vision_results = self.sdk.vision_query(
                        self.instance_id,
                        tmp_path,
                        topk=1,
                        mode=SDK_CONFIG['vision']['mode'],
                    )
                    if vision_results:
                        scene_id = vision_results[0].get('scene_id', '')
                        if scene_id:
                            self.current_location = scene_id
                            return self.current_location
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            except Exception as e:
                logger.error(f"SDK位置识别失败，回退本地: {e}")

        try:
            import cv2
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
        except ImportError:
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
        guide['ocr_engine'] = 'sdk' if self.sdk_available else 'simulation'

        return guide

    def analyze_game_state(self):
        """分析游戏状态"""
        screen_text = self.get_screen_text()

        if self.sdk_available:
            recommendations = self._analyze_with_sdk(screen_text)
        else:
            recommendations = self.detect_from_screen_text(screen_text)

        result = {
            'status': 'analyzing',
            'screen_text': screen_text,
            'recommendations': recommendations,
            'formatted': self.indexer.format_recommendations(recommendations),
            'ocr_engine': 'sdk' if self.sdk_available else 'simulation',
        }

        return result

    def _analyze_with_sdk(self, screen_text):
        """使用SDK进行完整分析"""
        recommendations = {
            'quest_hints': [],
            'boss_tips': [],
            'build_guides': [],
            'equipment_suggestions': [],
            'web_guides': [],
            'boss_schedule': [],
            'skill_info': [],
            'build_details': [],
        }

        img = self.screen_capture.capture_full_screen()
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
            import cv2
            cv2.imwrite(tmp_path, img)

            try:
                vision_results = self.sdk.vision_query(
                    self.instance_id,
                    tmp_path,
                    topk=SDK_CONFIG['vision']['topk'],
                    mode=SDK_CONFIG['vision']['mode'],
                )
                if vision_results:
                    for vr in vision_results:
                        scene_id = vr.get('scene_id', '')
                        score = vr.get('score', 0)
                        recommendations['quest_hints'].append({
                            'name': f"场景: {scene_id}",
                            'location': '',
                            'guide': f"Vision匹配 (置信度: {score:.2f})",
                            'act': 'Vision',
                            'relevance': score,
                        })
            except Exception as e:
                logger.error(f"Vision查询失败: {e}")

            try:
                knowledge_answer = self.sdk.knowledge_query(
                    self.instance_id,
                    f"游戏画面内容: {screen_text}，请给出任务指引和BOSS攻略",
                    knowledge_id=self.knowledge_id,
                )
                if knowledge_answer and knowledge_answer.strip():
                    recommendations['quest_hints'].insert(0, {
                        'name': 'Knowledge推荐',
                        'location': '',
                        'guide': knowledge_answer.strip(),
                        'act': 'RAG',
                        'relevance': 1.0,
                    })
            except Exception as e:
                logger.error(f"Knowledge查询失败: {e}")

            try:
                mmr_results = self.sdk.mmr_query(
                    self.instance_id,
                    text=screen_text,
                    image_path=tmp_path,
                    topk=SDK_CONFIG['mmr']['topk'],
                    threshold=SDK_CONFIG['mmr']['threshold'],
                )
                for mr in mmr_results:
                    score = mr.get('score', 0)
                    text = mr.get('text', '')
                    info = mr.get('info', '')
                    entry = {
                        'name': text[:50] if text else 'MMR匹配',
                        'relevance': score,
                    }
                    if info:
                        entry['guide'] = info
                    recommendations['build_guides'].append(entry)
            except Exception as e:
                logger.error(f"MMR查询失败: {e}")

        except Exception as e:
            logger.error(f"SDK分析过程失败: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        local_recs = self.indexer.get_context_recommendations(screen_text)
        for key in recommendations:
            if not recommendations[key]:
                recommendations[key] = local_recs.get(key, [])

        self._update_state_from_recommendations(recommendations)
        return recommendations

    def capture_and_analyze(self):
        """捕获并分析当前画面"""
        img = self.screen_capture.capture_full_screen()
        analysis = self.analyze_game_state()
        return img, analysis

    def search(self, query, top_n=5):
        """搜索游戏数据"""
        if self.sdk_available:
            try:
                answer = self.sdk.knowledge_query(
                    self.instance_id,
                    query,
                    knowledge_id=self.knowledge_id,
                )
                sdk_results = []
                if answer and answer.strip():
                    sdk_results.append({
                        'category': 'knowledge',
                        'score': 1.0,
                        'data': {
                            'name': 'Knowledge搜索',
                            'guide': answer.strip(),
                        },
                    })

                try:
                    mmr_results = self.sdk.mmr_query(
                        self.instance_id,
                        text=query,
                        topk=top_n,
                        threshold=SDK_CONFIG['mmr']['threshold'],
                    )
                    for mr in mmr_results:
                        sdk_results.append({
                            'category': 'mmr',
                            'score': mr.get('score', 0),
                            'data': {
                                'name': mr.get('text', '')[:50],
                                'info': mr.get('info', ''),
                            },
                        })
                except Exception as e:
                    logger.error(f"MMR搜索失败: {e}")

                local_results = self.indexer.search(query, top_n=top_n)
                sdk_results.extend(local_results)
                return sdk_results[:top_n]
            except Exception as e:
                logger.error(f"SDK搜索失败，回退本地: {e}")

        return self.indexer.search(query, top_n=top_n)

    def _get_simulation_text(self):
        """模拟获取屏幕文字（SDK不可用时的回退方案）"""
        import random
        simulation_texts = [
            "弗列斯泰克 严寒中的希望",
            "斯科斯格伦 枯萎的森林",
            "凯吉斯坦 光明大教堂",
            "哈维扎 最后的赫拉迪姆",
            "击败莉莉丝 深渊核心",
            "野蛮人 旋风斩 开荒",
            "法师 暴风雪 冰封之球",
            "游侠 穿刺射击 暗影灌注",
            "死灵法师 亡者大军 骨风暴",
            "德鲁伊 龙卷风 灰熊之怒",
            "暗金 护符 野蛮人",
            "暗金 头盔 法师",
            "巅峰盘 先祖之怒 野蛮人",
            "巅峰盘 风暴之眼 德鲁伊",
        ]
        return random.choice(simulation_texts)
