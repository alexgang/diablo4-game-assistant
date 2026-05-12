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
        """返回暗黑4默认任务数据"""
        return {
            "campaign": {
                "name": "主线任务",
                "quests": [
                    {"id": "q1", "name": "噩梦的开端", "location": "剑刃崖", "guide": "跟随指引到达避难所，与Nessa对话开启冒险"},
                    {"id": "q2", "name": "寻求庇护", "location": "避难所", "guide": "在避难所收集物资，建立防御工事"},
                    {"id": "q3", "name": "冰冻之息", "location": "斯科斯冠", "guide": "击败冰霜怪，收集冰霜碎片"},
                    {"id": "q4", "name": "撕裂天空", "location": "库尔浮沉", "guide": "在库尔浮沉击败Boss，获得关键道具"},
                    {"id": "q5", "name": "进入地狱", "location": "地狱之口", "guide": "穿过地狱之口进入烈焰地狱"},
                    {"id": "q6", "name": "奈克罗比里", "location": "卡尔蒂姆", "guide": "在卡尔蒂姆找到灵魂石，完成主线"}
                ]
            },
            "sidequest": {
                "name": "支线任务",
                "quests": [
                    {"id": "sq1", "name": "废弃的农场", "location": "撒加拿荒原", "guide": "清理农场中的怪物，救出被困的NPC"},
                    {"id": "sq2", "name": "沉没的图书馆", "location": "干流域", "guide": "探索水淹的图书馆，找到古老卷轴"},
                    {"id": "sq3", "name": "血色交易", "location": "卡尔蒂姆", "guide": "在卡尔蒂姆调查神秘商人，揭开血色交易的真相"},
                    {"id": "sq4", "name": "猎魔人", "location": "干燥平原", "guide": "帮助猎魔人清理区域内的恶魔巢穴"}
                ]
            }
        }

    def _get_default_bosses(self):
        """返回暗黑4默认BOSS数据"""
        return {
            "andariel_d4": {
                "name": "安达利尔",
                "act": "campaign",
                "weakness": ["冰霜伤害", "物理伤害"],
                "skills": ["剧毒新星", "蛛网喷射", "毒云"],
                "guide": "躲避地面毒液池，保持移动。利用安达利尔施放技能后的硬直窗口输出伤害。boss召唤小蜘蛛时优先清理。",
                "rewards": "大量经验，紫装掉落，第一章通关"
            },
            "durai": {
                "name": "都瑞尔",
                "act": "campaign",
                "weakness": ["物理伤害", "冰霜伤害"],
                "skills": ["冰冷冲锋", "甲壳护盾", "寒冰尖刺"],
                "guide": "boss进入护盾阶段时绕圈躲避尖刺伤害。物理Build优先输出，堆冰抗属性。",
                "rewards": "大量经验，传奇装备，第二章通关"
            },
            "mephisto_d4": {
                "name": "墨菲斯托",
                "act": "campaign",
                "weakness": ["火焰伤害", "物理伤害"],
                "skills": ["灵魂弹幕", "神圣审判", "相位打击"],
                "guide": "注意地面的灵魂池，站在安全区输出。召唤的灵魂优先击杀。保持移动避免神圣审判伤害。",
                "rewards": "大量经验，独特装备，第三章通关"
            },
            "lilith": {
                "name": "莉莉丝",
                "act": "campaign",
                "weakness": ["物理伤害", "冰霜伤害"],
                "skills": ["鲜血之雨", "暗影之触", "恐惧尖叫"],
                "guide": "莉莉丝会频繁传送，保持视角跟随。地面出现红色圈时快速离开。血量低时她会召唤小怪，优先处理。",
                "rewards": "主线通关，独特装备，等级提升"
            },
            "varshan": {
                "name": "瓦尔桑",
                "act": "nightmare",
                "weakness": ["火焰伤害", "物理伤害"],
                "skills": ["骨刺", "骨牢", "骨矛"],
                "guide": "躲避地面骨刺陷阱，boss施放骨牢时快速移动出圈。保持高护甲属性。",
                "rewards": "梦魇副本钥匙，传奇装备"
            }
        }

    def _get_default_skills(self):
        """返回暗黑4默认技能数据"""
        return {
            "barbarian": {
                "name": "野蛮人",
                "skills": {
                    "核心技能": ["顺劈斩", "锤击", "上古之锤", "疾奔"],
                    "防御技能": ["钢铁之肤", "战吼", "跳跃", "铁固"],
                    "被动技能": ["无情威力", "狂暴精神", "不灭", "战斗狂热"]
                },
                "builds": {
                    "粉碎野蛮人": ["顺劈斩", "地震", "战吼", "钢铁之肤", "跳跃"],
                    "狂战士之魂": ["狂战士之魂", "顺劈斩", "疾奔", "战吼", "被动技能全满"]
                }
            },
            "sorcerer": {
                "name": "法师",
                "skills": {
                    "冰霜系": ["冰霜球", "冰霜新星", "冰墙", "寒流"],
                    "火焰系": ["火球", "陨石", "燃烧", "传送"],
                    "闪电系": ["闪电箭", "连锁闪电", "电弧", "冰霜护盾"],
                    "被动技能": ["元素协调", "火焰精通", "冰霜精通", "静电能量"]
                },
                "builds": {
                    "冰霜法师": ["冰霜球", "冰霜新星", "寒流", "冰墙", "传送"],
                    "火焰法师": ["火球", "陨石", "燃烧", "冰霜护盾", "传送"]
                }
            },
            "rogue": {
                "name": "游侠",
                "skills": {
                    "核心技能": ["穿甲射击", "穿刺刃", "刀刃之舞", "灌注"],
                    "技巧技能": ["烟雾弹", "暗影脚步", "电网陷阱", "化学之力"],
                    "终极技能": ["Death Trap", "暗影集束", "寒霜之雨"],
                    "被动技能": ["暗影行者", "暴击精通", "伏击", "灵活机动"]
                },
                "builds": {
                    "穿刺游侠": ["穿刺刃", "穿甲射击", "烟雾弹", "电网陷阱", "暗影集束"],
                    "暗影游侠": ["刀刃之舞", "穿甲射击", "暗影脚步", "灌注", "Death Trap"]
                }
            },
            "necromancer": {
                "name": "死灵法师",
                "skills": {
                    "核心技能": ["骨刺", "骨矛", "亡灵军团", "精魂引爆"],
                    "召唤技能": ["骷髅战士", "骷髅法师", "魔像", "亡首护卫"],
                    "诅咒技能": ["脆弱", "衰老", "号令亡魂"],
                    "被动技能": ["骨系精通", "死灵宗师", "抽取精魄", "亡者之握"]
                },
                "builds": {
                    "召唤死灵": ["骷髅战士", "骷髅法师", "魔像", "亡首护卫", "精魂引爆"],
                    "骨系死灵": ["骨刺", "骨矛", "脆弱", "衰老", "号令亡魂"]
                }
            },
            "druid": {
                "name": "德鲁伊",
                "skills": {
                    "人形态技能": ["撕碎", "爪击", "大地震颤", "风暴之术"],
                    "变形技能": ["狼人变化", "熊人变化", "毁灭之爪", "地震"],
                    "被动技能": ["野兽之心", "自然之力", "原初之怒", "元素均衡"]
                },
                "builds": {
                    "狼德": ["撕碎", "大地震颤", "狼人变化", "风暴之术", "自然之力"],
                    "熊德": ["爪击", "毁灭之爪", "熊人变化", "大地震颤", "原初之怒"]
                }
            },
            "spiritborn": {
                "name": "灵刃",
                "skills": {
                    "核心技能": ["灵刃斩", "螳螂突刺", "虫群释放", "蜘蛛形态"],
                    "防御技能": ["蝗虫护盾", "蜈蚣之墙", "蜂群形态"],
                    "终极技能": ["魔奴呼唤", "蛛后降临"],
                    "被动技能": ["虫类精通", "灵性连接", "自然守卫", "协调灵性"]
                },
                "builds": {
                    "螳螂灵刃": ["螳螂突刺", "灵刃斩", "蝗虫护盾", "魔奴呼唤", "虫类精通"],
                    "蜘蛛灵刃": ["虫群释放", "蜘蛛形态", "蜈蚣之墙", "蛛后降临", "灵性连接"]
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