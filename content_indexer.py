#!/usr/bin/env python3
"""
内容索引引擎 - 根据游戏窗口内容智能匹配相关攻略和数据

核心功能：
1. 从屏幕OCR文字中提取关键词
2. 在本地数据库和网站缓存数据中进行模糊匹配
3. 按相关度排序返回结果
4. 生成上下文感知的推荐建议
"""

import json
import os
import re
from difflib import SequenceMatcher


class ContentIndexer:
    """内容索引引擎"""

    def __init__(self, game_db=None, web_data=None):
        self.game_db = game_db
        self.web_data = web_data
        self._build_index()

    def _build_index(self):
        """构建倒排索引"""
        self.index = {
            'quests': [],
            'bosses': [],
            'skills': [],
            'items': [],
            'guides': [],
            'equipment': [],
            'boss_schedule': [],
            'web_skills': [],
            'build_details': [],
        }
        self._index_local_data()
        self._index_web_data()

    def _index_local_data(self):
        """索引本地游戏数据"""
        if not self.game_db:
            return

        for act_key, act_data in self.game_db.quests.items():
            for quest in act_data.get('quests', []):
                self.index['quests'].append({
                    'id': quest.get('id'),
                    'name': quest.get('name', ''),
                    'location': quest.get('location', ''),
                    'guide': quest.get('guide', ''),
                    'act': act_data.get('name', ''),
                    'keywords': self._extract_keywords(
                        f"{quest.get('name', '')} {quest.get('location', '')} {quest.get('guide', '')}"
                    ),
                    'source': 'local',
                })

        for boss_key, boss_data in self.game_db.bosses.items():
            self.index['bosses'].append({
                'id': boss_key,
                'name': boss_data.get('name', ''),
                'weakness': boss_data.get('weakness', []),
                'skills': boss_data.get('skills', []),
                'guide': boss_data.get('guide', ''),
                'rewards': boss_data.get('rewards', ''),
                'keywords': self._extract_keywords(
                    f"{boss_data.get('name', '')} {' '.join(boss_data.get('weakness', []))} "
                    f"{' '.join(boss_data.get('skills', []))} {boss_data.get('guide', '')}"
                ),
                'source': 'local',
            })

        for class_key, class_data in self.game_db.skills.items():
            skill_names = []
            for category, skills in class_data.get('skills', {}).items():
                skill_names.extend(skills)
            build_info = []
            for build_name, build_skills in class_data.get('builds', {}).items():
                build_info.append(f"{build_name} {' '.join(build_skills)}")

            self.index['skills'].append({
                'id': class_key,
                'name': class_data.get('name', ''),
                'skills': class_data.get('skills', {}),
                'builds': class_data.get('builds', {}),
                'keywords': self._extract_keywords(
                    f"{class_data.get('name', '')} {' '.join(skill_names)} {' '.join(build_info)}"
                ),
                'source': 'local',
            })

        for item_type, item_data in self.game_db.items.items():
            if isinstance(item_data, dict):
                for sub_type, items in item_data.items():
                    if isinstance(items, list):
                        for item in items:
                            name = item.get('name', '') if isinstance(item, dict) else str(item)
                            desc = str(item) if isinstance(item, dict) else name
                            self.index['items'].append({
                                'name': name,
                                'type': f"{item_type}/{sub_type}",
                                'data': item,
                                'keywords': self._extract_keywords(name + ' ' + desc),
                                'source': 'local',
                            })
                    elif isinstance(items, dict):
                        name = items.get('name', sub_type)
                        desc = str(items)
                        self.index['items'].append({
                            'name': name,
                            'type': item_type,
                            'data': items,
                            'keywords': self._extract_keywords(name + ' ' + desc),
                            'source': 'local',
                        })

    def _index_web_data(self):
        """索引网站缓存数据"""
        if not self.web_data:
            return

        for guide in self.web_data.get('guides', []):
            title = guide.get('title', '')
            self.index['guides'].append({
                'title': title,
                'url': guide.get('url', ''),
                'author': guide.get('author', ''),
                'tags': guide.get('tags', []),
                'keywords': self._extract_keywords(title),
                'source': 'web',
            })

        for equip in self.web_data.get('equipment', []):
            name = equip.get('name', '')
            stats = ' '.join(equip.get('stats', []))
            self.index['equipment'].append({
                'name': name,
                'rarity': equip.get('rarity', ''),
                'stats': equip.get('stats', []),
                'keywords': self._extract_keywords(f"{name} {stats}"),
                'source': 'web',
            })

        for boss in self.web_data.get('boss_schedule', []):
            self.index['boss_schedule'].append({
                'name': boss.get('name', ''),
                'time': boss.get('time', ''),
                'source': 'web',
            })

        for skill in self.web_data.get('skills', []):
            name = skill.get('name', '')
            cls = skill.get('class', '')
            tags = ' '.join(skill.get('tags', []))
            desc = skill.get('description', '')
            self.index['web_skills'].append({
                'name': name,
                'class': cls,
                'tags': skill.get('tags', []),
                'description': desc,
                'keywords': self._extract_keywords(f"{name} {cls} {tags} {desc}"),
                'source': 'web',
            })

        for detail in self.web_data.get('build_details', []):
            title = detail.get('title', '')
            tags = ' '.join(detail.get('tags', []))
            skills = ' '.join(detail.get('skills', []))
            equip_list = detail.get('equipment', [])
            if equip_list and isinstance(equip_list[0], dict):
                equip = ' '.join(f"{e.get('name','')} {e.get('slot','')}" for e in equip_list)
            else:
                equip = ' '.join(str(e) for e in equip_list)
            aspects = ' '.join(detail.get('aspects', []))
            full_text = detail.get('full_text', '')
            self.index['build_details'].append({
                'bd_id': detail.get('bd_id', ''),
                'title': title,
                'url': detail.get('url', ''),
                'tags': detail.get('tags', []),
                'author': detail.get('author', ''),
                'skills': detail.get('skills', []),
                'equipment': detail.get('equipment', []),
                'full_text': full_text[:500],
                'keywords': self._extract_keywords(f"{title} {tags} {skills} {equip} {aspects} {full_text[:500]}"),
                'source': 'web',
            })

        for build in self.web_data.get('builds', []):
            title = build.get('title', '')
            tags = ' '.join(build.get('tags', []))
            existing_titles = {d.get('title') for d in self.index['build_details']}
            if title not in existing_titles:
                self.index['guides'].append({
                    'title': title,
                    'url': build.get('url', ''),
                    'author': '',
                    'tags': build.get('tags', []),
                    'keywords': self._extract_keywords(f"{title} {tags}"),
                    'source': 'web',
                })

    def _extract_keywords(self, text):
        """从文本中提取关键词"""
        if not text:
            return set()

        stop_words = {'的', '在', '和', '与', '或', '了', '是', '有', '为', '中',
                      '到', '从', '被', '把', '让', '将', '对', '等', '及', '以',
                      'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                      'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                      'would', 'could', 'should', 'may', 'might', 'can', 'shall',
                      'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                      'and', 'or', 'but', 'not', 'no', 'all', 'any', 'each'}

        text = text.lower()
        words = set()

        cn_chars = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        for phrase in cn_chars:
            for i in range(len(phrase)):
                for j in range(i + 2, min(i + 6, len(phrase) + 1)):
                    words.add(phrase[i:j])

        en_words = re.findall(r'[a-zA-Z]{2,}', text)
        words.update(w for w in en_words if w not in stop_words)

        digits = re.findall(r'\d+', text)
        words.update(digits)

        return words

    def _calc_relevance(self, query_keywords, entry_keywords):
        """计算相关度分数"""
        if not query_keywords or not entry_keywords:
            return 0.0

        exact_matches = query_keywords & entry_keywords
        exact_score = len(exact_matches) * 2.0

        fuzzy_score = 0.0
        unmatched_query = query_keywords - entry_keywords
        unmatched_entry = entry_keywords - query_keywords

        for qk in unmatched_query:
            best_ratio = 0.0
            for ek in unmatched_entry:
                ratio = SequenceMatcher(None, qk, ek).ratio()
                best_ratio = max(best_ratio, ratio)
            if best_ratio > 0.6:
                fuzzy_score += best_ratio

        total_possible = len(query_keywords)
        if total_possible == 0:
            return 0.0

        return (exact_score + fuzzy_score) / total_possible

    def search(self, screen_text, top_n=5, categories=None):
        """
        根据屏幕文字搜索相关内容

        Args:
            screen_text: 从游戏画面OCR识别的文字
            top_n: 返回前N个结果
            categories: 限定搜索的分类列表，None表示搜索所有

        Returns:
            按相关度排序的搜索结果
        """
        query_keywords = self._extract_keywords(screen_text)
        if not query_keywords:
            return []

        results = []
        search_categories = categories or self.index.keys()

        for category in search_categories:
            if category not in self.index:
                continue

            for entry in self.index[category]:
                score = self._calc_relevance(query_keywords, entry.get('keywords', set()))
                if score > 0.1:
                    results.append({
                        'category': category,
                        'score': round(score, 3),
                        'data': {k: v for k, v in entry.items() if k != 'keywords'},
                    })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_n]

    def get_context_recommendations(self, screen_text):
        """
        根据屏幕内容生成上下文感知的推荐

        Args:
            screen_text: 从游戏画面OCR识别的文字

        Returns:
            结构化的推荐结果
        """
        results = self.search(screen_text, top_n=30)
        recommendations = {
            'quest_hints': [],
            'boss_tips': [],
            'build_guides': [],
            'equipment_suggestions': [],
            'web_guides': [],
            'boss_schedule': [],
            'skill_info': [],
            'build_details': [],
        }

        for result in results:
            category = result['category']
            data = result['data']
            score = result['score']

            if category == 'quests' and score > 0.2:
                recommendations['quest_hints'].append({
                    'name': data.get('name', ''),
                    'location': data.get('location', ''),
                    'guide': data.get('guide', ''),
                    'act': data.get('act', ''),
                    'relevance': score,
                })

            elif category == 'bosses' and score > 0.2:
                recommendations['boss_tips'].append({
                    'name': data.get('name', ''),
                    'weakness': data.get('weakness', []),
                    'skills': data.get('skills', []),
                    'guide': data.get('guide', ''),
                    'relevance': score,
                })

            elif category == 'skills' and score > 0.2:
                recommendations['build_guides'].append({
                    'class': data.get('name', ''),
                    'builds': data.get('builds', {}),
                    'relevance': score,
                })

            elif category == 'items' and score > 0.2:
                recommendations['equipment_suggestions'].append({
                    'name': data.get('name', ''),
                    'type': data.get('type', ''),
                    'data': data.get('data', {}),
                    'relevance': score,
                })

            elif category == 'guides' and score > 0.15:
                recommendations['web_guides'].append({
                    'title': data.get('title', ''),
                    'url': data.get('url', ''),
                    'author': data.get('author', ''),
                    'tags': data.get('tags', []),
                    'relevance': score,
                })

            elif category == 'equipment' and score > 0.15:
                recommendations['equipment_suggestions'].append({
                    'name': data.get('name', ''),
                    'rarity': data.get('rarity', ''),
                    'type': data.get('type', ''),
                    'stats': data.get('stats', []),
                    'relevance': score,
                    'source': 'web',
                })

            elif category == 'boss_schedule' and score > 0.1:
                recommendations['boss_schedule'].append({
                    'name': data.get('name', ''),
                    'time': data.get('time', ''),
                })

            elif category == 'web_skills' and score > 0.2:
                recommendations['skill_info'].append({
                    'name': data.get('name', ''),
                    'class': data.get('class', ''),
                    'tags': data.get('tags', []),
                    'description': data.get('description', ''),
                    'relevance': score,
                })

            elif category == 'build_details' and score > 0.15:
                recommendations['build_details'].append({
                    'title': data.get('title', ''),
                    'url': data.get('url', ''),
                    'tags': data.get('tags', []),
                    'author': data.get('author', ''),
                    'skills': data.get('skills', []),
                    'equipment': data.get('equipment', []),
                    'full_text': data.get('full_text', ''),
                    'relevance': score,
                })

        return recommendations

    def format_recommendations(self, recommendations):
        """格式化推荐结果为可读文本"""
        lines = []

        if recommendations['quest_hints']:
            lines.append("📋 任务指引")
            for hint in recommendations['quest_hints'][:3]:
                lines.append(f"  [{hint['act']}] {hint['name']}")
                lines.append(f"    地点: {hint['location']}")
                lines.append(f"    攻略: {hint['guide']}")
                lines.append(f"    相关度: {hint['relevance']:.0%}")
            lines.append("")

        if recommendations['boss_tips']:
            lines.append("👹 BOSS攻略")
            for tip in recommendations['boss_tips'][:3]:
                lines.append(f"  {tip['name']}")
                lines.append(f"    弱点: {', '.join(tip['weakness'])}")
                lines.append(f"    技能: {', '.join(tip['skills'])}")
                lines.append(f"    攻略: {tip['guide']}")
                lines.append(f"    相关度: {tip['relevance']:.0%}")
            lines.append("")

        if recommendations['build_guides']:
            lines.append("🎯 流派推荐")
            for build in recommendations['build_guides'][:3]:
                lines.append(f"  {build['class']}")
                for build_name, skills in build['builds'].items():
                    lines.append(f"    {build_name}: {', '.join(skills)}")
                lines.append(f"    相关度: {build['relevance']:.0%}")
            lines.append("")

        if recommendations['web_guides']:
            lines.append("🌐 热门攻略")
            for guide in recommendations['web_guides'][:5]:
                lines.append(f"  {guide['title']}")
                if guide.get('tags'):
                    lines.append(f"    标签: {', '.join(guide['tags'])}")
                lines.append(f"    相关度: {guide['relevance']:.0%}")
            lines.append("")

        if recommendations['equipment_suggestions']:
            lines.append("⚔️ 装备推荐")
            for equip in recommendations['equipment_suggestions'][:5]:
                source_tag = " [网站]" if equip.get('source') == 'web' else ""
                lines.append(f"  {equip['name']}{source_tag}")
                if equip.get('stats') and isinstance(equip['stats'], list):
                    for stat in equip['stats'][:3]:
                        lines.append(f"    - {stat}")
                lines.append(f"    相关度: {equip['relevance']:.0%}")
            lines.append("")

        if recommendations['boss_schedule']:
            lines.append("⏰ 事件时间")
            for event in recommendations['boss_schedule']:
                lines.append(f"  {event['name']}: {event['time']}")
            lines.append("")

        if recommendations['skill_info']:
            lines.append("🔮 技能信息")
            for skill in recommendations['skill_info'][:5]:
                lines.append(f"  {skill['name']} [{skill['class']}]")
                if skill.get('tags'):
                    lines.append(f"    类型: {', '.join(skill['tags'][:4])}")
                if skill.get('description'):
                    lines.append(f"    效果: {skill['description'][:80]}")
                lines.append(f"    相关度: {skill['relevance']:.0%}")
            lines.append("")

        if recommendations['build_details']:
            lines.append("📖 构筑详情")
            for bd in recommendations['build_details'][:3]:
                lines.append(f"  {bd['title']}")
                if bd.get('tags'):
                    lines.append(f"    标签: {', '.join(bd['tags'][:4])}")
                if bd.get('skills'):
                    lines.append(f"    技能: {', '.join(bd['skills'][:6])}")
                if bd.get('equipment'):
                    eq_list = bd['equipment'][:4]
                    if eq_list and isinstance(eq_list[0], dict):
                        eq_str = ', '.join(f"{e.get('name','')}({e.get('slot','')})" for e in eq_list)
                    else:
                        eq_str = ', '.join(str(e) for e in eq_list)
                    lines.append(f"    装备: {eq_str}")
                if bd.get('full_text'):
                    lines.append(f"    攻略: {bd['full_text'][:100]}...")
                lines.append(f"    相关度: {bd['relevance']:.0%}")
            lines.append("")

        if not lines:
            lines.append("未找到与当前画面相关的内容")

        return '\n'.join(lines)

    def reload_web_data(self, web_data):
        """重新加载网站数据"""
        self.web_data = web_data
        self.index['guides'] = []
        self.index['equipment'] = []
        self.index['boss_schedule'] = []
        self.index['web_skills'] = []
        self.index['build_details'] = []
        self._index_web_data()


if __name__ == "__main__":
    from game_data import GameDatabase

    db = GameDatabase()

    cache_path = os.path.join(os.path.dirname(__file__), 'cache', 'web_data.json')
    web_data = None
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            web_data = json.load(f)

    indexer = ContentIndexer(game_db=db, web_data=web_data)

    print("=" * 60)
    print("  内容索引引擎 - 交互式测试")
    print("=" * 60)
    print("\n输入游戏画面文字（输入 q 退出）：\n")

    test_cases = [
        "安达利尔 地下墓穴",
        "野蛮人 旋风斩",
        "塔拉夏的古墓 都瑞尔",
        "术士 开荒",
        "暗金 护符 德鲁伊",
        "世界Boss 地狱狂潮",
    ]

    for text in test_cases:
        print(f"\n{'─' * 50}")
        print(f"输入: {text}")
        print(f"{'─' * 50}")
        recs = indexer.get_context_recommendations(text)
        print(indexer.format_recommendations(recs))
