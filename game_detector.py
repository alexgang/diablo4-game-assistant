#!/usr/bin/env python3
"""
游戏状态检测器 - 集成OCR + SDK Vision + Knowledge RAG + MMR

完整流程：
1. 屏幕捕获 → OCR文字提取 → Vision场景识别 → Knowledge RAG查询 → MMR多模态查询
2. 检测当前任务、BOSS、位置、职业
3. 提供上下文感知的智能推荐
4. SDK不可用时回退到本地模拟模式
"""

import json
import logging
import os
import tempfile
import time
import ctypes
from ctypes import wintypes

from screen_capture import ScreenCapture
from game_data import GameDatabase
from content_indexer import ContentIndexer
from ocr_recognizer import GameOCR, GameStateRecognizer
from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG

logger = logging.getLogger(__name__)


class GameDetector:
    """游戏状态检测器 - 集成OCR + SDK Vision + Knowledge RAG + MMR"""

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

        self.ocr = None
        self.ocr_available = False
        if use_ocr:
            try:
                self.ocr = GameOCR(engine=ocr_engine)
                self.ocr_available = self.ocr.available
                if self.ocr_available:
                    logger.info(f"OCR引擎已启用: {self.ocr.engine_name}")
                else:
                    logger.warning("OCR引擎不可用，将使用模拟模式")
            except Exception as e:
                logger.warning(f"OCR初始化失败: {e}，将使用模拟模式")
                self.ocr = None
                self.ocr_available = False

        self.state_recognizer = GameStateRecognizer(ocr_engine=ocr_engine) if use_ocr else None

        self.instance_id = SDK_CONFIG['instance_id']
        self.knowledge_id = SDK_CONFIG['knowledge']['knowledge_id']

        self.sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
        self.sdk_available = False
        try:
            if self.sdk.check_server():
                # 尝试初始化,如果全部失败(instance 冲突)则换新 ID 重试
                ok_count = self.sdk.init_all(self.instance_id)
                if ok_count == 0:
                    # 所有服务都初始化失败,可能是 instance 冲突,换新 ID
                    import time as _t
                    new_id = f"{SDK_CONFIG['instance_id']}_{int(_t.time()) % 100000}"
                    logger.info(f"SDK instance 全部冲突,切换到新 instance_id: {new_id}")
                    self.instance_id = new_id
                    ok_count = self.sdk.init_all(self.instance_id)
                self.sdk_available = True
                logger.info(f"SDK已连接并初始化, instance_id={self.instance_id}, 成功服务数={ok_count}")
            else:
                logger.warning("SDK服务不可用，使用本地模式")
        except Exception as e:
            logger.warning(f"SDK初始化失败: {e}，使用本地模式")
            self.sdk_available = False

        self.last_ocr_text = ''
        self.last_ocr_time = 0
        self.ocr_cache_ttl = 2.0

        self._cached_img = None
        self._cached_tmp_path = None
        self._cache_timestamp = 0
        self._cache_ttl = 1.0

    def _capture_screen(self):
        """捕获屏幕并缓存，避免同一分析周期内重复截屏"""
        now = time.time()
        if self._cached_img is not None and (now - self._cache_timestamp) < self._cache_ttl:
            return self._cached_img

        if not self.screen_capture.game_hwnd:
            self._try_reconnect_game()

        self._cached_img = self.screen_capture.capture_full_screen()
        self._cache_timestamp = now
        self._cleanup_temp_file()
        return self._cached_img

    def _try_reconnect_game(self):
        """尝试重新查找游戏窗口"""
        game_names = ["暗黑破坏神IV", "Diablo IV", "Diablo IV (Direct3D 11)"]
        for name in game_names:
            hwnd = ctypes.windll.user32.FindWindowW(None, name)
            if hwnd:
                logger.info(f"重新找到游戏窗口: {name} (hwnd={hwnd})")
                self.screen_capture.game_hwnd = hwnd
                rect = wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                self.screen_capture._game_rect = (rect.left, rect.top, rect.right, rect.bottom)
                return True
        return False

    def _get_temp_image_path(self):
        """获取截图的临时文件路径（缓存），供SDK Vision/MMR使用"""
        if self._cached_tmp_path and os.path.exists(self._cached_tmp_path):
            return self._cached_tmp_path
        img = self._capture_screen()
        try:
            import cv2
            tmp_path = os.path.join(
                tempfile.gettempdir(),
                f'_game_detect_{os.getpid()}_{int(time.time())}.png',
            )
            cv2.imwrite(tmp_path, img)
            self._cached_tmp_path = tmp_path
            return tmp_path
        except Exception as e:
            logger.error(f"保存临时截图失败: {e}")
            return None

    def _cleanup_temp_file(self):
        """清理临时截图文件"""
        if self._cached_tmp_path and os.path.exists(self._cached_tmp_path):
            try:
                os.unlink(self._cached_tmp_path)
            except Exception:
                pass
        self._cached_tmp_path = None

    def invalidate_cache(self):
        """手动使能缓存失效（新分析周期开始时调用）"""
        self._cached_img = None
        self._cache_timestamp = 0
        self._cleanup_temp_file()

    def _extract_ocr_text(self, img):
        """使用OCR从截图提取文字"""
        if self.ocr and self.ocr_available:
            for preprocess in ['auto', 'dark', 'high_contrast']:
                try:
                    text = self.ocr.extract_text(img, preprocess=preprocess)
                    text = GameOCR.postprocess_text(text)
                    if text.strip():
                        return text
                except Exception as e:
                    logger.debug(f"OCR提取失败({preprocess}): {e}")

        if self.state_recognizer:
            try:
                result = self.state_recognizer.analyze_image_full(img)
                text = result.get('raw_text', '')
                if text.strip():
                    return text
            except Exception as e:
                logger.debug(f"GameStateRecognizer提取失败: {e}")

        return ''

    def _recognize_scene(self, tmp_path):
        """使用SDK Vision识别场景上下文（返回场景信息，非文字）"""
        if not self.sdk_available:
            return []
        try:
            vision_results = self.sdk.vision_query(
                self.instance_id,
                tmp_path,
                topk=SDK_CONFIG['vision']['topk'],
                mode=SDK_CONFIG['vision']['mode'],
            )
            return vision_results or []
        except Exception as e:
            logger.error(f"Vision场景识别失败: {e}")
            return []

    def get_screen_text(self):
        """
        获取当前屏幕文字 - 使用OCR提取真实文字，回退到模拟模式

        Returns:
            str: 识别出的屏幕文字
        """
        img = self._capture_screen()

        ocr_text = self._extract_ocr_text(img)
        if ocr_text.strip():
            self.last_ocr_text = ocr_text
            self.last_ocr_time = time.time()
            return ocr_text

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
        screen_text = self.get_screen_text()

        if self.sdk_available:
            try:
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

        if self.sdk_available:
            try:
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
        """检测当前位置 - 优先Vision场景匹配，回退到OCR+颜色分析"""
        if self.sdk_available:
            try:
                tmp_path = self._get_temp_image_path()
                if tmp_path:
                    vision_results = self._recognize_scene(tmp_path)
                    if vision_results:
                        scene_id = vision_results[0].get('scene_id', '')
                        if scene_id:
                            self.current_location = scene_id
                            return self.current_location
            except Exception as e:
                logger.error(f"SDK位置识别失败，回退本地: {e}")

        img = self._capture_screen()

        if self.ocr and self.ocr_available:
            try:
                location_text = self.ocr.extract_location_text(img)
                if location_text.strip():
                    self.current_location = location_text
                    return self.current_location
            except Exception as e:
                logger.error(f"OCR位置识别失败: {e}")

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
        guide['ocr_engine'] = self._get_engine_label()

        return guide

    def analyze_game_state(self):
        """分析游戏状态"""
        self.invalidate_cache()

        img = self._capture_screen()
        ocr_text = self._extract_ocr_text(img)
        if not ocr_text.strip():
            ocr_text = self._get_simulation_text()

        self.last_ocr_text = ocr_text
        self.last_ocr_time = time.time()

        if self.sdk_available:
            recommendations = self._analyze_with_sdk(ocr_text)
        else:
            recommendations = self.detect_from_screen_text(ocr_text)

        result = {
            'status': 'analyzing',
            'screen_text': ocr_text,
            'recommendations': recommendations,
            'formatted': self.indexer.format_recommendations(recommendations),
            'ocr_engine': self._get_engine_label(),
        }

        return result

    def _analyze_with_sdk(self, ocr_text):
        """
        使用SDK进行完整分析 - OCR文字 + Vision场景 + Knowledge RAG + MMR

        流程：
        1. OCR文字已由调用方提供 (ocr_text)
        2. Vision场景识别 → 提供场景上下文
        3. Knowledge RAG查询 → 基于OCR文字+场景上下文
        4. MMR多模态查询 → 图文联合检索
        5. 合并所有结果 + 本地推荐补充
        """
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

        scene_context = ''
        tmp_path = self._get_temp_image_path()

        if tmp_path:
            try:
                vision_results = self._recognize_scene(tmp_path)
                if vision_results:
                    scene_parts = []
                    for vr in vision_results:
                        scene_id = vr.get('scene_id', '')
                        picture_id = vr.get('picture_id', '')
                        score = vr.get('score', 0)
                        scene_parts.append(f"场景:{scene_id}(画面:{picture_id}, 置信度:{score:.2f})")
                        recommendations['quest_hints'].append({
                            'name': f"场景: {scene_id}",
                            'location': picture_id,
                            'guide': f"Vision场景匹配 (置信度: {score:.2f})",
                            'act': 'Vision',
                            'relevance': score,
                        })
                    scene_context = '; '.join(scene_parts)
            except Exception as e:
                logger.error(f"Vision查询失败: {e}")

            try:
                query_text = ocr_text
                if scene_context:
                    query_text = f"{ocr_text} [{scene_context}]"
                knowledge_answer = self.sdk.knowledge_query(
                    self.instance_id,
                    f"游戏画面内容: {query_text}，请给出任务指引和BOSS攻略",
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
                    text=ocr_text,
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
                logger.debug(f"MMR查询失败: {e}")

        local_recs = self.indexer.get_context_recommendations(ocr_text)
        for key in recommendations:
            if not recommendations[key]:
                recommendations[key] = local_recs.get(key, [])

        self._update_state_from_recommendations(recommendations)
        return recommendations

    def capture_and_analyze(self):
        """捕获并分析当前画面"""
        self.invalidate_cache()
        img = self._capture_screen()
        analysis = self.analyze_game_state()
        return img, analysis

    def capture_and_query(self, query=None):
        """
        主入口：捕获屏幕 → OCR提取文字 → Vision场景识别 → Knowledge RAG → MMR → 合并结果

        Args:
            query: 可选的额外查询文本，会与OCR文字合并

        Returns:
            dict: 包含完整分析结果的字典
        """
        self.invalidate_cache()

        img = self._capture_screen()

        ocr_text = self._extract_ocr_text(img)
        if not ocr_text.strip():
            ocr_text = self._get_simulation_text()

        self.last_ocr_text = ocr_text
        self.last_ocr_time = time.time()

        combined_text = ocr_text
        if query and query.strip():
            combined_text = f"{ocr_text} {query.strip()}"

        scene_info = []
        tmp_path = self._get_temp_image_path()
        if tmp_path and self.sdk_available:
            scene_info = self._recognize_scene(tmp_path)

        scene_context = ''
        if scene_info:
            scene_parts = []
            for vr in scene_info:
                scene_id = vr.get('scene_id', '')
                picture_id = vr.get('picture_id', '')
                score = vr.get('score', 0)
                scene_parts.append({
                    'scene_id': scene_id,
                    'picture_id': picture_id,
                    'score': score,
                })
            scene_context = '; '.join(
                f"场景:{s['scene_id']}(置信度:{s['score']:.2f})" for s in scene_parts
            )

        knowledge_answer = ''
        if self.sdk_available:
            try:
                rag_query = combined_text
                if scene_context:
                    rag_query = f"{combined_text} [场景: {scene_context}]"
                knowledge_answer = self.sdk.knowledge_query(
                    self.instance_id,
                    rag_query,
                    knowledge_id=self.knowledge_id,
                )
            except Exception as e:
                logger.error(f"Knowledge查询失败: {e}")

        mmr_results = []
        if self.sdk_available and tmp_path:
            try:
                mmr_results = self.sdk.mmr_query(
                    self.instance_id,
                    text=combined_text,
                    image_path=tmp_path,
                    topk=SDK_CONFIG['mmr']['topk'],
                    threshold=SDK_CONFIG['mmr']['threshold'],
                )
            except Exception as e:
                logger.debug(f"MMR查询失败: {e}")

        local_recs = self.indexer.get_context_recommendations(combined_text)
        self._update_state_from_recommendations(local_recs)

        result = {
            'status': 'complete',
            'ocr_text': ocr_text,
            'scene_info': scene_info,
            'scene_context': scene_context,
            'knowledge_answer': knowledge_answer.strip() if knowledge_answer else '',
            'mmr_results': mmr_results,
            'recommendations': local_recs,
            'formatted': self.indexer.format_recommendations(local_recs),
            'ocr_engine': self._get_engine_label(),
            'location': self.current_location or '未知',
        }

        if knowledge_answer and knowledge_answer.strip():
            result['recommendations']['quest_hints'].insert(0, {
                'name': 'Knowledge推荐',
                'location': '',
                'guide': knowledge_answer.strip(),
                'act': 'RAG',
                'relevance': 1.0,
            })

        for mr in (mmr_results or []):
            score = mr.get('score', 0)
            text = mr.get('text', '')
            info = mr.get('info', '')
            entry = {
                'name': text[:50] if text else 'MMR匹配',
                'relevance': score,
            }
            if info:
                entry['guide'] = info
            result['recommendations']['build_guides'].append(entry)

        return result

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

    def _get_engine_label(self):
        """获取当前引擎标签"""
        if self.sdk_available and self.ocr_available:
            return f"sdk+ocr({self.ocr.engine_name})"
        elif self.sdk_available:
            return 'sdk'
        elif self.ocr_available:
            return f"ocr({self.ocr.engine_name})"
        return 'simulation'

    def _get_simulation_text(self):
        """模拟获取屏幕文字（OCR和SDK均不可用时的回退方案）"""
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
