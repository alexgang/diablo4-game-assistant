#!/usr/bin/env python3
"""
测试搜索"游侠升级攻略"功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_data import GameDatabase
from content_indexer import ContentIndexer
import json

print("="*60)
print("搜索测试: 游侠升级攻略")
print("="*60)

# 初始化
db = GameDatabase()

# 加载网站数据
web_data_path = os.path.join(os.path.dirname(__file__), 'cache', 'web_data.json')
if os.path.exists(web_data_path):
    with open(web_data_path, 'r', encoding='utf-8') as f:
        web_data = json.load(f)
    print(f"\n✓ 已加载网站数据:")
    print(f"  - 攻略: {len(web_data.get('guides', []))} 条")
    print(f"  - 装备: {len(web_data.get('equipment', []))} 件")
    print(f"  - 技能: {len(web_data.get('skills', []))} 个")
    print(f"  - 构筑详情: {len(web_data.get('build_details', []))} 个")
    indexer = ContentIndexer(game_db=db, web_data=web_data)
else:
    print("⚠ 未找到网站数据缓存")
    indexer = ContentIndexer(game_db=db)

# 执行搜索
query = '游侠升级攻略'
print(f"\n{'='*60}")
print(f"搜索关键词: {query}")
print(f"{'='*60}")

results = indexer.search(query, top_n=10)
print(f"\n找到 {len(results)} 条结果:\n")

# 分类统计
categories = {}
for r in results:
    cat = r['category']
    if cat not in categories:
        categories[cat] = []
    categories[cat].append(r)

print("分类统计:")
for cat, items in categories.items():
    print(f"  • {cat}: {len(items)} 条")

print(f"\n{'='*60}")
print("详细结果")
print(f"{'='*60}\n")

for i, r in enumerate(results, 1):
    cat = r['category']
    score = r['score']
    data = r['data']

    print(f"[{i}] [{cat.upper()}] 相关度: {score:.1%}")
    print("-" * 50)

    if cat == 'skills':
        print(f"职业: {data.get('name', '')}")
        builds = data.get('builds', {})
        for build_name, skills in builds.items():
            print(f"  构筑: {build_name}")
            print(f"    技能: {', '.join(skills)}")

    elif cat == 'guides':
        print(f"攻略: {data.get('title', '')}")
        if data.get('author'):
            print(f"作者: {data.get('author', '')}")
        if data.get('url'):
            print(f"链接: {data.get('url', '')}")

    elif cat == 'build_details':
        print(f"构筑: {data.get('title', '')}")
        if data.get('author'):
            print(f"作者: {data.get('author', '')}")
        if data.get('tags'):
            print(f"标签: {', '.join(data.get('tags', []))}")
        if data.get('skills'):
            print(f"核心技能: {', '.join(data.get('skills', [])[:5])}")
        if data.get('core_gear'):
            print(f"核心装备: {', '.join(data.get('core_gear', [])[:3])}")

    elif cat == 'equipment':
        print(f"装备: {data.get('name', '')}")
        print(f"品质: {data.get('rarity', '')}")
        print(f"类型: {data.get('type', '')}")

    elif cat == 'web_skills':
        print(f"技能: {data.get('name', '')}")
        print(f"职业: {data.get('class', '')}")

    elif cat == 'bosses':
        print(f"BOSS: {data.get('name', '')}")
        print(f"弱点: {', '.join(data.get('weakness', []))}")

    elif cat == 'quests':
        print(f"任务: {data.get('name', '')}")
        print(f"地点: {data.get('location', '')}")

    print()

# 获取推荐
print(f"{'='*60}")
print("智能推荐")
print(f"{'='*60}\n")

recommendations = indexer.get_context_recommendations(query)
print(indexer.format_recommendations(recommendations))

print(f"\n{'='*60}")
print("测试完成")
print(f"{'='*60}")
