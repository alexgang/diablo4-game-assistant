"""
D4 职业推荐数据模块

定义6个职业的推荐配置，包括：
- 职业OCR关键词
- 推荐攻略来源URL
- 装备词条推荐
- 天赋加点图
- 巅峰加点图
"""
import os
from enum import Enum
from typing import Dict, List
from dataclasses import dataclass, field

# 构筑截图目录(由 fetch_build_images.py 产出)
_BUILD_IMG_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'resources', 'images', 'builds',
)


def _img(name: str) -> str:
    """构筑图相对名 → 绝对路径(文件不存在也返回路径,GUI 自行判断)"""
    return os.path.join(_BUILD_IMG_DIR, name)


class D4Class(str, Enum):
    """D4 职业枚举"""
    BARBARIAN = "barbarian"  # 野蛮人
    ROGUE = "rogue"  # 游侠
    SORCERER = "sorcerer"  # 巫师(游戏内中文名,Sorcerer)
    DRUID = "druid"  # 德鲁伊
    NECROMANCER = "necromancer"  # 死灵法师
    SPIRITBORN = "spiritborn"  # 灵巫
    PALADIN = "paladin"  # 圣骑士(Lord of Hatred 资料片新职业)
    WARLOCK = "warlock"  # 术师(Lord of Hatred 资料片新职业, Warlock)


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
        'zh': '巫师',
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
    D4Class.PALADIN: {
        'zh': '圣骑士',
        'en': 'Paladin',
        'icon': '🛡️',
        'color': '#f1c40f',
    },
    D4Class.WARLOCK: {
        'zh': '术师',
        'en': 'Warlock',
        'icon': '🔥',
        'color': '#8e44ad',
    },
}


# OCR 关键词（用于从角色名/界面识别职业）
CLASS_OCR_KEYWORDS: Dict[D4Class, List[str]] = {
    D4Class.BARBARIAN: [
        '野蛮人', 'barbarian', 'barb', 'bb',
        '撼地者', 'berserker', '先祖之锤', '先祖', '双持', '尘魔',
        '旋风斩', '旋风', 'whirlwind', '猛击', 'bash',  # S13
    ],
    D4Class.ROGUE: [
        '游侠', 'rogue', 'rog',
        '刀锋', 'bladeshift', '穿刺', '箭雨', '穿透', '陷阱', '奇袭',
        '飞刀乱舞', '飞刀', 'dance of knives', '速射', 'rapid fire',  # S13
    ],
    D4Class.SORCERER: [
        '巫师', '法师', 'sorcerer', 'sorc', 'sor',  # 游戏内中文名"巫师"
        '冰法', '电法', '火法', '冰霜', '闪电', '燃烧', '电球',
        '球状闪电', '球闪', 'ball lightning', '冰晶碎片', 'ice shards',
    ],
    D4Class.DRUID: [
        '德鲁伊', 'druid',
        '狼人', '熊人', '风暴', '土狼', '伙伴', '大地',
        '同伴', 'companion', '山崩', 'landslide',
    ],
    D4Class.NECROMANCER: [
        '死灵法师', '死灵', 'necromancer', 'necro', 'nec',  # 死灵法师(4字)须先于法师(2字)命中
        '骷髅', '召唤', '亡者之书', '傀儡', '骨矛', '血雾', '钢铁',
        '血潮', '血浪', 'blood wave', '血涌', 'blood surge',
    ],
    D4Class.SPIRITBORN: [
        '灵巫', 'spiritborn',
        '虎掌', '鹰爪', '神龙', '朱鹤', '千喉',
        '闪避', 'evade', '反击', 'counterswarm', '尖刺齐射', 'quill volley',
    ],
    D4Class.PALADIN: [
        '圣骑士', 'paladin', 'pal',  # Lord of Hatred 资料片
        '正义', '狂热者', '审判者', '门徒', '主宰',  # 四誓约 Juggernaut/Zealot/Judicator/Disciple
        'juggernaut', 'zealot', 'judicator', 'disciple', '圣锤', '光环',
    ],
    D4Class.WARLOCK: [
        '术师', 'warlock',  # Lord of Hatred 资料片(勿与"术士/巫师"混淆)
        '地狱火', '恶魔', '召唤恶魔', '邪术', 'hellfire', 'eldritch',
    ],
}


