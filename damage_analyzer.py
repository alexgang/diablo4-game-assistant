#!/usr/bin/env python3
"""
伤害记录统计分析模块 - 从游戏画面捕获伤害数据并分析

功能：
1. 屏幕伤害数字捕获：通过OCR识别屏幕上的伤害数字
2. 伤害日志解析：解析D4高级战斗日志文本
3. 伤害统计：DPS、暴击率、伤害分布、技能占比
4. 攻略比对：与数据库中的构筑推荐数据比对
5. 优化建议：根据分析结果给出装备/技能调整建议

D4高级战斗日志格式参考：
  [Player] 野蛮人 施放 旋风斩 对 [Enemy] 恶魔 命中 造成 1,234,567 点伤害 (暴击)
  [Player] 野蛮人 施放 先祖召唤 对 [Enemy] BOSS 命中 造成 5,678,901 点伤害
  [Player] 野蛮人 受到 [Enemy] 恶魔 攻击 造成 12,345 点伤害
"""

import re
import time
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field

from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG

logger = logging.getLogger(__name__)

DAMAGE_PATTERNS = [
    re.compile(r'施放\s+(\S+)\s+.*?造成\s+([\d,]+)\s+点伤害\s*\(?(暴击)\)?', re.IGNORECASE),
    re.compile(r'施放\s+(\S+)\s+.*?造成\s+([\d,]+)\s+点伤害', re.IGNORECASE),
    re.compile(r'(\S+)\s+.*?命中.*?造成\s+([\d,]+)\s+点伤害\s*\(?(暴击)\)?', re.IGNORECASE),
    re.compile(r'(\S+)\s+.*?命中.*?造成\s+([\d,]+)\s+点伤害', re.IGNORECASE),
    re.compile(r'(\S+)\s+.*?造成\s+([\d,]+)\s+点伤害', re.IGNORECASE),
    re.compile(r'(\S+)\s+对.*?造成\s+([\d,]+)', re.IGNORECASE),
]

SCREEN_DAMAGE_PATTERN = re.compile(r'[\d,]+')
NUMBER_PATTERN = re.compile(r'[\d,]+')


@dataclass
class DamageEvent:
    skill_name: str = ''
    damage: int = 0
    is_crit: bool = False
    timestamp: float = 0.0
    target: str = ''
    source: str = 'player'


@dataclass
class DamageSession:
    events: list = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    total_damage: int = 0
    duration_seconds: float = 0.0

    def add_event(self, event):
        self.events.append(event)
        if event.source == 'player':
            self.total_damage += event.damage
        if self.start_time == 0.0:
            self.start_time = event.timestamp
        self.end_time = event.timestamp
        self.duration_seconds = self.end_time - self.start_time if self.start_time else 0.0


class DamageLogParser:
    """伤害日志解析器"""

    def __init__(self):
        self.player_class = ''

    def parse_line(self, line):
        """解析单行战斗日志"""
        line = line.strip()
        if not line:
            return None

        if '受到' in line and '攻击' in line:
            return self._parse_received_damage(line)

        for pattern in DAMAGE_PATTERNS:
            match = pattern.search(line)
            if match:
                groups = match.groups()
                skill_name = groups[0] if groups[0] else '普通攻击'
                damage_str = groups[1] if len(groups) > 1 else '0'
                is_crit = bool(groups[2]) if len(groups) > 2 else False

                try:
                    damage = int(damage_str.replace(',', ''))
                except ValueError:
                    continue

                target = ''
                target_match = re.search(r'\[Enemy\]\s*(\S+)', line)
                if target_match:
                    target = target_match.group(1)

                return DamageEvent(
                    skill_name=skill_name,
                    damage=damage,
                    is_crit=is_crit,
                    timestamp=time.time(),
                    target=target,
                    source='player',
                )

        return None

    def _parse_received_damage(self, line):
        """解析受到的伤害"""
        damage_match = re.search(r'造成\s+([\d,]+)\s+点伤害', line)
        if not damage_match:
            return None

        try:
            damage = int(damage_match.group(1).replace(',', ''))
        except ValueError:
            return None

        source_match = re.search(r'\[Enemy\]\s*(\S+)', line)
        source_name = source_match.group(1) if source_match else '未知'

        return DamageEvent(
            skill_name=source_name,
            damage=damage,
            is_crit=False,
            timestamp=time.time(),
            target='player',
            source='enemy',
        )

    def parse_text(self, text):
        """解析多行战斗日志文本"""
        events = []
        for line in text.split('\n'):
            event = self.parse_line(line)
            if event:
                events.append(event)
        return events

    def parse_screen_numbers(self, ocr_text):
        """从OCR识别的屏幕文字中提取伤害数字"""
        numbers = []
        matches = NUMBER_PATTERN.findall(ocr_text)
        for num_str in matches:
            try:
                num = int(num_str.replace(',', ''))
                if num >= 10:
                    numbers.append(num)
            except ValueError:
                continue
        return numbers


