#!/usr/bin/env python3
"""
BOSS 战对战辅导模块

功能：
1. BOSS 血条检测：基于 OpenCV HSV 颜色检测，识别屏幕底部中央的红色血条
2. BOSS 阶段切换：基于血量阈值（75%/50%/25%）判断 BOSS 战斗阶段
3. BOSS 弱点属性库：D4 主要 BOSS 的抗性/易伤元素数据
4. 克制词条推荐：根据 BOSS 弱点推荐对应元素伤害词条

D4 BOSS 血条特征：
- 位置：屏幕底部中央（技能栏上方）
- 颜色：红色填充（部分 BOSS 橙色/紫色）
- 形状：水平条形，左右对称
- BOSS 名字显示在血条上方
"""

import logging
import time
import os
import json
import numpy as np
import cv2

logger = logging.getLogger(__name__)


class BossHealthDetector:
    """BOSS 血条检测器 - 基于 OpenCV 颜色检测"""

    # D4 BOSS 血条位置（屏幕比例，自适应分辨率）
    # D4 BOSS 血条在屏幕顶部偏下,BOSS 名字下方,约 y=20%-25%
    # (实测 _debug_no_match 截图: y=20-25% 红色占比 7.50% 为最高峰)
    BLOOD_BAR_REGION = {'x': 0.30, 'y': 0.20, 'w': 0.40, 'h': 0.05}

    # 检测确认阈值：连续 N 帧检测到/未检测到才切换状态
    ACTIVATE_FRAMES = 2   # 连续 2 帧检测到血条 → BOSS 战开始(降低延迟)
    DEACTIVATE_FRAMES = 3  # 连续 3 帧未检测到 → BOSS 战结束

    # 血量平滑系数（指数移动平均）
    SMOOTHING_ALPHA = 0.4

    def __init__(self):
        self._consecutive_hits = 0
        self._consecutive_misses = 0
        self._boss_active = False
        self._last_health_pct = 100.0
        self._last_bar_rect = None
        self._boss_active_since = 0.0
        self._debug_log_count = 0  # 限制调试日志频率
        self._candidate_bar_rect = None  # 候选血条位置(用于位置稳定性验证,过滤随机红色特效)

    def detect(self, frame):
        """检测画面中的 BOSS 血条

        Args:
            frame: BGR 格式的游戏画面（numpy 数组）

        Returns:
            dict: {
                'active': bool,        # BOSS 战是否进行中
                'health_pct': float,   # 血量百分比 0-100
                'rect': tuple|None,    # 血条区域 (x, y, w, h)
                'just_activated': bool,  # 本次检测是否刚进入 BOSS 战
                'just_deactivated': bool  # 本次检测是否刚结束 BOSS 战
            }
        """
        if frame is None or frame.size == 0:
            return self._empty_result()

        h, w = frame.shape[:2]
        region = self.BLOOD_BAR_REGION
        x1 = int(region['x'] * w)
        y1 = int(region['y'] * h)
        x2 = int((region['x'] + region['w']) * w)
        y2 = int((region['y'] + region['h']) * h)
        crop = frame[y1:y2, x1:x2]

        if crop.size == 0:
            return self._empty_result()

        bar_rect, fill_ratio = self._detect_red_bar(crop)

        # 调试日志:每 5 次输出一次检测结果(避免日志过多)
        self._debug_log_count += 1
        if self._debug_log_count % 5 == 1:
            red_pct = self._count_red_pixels(crop)
            logger.info(
                f"[BOSS] 检测: frame={w}x{h}, region=({x1},{y1})-({x2},{y2}), "
                f"红色像素={red_pct:.2%}, bar={'有' if bar_rect else '无'}, "
                f"fill={fill_ratio:.3f}, active={self._boss_active}, "
                f"hits={self._consecutive_hits}/{self.ACTIVATE_FRAMES}"
            )

        just_activated = False
        just_deactivated = False

        if bar_rect is not None:
            self._consecutive_misses = 0

            if not self._boss_active:
                # 未激活时累计 hits,达到阈值才激活
                # 关键:要求连续帧血条位置稳定(过滤打小怪时的随机红色特效/伤害数字)
                # BOSS 血条位置固定在屏幕顶部中央,而伤害数字位置随机飘移
                if self._candidate_bar_rect is not None:
                    if not self._is_bar_stable(self._candidate_bar_rect, bar_rect):
                        # 位置漂移过大,重置候选(可能是随机红色特效)
                        logger.debug(f"[BOSS] 血条位置漂移,重置候选 (旧={self._candidate_bar_rect}, 新={bar_rect})")
                        self._consecutive_hits = 0
                self._candidate_bar_rect = bar_rect
                self._consecutive_hits += 1
                if self._consecutive_hits >= self.ACTIVATE_FRAMES:
                    self._boss_active = True
                    self._boss_active_since = time.time()
                    self._last_health_pct = 100.0
                    just_activated = True
                    self._candidate_bar_rect = None  # 激活后清空候选
                    logger.info(f"🐉 BOSS 战开始 (血条检测确认, 连续 {self._consecutive_hits} 帧)")
            else:
                # 已激活后不再累计 hits
                self._consecutive_hits = self.ACTIVATE_FRAMES

            if self._boss_active:
                raw_pct = max(0.0, min(100.0, fill_ratio * 100.0))
                self._last_health_pct = (
                    self.SMOOTHING_ALPHA * raw_pct +
                    (1 - self.SMOOTHING_ALPHA) * self._last_health_pct
                )
                rx, ry, rw, rh = bar_rect
                self._last_bar_rect = (x1 + rx, y1 + ry, rw, rh)
        else:
            self._consecutive_misses += 1
            self._consecutive_hits = 0
            self._candidate_bar_rect = None  # 丢失血条时清空候选

            if self._boss_active and self._consecutive_misses >= self.DEACTIVATE_FRAMES:
                self._boss_active = False
                just_deactivated = True
                duration = time.time() - self._boss_active_since if self._boss_active_since else 0
                logger.info(f"🏁 BOSS 战结束 (持续 {duration:.0f}s)")

        return {
            'active': self._boss_active,
            'health_pct': round(self._last_health_pct, 1),
            'rect': self._last_bar_rect,
            'just_activated': just_activated,
            'just_deactivated': just_deactivated,
        }

    def _detect_red_bar(self, crop):
        """在裁剪区域内检测红色血条

        Returns:
            (rect, fill_ratio): rect=(x,y,w,h) 相对于 crop 的坐标, fill_ratio=0-1
            若未检测到返回 (None, 0.0)
        """
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

        # 红色在 HSV 两端，合并两个范围
        mask1 = cv2.inRange(hsv, np.array([0, 80, 80]), np.array([10, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([170, 80, 80]), np.array([180, 255, 255]))
        # 橙色（部分 BOSS）
        mask3 = cv2.inRange(hsv, np.array([11, 80, 80]), np.array([18, 255, 255]))
        mask = cv2.bitwise_or(mask1, mask2)
        mask = cv2.bitwise_or(mask, mask3)

        # 形态学闭运算连接断点(水平方向连接更强,适配血条细长形态)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, 0.0

        # 筛选：面积最大的水平条形轮廓
        # BOSS 血条特征:细长水平条形,宽度大,面积较大
        # 排除:伤害数字(接近方形/小)、技能特效(面积小或形状不规则)
        best = None
        best_area = 0
        ch, cw = crop.shape[:2]
        min_area = cw * ch * 0.05         # 至少占检测区域 5%(提高,排除小特效)
        min_width_ratio = 0.40            # 血条宽度至少占检测区域 40%(BOSS 血条较宽)
        min_aspect = 5.0                  # 长宽比 >= 5(血条是细长条形,伤害数字接近方形)

        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            area = w * h
            if area < min_area:
                continue
            # 血条应该是细长的水平条形(宽 >> 高),排除伤害数字/方形特效
            if w < h * min_aspect:
                continue
            # 血条宽度应占检测区域较大比例(BOSS 血条通常横跨屏幕中央)
            if w < cw * min_width_ratio:
                continue
            if area > best_area:
                best_area = area
                best = (x, y, w, h)

        if best is None:
            return None, 0.0

        # fill_ratio = 血条区域内红色像素面积 / 血条轮廓面积
        # (D4 血条有固定边框,轮廓宽度不代表血量,用红色填充率更准确)
        x, y, bw, bh = best
        roi = mask[y:y+bh, x:x+bw]
        red_pixels = np.count_nonzero(roi)
        roi_pixels = roi.size if roi.size else 1
        fill_ratio = red_pixels / roi_pixels
        return best, fill_ratio

    def _count_red_pixels(self, crop):
        """统计裁剪区域内红色/橙色像素占比(用于调试日志)"""
        if crop is None or crop.size == 0:
            return 0.0
        try:
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            mask1 = cv2.inRange(hsv, np.array([0, 80, 80]), np.array([10, 255, 255]))
            mask2 = cv2.inRange(hsv, np.array([170, 80, 80]), np.array([180, 255, 255]))
            mask3 = cv2.inRange(hsv, np.array([11, 80, 80]), np.array([18, 255, 255]))
            mask = cv2.bitwise_or(mask1, mask2)
            mask = cv2.bitwise_or(mask, mask3)
            return np.count_nonzero(mask) / mask.size
        except Exception:
            return 0.0

    def _is_bar_stable(self, rect1, rect2, pos_tol=0.15):
        """检查两个血条位置是否稳定(位置漂移在容差内)

        BOSS 血条位置固定在屏幕顶部中央,连续帧位置漂移应很小。
        打小怪时的红色伤害数字/特效位置随机,连续帧位置漂移大。

        Args:
            rect1, rect2: (x, y, w, h) 相对于 crop 的坐标
            pos_tol: 位置容差(相对于血条宽度),默认 15%

        Returns:
            bool: True 表示位置稳定
        """
        try:
            x1, y1, w1, h1 = rect1
            x2, y2, w2, h2 = rect2
            ref_w = max(w1, w2, 1)
            # x 坐标漂移容差(BOSS 血条 x 坐标应几乎不变)
            if abs(x1 - x2) > ref_w * pos_tol:
                return False
            # 宽度变化容差(BOSS 血条宽度应稳定)
            if abs(w1 - w2) > ref_w * pos_tol:
                return False
            return True
        except Exception:
            return False

    def _empty_result(self):
        return {
            'active': self._boss_active,
            'health_pct': round(self._last_health_pct, 1),
            'rect': self._last_bar_rect,
            'just_activated': False,
            'just_deactivated': False,
        }

    def reset(self):
        """重置检测器状态"""
        self._consecutive_hits = 0
        self._consecutive_misses = 0
        self._boss_active = False
        self._last_health_pct = 100.0
        self._last_bar_rect = None
        self._boss_active_since = 0.0
        self._candidate_bar_rect = None

    def force_activate(self, boss_name=''):
        """强制激活 BOSS 战状态(由名字检测触发时调用)"""
        if not self._boss_active:
            self._boss_active = True
            self._consecutive_hits = self.ACTIVATE_FRAMES
            self._consecutive_misses = 0
            self._boss_active_since = time.time()
            logger.info(f"🐉 BOSS 战开始 (名字检测触发: {boss_name})")
            return True
        return False


class BossNameDetector:
    """BOSS 名字检测器 - 通过 OCR 识别屏幕上方的 BOSS 名字

    作为血条检测的补充触发方式:
    - 血条检测依赖颜色,某些 BOSS 血条颜色/位置特殊时可能漏检
    - 名字检测通过 OCR 识别血条上方的文字,匹配 BOSS 数据库即触发
    - 内置节流(默认 8 秒一次),避免频繁 OCR 拖慢性能
    """

    # D4 BOSS 名字位置: 画面最上方中间,血条(y=20-25%)正上方,约 y=2-7%
    # (实测截图: y=0.02 识别到 '齐示领主的折磨回响' = '齐尔领主的折磨回响')
    NAME_REGION = {'x': 0.25, 'y': 0.02, 'w': 0.50, 'h': 0.05}

    # OCR 节流间隔(秒)
    OCR_INTERVAL = 8.0

    # 最小文字长度(过滤噪声)
    MIN_TEXT_LENGTH = 2

    def __init__(self, ocr_engine=None):
        """
        Args:
            ocr_engine: OCR 引擎实例,需有 extract_text(frame, region, preprocess) 方法
                        若为 None 则检测器不可用
        """
        self._ocr = ocr_engine
        self._last_ocr_time = 0.0
        self._last_detected_name = ''
        self._debug_log_count = 0

    def set_ocr_engine(self, ocr_engine):
        """设置 OCR 引擎(延迟注入,避免初始化时序问题)"""
        self._ocr = ocr_engine

    def detect(self, frame):
        """检测屏幕上方的 BOSS 名字

        Returns:
            dict: {
                'detected': bool,        # 是否检测到 BOSS 名字
                'text': str,             # OCR 识别的原始文字
                'boss_data': dict|None,  # 匹配到的 BOSS 数据
                'skipped': bool,         # 是否因节流跳过
            }
        """
        if self._ocr is None:
            return {'detected': False, 'text': '', 'boss_data': None, 'skipped': True}

        # 节流检查
        now = time.time()
        if now - self._last_ocr_time < self.OCR_INTERVAL:
            return {'detected': False, 'text': '', 'boss_data': None, 'skipped': True}
        self._last_ocr_time = now

        if frame is None or frame.size == 0:
            return {'detected': False, 'text': '', 'boss_data': None, 'skipped': False}

        try:
            h, w = frame.shape[:2]
            region = self.NAME_REGION
            x1 = int(region['x'] * w)
            y1 = int(region['y'] * h)
            x2 = int((region['x'] + region['w']) * w)
            y2 = int((region['y'] + region['h']) * h)
            crop = frame[y1:y2, x1:x2]

            if crop.size == 0:
                return {'detected': False, 'text': '', 'boss_data': None, 'skipped': False}

            # OCR 识别策略: 先用原图识别(easyocr 原图即可识别),返回空时降级放大2倍重试
            # (实测: easyocr 在 60px 高的原图上即可完美识别"齐尔领主的折磨回响";
            #  2560x1600 高分辨率下放大2倍反而可能乱码,故优先原图)
            text = ''
            try:
                text = self._ocr.extract_text(crop, preprocess='none')
            except Exception as e:
                logger.debug(f"BOSS 名字 OCR 异常(原图): {e}")

            text = text.strip() if text else ''

            # 原图识别为空时,降级放大2倍重试(兼容小分辨率)
            if len(text) < self.MIN_TEXT_LENGTH:
                crop_scaled = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                try:
                    text2 = self._ocr.extract_text(crop_scaled, preprocess='none')
                    if text2 and len(text2.strip()) >= self.MIN_TEXT_LENGTH:
                        text = text2.strip()
                except Exception as e:
                    logger.debug(f"BOSS 名字 OCR 异常(放大2倍): {e}")

            # 调试日志
            self._debug_log_count += 1
            if self._debug_log_count % 3 == 1:
                logger.info(f"[BOSS-Name] OCR: region=({x1},{y1})-({x2},{y2}), crop={crop.shape[:2]}, text='{text}'")

            if len(text) < self.MIN_TEXT_LENGTH:
                return {'detected': False, 'text': text, 'boss_data': None, 'skipped': False}

            # 匹配 BOSS 数据库
            boss_data = lookup_boss(text)
            if boss_data:
                self._last_detected_name = boss_data['name']
                logger.info(f"[BOSS-Name] 匹配到 BOSS: {boss_data['name']} (OCR: '{text}')")
                return {
                    'detected': True,
                    'text': text,
                    'boss_data': boss_data,
                    'skipped': False,
                }

            return {'detected': False, 'text': text, 'boss_data': None, 'skipped': False}
        except Exception as e:
            logger.debug(f"BOSS 名字检测异常: {e}")
            return {'detected': False, 'text': '', 'boss_data': None, 'skipped': False}

    def reset_throttle(self):
        """重置节流时间(血条激活时调用,确保能立即做名字检测)"""
        self._last_ocr_time = 0.0

    def reset(self):
        """重置检测器状态"""
        self._last_ocr_time = 0.0
        self._last_detected_name = ''


class BossPhaseTracker:
    """BOSS 阶段追踪器 - 基于血量阈值判断战斗阶段"""

    # 阶段切换血量阈值（百分比）
    # D4 大部分 BOSS 有 2-3 个阶段，在 75%/50%/25% 切换
    PHASE_THRESHOLDS = [75.0, 50.0, 25.0]

    def __init__(self):
        self._current_phase = 0  # 0=未战斗, 1=阶段一, 2=阶段二, 3=阶段三
        self._phase_history = []
        self.on_phase_change = None  # 回调: (new_phase, old_phase, health_pct)

    def update(self, health_pct, boss_active):
        """更新血量，检测阶段切换

        Returns:
            dict: {'phase': int, 'changed': bool, 'phase_name': str}
        """
        if not boss_active:
            if self._current_phase != 0:
                old = self._current_phase
                self._current_phase = 0
                self._phase_history = []
                if self.on_phase_change:
                    self.on_phase_change(0, old, health_pct)
            return {'phase': 0, 'changed': self._current_phase != 0, 'phase_name': '未战斗'}

        # 根据血量判断应该在哪个阶段
        target_phase = 1
        for i, threshold in enumerate(self.PHASE_THRESHOLDS):
            if health_pct <= threshold:
                target_phase = i + 2  # 75%→阶段2, 50%→阶段3, 25%→阶段4

        # 限制最高阶段
        target_phase = min(target_phase, len(self.PHASE_THRESHOLDS) + 1)

        changed = target_phase != self._current_phase
        if changed and self._current_phase > 0:
            # 只在已有阶段的基础上递增（血量下降才会换阶段）
            if target_phase > self._current_phase:
                old = self._current_phase
                self._current_phase = target_phase
                self._phase_history.append({'phase': target_phase, 'hp': health_pct, 'time': time.time()})
                logger.info(f"🔄 BOSS 阶段切换: {old} → {target_phase} (血量 {health_pct:.1f}%)")
                if self.on_phase_change:
                    self.on_phase_change(target_phase, old, health_pct)
            changed = target_phase != self._current_phase
        elif self._current_phase == 0:
            # 首次进入战斗
            self._current_phase = 1
            self._phase_history.append({'phase': 1, 'hp': health_pct, 'time': time.time()})
            logger.info(f"🔄 BOSS 进入阶段 1 (血量 {health_pct:.1f}%)")
            if self.on_phase_change:
                self.on_phase_change(1, 0, health_pct)
            changed = True

        return {
            'phase': self._current_phase,
            'changed': changed,
            'phase_name': self._phase_name(self._current_phase),
        }

    def _phase_name(self, phase):
        names = {0: '未战斗', 1: '阶段一', 2: '阶段二', 3: '阶段三', 4: '阶段四'}
        return names.get(phase, f'阶段{phase}')

    def reset(self):
        self._current_phase = 0
        self._phase_history = []

    @property
    def current_phase(self):
        """当前阶段(0=未战斗, 1=阶段一, 2=阶段二, ...)"""
        return self._current_phase


# D4 BOSS 弱点属性数据库（覆盖剧情/世界/终局天梯 BOSS）
# 元素类型: physical(物理) / fire(火焰) / cold(冰霜) / lightning(闪电) /
#           poison(毒素) / shadow(暗影) / holy(神圣)
#
# 数据来源: D4 官方资料 + 游民星空/Maxroll 攻略库
# boss_guide_7: 数据外置到 boss_data.json, 赛季改版时可直接编辑 JSON 刷新,
# 无需改动代码。JSON 不存在或损坏时回退到此内置数据。
_HARDCODED_BOSS_DB = {
    # ========== 终局 BOSS 天梯 (Endgame Boss Ladder) ==========
    '瓦尔山的回响': {
        'aliases': ['varshan', 'echo of varshan', '瓦尔山', '瓦尔申'],
        'weakness': ['holy', 'physical'],
        'resist': ['shadow'],
        'phases': 2,
        'tips': '主要造成暗影伤害,装备紫水晶宝石和暗影抗性药水;注意躲避地下触手袭击',
    },
    '电圣格里瓜尔': {
        'aliases': ['grigoire', 'galvanic saint', '格里瓜尔', '格里高尔', '电圣'],
        'weakness': ['physical'],
        'resist': ['lightning'],
        'phases': 2,
        'tips': '主要造成闪电伤害,装备黄玉宝石提升闪电抗性;注意躲避雷霆制裁技能',
    },
    '齐尔大人': {
        'aliases': ['lord zir', 'zir', '齐尔', '齐尔领主', '血腥齐尔'],
        'weakness': ['holy', 'fire'],
        'resist': ['shadow'],
        'phases': 3,
        'tips': '鲜血攻击造成暗影伤害,装备紫水晶宝石;多阶段战斗,注意躲避血池和新月斩',
    },
    '冰中的野兽': {
        'aliases': ['beast in the ice', 'beast', '冰兽', '冰中野兽'],
        'weakness': ['fire'],
        'resist': ['cold'],
        'phases': 2,
        'tips': '主要造成冰霜伤害,装备蓝宝石宝石和冰冷抗性药水;注意躲避冰柱冲击和冰冻新星',
    },
    '都瑞尔，蛆虫之王': {
        'aliases': ['duriel', 'king of maggots', '都瑞尔', '蛆虫之王'],
        'weakness': ['fire', 'cold'],
        'resist': ['poison'],
        'phases': 2,
        'tips': '主要造成毒素伤害,装备祖母绿宝石和毒抗药水;注意躲避地刺突袭和毒云区域',
    },
    '痛苦少女安达利尔': {
        'aliases': ['andariel', 'maiden of anguish', '安达利尔', '苦难之女'],
        'weakness': ['physical'],
        'resist': ['fire', 'cold', 'lightning', 'poison', 'shadow'],
        'phases': 2,
        'tips': '造成全元素伤害,装备钻石宝石提升全抗性;与都瑞尔共享 Uber Unique 战利品表',
    },
    '莉莉丝的回声': {
        'aliases': ['uber lilith', 'echo of lilith', '莉莉丝', 'uber莉莉丝', '巅峰莉莉丝'],
        'weakness': ['holy'],
        'resist': ['shadow'],
        'phases': 4,
        'tips': '巅峰BOSS(100级),多阶段战斗;注意躲避血池、红光冲锋和暗影之刃;掉落灿烂火花制作 Uber Unique',
    },
    # ========== 世界 BOSS (World Bosses) ==========
    '疫王阿沙瓦': {
        'aliases': ['ashava', '阿沙瓦', '阿煞巴', '疫王'],
        'weakness': ['fire', 'holy'],
        'resist': ['poison', 'physical'],
        'phases': 2,
        'tips': '世界BOSS,毒素+物理伤害;注意躲避毒雾喷吐、地刺和冲锋;需组队击杀,散开站位避免AOE',
    },
    '流浪死神': {
        'aliases': ['wandering death', '流浪的死亡', '死亡流浪者'],
        'weakness': ['holy', 'lightning'],
        'resist': ['shadow'],
        'phases': 2,
        'tips': '世界BOSS,暗影伤害;注意躲避死亡之握和灵魂收割;分散站位,利用硬直时间输出',
    },
    '贪婪': {
        'aliases': ['avarice', '贪婪之主', '贪婪者'],
        'weakness': ['fire', 'cold'],
        'resist': ['physical'],
        'phases': 2,
        'tips': '世界BOSS,物理伤害;注意躲避金币冲击和贪欲之握;保持距离输出,利用硬直时间',
    },
    # ========== 剧情/野外 BOSS ==========
    '屠夫': {
        'aliases': ['the butcher', 'butcher', '屠夫BOSS', '肉钩'],
        'weakness': ['fire'],
        'resist': ['physical'],
        'phases': 1,
        'tips': '野外随机遭遇,物理伤害极高;注意躲避肉钩拖拽和劈砍;血量低时会逃跑,优先击杀',
    },
    '埃利亚斯': {
        'aliases': ['elias', '以利亚斯', ' Elias'],
        'weakness': ['holy', 'fire'],
        'resist': ['shadow'],
        'phases': 3,
        'tips': '剧情BOSS,暗影+召唤伤害;注意躲避暗影新星和召唤亡灵;优先清理召唤物再集火BOSS',
    },
}

# boss_data.json 路径(与本文件同目录)
BOSS_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boss_data.json')

# 当前 BOSS 数据库(运行时从 JSON 加载, 回退到 _HARDCODED_BOSS_DB)
# 格式: {'season': str, 'bosses': {name: {aliases, weakness, resist, phases, tips}}}
BOSS_WEAKNESS_DB = dict(_HARDCODED_BOSS_DB)
_CURRENT_SEASON = '内置数据'


def load_boss_db():
    """从 boss_data.json 加载 BOSS 数据(boss_guide_7)

    JSON 格式:
        {
            "season": "炼狱大军S5",
            "bosses": {
                "都瑞尔": {"aliases": [...], "weakness": [...], ...},
                ...
            }
        }
    加载失败(文件不存在/格式错误)时回退到内置数据。
    """
    global BOSS_WEAKNESS_DB, _CURRENT_SEASON
    try:
        if not os.path.isfile(BOSS_DATA_FILE):
            return False
        with open(BOSS_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        bosses = data.get('bosses', {})
        if not isinstance(bosses, dict) or not bosses:
            logger.warning("boss_data.json 内容为空, 回退到内置数据")
            return False
        BOSS_WEAKNESS_DB = dict(bosses)
        _CURRENT_SEASON = data.get('season', '未标注赛季')
        logger.info(f"BOSS 数据已从 JSON 加载: 赛季={_CURRENT_SEASON}, BOSS 数={len(BOSS_WEAKNESS_DB)}")
        return True
    except Exception as e:
        logger.warning(f"加载 boss_data.json 失败, 回退到内置数据: {e}")
        BOSS_WEAKNESS_DB = dict(_HARDCODED_BOSS_DB)
        _CURRENT_SEASON = '内置数据'
        return False


def save_boss_db(bosses, season):
    """保存 BOSS 数据到 boss_data.json(boss_guide_7)

    供外部工具(如赛季改版同步脚本)调用,更新 BOSS 弱点数据。
    """
    try:
        data = {'season': season, 'bosses': bosses}
        with open(BOSS_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"BOSS 数据已保存到 JSON: 赛季={season}, BOSS 数={len(bosses)}")
        return True
    except Exception as e:
        logger.error(f"保存 boss_data.json 失败: {e}")
        return False


def refresh_boss_db():
    """热重载 BOSS 数据库(boss_guide_7)

    赛季改版后用户编辑 boss_data.json, 调用此函数刷新内存数据,
    无需重启程序。返回 (是否成功, 赛季名, BOSS 数)。
    """
    ok = load_boss_db()
    return ok, _CURRENT_SEASON, len(BOSS_WEAKNESS_DB)


def get_boss_db_season():
    """获取当前 BOSS 数据对应的赛季标识(boss_guide_7)"""
    return _CURRENT_SEASON


def export_hardcoded_db_to_json():
    """将内置 BOSS 数据导出为 boss_data.json(boss_guide_7)

    首次使用或重置时调用, 生成可编辑的 JSON 模板。
    """
    return save_boss_db(_HARDCODED_BOSS_DB, '内置数据(导出)')


# 启动时自动加载 JSON(若存在)
load_boss_db()

# 元素中英文映射
ELEMENT_NAMES = {
    'physical': '物理',
    'fire': '火焰',
    'cold': '冰霜',
    'lightning': '闪电',
    'poison': '毒素',
    'shadow': '暗影',
    'holy': '神圣',
}

# 克制词条推荐
ELEMENT_AFFIXES = {
    'physical': ['物理伤害%', '近战伤害%', '暴击伤害'],
    'fire': ['火焰伤害%', '元素伤害%', '易伤'],
    'cold': ['冰霜伤害%', '冰冷效果', '减速增强'],
    'lightning': ['闪电伤害%', '连锁伤害%', '暴击率'],
    'poison': ['毒素伤害%', '持续伤害%', '中毒增强'],
    'shadow': ['暗影伤害%', '持续伤害%', '生命吸取'],
    'holy': ['神圣伤害%', '对恶魔伤害%', '易伤'],
}


def _build_common_chars():
    """统计在 >=2 个 BOSS 中出现的中文字符(通用字),用于过滤干扰

    通用字如"的、尔、回、响、王"在多个 BOSS 名中重复出现,
    作为关键字会导致误匹配(如"回响"同时出现在瓦尔山和齐尔领主的折磨回响)。
    """
    char_bosses = {}
    for boss_name, data in BOSS_WEAKNESS_DB.items():
        all_names = [boss_name] + data.get('aliases', [])
        chars_in_boss = set()
        for n in all_names:
            for c in n:
                if '\u4e00' <= c <= '\u9fff':
                    chars_in_boss.add(c)
        for c in chars_in_boss:
            char_bosses.setdefault(c, set()).add(boss_name)
    return {c for c, bosses in char_bosses.items() if len(bosses) >= 2}


def lookup_boss(name):
    """根据 BOSS 名字查询弱点属性（支持别名匹配 + OCR 容错匹配）

    匹配优先级:
    1. 精确匹配(忽略大小写)
    2. 别名子串匹配(OCR 文本包含任一别名)
    3. OCR 容错匹配: 基于别名"独有字"命中数(排除通用字干扰)

    OCR 容错匹配策略:
    - 预计算通用字(在 >=2 个 BOSS 中出现的字,如"的/尔/回/响")
    - 对每个别名(含 BOSS 名)单独计算独有字命中数
    - 取所有别名中命中数最高的作为 BOSS 得分
    - 优先匹配命中数最多的 BOSS
    - 应对 OCR 把"齐尔领主"识别成"齐示领王"等情况

    Returns:
        dict|None: BOSS 属性信息，未找到返回 None
    """
    if not name:
        return None
    name_lower = name.lower().strip()

    # 1. 精确匹配 + 别名子串匹配
    for boss_name, data in BOSS_WEAKNESS_DB.items():
        if name == boss_name or name_lower == boss_name.lower():
            return {'name': boss_name, **data}
        for alias in data.get('aliases', []):
            if name_lower == alias.lower() or alias.lower() in name_lower:
                return {'name': boss_name, **data}

    # 2. OCR 容错匹配: 基于别名"独有字"命中数
    common_chars = _build_common_chars()

    best_match = None
    best_hit_count = 0   # 独有字命中数(绝对值,优先比较)
    best_hit_rate = 0.0  # 命中率(命中数相同时比较)

    for boss_name, data in BOSS_WEAKNESS_DB.items():
        # BOSS 名 + 所有别名都参与匹配,取最高分
        all_aliases = [boss_name] + data.get('aliases', [])
        for alias in all_aliases:
            # 提取别名的独有中文字(排除通用字)
            alias_unique = [c for c in alias
                            if '\u4e00' <= c <= '\u9fff' and c not in common_chars]
            if len(alias_unique) < 2:
                continue

            hit_count = sum(1 for c in alias_unique if c in name)
            if hit_count == 0:
                continue
            hit_rate = hit_count / len(alias_unique)

            # 阈值: 独有字命中数 >= 2,且命中率 >= 0.5
            # (避免独有字仅 2 个时命中 1 个就匹配,如"瓦尔山的回响"独有字['山','响']
            #   OCR 乱码命中"响"1 个,命中率 0.5 不应匹配)
            if hit_count >= 2 and hit_rate >= 0.5:
                # 优先看命中数(绝对值),再看命中率
                if (hit_count > best_hit_count or
                        (hit_count == best_hit_count and hit_rate > best_hit_rate)):
                    best_hit_count = hit_count
                    best_hit_rate = hit_rate
                    best_match = {'name': boss_name, **data}

    if best_match:
        return best_match

    return None


def recommend_affixes(boss_data):
    """根据 BOSS 弱点推荐克制词条

    Returns:
        dict: {'weakness_affixes': [...], 'avoid_affixes': [...], 'tips': str}
    """
    if not boss_data:
        return {'weakness_affixes': [], 'avoid_affixes': [], 'tips': ''}

    weakness_affixes = []
    for elem in boss_data.get('weakness', []):
        weakness_affixes.extend(ELEMENT_AFFIXES.get(elem, []))

    avoid_affixes = []
    for elem in boss_data.get('resist', []):
        avoid_affixes.extend(ELEMENT_AFFIXES.get(elem, []))

    return {
        'weakness_affixes': list(dict.fromkeys(weakness_affixes)),  # 去重保序
        'avoid_affixes': list(dict.fromkeys(avoid_affixes)),
        'weakness_elements': [ELEMENT_NAMES.get(e, e) for e in boss_data.get('weakness', [])],
        'resist_elements': [ELEMENT_NAMES.get(e, e) for e in boss_data.get('resist', [])],
        'tips': boss_data.get('tips', ''),
    }


# ===================== 预生成音频查找 =====================

_AUDIO_INDEX_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'resources', 'audio', 'bosses', 'audio_index.json'
)
_AUDIO_INDEX_CACHE = None
_AUDIO_INDEX_MTIME = 0


def _load_audio_index():
    """加载音频索引(带缓存,文件变更时自动重载)"""
    global _AUDIO_INDEX_CACHE, _AUDIO_INDEX_MTIME
    try:
        mtime = os.path.getmtime(_AUDIO_INDEX_PATH)
    except OSError:
        return {}
    if _AUDIO_INDEX_CACHE is not None and mtime == _AUDIO_INDEX_MTIME:
        return _AUDIO_INDEX_CACHE
    try:
        with open(_AUDIO_INDEX_PATH, 'r', encoding='utf-8') as f:
            _AUDIO_INDEX_CACHE = json.load(f)
        _AUDIO_INDEX_MTIME = mtime
        logger.info(f"[BOSS-Audio] 音频索引已加载: {len(_AUDIO_INDEX_CACHE)} 个 BOSS")
        return _AUDIO_INDEX_CACHE
    except Exception as e:
        logger.warning(f"[BOSS-Audio] 音频索引加载失败: {e}")
        return {}


def get_boss_audio(boss_name, segment='intro'):
    """查找 BOSS 的预生成音频文件路径

    Args:
        boss_name: BOSS 名字(支持别名匹配,复用 lookup_boss 逻辑)
        segment: 音频分段名 ('intro'/'phase1'/'phase2'/'phase3'/'outro')

    Returns:
        str|None: 音频文件绝对路径,未找到返回 None
    """
    index = _load_audio_index()
    if not index:
        return None

    # 先用 lookup_boss 找到 BOSS 的标准 key
    boss_data = lookup_boss(boss_name)
    if not boss_data:
        return None

    boss_key = boss_data.get('name', '')
    entry = index.get(boss_key)
    if not entry:
        return None

    segments = entry.get('segments', [])
    for seg in segments:
        if seg['name'] == segment:
            audio_path = os.path.join(
                os.path.dirname(_AUDIO_INDEX_PATH),
                seg['filename']
            )
            if os.path.isfile(audio_path):
                return audio_path
            logger.warning(f"[BOSS-Audio] 音频文件不存在: {seg['filename']}")
            return None

    logger.debug(f"[BOSS-Audio] 找不到分段 '{segment}' (BOSS={boss_key})")
    return None


def get_boss_audio_segments(boss_name):
    """获取 BOSS 的所有音频分段信息

    Returns:
        list[str]: 可用的分段名列表(如 ['intro','phase1','phase2','phase3','outro'])
    """
    index = _load_audio_index()
    if not index:
        return []
    boss_data = lookup_boss(boss_name)
    if not boss_data:
        return []
    boss_key = boss_data.get('name', '')
    entry = index.get(boss_key)
    if not entry:
        return []
    return [seg['name'] for seg in entry.get('segments', [])]


def get_common_audio(name):
    """获取通用提示音路径

    Args:
        name: 'boss_start' / 'boss_end'

    Returns:
        str|None: 音频文件路径,未找到返回 None
    """
    audio_dir = os.path.dirname(_AUDIO_INDEX_PATH)
    path = os.path.join(audio_dir, f'_common_{name}.mp3')
    if os.path.isfile(path):
        return path
    return None


class BossSkillDetector:
    """BOSS 技能前摇检测器 - 基于画面亮色区域检测(boss_guide_2)

    检测画面中央区域的高亮度像素（技能特效通常很亮），
    当亮色区域超过阈值时判断为技能施放，触发预警。

    注: 此为 CV 基础版本，后续可集成 SDK BAR 服务提升精度。
    """

    # 技能特效检测区域（画面中央，BOSS 和技能特效通常在中央）
    SKILL_EFFECT_REGION = {'x': 0.20, 'y': 0.25, 'w': 0.60, 'h': 0.45}

    # 亮色区域面积阈值（占检测区域的比例）
    EFFECT_AREA_THRESHOLD = 0.05

    # 预警冷却时间（秒），避免频繁预警
    WARNING_COOLDOWN = 8.0

    def __init__(self):
        self._last_warning_time = 0.0

    def detect(self, frame):
        """检测画面中的 BOSS 技能特效

        Returns:
            dict: {
                'detected': bool,       # 是否检测到技能特效
                'area_ratio': float,    # 亮色区域占比
                'warning': str|None,    # 预警消息(检测到时)
            }
        """
        if frame is None or frame.size == 0:
            return {'detected': False, 'area_ratio': 0.0, 'warning': None}

        h, w = frame.shape[:2]
        region = self.SKILL_EFFECT_REGION
        x1 = int(region['x'] * w)
        y1 = int(region['y'] * h)
        x2 = int((region['x'] + region['w']) * w)
        y2 = int((region['y'] + region['h']) * h)
        crop = frame[y1:y2, x1:x2]

        if crop.size == 0:
            return {'detected': False, 'area_ratio': 0.0, 'warning': None}

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        # 检测高亮度像素（V >= 200），技能特效如火球/闪电/光柱通常很亮
        bright_mask = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 100, 255]))
        # 形态学开运算去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        bright_mask = cv2.morphologyEx(bright_mask, cv2.MORPH_OPEN, kernel)

        bright_ratio = np.count_nonzero(bright_mask) / bright_mask.size

        if bright_ratio > self.EFFECT_AREA_THRESHOLD:
            now = time.time()
            if now - self._last_warning_time > self.WARNING_COOLDOWN:
                self._last_warning_time = now
                logger.info(f"[BOSS] 技能特效检测: 亮色区域 {bright_ratio:.1%} > {self.EFFECT_AREA_THRESHOLD:.0%}")
                return {
                    'detected': True,
                    'area_ratio': round(bright_ratio, 3),
                    'warning': '⚠️ 检测到技能特效! 注意躲避!',
                }

        return {'detected': False, 'area_ratio': round(bright_ratio, 3), 'warning': None}