# ============== 角色名 → 职业 映射（本机实际角色，最可靠的识别依据） ==============
# 来自角色选择界面。OCR 读到角色名即可直接定职业,无需图标/属性。
# 注意:可能有重名(如两个角色同名但不同职业),重名时此表给主用职业,
#       需配合图标模板或主属性消歧。维护时按实际角色更新。
CHARACTER_NAME_TO_CLASS: Dict[str, D4Class] = {
    '芝麻莱妮雅': D4Class.BARBARIAN,
    '芝麻苏玛雅': D4Class.ROGUE,
    '芝麻冬瓜': D4Class.SORCERER,
    '芝麻赛斯美': D4Class.WARLOCK,   # 术师
    '芝麻厚礼活': D4Class.PALADIN,   # 圣骑士
    # '芝麻老狼' 重名:既有死灵也有德鲁伊 —— 见 AMBIGUOUS_NAMES,需消歧
}

# 重名角色:同名对应多个职业,需用图标/主属性进一步区分
AMBIGUOUS_CHARACTER_NAMES: Dict[str, List[D4Class]] = {
    '芝麻老狼': [D4Class.NECROMANCER, D4Class.DRUID],
}


def _name_fuzzy_match(name: str, text: str) -> bool:
    """角色名模糊匹配:容忍 OCR 单字误识(如"芝"→"芰")。
    策略:精确包含→命中;否则取核心部分(去公共前缀"芝麻"),核心在 text 中
    则命中;再否则允许核心字符按序出现时漏1个(容忍单字误识)。"""
    if not name or not text:
        return False
    if name in text:
        return True
    core = name[2:] if name.startswith('芝麻') and len(name) > 3 else name
    if len(core) < 2:
        return False
    if core in text:
        return True
    pos, hit = -1, 0
    for ch in core:
        idx = text.find(ch, pos + 1)
        if idx > pos:
            hit += 1
            pos = idx
    return hit >= len(core) - 1


def matched_character_name(text: str):
    """返回 text 中匹配到的已知角色名(用于判断是否'新角色名')。未命中返回 ''。"""
    if not text:
        return ''
    for name in AMBIGUOUS_CHARACTER_NAMES:
        if _name_fuzzy_match(name, text):
            return name
    for name in CHARACTER_NAME_TO_CLASS:
        if _name_fuzzy_match(name, text):
            return name
    return ''


def detect_class_from_character_name(text: str):
    """从 OCR 文本中匹配已知角色名 → 职业。
    返回 (D4Class, ambiguous: bool)。未命中返回 (None, False)。
    ambiguous=True 表示命中重名角色,调用方需用图标/属性进一步消歧。
    匹配容忍 OCR 单字误识(如"芝麻苏玛雅"被识别为"芰麻苏玛雅")。"""
    if not text:
        return None, False
    # 先查重名(更具体)
    for name, classes in AMBIGUOUS_CHARACTER_NAMES.items():
        if _name_fuzzy_match(name, text):
            return classes[0], True   # 返回首选职业 + 标记需消歧
    for name, cls in CHARACTER_NAME_TO_CLASS.items():
        if _name_fuzzy_match(name, text):
            return cls, False
    return None, False


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


