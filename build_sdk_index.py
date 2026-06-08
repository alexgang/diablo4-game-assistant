#!/usr/bin/env python3
"""
SDK 索引构建工具 - Knowledge + MMR + Vision

用途：将游戏数据导入SDK服务，使Knowledge RAG和MMR查询可用
流程：
1. 从GameDatabase和web_data.json提取游戏内容
2. 生成文本文件并导入SDK Knowledge
3. 构建Knowledge索引
4. 将内容导入SDK MMR（支持图文联合检索）
5. 构建MMR索引

使用方法：
  python build_sdk_index.py              # 构建所有索引
  python build_sdk_index.py --knowledge  # 仅构建Knowledge
  python build_sdk_index.py --mmr        # 仅构建MMR
  python build_sdk_index.py --vision     # 仅构建Vision
"""

import json
import os
import sys
import tempfile
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdk_client import GamingAssistantSDK
from game_data import GameDatabase
from config import SDK_CONFIG, CACHE_DIR

INSTANCE_ID = SDK_CONFIG['instance_id']
KNOWLEDGE_ID = SDK_CONFIG['knowledge']['knowledge_id']
SDK_URL = SDK_CONFIG['server_url']
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), 'game_screenshots')
KNOWLEDGE_DATA_DIR = os.path.join(tempfile.gettempdir(), 'd4_sdk_knowledge')


def generate_knowledge_files():
    """从GameDatabase和web_data生成Knowledge文本文件"""
    os.makedirs(KNOWLEDGE_DATA_DIR, exist_ok=True)

    db = GameDatabase()
    files = []

    for act_key, act_data in db.quests.items():
        lines = [f"=== {act_data.get('name', act_key)} ===\n"]
        for quest in act_data.get('quests', []):
            lines.append(f"任务: {quest.get('name', '')}")
            lines.append(f"  地点: {quest.get('location', '')}")
            lines.append(f"  指引: {quest.get('guide', '')}")
            lines.append("")
        path = os.path.join(KNOWLEDGE_DATA_DIR, f'quests_{act_key}.txt')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        files.append(path)

    for boss_key, boss_data in db.bosses.items():
        lines = [f"=== BOSS: {boss_data.get('name', boss_key)} ===\n"]
        lines.append(f"所在章节: {boss_data.get('act', '')}")
        lines.append(f"弱点: {', '.join(boss_data.get('weakness', []))}")
        lines.append(f"技能: {', '.join(boss_data.get('skills', []))}")
        lines.append(f"攻略: {boss_data.get('guide', '')}")
        lines.append(f"奖励: {boss_data.get('rewards', '')}")
        path = os.path.join(KNOWLEDGE_DATA_DIR, f'boss_{boss_key}.txt')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        files.append(path)

    for class_key, class_data in db.skills.items():
        lines = [f"=== {class_data.get('name', class_key)} ===\n"]
        for category, skills in class_data.get('skills', {}).items():
            lines.append(f"{category}: {', '.join(skills)}")
        lines.append("\n构筑推荐:")
        for build_name, build_skills in class_data.get('builds', {}).items():
            lines.append(f"  {build_name}: {', '.join(build_skills)}")
        path = os.path.join(KNOWLEDGE_DATA_DIR, f'skills_{class_key}.txt')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        files.append(path)

    for item_type, item_data in db.items.items():
        lines = [f"=== 装备: {item_type} ===\n"]
        if isinstance(item_data, dict):
            for sub_type, items in item_data.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            name = item.get('name', '')
                            effects = item.get('effects', item.get('effect', ''))
                            if isinstance(effects, list):
                                effects = ', '.join(effects)
                            rarity = item.get('rarity', '')
                            slot = item.get('slot', item.get('type', ''))
                            lines.append(f"  {name} [{rarity}] ({slot}): {effects}")
                        else:
                            lines.append(f"  {item}")
        path = os.path.join(KNOWLEDGE_DATA_DIR, f'items_{item_type}.txt')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        files.append(path)

    cache_path = os.path.join(CACHE_DIR, 'web_data.json')
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            web_data = json.load(f)

        web_lines = []
        for guide in web_data.get('guides', []):
            web_lines.append(f"攻略: {guide.get('title', '')}")
            if guide.get('tags'):
                web_lines.append(f"  标签: {', '.join(guide['tags'])}")
            if guide.get('url'):
                web_lines.append(f"  链接: {guide['url']}")
            web_lines.append("")

        for bd in web_data.get('build_details', []):
            web_lines.append(f"构筑: {bd.get('title', '')}")
            if bd.get('tags'):
                web_lines.append(f"  标签: {', '.join(bd['tags'][:5])}")
            if bd.get('skills'):
                web_lines.append(f"  技能: {', '.join(bd['skills'][:8])}")
            if bd.get('equipment'):
                for eq in bd['equipment'][:5]:
                    if isinstance(eq, dict):
                        web_lines.append(f"  装备: {eq.get('name', '')} ({eq.get('slot', '')})")
            if bd.get('full_text'):
                web_lines.append(f"  详情: {bd['full_text'][:300]}")
            web_lines.append("")

        for skill in web_data.get('skills', []):
            web_lines.append(f"技能: {skill.get('name', '')} [{skill.get('class', '')}]")
            if skill.get('tags'):
                web_lines.append(f"  类型: {', '.join(skill['tags'][:4])}")
            if skill.get('description'):
                web_lines.append(f"  效果: {skill['description'][:100]}")
            web_lines.append("")

        for boss in web_data.get('boss_schedule', []):
            web_lines.append(f"世界BOSS: {boss.get('name', '')} - {boss.get('time', '')}")
            web_lines.append("")

        if web_lines:
            path = os.path.join(KNOWLEDGE_DATA_DIR, 'web_data.txt')
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(web_lines))
            files.append(path)

    print(f"✓ 已生成 {len(files)} 个知识文件到 {KNOWLEDGE_DATA_DIR}")
    return files