class DamageStatistics:
    """伤害统计分析"""

    def __init__(self):
        self.session = DamageSession()
        self._skill_damage = defaultdict(lambda: {'total': 0, 'count': 0, 'crits': 0, 'max': 0, 'min': float('inf')})
        self._target_damage = defaultdict(int)
        self._damage_timeline = []

    def add_event(self, event):
        """添加伤害事件"""
        self.session.add_event(event)

        if event.source == 'player' and event.skill_name:
            stats = self._skill_damage[event.skill_name]
            stats['total'] += event.damage
            stats['count'] += 1
            if event.is_crit:
                stats['crits'] += 1
            stats['max'] = max(stats['max'], event.damage)
            stats['min'] = min(stats['min'], event.damage)

        if event.target and event.source == 'player':
            self._target_damage[event.target] += event.damage

        self._damage_timeline.append({
            'time': event.timestamp,
            'damage': event.damage if event.source == 'player' else 0,
            'skill': event.skill_name,
            'crit': event.is_crit,
        })

    def add_events(self, events):
        """批量添加伤害事件"""
        for event in events:
            self.add_event(event)

    def get_dps(self):
        """计算总DPS"""
        if self.session.duration_seconds <= 0:
            return 0.0
        return self.session.total_damage / self.session.duration_seconds

    def get_crit_rate(self):
        """计算总暴击率"""
        total_hits = sum(s['count'] for s in self._skill_damage.values())
        total_crits = sum(s['crits'] for s in self._skill_damage.values())
        if total_hits == 0:
            return 0.0
        return total_crits / total_hits

    def get_skill_breakdown(self):
        """获取技能伤害分布"""
        if self.session.total_damage == 0:
            return {}

        breakdown = {}
        for skill, stats in sorted(self._skill_damage.items(), key=lambda x: x[1]['total'], reverse=True):
            pct = (stats['total'] / self.session.total_damage) * 100
            avg = stats['total'] / stats['count'] if stats['count'] > 0 else 0
            crit_rate = (stats['crits'] / stats['count'] * 100) if stats['count'] > 0 else 0
            breakdown[skill] = {
                'total_damage': stats['total'],
                'percentage': round(pct, 1),
                'hit_count': stats['count'],
                'avg_damage': round(avg),
                'max_damage': stats['max'],
                'min_damage': stats['min'] if stats['min'] != float('inf') else 0,
                'crit_count': stats['crits'],
                'crit_rate': round(crit_rate, 1),
            }
        return breakdown

    def get_top_skill(self):
        """获取伤害最高的技能"""
        if not self._skill_damage:
            return None
        top = max(self._skill_damage.items(), key=lambda x: x[1]['total'])
        return top[0]

    def get_damage_received(self):
        """获取受到的总伤害"""
        return sum(e.damage for e in self.session.events if e.source == 'enemy')

    def get_summary(self):
        """获取伤害统计摘要"""
        return {
            'total_damage': self.session.total_damage,
            'duration': round(self.session.duration_seconds, 1),
            'dps': round(self.get_dps()),
            'crit_rate': round(self.get_crit_rate() * 100, 1),
            'total_hits': sum(s['count'] for s in self._skill_damage.values()),
            'skill_count': len(self._skill_damage),
            'top_skill': self.get_top_skill(),
            'damage_received': self.get_damage_received(),
            'skill_breakdown': self.get_skill_breakdown(),
        }

    def reset(self):
        """重置统计"""
        self.session = DamageSession()
        self._skill_damage = defaultdict(lambda: {'total': 0, 'count': 0, 'crits': 0, 'max': 0, 'min': float('inf')})
        self._target_damage = defaultdict(int)
        self._damage_timeline = []


