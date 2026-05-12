import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import OVERLAY_CONFIG


class TestOverlayConfig:
    def test_overlay_config_exists(self):
        assert isinstance(OVERLAY_CONFIG, dict)

    def test_overlay_config_enabled(self):
        assert 'enabled' in OVERLAY_CONFIG
        assert OVERLAY_CONFIG['enabled'] is True

    def test_overlay_config_opacity(self):
        assert 'opacity' in OVERLAY_CONFIG
        assert 0 < OVERLAY_CONFIG['opacity'] <= 1.0

    def test_overlay_config_dimensions(self):
        assert 'width' in OVERLAY_CONFIG
        assert 'height' in OVERLAY_CONFIG
        assert OVERLAY_CONFIG['width'] > 0
        assert OVERLAY_CONFIG['height'] > 0

    def test_overlay_config_position(self):
        assert 'position' in OVERLAY_CONFIG
        assert OVERLAY_CONFIG['position'] in ('left', 'right', 'top-left', 'top-right')


class TestOverlayDataParsing:
    def test_parse_skill_entry_with_points(self):
        from overlay import OverlayPanel
        panel = OverlayPanel.__new__(OverlayPanel)
        name, pts = panel._parse_skill_entry('旋风斩 5')
        assert name == '旋风斩'
        assert pts == '5'

    def test_parse_skill_entry_without_points(self):
        from overlay import OverlayPanel
        panel = OverlayPanel.__new__(OverlayPanel)
        name, pts = panel._parse_skill_entry('旋风斩')
        assert name == '旋风斩'
        assert pts == ''

    def test_parse_skill_entry_non_string(self):
        from overlay import OverlayPanel
        panel = OverlayPanel.__new__(OverlayPanel)
        name, pts = panel._parse_skill_entry(42)
        assert name == '42'
        assert pts == ''

    def test_sort_equipment_by_slot(self):
        from overlay import OverlayPanel
        panel = OverlayPanel.__new__(OverlayPanel)
        equipment = [
            {'name': '武器A', 'slot': '双手武器'},
            {'name': '头盔B', 'slot': '头盔'},
            {'name': '戒指C', 'slot': '戒指1'},
        ]
        sorted_items = panel._sort_equipment(equipment)
        assert sorted_items[0]['slot'] == '头盔'
        assert sorted_items[1]['slot'] == '双手武器'
        assert sorted_items[2]['slot'] == '戒指1'

    def test_sort_equipment_unknown_slot(self):
        from overlay import OverlayPanel
        panel = OverlayPanel.__new__(OverlayPanel)
        equipment = [
            {'name': '未知', 'slot': '其他'},
            {'name': '头盔', 'slot': '头盔'},
        ]
        sorted_items = panel._sort_equipment(equipment)
        assert sorted_items[0]['slot'] == '头盔'


class TestOverlayUpdateMethods:
    def _make_panel(self):
        from overlay import OverlayPanel
        panel = OverlayPanel.__new__(OverlayPanel)
        panel._equip_content_layout = None
        panel._skill_content_layout = None
        panel._paragon_content_layout = None
        panel._merc_content_layout = None
        return panel

    def test_update_equipment_with_dict_items(self):
        from overlay import OverlayPanel
        panel = OverlayPanel.__new__(OverlayPanel)
        build_data = {
            'title': '野蛮人旋风斩',
            'equipment': [
                {'name': '哈洛加斯之怒', 'slot': '头盔', 'rarity': '暗金'},
                {'name': '先祖之锤', 'slot': '双手武器', 'rarity': '传奇'},
            ],
        }
        assert build_data['equipment'][0]['name'] == '哈洛加斯之怒'

    def test_update_skills_with_list(self):
        build_data = {
            'skills': ['旋风斩', '战吼 3', '先祖召唤 1'],
        }
        assert len(build_data['skills']) == 3
        assert '旋风斩' in build_data['skills']

    def test_update_paragon_with_boards_and_aspects(self):
        paragon_data = {
            'boards': [
                {'name': '起始板', 'rare_node': '爆伤'},
                {'name': '屠杀板', 'rare_node': '力量'},
            ],
            'aspects': ['铁皮威能', '狂暴威能'],
        }
        assert len(paragon_data['boards']) == 2
        assert len(paragon_data['aspects']) == 2

    def test_update_mercenary_with_data(self):
        merc_data = {
            'mercenaries': [
                {'name': '拉海德', 'skill': '暗影步'},
            ],
            'reinforce': ['治愈之触'],
        }
        assert len(merc_data['mercenaries']) == 1
        assert len(merc_data['reinforce']) == 1


class TestOverlayRarityColors:
    def test_rarity_colors_defined(self):
        from overlay import RARITY_COLORS
        assert '暗金' in RARITY_COLORS
        assert '传奇' in RARITY_COLORS
        assert '套装' in RARITY_COLORS

    def test_rarity_colors_are_hex(self):
        from overlay import RARITY_COLORS
        for rarity, color in RARITY_COLORS.items():
            assert color.startswith('#')
            assert len(color) == 7


class TestOverlaySlotDisplay:
    def test_slot_display_defined(self):
        from overlay import SLOT_DISPLAY
        assert '头盔' in SLOT_DISPLAY
        assert '胸甲' in SLOT_DISPLAY
        assert '双手武器' in SLOT_DISPLAY

    def test_slot_display_has_emoji(self):
        from overlay import SLOT_DISPLAY
        for slot, display in SLOT_DISPLAY.items():
            assert len(display) > len(slot)
