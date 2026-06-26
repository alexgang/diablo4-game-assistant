# -*- coding: utf-8 -*-
"""
构筑截图配置 —— d2core(暗黑核) 中文构筑, Season 13。
fetch_build_images.py 读这里。planner 页是长图,整页截图含技能树+装备+巅峰+攻略全文。

字段: class 职业 / name 构筑名(显示用) / kind 图类型 / url d2core planner页 / file 输出名

★德鲁伊/灵巫: d2core首页未列出,暂用 maxroll 兜底或后续补 d2core URL。
"""

BUILD_SHOTS = [
    # ── 游侠 Rogue (主打,d2core中文) ──
    {"class": "rogue", "name": "箭雨冰穿游侠", "kind": "skills",
     "url": "https://www.d2core.com/d4/planner?bd=1UPR",
     "file": "rogue_d2c_skills.png", "selector": None},

    # ── 野蛮人 Barbarian ──
    {"class": "barbarian", "name": "溶解旋风野蛮人", "kind": "skills",
     "url": "https://www.d2core.com/d4/planner?bd=1SZ2",
     "file": "barb_d2c_skills.png", "selector": None},

    # ── 法师 Sorcerer ──
    {"class": "sorcerer", "name": "电球法师", "kind": "skills",
     "url": "https://www.d2core.com/d4/planner?bd=1Tok",
     "file": "sorc_d2c_skills.png", "selector": None},

    # ── 死灵 Necromancer ──
    {"class": "necromancer", "name": "纯招骷髅死灵", "kind": "skills",
     "url": "https://www.d2core.com/d4/planner?bd=1T85",
     "file": "necro_d2c_skills.png", "selector": None},
]
