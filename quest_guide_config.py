#!/usr/bin/env python3
"""
暗黑破坏神4 - 任务图文攻略配置

数据来源:游民星空 gamersky.com
内容覆盖:支线任务(按区域) + 主线/DLC流程攻略

URL 规律:
  - 文章首页: https://wap.gamersky.com/gl/Content-{id}.html
  - 文章分页: https://wap.gamersky.com/gl/Content-{id}_{page}.html
  - 图片 CDN: https://aka.doubaocdn.com/ 或 https://imgs.gamersky.com/
"""

GAMERSKY_BASE = 'https://wap.gamersky.com/gl'

# ============================================================
# 支线任务攻略(按区域分类)
# 全支线任务攻略主文章 Content-1603796,分页 214 页,按区域分段
# 下面是各区域的快捷入口(直接跳到该区域起始页)
# ============================================================
SIDE_QUESTS = {
    '破碎群峰': {
        'url': f'{GAMERSKY_BASE}/Content-1603796.html',
        'start_page': 1,
        'desc': '破碎群峰全支线任务(基奥瓦沙/马尔诺克/熊部落等)',
    },
    '索格伦': {
        'url': f'{GAMERSKY_BASE}/Content-1603796_36.html',
        'start_page': 36,
        'desc': '索格伦全支线任务(凯巴杜/图尔杜拉/耶雷斯等)',
    },
    '干燥平原': {
        'url': f'{GAMERSKY_BASE}/Content-1603796_83.html',
        'start_page': 83,
        'desc': '干燥平原全支线任务(卡尔蒂姆/铁狼营地等)',
    },
    '凯基斯坦': {
        'url': f'{GAMERSKY_BASE}/Content-1603796_122.html',
        'start_page': 122,
        'desc': '凯基斯坦全支线任务(吉库尔/塔斯拉等)',
    },
    '哈维泽': {
        'url': f'{GAMERSKY_BASE}/Content-1603796_166.html',
        'start_page': 166,
        'desc': '哈维泽全支线任务(扎尔宾/蒂梅恩等)',
    },
    '三神教': {
        'url': f'{GAMERSKY_BASE}/Content-1613976.html',
        'start_page': 1,
        'desc': '三神教支线任务(光明圣教军系列)',
    },
}

# ============================================================
# 主线 / DLC 流程攻略
# ============================================================
MAIN_QUESTS = {
    '主线剧情流程': {
        'url': f'{GAMERSKY_BASE}/Content-1578673.html',
        'desc': '暗黑破坏神4 主线剧情全程图文攻略',
    },
    '憎恨之王DLC流程': {
        'url': f'{GAMERSKY_BASE}/Content-2132802.html',
        'desc': '憎恨之王 DLC 主线流程攻略',
    },
    '创世编年史收集': {
        'url': f'{GAMERSKY_BASE}/Content-2132868.html',
        'desc': 'DLC 创世编年史全收集攻略',
    },
    'DLC便利功能介绍': {
        'url': f'{GAMERSKY_BASE}/Content-2132428.html',
        'desc': 'DLC 新增便利功能介绍',
    },
    'DLC中文CG剧情': {
        'url': f'{GAMERSKY_BASE}/Content-2132827.html',
        'desc': 'DLC 中文 CG 剧情合集',
    },
    'DLC剧情讲解': {
        'url': f'{GAMERSKY_BASE}/Content-2133193.html',
        'desc': 'DLC 剧情深度讲解',
    },
}

# ============================================================
# 新手指南
# ============================================================
BEGINNER_GUIDES = {
    '入门指南': {
        'url': f'{GAMERSKY_BASE}/Content-1578673.html',
        'desc': '新手入门基础指南',
    },
    '人物基础属性': {
        'url': f'{GAMERSKY_BASE}/Content-1602802.html',
        'desc': '力量/智力/敏捷/意志/护甲/抗性详解',
    },
    '常用快捷键': {
        'url': f'{GAMERSKY_BASE}/Content-1602990.html',
        'desc': 'PC/主机快捷键一览',
    },
    '技能树系统解析': {
        'url': f'{GAMERSKY_BASE}/Content-1602824.html',
        'desc': '技能树机制与加点思路',
    },
    '装备种类及品质': {
        'url': f'{GAMERSKY_BASE}/Content-1602929.html',
        'desc': '装备稀有度/词缀/威能系统',
    },
    '增伤机制解析': {
        'url': f'{GAMERSKY_BASE}/Content-1603062.html',
        'desc': '伤害计算公式与增伤乘区',
    },
    '声望系统介绍': {
        'url': f'{GAMERSKY_BASE}/Content-1602835.html',
        'desc': '区域声望奖励与获取方式',
    },
    '地狱狂潮玩法': {
        'url': f'{GAMERSKY_BASE}/Content-1603050.html',
        'desc': '地狱狂潮机制与速刷技巧',
    },
    '低语事件': {
        'url': f'{GAMERSKY_BASE}/Content-1603032.html',
        'desc': '低语事件触发与奖励',
    },
    '秘语之树': {
        'url': f'{GAMERSKY_BASE}/Content-1603041.html',
        'desc': '秘语之树玩法详解',
    },
}

