import json

d = json.load(open('cache/web_data.json', 'r', encoding='utf-8'))

print("=== 数据统计 ===")
for k, v in d['stats'].items():
    print(f"  {k}: {v}")
print(f"  总计: {sum(d['stats'].values())}")

print("\n=== 技能按职业分类 ===")
for cls, skills in d.get('skills_by_class', {}).items():
    print(f"  {cls}: {len(skills)} 个技能")

print("\n=== 构筑详情示例 ===")
for bd in d.get('build_details', [])[:2]:
    print(f"  标题: {bd['title']}")
    print(f"  标签: {bd['tags']}")
    print(f"  技能: {bd['skills'][:5]}")
    print(f"  装备: {bd['equipment'][:3]}")
    print(f"  攻略摘要: {bd['full_text'][:120]}...")
    print()

print("=== 暗金装备类型分布 ===")
type_count = {}
for eq in d.get('equipment', []):
    t = eq.get('type', '未知')
    if t not in type_count:
        type_count[t] = 0
    type_count[t] += 1
for t, c in sorted(type_count.items(), key=lambda x: -x[1]):
    print(f"  {t}: {c}")
