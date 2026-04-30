import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from damage_analyzer import (
    DamageEvent, DamageSession, DamageLogParser,
    DamageStatistics, BuildComparator, DamageMonitor,
)
from config import DAMAGE_CONFIG


class TestDamageEvent:
    def test_create_event(self):
        event = DamageEvent(
            skill_name='旋风斩',
            damage=1234567,
            is_crit=True,
            timestamp=time.time(),
            source='player',
        )
        assert event.skill_name == '旋风斩'
        assert event.damage == 1234567
        assert event.is_crit is True
        assert event.source == 'player'

    def test_default_values(self):
        event = DamageEvent()
        assert event.skill_name == ''
        assert event.damage == 0
        assert event.is_crit is False
        assert event.source == 'player'


class TestDamageSession:
    def test_add_event(self):
        session = DamageSession()
        event = DamageEvent(skill_name='旋风斩', damage=1000, timestamp=time.time(), source='player')
        session.add_event(event)
        assert session.total_damage == 1000
        assert len(session.events) == 1

    def test_total_damage_player_only(self):
        session = DamageSession()
        session.add_event(DamageEvent(damage=1000, timestamp=time.time(), source='player'))
        session.add_event(DamageEvent(damage=500, timestamp=time.time(), source='enemy'))
        assert session.total_damage == 1000

    def test_duration(self):
        session = DamageSession()
        t1 = time.time()
        session.add_event(DamageEvent(damage=100, timestamp=t1, source='player'))
        session.add_event(DamageEvent(damage=200, timestamp=t1 + 10, source='player'))
        assert session.duration_seconds == pytest.approx(10.0, abs=0.1)


class TestDamageLogParser:
    def setup_method(self):
        self.parser = DamageLogParser()

    def test_parse_skill_damage(self):
        line = '[Player] 野蛮人 施放 旋风斩 对 [Enemy] 恶魔 命中 造成 1,234,567 点伤害'
        event = self.parser.parse_line(line)
        assert event is not None
        assert event.skill_name == '旋风斩'
        assert event.damage == 1234567
        assert event.source == 'player'

    def test_parse_crit_damage(self):
        line = '[Player] 野蛮人 施放 旋风斩 对 [Enemy] 恶魔 命中 造成 1,234,567 点伤害 (暴击)'
        event = self.parser.parse_line(line)
        assert event is not None
        assert event.is_crit is True
        assert event.damage == 1234567

    def test_parse_received_damage(self):
        line = '[Player] 野蛮人 受到 [Enemy] 恶魔 攻击 造成 12,345 点伤害'
        event = self.parser.parse_line(line)
        assert event is not None
        assert event.source == 'enemy'
        assert event.damage == 12345

    def test_parse_empty_line(self):
        assert self.parser.parse_line('') is None
        assert self.parser.parse_line('   ') is None

    def test_parse_non_damage_line(self):
        assert self.parser.parse_line('玩家进入了游戏') is None

    def test_parse_text_multiline(self):
        text = (
            '[Player] 野蛮人 施放 旋风斩 对 [Enemy] 恶魔 命中 造成 1,000,000 点伤害\n'
            '[Player] 野蛮人 施放 先祖召唤 对 [Enemy] BOSS 命中 造成 5,000,000 点伤害 (暴击)\n'
            '普通文本行\n'
        )
        events = self.parser.parse_text(text)
        assert len(events) == 2
        assert events[0].skill_name == '旋风斩'
        assert events[1].skill_name == '先祖召唤'
        assert events[1].is_crit is True

    def test_parse_screen_numbers(self):
        text = '伤害 1,234,567 暴击 999,999 治疗 50'
        numbers = self.parser.parse_screen_numbers(text)
        assert 1234567 in numbers
        assert 999999 in numbers


