"""
D4 职业推荐数据模块

定义6个职业的推荐配置，包括：
- 职业OCR关键词
- 推荐攻略来源URL
- 装备词条推荐
- 天赋加点图
- 巅峰加点图
"""
from enum import Enum
from typing import Dict, List
from dataclasses import dataclass, field


class D4Class(str, Enum):
    """D4 职业枚举"""
    BARBARIAN = "barbarian"  # 野蛮人
    ROGUE = "rogue"  # 游侠
    SORCERER = "sorcerer"  # 法师
    DRUID = "druid"  # 德鲁伊
    NECROMANCER = "necromancer"  # 死灵法师
    SPIRITBORN = "spiritborn"  # 灵巫（赛季新职业）


# 职业的中英文名称（用于OCR匹配和显示）
CLASS_NAMES: Dict[D4Class, Dict[str, str]] = {
    D4Class.BARBARIAN: {
        'zh': '野蛮人',
        'en': 'Barbarian',
        'icon': '⚔️',
        'color': '#c9302c',
    },
    D4Class.ROGUE: {
        'zh': '游侠',
        'en': 'Rogue',
        'icon': '🗡️',
        'color': '#e8b923',
    },
    D4Class.SORCERER: {
        'zh': '法师',
        'en': 'Sorcerer',
        'icon': '🔮',
        'color': '#5b9bd5',
    },
    D4Class.DRUID: {
        'zh': '德鲁伊',
        'en': 'Druid',
        'icon': '🌿',
        'color': '#70ad47',
    },
    D4Class.NECROMANCER: {
        'zh': '死灵法师',
        'en': 'Necromancer',
        'icon': '💀',
        'color': '#7030a0',
    },
    D4Class.SPIRITBORN: {
        'zh': '灵巫',
        'en': 'Spiritborn',
        'icon': '🐉',
        'color': '#00b050',
    },
}


# OCR 关键词（用于从角色名/界面识别职业）
CLASS_OCR_KEYWORDS: Dict[D4Class, List[str]] = {
    D4Class.BARBARIAN: [
        '野蛮人', 'barbarian', 'barb', 'bb',
        '撼地者', 'berserker', '先祖之锤', '先祖', '双持', '尘魔',
    ],
    D4Class.ROGUE: [
        '游侠', 'rogue', 'rog',
        '刀锋', 'bladeshift', '穿刺', '箭雨', '穿透', '陷阱', '奇袭',
    ],
    D4Class.SORCERER: [
        '法师', '术士', 'warlock', 'sorcerer', 'sorc', 'sor',
        '冰法', '电法', '火法', '冰霜', '闪电', '燃烧', '电球',
    ],
    D4Class.DRUID: [
        '德鲁伊', 'druid',
        '狼人', '熊人', '风暴', '土狼', '伙伴', '大地',
    ],
    D4Class.NECROMANCER: [
        '死灵', 'necromancer', 'necro', 'nec',
        '骷髅', '召唤', '亡者之书', '傀儡', '骨矛', '血雾', '钢铁',
    ],
    D4Class.SPIRITBORN: [
        '灵巫', 'spiritborn',
        '虎掌', '鹰爪', '神龙', '朱鹤', '千喉',
    ],
}


@dataclass
class ClassBuildGuide:
    """职业 BD 推荐攻略"""
    class_type: D4Class
    build_name: str  # BD名称，如"钢铁傀儡死灵"
    season: str  # 适用赛季
    source_url: str  # 攻略来源URL
    image_paths: Dict[str, str] = field(default_factory=dict)  # 本地图片路径
    # image_paths = {
    #     'skills': 'xxx.png',     # 技能加点图
    #     'paragon': 'xxx.png',    # 巅峰加点图
    #     'gear': 'xxx.png',       # 装备推荐图
    #     'affixes': 'xxx.png',    # 词条优先级图
    # }