def build_knowledge_index(sdk):
    """构建Knowledge索引"""
    print("\n" + "=" * 60)
    print("  构建 Knowledge 索引")
    print("=" * 60)

    try:
        sdk.knowledge_init(INSTANCE_ID)
        print("✓ Knowledge实例已初始化")
    except Exception as e:
        if "has existed" in str(e):
            print("✓ Knowledge实例已存在")
        else:
            print(f"⚠️ 初始化: {e}")

    files = generate_knowledge_files()
    if not files:
        print("❌ 没有知识文件可导入")
        return False

    success_count = 0
    for i, fpath in enumerate(files, 1):
        fname = os.path.basename(fpath)
        texts_id = os.path.splitext(fname)[0]
        print(f"\n[{i}/{len(files)}] 导入: {fname}")

        try:
            sdk.knowledge_insert(
                instance_id=INSTANCE_ID,
                knowledge_id=KNOWLEDGE_ID,
                text_paths=[fpath],
                texts_id=texts_id,
            )
            print(f"  ✓ 成功导入")
            success_count += 1
        except Exception as e:
            print(f"  ❌ 导入失败: {e}")

    if success_count == 0:
        print("\n❌ 没有成功导入任何知识文件")
        return False

    print(f"\n正在构建Knowledge索引 ({success_count} 个文件)...")
    try:
        sdk.knowledge_build(INSTANCE_ID, full_build=True)
        print("\n✓ Knowledge索引构建完成!")
        return True
    except Exception as e:
        print(f"\n❌ Knowledge索引构建失败: {e}")
        return False


def build_mmr_index(sdk):
    """构建MMR索引"""
    print("\n" + "=" * 60)
    print("  构建 MMR 索引")
    print("=" * 60)

    try:
        sdk.mmr_init(INSTANCE_ID)
        print("✓ MMR实例已初始化")
    except Exception as e:
        if "has existed" in str(e):
            print("✓ MMR实例已存在")
        else:
            print(f"⚠️ 初始化: {e}")

    db = GameDatabase()
    records = []

    for act_key, act_data in db.quests.items():
        for quest in act_data.get('quests', []):
            text = f"{quest.get('name', '')} {quest.get('location', '')}"
            info = f"任务指引: {quest.get('guide', '')} (章节: {act_data.get('name', '')})"
            records.append((text, info))

    for boss_key, boss_data in db.bosses.items():
        text = f"BOSS: {boss_data.get('name', '')} 弱点: {', '.join(boss_data.get('weakness', []))}"
        info = f"攻略: {boss_data.get('guide', '')} 技能: {', '.join(boss_data.get('skills', []))}"
        records.append((text, info))

    for class_key, class_data in db.skills.items():
        for build_name, build_skills in class_data.get('builds', {}).items():
            text = f"{class_data.get('name', '')} {build_name}构筑: {', '.join(build_skills)}"
            info = f"职业: {class_data.get('name', '')} 构筑: {build_name}"
            records.append((text, info))

    cache_path = os.path.join(CACHE_DIR, 'web_data.json')
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            web_data = json.load(f)
        for bd in web_data.get('build_details', []):
            title = bd.get('title', '')
            skills = ', '.join(bd.get('skills', [])[:6])
            text = f"构筑: {title} 技能: {skills}"
            info = bd.get('full_text', '')[:200] if bd.get('full_text') else ''
            records.append((text, info))

    if not records:
        print("❌ 没有MMR记录可导入")
        return False

    print(f"\n导入 {len(records)} 条MMR记录...")
    success_count = 0
    for i, (text, info) in enumerate(records, 1):
        try:
            sdk.mmr_insert(
                instance_id=INSTANCE_ID,
                text=text,
                info=info,
            )
            success_count += 1
        except Exception as e:
            print(f"  [{i}] 插入失败: {e}")

    print(f"\n成功导入 {success_count}/{len(records)} 条记录")

    if success_count == 0:
        print("❌ 没有成功导入任何MMR记录")
        return False

    print("正在构建MMR索引...")
    try:
        sdk.mmr_build(INSTANCE_ID)
        print("\n✓ MMR索引构建完成!")
        return True
    except Exception as e:
        print(f"\n❌ MMR索引构建失败: {e}")
        return False


