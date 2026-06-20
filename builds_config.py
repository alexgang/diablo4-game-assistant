# -*- coding: utf-8 -*-
"""
构筑截图配置 —— Season 13 "Season of Reckoning" 6职业热门构筑。

每条 = 一张要截的图。fetch_build_images.py 读这里。
字段:
  class    职业 (barbarian/rogue/sorcerer/druid/necromancer/spiritborn)
  name     构筑名(中文,会显示在 GUI)
  kind     图类型 skills(技能) / paragon(巅峰) / gear(装备)
  url      构筑详情页 URL —— ★换成你在 d2core 浏览时中意的中文构筑页★
  file     输出文件名(相对 resources/images/builds/)
  selector 可选:只截某 CSS 元素(留 None 则整页截图)

★ 使用建议:
  1. 先用 maxroll 这批 URL 跑通流程(英文但能截到技能/巅峰/装备图)
  2. demo 想要中文界面:在 d2core.com 浏览构筑,把详情页 URL 替换进来
     (d2core 构筑详情形如 https://www.d2core.com/d4/guide/xxxx)
  3. selector 先留 None 整页截;若想精准截某区块,F12 找到容器的 class 填进去
"""

# maxroll 当前可访问的构筑指南页(S13)。同一页截 3 种图,靠 selector 区分;
# 先整页截(selector=None),跑通后再按需精修。
BUILD_SHOTS = [
    # ── 游侠 Rogue(优先)──
    {"class": "rogue", "name": "飞刀乱舞", "kind": "skills",
     "url": "https://maxroll.gg/d4/build-guides/dance-of-knives-rogue-guide",
     "file": "rogue_dok_skills.png", "selector": None},
    {"class": "rogue", "name": "飞刀乱舞", "kind": "paragon",
     "url": "https://maxroll.gg/d4/build-guides/dance-of-knives-rogue-guide",
     "file": "rogue_dok_paragon.png", "selector": None},
    {"class": "rogue", "name": "飞刀乱舞", "kind": "gear",
     "url": "https://maxroll.gg/d4/build-guides/dance-of-knives-rogue-guide",
     "file": "rogue_dok_gear.png", "selector": None},

    # ── 法师 Sorcerer ──
    {"class": "sorcerer", "name": "球状闪电", "kind": "skills",
     "url": "https://maxroll.gg/d4/build-guides/ball-lightning-sorcerer-guide",
     "file": "sorc_bl_skills.png", "selector": None},
    {"class": "sorcerer", "name": "球状闪电", "kind": "paragon",
     "url": "https://maxroll.gg/d4/build-guides/ball-lightning-sorcerer-guide",
     "file": "sorc_bl_paragon.png", "selector": None},

    # ── 野蛮人 Barbarian ──
    {"class": "barbarian", "name": "旋风斩", "kind": "skills",
     "url": "https://maxroll.gg/d4/build-guides/whirlwind-barbarian-guide",
     "file": "barb_ww_skills.png", "selector": None},
    {"class": "barbarian", "name": "旋风斩", "kind": "paragon",
     "url": "https://maxroll.gg/d4/build-guides/whirlwind-barbarian-guide",
     "file": "barb_ww_paragon.png", "selector": None},

    # ── 死灵 Necromancer ──
    {"class": "necromancer", "name": "血潮", "kind": "skills",
     "url": "https://maxroll.gg/d4/build-guides/blood-wave-necromancer-guide",
     "file": "necro_bw_skills.png", "selector": None},
    {"class": "necromancer", "name": "血潮", "kind": "paragon",
     "url": "https://maxroll.gg/d4/build-guides/blood-wave-necromancer-guide",
     "file": "necro_bw_paragon.png", "selector": None},

    # ── 德鲁伊 Druid ──
    {"class": "druid", "name": "同伴德", "kind": "skills",
     "url": "https://maxroll.gg/d4/build-guides/companion-druid-guide",
     "file": "druid_comp_skills.png", "selector": None},
    {"class": "druid", "name": "同伴德", "kind": "paragon",
     "url": "https://maxroll.gg/d4/build-guides/companion-druid-guide",
     "file": "druid_comp_paragon.png", "selector": None},

    # ── 灵巫 Spiritborn ──
    {"class": "spiritborn", "name": "闪避反击", "kind": "skills",
     "url": "https://maxroll.gg/d4/build-guides/evade-counterswarm-spiritborn-guide",
     "file": "spirit_evade_skills.png", "selector": None},
    {"class": "spiritborn", "name": "闪避反击", "kind": "paragon",
     "url": "https://maxroll.gg/d4/build-guides/evade-counterswarm-spiritborn-guide",
     "file": "spirit_evade_paragon.png", "selector": None},
]
