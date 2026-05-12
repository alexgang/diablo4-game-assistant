import json
import os
from config import DATA_DIR


class GameDatabase:
    """游戏数据数据库类"""

    def __init__(self):
        self.quests = {}
        self.bosses = {}
        self.skills = {}
        self.items = {}
        self.load_data()

    def load_data(self):
        """加载游戏数据"""
        # 加载任务数据
        quests_path = os.path.join(DATA_DIR, 'quests.json')
        if os.path.exists(quests_path):
            with open(quests_path, 'r', encoding='utf-8') as f:
                self.quests = json.load(f)
        else:
            self.quests = self._get_default_quests()

        # 加载BOSS数据
        bosses_path = os.path.join(DATA_DIR, 'bosses.json')
        if os.path.exists(bosses_path):
            with open(bosses_path, 'r', encoding='utf-8') as f:
                self.bosses = json.load(f)
        else:
            self.bosses = self._get_default_bosses()

        # 加载技能数据
        skills_path = os.path.join(DATA_DIR, 'skills.json')
        if os.path.exists(skills_path):
            with open(skills_path, 'r', encoding='utf-8') as f:
                self.skills = json.load(f)
        else:
            self.skills = self._get_default_skills()

        # 加载装备数据
        items_path = os.path.join(DATA_DIR, 'items.json')
        if os.path.exists(items_path):
            with open(items_path, 'r', encoding='utf-8') as f:
                self.items = json.load(f)
        else:
            self.items = self._get_default_items()

    def _get_default_quests(self):
        """返回默认任务数据"""
        return {
            "act1": {
                "name": "第一幕",
                "quests": [
                    {"id": "q1", "name": "救出迪卡凯恩", "location": "邪恶洞穴", "guide": "进入邪恶洞穴，消灭所有怪物，找到迪卡凯恩"},
                    {"id": "q2", "name": "杀死血鸟", "location": "冰冷之原→埋骨之地", "guide": "在埋骨之地找到血鸟并击败她"},
                    {"id": "q3", "name": "寻找凯恩之书", "location": "黑暗森林→黑色荒地", "guide": "找到遗忘之塔并获取凯恩之书"},
                    {"id": "q4", "name": "杀死安达利尔", "location": "修道院→地下墓穴", "guide": "深入地下墓穴第四层，击败安达利尔"}
                ]
            },
            "act2": {
                "name": "第二幕",
                "quests": [
                    {"id": "q5", "name": "寻找赫拉迪克之杖", "location": "干燥高地→死亡神殿", "guide": "在死亡神殿第三层获取赫拉迪克之杖"},
                    {"id": "q6", "name": "寻找方块", "location": "遥远的绿洲→蛆虫巢穴", "guide": "在蛆虫巢穴第三层找到赫拉迪克方块"},
                    {"id": "q7", "name": "组合法杖", "location": "神秘避难所", "guide": "阅读赫拉森日记，获得正确的古墓位置"},
                    {"id": "q8", "name": "杀死都瑞尔", "location": "塔拉夏的古墓", "guide": "进入正确的古墓，击败都瑞尔"}
                ]
            },
            "act3": {
                "name": "第三幕",
                "quests": [
                    {"id": "q9", "name": "杀死邪恶之手", "location": "蜘蛛森林", "guide": "在蜘蛛森林找到并杀死邪恶之手"},
                    {"id": "q10", "name": "寻找吉得宾", "location": "庞大湿地→科克", "guide": "找到吉得宾护符"},
                    {"id": "q11", "name": "保护凯恩", "location": "库拉斯特商场", "guide": "保护凯恩不被敌人攻击"},
                    {"id": "q12", "name": "杀死墨菲斯托", "location": "憎恨的囚牢", "guide": "深入憎恨的囚牢第三层，击败墨菲斯托"}
                ]
            },
            "act4": {
                "name": "第四幕",
                "quests": [
                    {"id": "q13", "name": "摧毁灵魂石", "location": "火焰之河", "guide": "在火焰之河摧毁灵魂石"},
                    {"id": "q14", "name": "杀死暗黑破坏神", "location": "混沌要塞", "guide": "进入混沌要塞，击败暗黑破坏神"}
                ]
            },
            "act5": {
                "name": "第五幕",
                "quests": [
                    {"id": "q15", "name": "拯救野蛮人", "location": "血腥丘陵", "guide": "拯救被困的野蛮人"},
                    {"id": "q16", "name": "摧毁地狱熔炉", "location": "火焰之河", "guide": "将灵魂石放入地狱熔炉摧毁"},
                    {"id": "q17", "name": "开启通往世界之石的道路", "location": "远古之路", "guide": "清理远古之路的怪物"},
                    {"id": "q18", "name": "杀死巴尔", "location": "世界之石要塞", "guide": "深入世界之石要塞，击败巴尔"}
                ]
            }
        }

    def _get_default_bosses(self):
        """返回默认BOSS数据"""
        return {
            "andariel": {
                "name": "安达利尔",
                "act": "act1",
                "weakness": ["火焰", "冰冷"],
                "skills": ["毒云", "冲锋", "恐惧"],
                "guide": "保持距离，使用火/冰技能攻击。注意躲避毒云和冲锋技能",
                "rewards": "大量经验，第一幕通关"
            },
            "duriel": {
                "name": "都瑞尔",
                "act": "act2",
                "weakness": ["火焰", "闪电"],
                "skills": ["寒冰新星", "冰冻光环", "猛击"],
                "guide": "堆高冰抗，使用火技能攻击。注意保持移动躲避冰冻光环",
                "rewards": "大量经验，第二幕通关"
            },
            "mephisto": {
                "name": "墨菲斯托",
                "act": "act3",
                "weakness": ["闪电", "冰冷"],
                "skills": ["充能弹", "传送", "审判光环"],
                "guide": "注意躲避充能弹，保持移动。使用电/冰技能攻击",
                "rewards": "大量经验，第三幕通关，高级装备"
            },
            "diablo": {
                "name": "暗黑破坏神",
                "act": "act4",
                "weakness": ["冰冷"],
                "skills": ["火焰风暴", "紫电", "骨牢"],
                "guide": "堆高火抗，保持移动。使用冰技能攻击，注意躲避紫电",
                "rewards": "大量经验，第四幕通关，顶级装备"
            },
            "baal": {
                "name": "巴尔",
                "act": "act5",
                "weakness": ["毒素", "魔法"],
                "skills": ["召唤", "传送", "死亡之触"],
                "guide": "先清理召唤的小怪，再攻击巴尔。注意躲避死亡之触技能",
                "rewards": "大量经验，游戏通关，顶级装备"
            }
        }

    def _get_default_skills(self):
        """返回默认技能数据"""
        return {
            "barbarian": {
                "name": "野蛮人",
                "skills": {
                    "core": ["重击", "顺劈斩", "旋风斩", "上古之矛"],
                    "defensive": ["钢铁胆识", "战吼", "盾墙", "狂战之怒"],
                    "brawling": ["地面打击", "惊喜攻击", "踢击"],
                    "ultimate": ["先祖召唤", "撕裂", "战吼"],
                    "passive": ["持久愤怒", "钢铁之躯", "残暴", "无情", "不屈", "众志成城"]
                },
                "builds": {
                    "whirlwind": ["旋风斩", "战吼", "先祖召唤", "地面打击", "持久愤怒", "钢铁之躯", "残暴"],
                    "thorns": ["顺劈斩", "盾墙", "惊喜攻击", "不屈", "众志成城", "无情"]
                }
            },
            "sorcerer": {
                "name": "法师",
                "skills": {
                    "fire": ["火焰弹", "燃烧", "火球", "陨石术", "烈焰风暴"],
                    "ice": ["寒冰弹", "冰霜新星", "冰川之矛", "冰封球", "寒冰护甲"],
                    "lightning": ["电弧", "闪电", "传送", "连锁闪电", "暴风雨"],
                    "conjuration": ["冰霜射线", "火焰强化", "闪电强化"],
                    "passive": ["火焰亲和", "冰冷亲和", "闪电亲和", "元素协调", "玻璃大炮", "元素掌握"]
                },
                "builds": {
                    "fireball": ["火球", "燃烧", "火焰弹", "元素掌握", "火焰亲和", "玻璃大炮"],
                    "glacier": ["冰川之矛", "冰封球", "冰霜新星", "寒冰护甲", "冰冷亲和", "元素协调"]
                }
            },
            "rogue": {
                "name": "游侠",
                "skills": {
                    "core": ["穿刺", "穿刺射击", "刀刃风暴", "冲撞射击"],
                    "agility": ["暗影脚步", "战术位移", "逃脱", "闪避"],
                    "subterfuge": ["暗影伪装", "烟雾弹", "催泪弹", "消失"],
                    "combo": ["穿刺之舞", "刀锋之舞", "致命华彩", "暗影灌注"],
                    "ultimate": ["准备就绪", "内乱", "暗影步伐"],
                    "passive": ["隐秘", "精准", "反制", "武学之道", "动能", "灵活走位", "暗影掌控"]
                },
                "builds": {
                    "rapid_fire": ["穿刺射击", "冲撞射击", "暗影脚步", "暗影伪装", "隐秘", "精准", "武学之道"],
                    "bladedancer": ["刀刃风暴", "穿刺之舞", "刀锋之舞", "闪避", "暗影掌控", "动能", "灵活走位"]
                }
            },
            "necromancer": {
                "name": "死灵法师",
                "skills": {
                    "core": ["骨刺", "骨爆", "鲜血尖刺", "尸体爆炸"],
                    "gore": ["血肉之墙", "血肉之盾", "骨牢"],
                    "curses": ["衰老", "易爆", "支配"],
                    "corpses": ["召唤骷髅", "骷髅法师", "复活尸体", "尸体爆炸"],
                    "blood": ["血雾", "鲜血穿梭", "血之新陈代谢"],
                    "ultimate": ["军团", "死灵之魂", "号令骸骨"],
                    "passive": ["骨骼强化", "亡魂精修", "骸骨精通", "鲜血精通", "死灵之赐", "活力", "最终奉祀"]
                },
                "builds": {
                    "summoner": ["召唤骷髅", "骷髅法师", "复活尸体", "军团", "骨骼强化", "亡魂精修", "骸骨精通"],
                    "bone": ["骨刺", "骨爆", "骨牢", "尸体爆炸", "死灵之赐", "鲜血精通", "活力"]
                }
            },
            "druid": {
                "name": "德鲁伊",
                "skills": {
                    "earth": ["崩石破", "山崩", "土狼", "石墙"],
                    "storm": ["风冲击", "龙卷风", "雷暴", "飓风封印"],
                    "werewolf": ["狼人撕咬", "狼群冲锋", "狂犬病毒", "血性本能"],
                    "werebear": ["熊人拍击", "爪击", "震地", "铁石之躯"],
                    "companion": ["狼魂", "渡鸦", "花猫", "蝎尾狮"],
                    "ultimate": ["巨狼", "暴熊", "天灾"],
                    "passive": ["野兽之心", "自然之力", "原初之怒", "过敏", "掠食", "适应", "风暴之力"]
                },
                "builds": {
                    "wind": ["龙卷风", "风冲击", "飓风封印", "狼魂", "原初之怒", "自然之力", "风暴之力"],
                    "shapeshift": ["狼人撕咬", "熊人拍击", "巨狼", "暴熊", "野兽之心", "掠食", "适应"]
                }
            },
            "paladin": {
                "name": "圣骑士",
                "skills": {
                    "core": ["祝福之锤", "正义之锤", "天堂之拳", "祝福枪击"],
                    "defensive": ["圣光护盾", "制裁", "反射", "天堂之光"],
                    "vasions": ["天堂之拳", "旅行者的祈祷"],
                    "conviction": ["审判", "狂热", "虔诚"],
                    "aura": ["力量", "抵抗", "救赎", "追求"],
                    "ultimate": ["毁灭", "战斗号召"],
                    "passive": ["狂热信念", "神盾", "力量信仰", "决心", "神圣庇护", "神圣意志"]
                },
                "builds": {
                    "hammerdin": ["祝福之锤", "审判", "狂热", "天堂之拳", "力量", "信仰", "狂热信念", "神圣庇护"],
                    "aura_holy": ["正义之锤", "制裁", "虔诚", "救赎", "抵抗", "神盾", "力量信仰", "决心"]
                }
            }
        }

    def _get_default_items(self):
        """返回默认装备数据"""
        return {
            "weapons": {
                "swords": [
                    {"name": "双手剑", "type": "近战", "damage": "高", "speed": "慢", "requirement": "高力量"},
                    {"name": "长剑", "type": "近战", "damage": "中", "speed": "中", "requirement": "中力量"},
                    {"name": "匕首", "type": "近战", "damage": "低", "speed": "快", "requirement": "低"}
                ],
                "staffs": [
                    {"name": "法杖", "type": "法师", "damage": "中", "speed": "中", "requirement": "高精力"},
                    {"name": "魔杖", "type": "法师", "damage": "低", "speed": "快", "requirement": "中精力"}
                ],
                "bows": [
                    {"name": "弓", "type": "远程", "damage": "中高", "speed": "快", "requirement": "高敏捷"},
                    {"name": "十字弓", "type": "远程", "damage": "高", "speed": "慢", "requirement": "中敏捷"}
                ],
                "polearms": [
                    {"name": "长柄武器", "type": "近战", "damage": "高", "speed": "慢", "requirement": "高力量"}
                ]
            },
            "armor": {
                "heavy": [
                    {"name": "板甲", "defense": "极高", "weight": "重", "requirement": "高力量"},
                    {"name": "锁子甲", "defense": "中高", "weight": "中", "requirement": "中力量"}
                ],
                "light": [
                    {"name": "皮甲", "defense": "中", "weight": "轻", "requirement": "低"},
                    {"name": "布甲", "defense": "低", "weight": "极轻", "requirement": "低"}
                ],
                "shields": [
                    {"name": "大盾牌", "defense": "高", "block": "高", "requirement": "高力量"},
                    {"name": "小盾牌", "defense": "中", "block": "中", "requirement": "中力量"}
                ]
            },
            "accessories": {
                "rings": [
                    {"name": "戒指", "slots": 2, "effects": ["属性加成", "抗性", "技能等级"]},
                ],
                "amulets": [
                    {"name": "项链", "slots": 1, "effects": ["技能等级", "抗性", "属性加成"]}
                ],
                "gloves": [
                    {"name": "手套", "effects": ["攻击速度", "元素伤害", "抗性"]}
                ],
                "boots": [
                    {"name": "靴子", "effects": ["移动速度", "抗性", "属性加成"]}
                ]
            },
            "runes": {
                "spirit": {"name": "精神", "runes": ["Tal", "Thul", "Ort", "Amn"], "effects": ["+2所有技能", "法力恢复"]},
                "enigma": {"name": "谜团", "runes": ["Jah", "Ith", "Ber"], "effects": ["等级1传送", "+2所有技能"]},
                "infinity": {"name": "无限", "runes": ["Ber", "Mal", "Ber", "Ist"], "effects": ["审判光环", "降低敌人抗性"]},
                "fortitude": {"name": "刚毅", "runes": ["El", "Sol", "Dol", "Lo"], "effects": ["+300%伤害/防御", "抗性"]}
            }
        }

    def get_quest_guide(self, quest_id):
        """获取任务指引"""
        for act, act_data in self.quests.items():
            for quest in act_data['quests']:
                if quest['id'] == quest_id:
                    return quest
        return None

    def get_boss_guide(self, boss_name):
        """获取BOSS攻略"""
        return self.bosses.get(boss_name.lower())

    def get_class_skills(self, class_name):
        """获取职业技能"""
        return self.skills.get(class_name.lower())

    def get_item_info(self, item_type):
        """获取装备信息"""
        return self.items.get(item_type.lower())

    def search_quest_by_location(self, location):
        """根据地点搜索任务"""
        for act, act_data in self.quests.items():
            for quest in act_data['quests']:
                if location.lower() in quest['location'].lower():
                    return quest
        return None

    def save_data(self):
        """保存数据到文件"""
        with open(os.path.join(DATA_DIR, 'quests.json'), 'w', encoding='utf-8') as f:
            json.dump(self.quests, f, ensure_ascii=False, indent=2)
        with open(os.path.join(DATA_DIR, 'bosses.json'), 'w', encoding='utf-8') as f:
            json.dump(self.bosses, f, ensure_ascii=False, indent=2)
        with open(os.path.join(DATA_DIR, 'skills.json'), 'w', encoding='utf-8') as f:
            json.dump(self.skills, f, ensure_ascii=False, indent=2)
        with open(os.path.join(DATA_DIR, 'items.json'), 'w', encoding='utf-8') as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)