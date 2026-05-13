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
        quests_path = os.path.join(DATA_DIR, 'quests.json')
        if os.path.exists(quests_path):
            with open(quests_path, 'r', encoding='utf-8') as f:
                self.quests = json.load(f)
        else:
            self.quests = self._get_default_quests()

        bosses_path = os.path.join(DATA_DIR, 'bosses.json')
        if os.path.exists(bosses_path):
            with open(bosses_path, 'r', encoding='utf-8') as f:
                self.bosses = json.load(f)
        else:
            self.bosses = self._get_default_bosses()

        skills_path = os.path.join(DATA_DIR, 'skills.json')
        if os.path.exists(skills_path):
            with open(skills_path, 'r', encoding='utf-8') as f:
                self.skills = json.load(f)
        else:
            self.skills = self._get_default_skills()

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
                "name": "第一幕 - 弗列斯泰克",
                "quests": [
                    {"id": "q1", "name": "严寒中的希望", "location": "弗列斯泰克", "guide": "前往弗列斯泰克寻找幸存者"},
                    {"id": "q2", "name": "旧矿坑的秘密", "location": "旧矿坑", "guide": "探索旧矿坑，发现暗黑石的秘密"},
                    {"id": "q3", "name": "光之教堂", "location": "弗列斯泰克教堂", "guide": "调查光之教堂的异变"},
                    {"id": "q4", "name": "击败莉莉丝的仆从", "location": "弗列斯泰克", "guide": "击败莉莉丝的仆从，拯救弗列斯泰克"}
                ]
            },
            "act2": {
                "name": "第二幕 - 斯科斯格伦",
                "quests": [
                    {"id": "q5", "name": "枯萎的森林", "location": "斯科斯格伦", "guide": "调查斯科斯格伦森林的枯萎原因"},
                    {"id": "q6", "name": "德鲁伊的请求", "location": "图尔·杜拉", "guide": "帮助德鲁伊恢复自然之力"},
                    {"id": "q7", "name": "暗影之泉", "location": "暗影之泉", "guide": "净化被污染的暗影之泉"},
                    {"id": "q8", "name": "击败阿沙文", "location": "斯科斯格伦深处", "guide": "击败阿沙文，拯救斯科斯格伦"}
                ]
            },
            "act3": {
                "name": "第三幕 - 凯吉斯坦",
                "quests": [
                    {"id": "q9", "name": "沙漠中的秘密", "location": "凯吉斯坦沙漠", "guide": "探索凯吉斯坦沙漠中的远古遗迹"},
                    {"id": "q10", "name": "光明大教堂", "location": "卡尔蒂姆", "guide": "调查光明大教堂的阴谋"},
                    {"id": "q11", "name": "赫拉迪姆的遗产", "location": "赫拉迪姆圣所", "guide": "寻找赫拉迪姆的遗物"},
                    {"id": "q12", "name": "击败艾尼尔", "location": "卡尔蒂姆地下", "guide": "击败艾尼尔，阻止黑暗仪式"}
                ]
            },
            "act4": {
                "name": "第四幕 - 干燥草原",
                "quests": [
                    {"id": "q13", "name": "天使与恶魔", "location": "地狱之门", "guide": "前往地狱之门寻找真相"},
                    {"id": "q14", "name": "伊纳瑞斯的审判", "location": "天堂之阶", "guide": "面对伊纳瑞斯的审判"}
                ]
            },
            "act5": {
                "name": "第五幕 - 哈维扎",
                "quests": [
                    {"id": "q15", "name": "最后的赫拉迪姆", "location": "哈维扎", "guide": "集结最后的赫拉迪姆成员"},
                    {"id": "q16", "name": "深渊之门", "location": "深渊", "guide": "进入深渊，面对最终的黑暗"},
                    {"id": "q17", "name": "灵魂之井", "location": "灵魂之井", "guide": "摧毁灵魂之井，切断莉莉丝的力量"},
                    {"id": "q18", "name": "击败莉莉丝", "location": "深渊核心", "guide": "面对莉莉丝，拯救圣休亚瑞"}
                ]
            }
        }

    def _get_default_bosses(self):
        """返回默认BOSS数据"""
        return {
            "liliths_daughter": {
                "name": "莉莉丝之女",
                "act": "act1",
                "weakness": ["火焰", "神圣"],
                "skills": ["暗影触手", "腐蚀之雨", "暗影传送"],
                "guide": "保持移动躲避暗影触手，使用火属性技能攻击",
                "rewards": "大量经验，第一幕通关"
            },
            "ashava": {
                "name": "阿沙文",
                "act": "act2",
                "weakness": ["冰冷", "神圣"],
                "skills": ["暗影之拥", "枯萎之触", "暗影传送"],
                "guide": "堆高暗影抗性，使用冰/神圣技能攻击",
                "rewards": "大量经验，第二幕通关"
            },
            "aenir": {
                "name": "艾尼尔",
                "act": "act3",
                "weakness": ["闪电", "火焰"],
                "skills": ["沙暴", "石化凝视", "地震"],
                "guide": "注意躲避石化凝视，保持移动",
                "rewards": "大量经验，第三幕通关，高级装备"
            },
            "inarius": {
                "name": "伊纳瑞斯",
                "act": "act4",
                "weakness": ["暗影", "毒素"],
                "skills": ["天使之怒", "圣光审判", "神圣之盾"],
                "guide": "使用暗影属性攻击，躲避圣光审判的范围",
                "rewards": "大量经验，第四幕通关，顶级装备"
            },
            "lilith": {
                "name": "莉莉丝",
                "act": "act5",
                "weakness": ["神圣", "火焰"],
                "skills": ["暗影风暴", "腐蚀之触", "末日降临", "暗影裂隙"],
                "guide": "最终BOSS，保持高抗性，躲避暗影裂隙和末日降临",
                "rewards": "大量经验，游戏通关，顶级装备"
            }
        }

    def _get_default_skills(self):
        """返回默认技能数据"""
        return {
            "barbarian": {
                "name": "野蛮人",
                "skills": {
                    "core": ["打击", "狂乱", "旋风斩", "先祖之锤"],
                    "defensive": ["挑战怒吼", "战吼", "无视痛楚", "铁皮"],
                    "weapon_mastery": ["重击", "双持投掷", "狂暴者之怒"],
                    "ultimate": ["先祖召唤", "狂战士之怒"],
                    "passive": ["无尽怒火", "武器专家", "残暴", "好斗", "厚皮", "不屈意志"]
                },
                "builds": {
                    "whirlwind": ["旋风斩", "战吼", "先祖召唤", "狂暴者之怒", "无尽怒火", "残暴", "好斗"],
                    "thorns": ["狂乱", "挑战怒吼", "铁皮", "无视痛楚", "厚皮", "不屈意志"]
                }
            },
            "sorcerer": {
                "name": "法师",
                "skills": {
                    "fire": ["火球", "焚烧", "火墙", "陨石"],
                    "ice": ["冰霜弹", "冰霜新星", "暴风雪", "冰封之球"],
                    "lightning": ["电弧", "连锁闪电", "传送", "不稳定电流"],
                    "conjuration": ["九头蛇", "冰霜射线", "火焰强化"],
                    "passive": ["元素协调", "玻璃大炮", "燃烧本能", "冰冷之触", "电光火石", "元素大师"]
                },
                "builds": {
                    "fireball": ["火球", "焚烧", "陨石", "元素大师", "燃烧本能", "玻璃大炮"],
                    "blizzard": ["暴风雪", "冰封之球", "冰霜新星", "冰冷之触", "元素协调", "元素大师"]
                }
            },
            "rogue": {
                "name": "游侠",
                "skills": {
                    "core": ["穿刺射击", "快刀乱刺", "乱射", "穿射"],
                    "agility": ["暗影步", "疾行", "闪避", "逃脱"],
                    "subterfuge": ["暗影伪装", "烟雾弹", "毒陷阱", "暗影灌注"],
                    "combo": ["刀锋之舞", "回旋刀锋", "致命华彩"],
                    "ultimate": ["暗影之雨", "死亡之影"],
                    "passive": ["隐秘", "精准", "暗影掌控", "动能", "灵活走位", "暗影之拥"]
                },
                "builds": {
                    "rapidfire": ["穿刺射击", "暗影步", "暗影灌注", "暗影之雨", "精准", "动能", "暗影掌控"],
                    "twinning": ["快刀乱刺", "刀锋之舞", "回旋刀锋", "闪避", "灵活走位", "隐秘", "暗影之拥"]
                }
            },
            "necromancer": {
                "name": "死灵法师",
                "skills": {
                    "core": ["骨刺", "骨爆", "鲜血尖刺", "收割"],
                    "corpse": ["尸体爆炸", "骷髅战士", "骷髅法师", "魔像"],
                    "blood": ["血雾", "鲜血穿梭", "鲜血之壁"],
                    "bone": ["骨牢", "骨风暴", "骨墙"],
                    "ultimate": ["亡者大军", "血潮"],
                    "passive": ["骨骼强化", "亡魂精修", "鲜血精通", "死灵之赐", "活力", "最终奉祀"]
                },
                "builds": {
                    "summoner": ["骷髅战士", "骷髅法师", "魔像", "亡者大军", "骨骼强化", "亡魂精修", "最终奉祀"],
                    "bone_spear": ["骨刺", "骨爆", "骨风暴", "骨牢", "鲜血精通", "死灵之赐", "活力"]
                }
            },
            "druid": {
                "name": "德鲁伊",
                "skills": {
                    "earth": ["崩石破", "山崩", "石化之怒"],
                    "storm": ["风冲击", "龙卷风", "雷暴", "飓风"],
                    "werewolf": ["狼人撕咬", "狂犬病", "血性本能"],
                    "werebear": ["熊人拍击", "震地", "铁石之躯"],
                    "companion": ["狼群", "渡鸦", "藤蔓"],
                    "ultimate": ["灰熊之怒", "大灾变"],
                    "passive": ["野兽之心", "自然之力", "原初之怒", "掠食", "适应", "风暴之力"]
                },
                "builds": {
                    "tornado": ["龙卷风", "风冲击", "飓风", "狼群", "原初之怒", "自然之力", "风暴之力"],
                    "werewolf": ["狼人撕咬", "狂犬病", "灰熊之怒", "血性本能", "野兽之心", "掠食", "适应"]
                }
            }
        }

    def _get_default_items(self):
        return {
            "weapons": {
                "swords": [
                    {"name": "屠夫的砍刀", "type": "双手剑", "damage": "高", "speed": "慢", "rarity": "暗金", "effect": "对流血敌人暴击率+15%"},
                    {"name": "末日先驱", "type": "单手剑", "damage": "中高", "speed": "中", "rarity": "暗金", "effect": "暗影伤害+40%"}
                ],
                "staffs": [
                    {"name": "埃苏的传家宝", "type": "法杖", "damage": "中", "speed": "中", "rarity": "暗金", "effect": "火焰技能伤害+30%"}
                ],
                "bows": [
                    {"name": "风之力的回响", "type": "弓", "damage": "中高", "speed": "快", "rarity": "暗金", "effect": "远程伤害+25%"}
                ],
                "daggers": [
                    {"name": "暗影之拥", "type": "匕首", "damage": "低", "speed": "极快", "rarity": "暗金", "effect": "暗影灌注伤害+50%"}
                ],
                "maces": [
                    {"name": "碎骨锤", "type": "双手锤", "damage": "极高", "speed": "慢", "rarity": "暗金", "effect": "晕眩持续时间+30%"}
                ]
            },
            "armor": {
                "heavy": [
                    {"name": "先祖之怒", "defense": "极高", "slot": "胸甲", "rarity": "暗金", "effect": "狂暴时伤害+50%"},
                    {"name": "血涌", "defense": "高", "slot": "胸甲", "rarity": "暗金", "effect": "鲜血技能伤害+40%"}
                ],
                "light": [
                    {"name": "无限之焰", "defense": "中", "slot": "胸甲", "rarity": "暗金", "effect": "火焰技能暴击+20%"},
                    {"name": "冰霜织造者", "defense": "中高", "slot": "胸甲", "rarity": "暗金", "effect": "冰霜技能消耗-25%"}
                ],
                "helmets": [
                    {"name": "哈维拉的教诲", "defense": "高", "slot": "头盔", "rarity": "暗金", "effect": "全技能+2"},
                    {"name": "风暴之眼", "defense": "中", "slot": "头盔", "rarity": "暗金", "effect": "风暴技能伤害+40%"}
                ]
            },
            "accessories": {
                "rings": [
                    {"name": "星火之环", "slots": 1, "effects": ["闪电伤害+20%", "暴击率+8%"], "rarity": "暗金"},
                    {"name": "夜嚎", "slots": 1, "effects": ["暗影伤害+25%", "移动速度+10%"], "rarity": "暗金"}
                ],
                "amulets": [
                    {"name": "哈维拉的誓言", "slots": 1, "effects": ["全技能+3", "全抗性+15%"], "rarity": "暗金"},
                    {"name": "艾尼弗的奖赏", "slots": 1, "effects": ["资源生成+20%", "技能伤害+15%"], "rarity": "暗金"}
                ],
                "gloves": [
                    {"name": "灰烬之握", "effects": ["攻击速度+12%", "火焰伤害+15%"], "rarity": "暗金"},
                    {"name": "冰霜之触", "effects": ["暴击率+8%", "冰霜伤害+20%"], "rarity": "暗金"}
                ],
                "boots": [
                    {"name": "暗影之步", "effects": ["移动速度+15%", "暗影步+1"], "rarity": "暗金"},
                    {"name": "风暴行者", "effects": ["移动速度+12%", "闪避+8%"], "rarity": "暗金"}
                ]
            },
            "unique_items": [
                {"name": "屠夫的砍刀", "slot": "双手武器", "rarity": "暗金", "effect": "对流血敌人暴击率+15%"},
                {"name": "哈维拉的誓言", "slot": "护符", "rarity": "暗金", "effect": "所有技能+3"},
                {"name": "先祖之怒", "slot": "胸甲", "rarity": "暗金", "effect": "狂暴时伤害+50%"},
                {"name": "风暴之眼", "slot": "头盔", "rarity": "暗金", "effect": "风暴技能伤害+40%"},
                {"name": "末日先驱", "slot": "单手武器", "rarity": "暗金", "effect": "暗影伤害+40%"},
                {"name": "埃苏的传家宝", "slot": "法杖", "rarity": "暗金", "effect": "火焰技能伤害+30%"},
                {"name": "星火之环", "slot": "戒指", "rarity": "暗金", "effect": "闪电伤害+20%"},
                {"name": "暗影之拥", "slot": "匕首", "rarity": "暗金", "effect": "暗影灌注伤害+50%"},
                {"name": "血涌", "slot": "胸甲", "rarity": "暗金", "effect": "鲜血技能伤害+40%"},
                {"name": "灰烬之握", "slot": "手套", "rarity": "暗金", "effect": "攻击速度+12%"},
                {"name": "暗影之步", "slot": "靴子", "rarity": "暗金", "effect": "移动速度+15%"},
                {"name": "冰霜织造者", "slot": "胸甲", "rarity": "暗金", "effect": "冰霜技能消耗-25%"}
            ]
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