# ============================================================
# 赛季专属攻略 (S13)
# ============================================================
SEASON_GUIDES = {
    'S13赛季改动': {
        'url': f'{GAMERSKY_BASE}/Content-2132420.html',
        'desc': 'S13 清算赛季玩法改动整理',
    },
    '奶牛关任务': {
        'url': f'{GAMERSKY_BASE}/Content-2137071.html',
        'desc': 'S13 隐藏奶牛关前置任务攻略',
    },
    '调谐石词缀表': {
        'url': f'{GAMERSKY_BASE}/Content-2140091.html',
        'desc': 'S13 调谐石(赫拉迪姆协调石)词缀一览',
    },
    '战争计划加点': {
        'url': f'{GAMERSKY_BASE}/Content-2140374.html',
        'desc': 'S13 战争计划加点分享',
    },
    '暗金掉落表': {
        'url': f'{GAMERSKY_BASE}/Content-2136913.html',
        'desc': 'S13 暗金装备掉落表',
    },
    '圣骑士套装效果': {
        'url': f'{GAMERSKY_BASE}/Content-2134007.html',
        'desc': 'S13 圣骑士套装效果评析',
    },
    '德鲁伊套装效果': {
        'url': f'{GAMERSKY_BASE}/Content-2133524.html',
        'desc': 'S13 德鲁伊套装效果评析',
    },
    '魔盒功能介绍': {
        'url': f'{GAMERSKY_BASE}/Content-2133979.html',
        'desc': 'S13 魔盒功能玩法介绍',
    },
}

# ============================================================
# 合集:所有攻略(用于搜索匹配)
# ============================================================
ALL_GUIDES = {}
for category, guides in [
    ('支线任务', SIDE_QUESTS),
    ('主线DLC', MAIN_QUESTS),
    ('新手指南', BEGINNER_GUIDES),
    ('赛季攻略', SEASON_GUIDES),
]:
    for name, info in guides.items():
        ALL_GUIDES[name] = {
            'category': category,
            'url': info['url'],
            'desc': info.get('desc', ''),
        }


def search_guide(keyword):
    """根据关键词搜索攻略,返回匹配的 (名称, 信息) 列表

    匹配规则:
      1. 名称完全包含关键词
      2. 描述包含关键词
      3. 区域名/别名模糊匹配
    """
    keyword = keyword.strip().lower()
    if not keyword:
        return []

    # 别名映射(常见简称/错别字)
    aliases = {
        '破碎': '破碎群峰',
        '索格伦': '索格伦',
        '斯科斯格伦': '索格伦',
        '干燥': '干燥平原',
        '凯吉斯坦': '凯基斯坦',
        '哈维泽': '哈维泽',
        'dlc': '憎恨之王DLC流程',
        '憎恨之王': '憎恨之王DLC流程',
        '奶牛': '奶牛关任务',
        '奶牛关': '奶牛关任务',
        '地狱狂潮': '地狱狂潮玩法',
        '声望': '声望系统介绍',
        '快捷键': '常用快捷键',
        '属性': '人物基础属性',
        '增伤': '增伤机制解析',
        '技能树': '技能树系统解析',
        '装备': '装备种类及品质',
        '低语': '低语事件',
        '秘语': '秘语之树',
        '调谐石': '调谐石词缀表',
        '协调石': '调谐石词缀表',
        '战争计划': '战争计划加点',
        '暗金': '暗金掉落表',
        '套装': '圣骑士套装效果',
        '魔盒': '魔盒功能介绍',
        '创世': '创世编年史收集',
        '编年史': '创世编年史收集',
        'cg': 'DLC中文CG剧情',
        '剧情': 'DLC剧情讲解',
        '开荒': '入门指南',
        '新手': '入门指南',
        '入门': '入门指南',
        # 主线任务名 -> 主线剧情流程攻略
        '山上黄昏': '主线剧情流程',
        '黄昏': '主线剧情流程',
        '庇护所': '主线剧情流程',
        '城镇': '主线剧情流程',
        '主线': '主线剧情流程',
        '罗格营地': '主线剧情流程',
        '寻找庇护': '主线剧情流程',
    }

    # 别名直接命中
    if keyword in aliases:
        target = aliases[keyword]
        if target in ALL_GUIDES:
            return [(target, ALL_GUIDES[target])]

    # OCR 整段文字匹配:检查文字中是否包含别名关键词
    for alias_key, target_name in aliases.items():
        if alias_key in keyword:
            if target_name in ALL_GUIDES:
                return [(target_name, ALL_GUIDES[target_name])]

    results = []
    for name, info in ALL_GUIDES.items():
        name_lower = name.lower()
        desc_lower = info.get('desc', '').lower()
        if keyword in name_lower or keyword in desc_lower:
            results.append((name, info))

    return results


def get_guide_url(name):
    """根据攻略名称获取 URL,找不到返回 None"""
    info = ALL_GUIDES.get(name)
    return info['url'] if info else None


def get_guides_by_category(category):
    """按分类获取攻略列表
    category ∈ {'支线任务', '主线DLC', '新手指南', '赛季攻略'}
    """
    cat_map = {
        '支线任务': SIDE_QUESTS,
        '主线DLC': MAIN_QUESTS,
        '新手指南': BEGINNER_GUIDES,
        '赛季攻略': SEASON_GUIDES,
    }
    return cat_map.get(category, {})


# 游民星空暗黑4专区首页
GAMERSKY_D4_HOME = 'https://www.gamersky.com/z/diablo4/'