class BuildComparator:
    """构筑比对器 - 将实际伤害数据与攻略推荐比对"""

    BENCHMARK_DPS = {
        '野蛮人': {'low': 500000, 'mid': 2000000, 'high': 5000000, 'top': 10000000},
        '巫师': {'low': 400000, 'mid': 1800000, 'high': 4500000, 'top': 9000000},
        '德鲁伊': {'low': 450000, 'mid': 1700000, 'high': 4000000, 'top': 8000000},
        '游侠': {'low': 400000, 'mid': 1900000, 'high': 4800000, 'top': 9500000},
        '死灵法师': {'low': 420000, 'mid': 1800000, 'high': 4200000, 'top': 8500000},
        '灵巫': {'low': 450000, 'mid': 2000000, 'high': 5000000, 'top': 10000000},
    }

    CRIT_RATE_BENCHMARK = {'low': 25, 'mid': 40, 'high': 55, 'top': 65}

    def __init__(self, content_indexer=None):
        self.indexer = content_indexer

    def evaluate_dps(self, dps, class_name=''):
        """评估DPS等级"""
        benchmarks = self.BENCHMARK_DPS.get(class_name, self.BENCHMARK_DPS.get('野蛮人'))

        if dps >= benchmarks['top']:
            return {'tier': 'S', 'label': '顶尖', 'color': '#ff8000'}
        elif dps >= benchmarks['high']:
            return {'tier': 'A', 'label': '优秀', 'color': '#bf642f'}
        elif dps >= benchmarks['mid']:
            return {'tier': 'B', 'label': '良好', 'color': '#4ade80'}
        elif dps >= benchmarks['low']:
            return {'tier': 'C', 'label': '一般', 'color': '#ffff00'}
        else:
            return {'tier': 'D', 'label': '需提升', 'color': '#ff4444'}

    def evaluate_crit_rate(self, crit_rate):
        """评估暴击率等级"""
        if crit_rate >= self.CRIT_RATE_BENCHMARK['top']:
            return {'tier': 'S', 'label': '顶尖'}
        elif crit_rate >= self.CRIT_RATE_BENCHMARK['high']:
            return {'tier': 'A', 'label': '优秀'}
        elif crit_rate >= self.CRIT_RATE_BENCHMARK['mid']:
            return {'tier': 'B', 'label': '良好'}
        elif crit_rate >= self.CRIT_RATE_BENCHMARK['low']:
            return {'tier': 'C', 'label': '一般'}
        else:
            return {'tier': 'D', 'label': '需提升'}

    def compare_with_builds(self, stats_summary, class_name=''):
        """与攻略构筑数据比对"""
        recommendations = []

        dps = stats_summary.get('dps', 0)
        crit_rate = stats_summary.get('crit_rate', 0)
        skill_breakdown = stats_summary.get('skill_breakdown', {})
        top_skill = stats_summary.get('top_skill', '')

        dps_eval = self.evaluate_dps(dps, class_name)
        crit_eval = self.evaluate_crit_rate(crit_rate)

        if dps_eval['tier'] in ('D', 'C'):
            recommendations.append({
                'type': 'dps_low',
                'severity': 'high',
                'message': f"DPS评级 {dps_eval['tier']}（{dps_eval['label']}），建议优化装备和技能搭配",
                'suggestions': self._dps_improvement_suggestions(stats_summary, class_name),
            })

        if crit_eval['tier'] in ('D', 'C'):
            recommendations.append({
                'type': 'crit_low',
                'severity': 'medium',
                'message': f"暴击率 {crit_rate:.1f}% 评级 {crit_eval['tier']}，建议增加暴击率属性",
                'suggestions': [
                    '装备选择暴击率词缀',
                    '巅峰盘点出暴击节点',
                    '使用增加暴击率的技能增益',
                ],
            })

        if skill_breakdown:
            top_pct = list(skill_breakdown.values())[0].get('percentage', 0)
            if top_pct > 80:
                recommendations.append({
                    'type': 'skill_monotone',
                    'severity': 'low',
                    'message': f"技能分布过于集中（{top_skill} 占 {top_pct:.1f}%），可能存在更优搭配",
                    'suggestions': [
                        '检查是否有技能增益未生效',
                        '尝试搭配增伤辅助技能',
                    ],
                })

        if not recommendations:
            recommendations.append({
                'type': 'good',
                'severity': 'none',
                'message': f"当前表现评级 {dps_eval['tier']}（{dps_eval['label']}），继续保持！",
                'suggestions': [],
            })

        return {
            'dps_evaluation': dps_eval,
            'crit_evaluation': crit_eval,
            'recommendations': recommendations,
        }

    def _dps_improvement_suggestions(self, stats_summary, class_name):
        """生成DPS提升建议"""
        suggestions = []

        if self.indexer:
            results = self.indexer.search(f'{class_name} 构筑 推荐', top_n=3, categories=['build_details'])
            if results:
                for r in results[:2]:
                    title = r['data'].get('title', '')
                    if title:
                        suggestions.append(f"参考构筑: {title}")

        suggestions.extend([
            '检查装备是否为当前版本最优',
            '确保巅峰盘核心节点已点出',
            '优化技能循环，减少空档期',
            '升级装备宝石和附魔',
        ])

        return suggestions[:5]