def build_vision_index(sdk):
    """构建Vision索引"""
    print("\n" + "=" * 60)
    print("  构建 Vision 索引")
    print("=" * 60)

    if not os.path.exists(SCREENSHOTS_DIR):
        os.makedirs(SCREENSHOTS_DIR)
        print(f"✓ 已创建截图目录: {SCREENSHOTS_DIR}")

    images = []
    for f in os.listdir(SCREENSHOTS_DIR):
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            images.append(f)

    if not images:
        print("\n📸 截图目录为空!")
        print(f"请将游戏截图放入: {SCREENSHOTS_DIR}")
        print("文件命名格式: 场景名称.png")
        print("\n建议截图内容:")
        print("  - 角色选择界面 (野蛮人/法师/游侠/死灵/德鲁伊)")
        print("  - 主菜单界面")
        print("  - 游戏内各章节场景")
        print("  - BOSS战界面")
        print("  - 技能界面 / 物品栏界面")
        return False

    try:
        sdk.vision_init(INSTANCE_ID)
        print("✓ Vision实例已初始化")
    except Exception as e:
        if "has existed" in str(e):
            print("✓ Vision实例已存在")
        else:
            print(f"⚠️ 初始化: {e}")

    success_count = 0
    for i, img_file in enumerate(images, 1):
        img_path = os.path.join(SCREENSHOTS_DIR, img_file)
        scene_id = os.path.splitext(img_file)[0]
        pictures_id = f"pic_{scene_id}"

        print(f"\n[{i}/{len(images)}] 插入场景: {scene_id}")
        try:
            sdk.vision_insert_scene(
                instance_id=INSTANCE_ID,
                scene_id=scene_id,
                image_paths=[img_path],
                pictures_id=pictures_id,
                mode="accurate",
            )
            print(f"  ✓ 成功插入")
            success_count += 1
        except Exception as e:
            print(f"  ❌ 插入失败: {e}")

    if success_count == 0:
        print("\n❌ 没有成功插入任何场景图片")
        return False

    print(f"\n正在构建Vision索引 ({success_count} 个场景)...")
    try:
        result = sdk.vision_build(INSTANCE_ID, mode="accurate", full_build=True)
        threshold = result.get('threshold', 'N/A')
        threshold_2 = result.get('threshold_2', 'N/A')
        print(f"\n✓ Vision索引构建完成!")
        print(f"  阈值: {threshold}")
        print(f"  阈值2: {threshold_2}")
        return True
    except Exception as e:
        print(f"\n❌ Vision索引构建失败: {e}")
        return False


def main():
    print("=" * 60)
    print("  SDK 索引构建工具")
    print("=" * 60)

    sdk = GamingAssistantSDK(SDK_URL)

    if not sdk.check_server():
        print("❌ SDK服务器未连接")
        print(f"   请先启动SDK服务器: {SDK_URL}")
        return

    print(f"✓ SDK服务器已连接: {SDK_URL}")

    build_know = '--knowledge' in sys.argv or len(sys.argv) == 1
    build_mmr_flag = '--mmr' in sys.argv or len(sys.argv) == 1
    build_vis = '--vision' in sys.argv or len(sys.argv) == 1

    results = {}

    if build_know:
        results['knowledge'] = build_knowledge_index(sdk)

    if build_mmr_flag:
        results['mmr'] = build_mmr_index(sdk)

    if build_vis:
        results['vision'] = build_vision_index(sdk)

    print("\n" + "=" * 60)
    print("  构建结果汇总")
    print("=" * 60)
    for name, success in results.items():
        status = "✓ 成功" if success else "❌ 失败"
        print(f"  {name}: {status}")

    if all(results.values()):
        print("\n🎉 所有索引构建完成！现在可以使用SDK进行智能查询了")
    elif any(results.values()):
        print("\n⚠️ 部分索引构建成功，其他服务可能需要额外数据")
    else:
        print("\n❌ 所有索引构建失败，请检查SDK服务状态")


if __name__ == "__main__":
    main()
