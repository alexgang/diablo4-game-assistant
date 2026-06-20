#!/usr/bin/env python3
"""
游戏场景分类器 - 将 Vision 识别的场景 ID 映射到游戏助手的功能 Tab

支持场景类别：
- equipment: 装备/物品栏界面
- skill: 技能/天赋界面
- peak: 巅峰界面（Paragon Board）
- map: 地图/世界/任务界面
- combat: 战斗/世界探索（默认）
"""

from enum import Enum
from typing import Dict, List, Optional


class SceneCategory(str, Enum):
    """场景类别枚举"""
    EQUIPMENT = "equipment"
    SKILL = "skill"
    PEAK = "peak"
    MAP = "map"
    COMBAT = "combat"
    UNKNOWN = "unknown"


SCENE_KEYWORDS: Dict[SceneCategory, List[str]] = {
    SceneCategory.EQUIPMENT: [
        # 装备 / 物品 / 库存
        'inventory', 'item', 'equipment', 'gear', 'stash',
        'codex', 'tempering', 'masterworking', 'itemization',
        'codex_of_power', 'temper', 'affix', 'reroll',
        'inventory', '装备', '物品', '背包', '仓库', '词条', '强化', '精工',
        '游侠装备', 'weapon', 'armor', 'armour', 'helmet', 'chest',
    ],
    SceneCategory.SKILL: [
        # 技能 / 天赋
        'skill', 'talent', 'tree', 'ability',
        'skill_tree', 'passive', 'mastery',
        '技能', '天赋', '树', '被动',
    ],
    SceneCategory.PEAK: [
        # 巅峰（Paragon Board）—— 独立于技能界面
        'paragon', 'paragon_board', 'paragonboard', 'glyph', 'glygh',
        'paragon_glyph', 'board', 'renown',
        '巅峰', '巅峰盘', '巅峰点', '雕文',
    ],
    SceneCategory.MAP: [
        # 地图 / 世界 / 任务
        'map', 'world', 'quest', 'waypoint', 'region',
        'world_map', 'quest_tracker', 'journal', 'codex',
        '地图', '世界', '任务', '传送点', '区域',
    ],
    SceneCategory.COMBAT: [
        # 战斗 / 地下城
        'combat', 'dungeon', 'boss', 'fight', 'battle',
        'blood', 'maiden', 'helltide', 'nightmare', 'pit',
        '战斗', '地下城', 'boss', '血', '炼狱', '梦魇',
    ],
}


def classify_scene(scene_id: str, scene_labels: List[str] = None) -> SceneCategory:
    """
    根据 Vision 场景 ID 和可选的标签列表，分类场景类别

    优先级：先看 PEAK 关键词（更具体），再看其他类别，避免 paragon 误入 SKILL。

    Args:
        scene_id: SDK Vision 返回的场景 ID (e.g. "diablo4_s4_inventory")
        scene_labels: 额外的标签列表（未来扩展）

    Returns:
        SceneCategory: 场景类别
    """
    if not scene_id:
        return SceneCategory.UNKNOWN

    scene_id_lower = scene_id.lower()
    labels_lower = [l.lower() for l in (scene_labels or [])]

    # 优先匹配 PEAK 关键词（paragon/glyph 等），避免被 SKILL 误抓
    peak_keywords = SCENE_KEYWORDS.get(SceneCategory.PEAK, [])
    for kw in peak_keywords:
        kw_lower = kw.lower()
        if kw_lower in scene_id_lower:
            return SceneCategory.PEAK
        for label in labels_lower:
            if kw_lower in label:
                return SceneCategory.PEAK

    scores = {cat: 0 for cat in SceneCategory if cat != SceneCategory.PEAK}
    for cat, keywords in SCENE_KEYWORDS.items():
        if cat == SceneCategory.PEAK:
            continue
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in scene_id_lower:
                scores[cat] += 2
            for label in labels_lower:
                if kw_lower in label:
                    scores[cat] += 1

    best = max(scores.items(), key=lambda x: x[1])
    if best[1] == 0:
        return SceneCategory.UNKNOWN
    return best[0]


def get_tab_index(category: SceneCategory, tab_order: List[str]) -> int:
    """
    获取 Tab 索引（按 tab_order 顺序）

    Args:
        category: 场景类别
        tab_order: Tab 顺序列表（按界面需求定义），如 ['combat', 'equipment', 'skill', 'peak', 'map']

    Returns:
        Tab 索引，0-based
    """
    try:
        return tab_order.index(category.value)
    except ValueError:
        return 0


def get_category_display_name(category: SceneCategory) -> str:
    """获取类别的中文显示名"""
    names = {
        SceneCategory.EQUIPMENT: '装备/物品',
        SceneCategory.SKILL: '技能/天赋',
        SceneCategory.PEAK: '巅峰/雕文',
        SceneCategory.MAP: '地图/任务',
        SceneCategory.COMBAT: '战斗',
        SceneCategory.UNKNOWN: '未识别',
    }
    return names.get(category, '未识别')


def get_category_color(category: SceneCategory) -> str:
    """获取类别对应的颜色"""
    colors = {
        SceneCategory.EQUIPMENT: '#ff6b35',
        SceneCategory.SKILL: '#9b59b6',
        SceneCategory.PEAK: '#f1c40f',
        SceneCategory.MAP: '#3498db',
        SceneCategory.COMBAT: '#e74c3c',
        SceneCategory.UNKNOWN: '#888888',
    }
    return colors.get(category, '#888888')