class DamageMonitor:
    """伤害监控器 - 持续监控并分析伤害"""

    def __init__(self, ocr_recognizer=None, content_indexer=None, use_sdk_bar=True):
        self.ocr = ocr_recognizer
        self.parser = DamageLogParser()
        self.stats = DamageStatistics()
        self.comparator = BuildComparator(content_indexer=content_indexer)
        self.is_monitoring = False
        self._monitor_thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.player_class = ''
        self._log_buffer = []
        self._last_ocr_time = 0.0

        self.bar_available = False
        self._sdk = None
        self._bar_instance_id = None
        self._boss_id = SDK_CONFIG.get('bar_boss_id', 'default_boss')
        self._k_actions = SDK_CONFIG.get('bar_k_actions', 3)
        self._last_bar_result = None

        if use_sdk_bar:
            try:
                self._sdk = GamingAssistantSDK()
                if self._sdk.check_server():
                    self._bar_instance_id = self._sdk.bar_init(SDK_CONFIG.get('instance_id', 'default'))
                    self.bar_available = True
                    logger.info("SDK BAR 服务初始化成功")
                else:
                    logger.warning("SDK BAR 服务不可用")
            except Exception as e:
                self.bar_available = False
                logger.warning(f"SDK BAR 服务初始化失败: {e}")

    def start_monitoring(self, callback=None):
        """开始监控"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self._stop_event.clear()
        self.on_update = callback

        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("伤害监控已启动")

    def stop_monitoring(self):
        """停止监控"""
        self._stop_event.set()
        self.is_monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("伤害监控已停止")

    def _monitor_loop(self):
        """监控循环"""
        while not self._stop_event.is_set():
            try:
                self._capture_and_analyze()
            except Exception as e:
                logger.error(f"伤害监控异常: {e}")
            self._stop_event.wait(1.0)

    def _capture_and_analyze(self):
        """捕获并分析伤害数据"""
        if not self.ocr or not self.ocr.ocr.available:
            return

        bar_result = None

        try:
            from screen_capture import ScreenCapture
            capture = ScreenCapture()
            img = capture.capture_full_screen()

            from config import D4_REGIONS
            chat_region = D4_REGIONS.get('chat_area', {})
            if chat_region:
                h, w = img.shape[:2]
                region = (
                    int(chat_region.get('x_ratio', 0) * w),
                    int(chat_region.get('y_ratio', 0) * h),
                    int(chat_region.get('w_ratio', 0.25) * w),
                    int(chat_region.get('h_ratio', 0.4) * h),
                )
                text = self.ocr.ocr.extract_text(img, region=region, preprocess='dark')
            else:
                text = self.ocr.ocr.extract_text(img, preprocess='dark')

            if self.bar_available:
                try:
                    import tempfile
                    import cv2
                    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                    cv2.imwrite(tmp.name, img)
                    tmp.close()
                    bar_result = self.recognize_boss_action(tmp.name)
                except Exception as e:
                    logger.error(f"BAR 帧分析失败: {e}")

            if text:
                events = self.parser.parse_text(text)
                if events:
                    with self._lock:
                        self.stats.add_events(events)

                    if self.on_update:
                        self.on_update(self.get_report())

            if bar_result:
                if self.on_update:
                    report = self.get_report()
                    report['boss_action'] = bar_result
                    self.on_update(report)

        except Exception as e:
            logger.error(f"伤害捕获失败: {e}")

    def recognize_boss_action(self, frame_path):
        """通过SDK BAR服务识别Boss动作"""
        if not self.bar_available or not self._sdk:
            return None

        try:
            result = self._sdk.bar_query(
                self._bar_instance_id,
                self._boss_id,
                frame_path,
                self._k_actions,
            )
            self._last_bar_result = result
            return {
                'boss_id': result.get('boss_id', self._boss_id),
                'action_id': result.get('action_id', ''),
                'score': result.get('score', 0.0),
            }
        except Exception as e:
            logger.error(f"BAR 识别失败: {e}")
            return None

    def get_boss_status(self):
        """获取当前Boss识别状态"""
        return {
            'bar_available': self.bar_available,
            'boss_id': self._boss_id,
            'last_result': self._last_bar_result,
        }

    def feed_log_text(self, text):
        """手动输入日志文本进行分析"""
        events = self.parser.parse_text(text)
        if events:
            with self._lock:
                self.stats.add_events(events)
        return events

    def feed_screen_numbers(self, numbers):
        """输入从屏幕识别的伤害数字"""
        events = []
        now = time.time()
        for num in numbers:
            event = DamageEvent(
                skill_name='未知技能',
                damage=num,
                is_crit=False,
                timestamp=now,
                source='player',
            )
            events.append(event)

        with self._lock:
            self.stats.add_events(events)
        return events

    def get_report(self):
        """获取伤害分析报告"""
        with self._lock:
            summary = self.stats.get_summary()
            comparison = self.comparator.compare_with_builds(summary, self.player_class)

        return {
            'summary': summary,
            'comparison': comparison,
            'player_class': self.player_class,
            'monitoring': self.is_monitoring,
        }

    def reset(self):
        """重置统计数据"""
        with self._lock:
            self.stats.reset()

    def set_player_class(self, class_name):
        """设置玩家职业"""
        self.player_class = class_name