# 默认推荐 BD 配置（Season 13 "Season of Reckoning"，来源 maxroll/d2core）
# image_paths 指向 fetch_build_images.py 截好的本地图;文件不在时 GUI 显示占位提示。
DEFAULT_BUILDS: Dict[D4Class, List[ClassBuildGuide]] = {
    D4Class.BARBARIAN: [
        ClassBuildGuide(
            class_type=D4Class.BARBARIAN,
            build_name='溶解旋风野蛮人',
            season='S13',
            source_url='https://www.d2core.com/d4/planner?bd=1SZ2',
            image_paths={
                'skills': _img('barb_d2c.png'),
            },
        ),
    ],
    D4Class.ROGUE: [
        ClassBuildGuide(
            class_type=D4Class.ROGUE,
            build_name='箭雨冰穿游侠',
            season='S13',
            source_url='https://www.d2core.com/d4/planner?bd=1UPR',
            image_paths={
                'skills': _img('rogue_d2c.png'),
            },
        ),
    ],
    D4Class.SORCERER: [
        ClassBuildGuide(
            class_type=D4Class.SORCERER,
            build_name='电球法师',
            season='S13',
            source_url='https://www.d2core.com/d4/planner?bd=1Tok',
            image_paths={
                'skills': _img('sorc_d2c.png'),
            },
        ),
    ],
    D4Class.DRUID: [
        ClassBuildGuide(
            class_type=D4Class.DRUID,
            build_name='同伴德鲁伊',
            season='S13',
            source_url='https://maxroll.gg/d4/build-guides/companion-druid-guide',
            image_paths={
                'skills': _img('druid_comp_skills.png'),
                'paragon': _img('druid_comp_paragon.png'),
            },
        ),
    ],
    D4Class.NECROMANCER: [
        ClassBuildGuide(
            class_type=D4Class.NECROMANCER,
            build_name='纯招骷髅死灵',
            season='S13',
            source_url='https://www.d2core.com/d4/planner?bd=1T85',
            image_paths={
                'skills': _img('necro_d2c.png'),
            },
        ),
    ],
    D4Class.SPIRITBORN: [
        ClassBuildGuide(
            class_type=D4Class.SPIRITBORN,
            build_name='闪避反击灵巫',
            season='S13',
            source_url='https://maxroll.gg/d4/build-guides/evade-counterswarm-spiritborn-guide',
            image_paths={
                'skills': _img('spirit_evade_skills.png'),
                'paragon': _img('spirit_evade_paragon.png'),
            },
        ),
    ],
    # 资料片新职业 —— d2core 构筑 URL 待用户提供后替换
    D4Class.PALADIN: [
        ClassBuildGuide(
            class_type=D4Class.PALADIN,
            build_name='圣骑士构筑',
            season='',
            source_url='https://www.d2core.com/d4',
            image_paths={},
        ),
    ],
    D4Class.WARLOCK: [
        ClassBuildGuide(
            class_type=D4Class.WARLOCK,
            build_name='术师构筑',
            season='',
            source_url='https://www.d2core.com/d4',
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


# ============== 职业识别结果持久化(跨会话记住上次识别成功的职业) ==============
# 策略: OCR 识别到角色名/职业后存盘,之后默认沿用;只有识别到"新角色名"才更新。
# 这样战斗等无文字画面不会丢失职业,也不会被误判覆盖。
_CLASS_CACHE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'cache', 'last_class.json'
)


def load_cached_class():
    """读取上次识别成功的职业。返回 (D4Class|None, char_name:str|None)。"""
    try:
        import json
        if not os.path.exists(_CLASS_CACHE_FILE):
            return None, None
        with open(_CLASS_CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        cls_val = data.get('class')
        name = data.get('char_name')
        cls = None
        if cls_val:
            for c in D4Class:
                if c.value == cls_val:
                    cls = c
                    break
        return cls, name
    except Exception:
        return None, None


def save_cached_class(class_type, char_name=None):
    """保存识别成功的职业(及来源角色名)到磁盘,供下次启动/无文字画面沿用。"""
    if class_type is None:
        return
    try:
        import json
        os.makedirs(os.path.dirname(_CLASS_CACHE_FILE), exist_ok=True)
        cls_val = class_type.value if hasattr(class_type, 'value') else str(class_type)
        with open(_CLASS_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'class': cls_val, 'char_name': char_name or ''},
                      f, ensure_ascii=False)
    except Exception:
        pass


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