# 默认推荐 BD 配置（来自 3DM/灰机/MAXROLL 等社区资源）
DEFAULT_BUILDS: Dict[D4Class, List[ClassBuildGuide]] = {
    D4Class.BARBARIAN: [
        ClassBuildGuide(
            class_type=D4Class.BARBARIAN,
            build_name='双持先祖之锤',
            season='S11',
            source_url='https://m.3dmgame.com/ol/gl/diablo4/',
            image_paths={},
        ),
        ClassBuildGuide(
            class_type=D4Class.BARBARIAN,
            build_name='地震冲锋',
            season='S11',
            source_url='https://m.3dmgame.com/ol/gl/diablo4/',
            image_paths={},
        ),
    ],
    D4Class.ROGUE: [
        ClassBuildGuide(
            class_type=D4Class.ROGUE,
            build_name='穿刺刀锋',
            season='S11',
            source_url='https://m.3dmgame.com/ol/gl/diablo4/',
            image_paths={},
        ),
        ClassBuildGuide(
            class_type=D4Class.ROGUE,
            build_name='速射弓',
            season='S11',
            source_url='https://m.3dmgame.com/ol/gl/diablo4/',
            image_paths={},
        ),
    ],
    D4Class.SORCERER: [
        ClassBuildGuide(
            class_type=D4Class.SORCERER,
            build_name='冰霜新星',
            season='S11',
            source_url='https://m.3dmgame.com/ol/gl/diablo4/',
            image_paths={},
        ),
        ClassBuildGuide(
            class_type=D4Class.SORCERER,
            build_name='电法连锁闪电',
            season='S11',
            source_url='https://m.3dmgame.com/ol/gl/diablo4/',
            image_paths={},
        ),
    ],
    D4Class.DRUID: [
        ClassBuildGuide(
            class_type=D4Class.DRUID,
            build_name='风暴狼',
            season='S11',
            source_url='https://m.3dmgame.com/ol/gl/diablo4/',
            image_paths={},
        ),
        ClassBuildGuide(
            class_type=D4Class.DRUID,
            build_name='大地熊',
            season='S11',
            source_url='https://m.3dmgame.com/ol/gl/diablo4/',
            image_paths={},
        ),
    ],
    D4Class.NECROMANCER: [
        ClassBuildGuide(
            class_type=D4Class.NECROMANCER,
            build_name='钢铁傀儡',
            season='S11',
            source_url='https://m.3dmgame.com/ol/gl/329004.html',
            image_paths={},
        ),
        ClassBuildGuide(
            class_type=D4Class.NECROMANCER,
            build_name='傀儡流',
            season='S11',
            source_url='https://m.3dmgame.com/ol/gl/330348.html',
            image_paths={},
        ),
        ClassBuildGuide(
            class_type=D4Class.NECROMANCER,
            build_name='骨矛',
            season='S11',
            source_url='https://m.3dmgame.com/ol/gl/diablo4/',
            image_paths={},
        ),
    ],
    D4Class.SPIRITBORN: [
        ClassBuildGuide(
            class_type=D4Class.SPIRITBORN,
            build_name='虎掌猛击',
            season='S11',
            source_url='https://m.3dmgame.com/ol/gl/diablo4/',
            image_paths={},
        ),
    ],
}


def detect_class_from_text(text: str) -> D4Class:
    """
    从 OCR 文本识别职业
    匹配优先级：长关键词 > 短关键词
    """
    text_lower = text.lower()
    
    matches = []
    for class_type, keywords in CLASS_OCR_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                matches.append((class_type, len(kw)))
    
    if not matches:
        return None
    
    # 按关键词长度排序（长的优先）
    matches.sort(key=lambda x: -x[1])
    return matches[0][0]


def get_class_display_name(class_type: D4Class, lang: str = 'zh') -> str:
    """获取职业显示名"""
    if class_type is None:
        return '未识别'
    info = CLASS_NAMES.get(class_type, {})
    return info.get(lang, class_type.value)


def get_class_color(class_type: D4Class) -> str:
    """获取职业主题色"""
    if class_type is None:
        return '#888888'
    info = CLASS_NAMES.get(class_type, {})
    return info.get('color', '#888888')


def get_class_icon(class_type: D4Class) -> str:
    """获取职业图标"""
    if class_type is None:
        return '❓'
    info = CLASS_NAMES.get(class_type, {})
    return info.get('icon', '❓')


if __name__ == '__main__':
    # 测试职业识别
    test_texts = [
        '我的野蛮人在用先祖之锤',
        'Necromancer 钢铁傀儡 build',
        'Druid 大地熊',
        '游侠箭雨',
        '法师冰法',
    ]
    for text in test_texts:
        cls = detect_class_from_text(text)
        print(f'"{text}" -> {get_class_display_name(cls)} {get_class_icon(cls)}')