class TestDamageStatistics:
    def setup_method(self):
        self.stats = DamageStatistics()

    def test_add_events(self):
        events = [
            DamageEvent(skill_name='旋风斩', damage=1000, is_crit=True, timestamp=time.time(), source='player'),
            DamageEvent(skill_name='旋风斩', damage=800, is_crit=False, timestamp=time.time(), source='player'),
            DamageEvent(skill_name='战吼', damage=200, is_crit=False, timestamp=time.time(), source='player'),
        ]
        self.stats.add_events(events)
        summary = self.stats.get_summary()
        assert summary['total_damage'] == 2000
        assert summary['total_hits'] == 3

    def test_dps_calculation(self):
        t = time.time()
        self.stats.add_event(DamageEvent(skill_name='A', damage=1000, timestamp=t, source='player'))
        self.stats.add_event(DamageEvent(skill_name='A', damage=1000, timestamp=t + 10, source='player'))
        summary = self.stats.get_summary()
        assert summary['dps'] == pytest.approx(200, abs=5)

    def test_crit_rate(self):
        self.stats.add_event(DamageEvent(skill_name='A', damage=100, is_crit=True, timestamp=time.time(), source='player'))
        self.stats.add_event(DamageEvent(skill_name='A', damage=100, is_crit=False, timestamp=time.time(), source='player'))
        self.stats.add_event(DamageEvent(skill_name='A', damage=100, is_crit=True, timestamp=time.time(), source='player'))
        summary = self.stats.get_summary()
        assert summary['crit_rate'] == pytest.approx(66.7, abs=0.5)

    def test_skill_breakdown(self):
        self.stats.add_event(DamageEvent(skill_name='旋风斩', damage=1000, is_crit=True, timestamp=time.time(), source='player'))
        self.stats.add_event(DamageEvent(skill_name='战吼', damage=500, is_crit=False, timestamp=time.time(), source='player'))
        breakdown = self.stats.get_skill_breakdown()
        assert '旋风斩' in breakdown
        assert breakdown['旋风斩']['percentage'] == pytest.approx(66.7, abs=0.5)
        assert breakdown['战吼']['percentage'] == pytest.approx(33.3, abs=0.5)

    def test_top_skill(self):
        self.stats.add_event(DamageEvent(skill_name='旋风斩', damage=1000, timestamp=time.time(), source='player'))
        self.stats.add_event(DamageEvent(skill_name='战吼', damage=200, timestamp=time.time(), source='player'))
        assert self.stats.get_top_skill() == '旋风斩'

    def test_damage_received(self):
        self.stats.add_event(DamageEvent(damage=1000, timestamp=time.time(), source='player'))
        self.stats.add_event(DamageEvent(damage=500, timestamp=time.time(), source='enemy'))
        assert self.stats.get_damage_received() == 500

    def test_reset(self):
        self.stats.add_event(DamageEvent(skill_name='A', damage=1000, timestamp=time.time(), source='player'))
        self.stats.reset()
        summary = self.stats.get_summary()
        assert summary['total_damage'] == 0
        assert summary['total_hits'] == 0

    def test_empty_summary(self):
        summary = self.stats.get_summary()
        assert summary['total_damage'] == 0
        assert summary['dps'] == 0
        assert summary['crit_rate'] == 0
        assert summary['top_skill'] is None


class TestBuildComparator:
    def setup_method(self):
        self.comparator = BuildComparator()

    def test_evaluate_dps_s_tier(self):
        result = self.comparator.evaluate_dps(12000000, '野蛮人')
        assert result['tier'] == 'S'

    def test_evaluate_dps_a_tier(self):
        result = self.comparator.evaluate_dps(6000000, '野蛮人')
        assert result['tier'] == 'A'

    def test_evaluate_dps_b_tier(self):
        result = self.comparator.evaluate_dps(2500000, '野蛮人')
        assert result['tier'] == 'B'

    def test_evaluate_dps_c_tier(self):
        result = self.comparator.evaluate_dps(700000, '野蛮人')
        assert result['tier'] == 'C'

    def test_evaluate_dps_d_tier(self):
        result = self.comparator.evaluate_dps(100000, '野蛮人')
        assert result['tier'] == 'D'

    def test_evaluate_crit_rate(self):
        assert self.comparator.evaluate_crit_rate(70)['tier'] == 'S'
        assert self.comparator.evaluate_crit_rate(60)['tier'] == 'A'
        assert self.comparator.evaluate_crit_rate(50)['tier'] == 'B'
        assert self.comparator.evaluate_crit_rate(30)['tier'] == 'C'
        assert self.comparator.evaluate_crit_rate(15)['tier'] == 'D'

    def test_compare_with_builds_low_dps(self):
        summary = {'dps': 300000, 'crit_rate': 20, 'skill_breakdown': {}, 'top_skill': '旋风斩'}
        result = self.comparator.compare_with_builds(summary, '野蛮人')
        assert result['dps_evaluation']['tier'] in ('C', 'D')
        assert len(result['recommendations']) > 0

    def test_compare_with_builds_high_dps(self):
        summary = {'dps': 8000000, 'crit_rate': 60, 'skill_breakdown': {}, 'top_skill': '旋风斩'}
        result = self.comparator.compare_with_builds(summary, '野蛮人')
        assert result['dps_evaluation']['tier'] in ('S', 'A')

    def test_compare_with_builds_monotone_skill(self):
        breakdown = {'旋风斩': {'percentage': 90, 'avg_damage': 100000, 'max_damage': 200000}}
        summary = {'dps': 3000000, 'crit_rate': 45, 'skill_breakdown': breakdown, 'top_skill': '旋风斩'}
        result = self.comparator.compare_with_builds(summary, '野蛮人')
        has_monotone = any(r['type'] == 'skill_monotone' for r in result['recommendations'])
        assert has_monotone


class TestDamageConfig:
    def test_damage_config_exists(self):
        assert isinstance(DAMAGE_CONFIG, dict)

    def test_damage_config_enabled(self):
        assert DAMAGE_CONFIG['enabled'] is True

    def test_damage_config_interval(self):
        assert DAMAGE_CONFIG['monitor_interval'] > 0

    def test_damage_config_min_damage(self):
        assert DAMAGE_CONFIG['min_damage_number'] >= 0
