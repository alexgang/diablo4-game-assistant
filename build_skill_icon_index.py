#!/usr/bin/env python3
"""
将技能池图标添加到 SDK Vision 索引，用于职业识别

每个职业的技能池图标作为一个 scene 添加到 Vision 索引：
  scene_id = skill_icon_barbarian
  scene_id = skill_icon_rogue
  scene_id = skill_icon_sorcerer
  scene_id = skill_icon_druid
  scene_id = skill_icon_necromancer
  scene_id = skill_icon_spiritborn   (灵巫,赛季新职业)

查询时，技能栏图标匹配到某职业的任何技能池图标 → 该职业

使用方法:
  python build_skill_icon_index.py          # 添加并构建索引
  python build_skill_icon_index.py --test   # 测试匹配(需要先构建索引)
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG

SDK_URL = SDK_CONFIG['server_url']
INSTANCE_ID = SDK_CONFIG['instance_id']
POOL_DIR = os.path.join(os.path.dirname(__file__), 'class_icon_templates', 'pool')

# 6 个职业全列(含灵巫 spiritborn);采集了哪个职业的图标,POOL_DIR 下就会有对应子目录,
# 没有子目录的职业会在 add_skill_icons_to_index 里被自动跳过,所以全列不会报错。
CLASSES = ['barbarian', 'rogue', 'sorcerer', 'druid', 'necromancer', 'spiritborn']


def add_skill_icons_to_index(sdk):
    """将技能池图标添加到 Vision 索引"""
    print("=" * 60)
    print("添加技能池图标到 Vision 索引")
    print("=" * 60)

    # 初始化 Vision 实例
    try:
        sdk.vision_init(INSTANCE_ID)
        print("✓ Vision 实例已初始化")
    except Exception as e:
        if "has existed" in str(e):
            print("✓ Vision 实例已存在")
        else:
            print(f"⚠️ 初始化: {e}")

    total = 0
    for cls_name in CLASSES:
        cls_dir = os.path.join(POOL_DIR, cls_name)
        if not os.path.isdir(cls_dir):
            print(f"⚠️ 跳过 {cls_name}: 目录不存在")
            continue

        icons = sorted(glob.glob(os.path.join(cls_dir, '*.png')))
        if not icons:
            print(f"⚠️ 跳过 {cls_name}: 无图标文件")
            continue

        scene_id = f'skill_icon_{cls_name}'
        print(f"\n[{cls_name}] {len(icons)} 个图标 → scene_id={scene_id}")

        # 逐个添加图标到同一 scene
        success = 0
        for i, icon_path in enumerate(icons):
            pictures_id = f'{cls_name}_icon_{i:02d}'
            try:
                sdk.vision_insert_scene(
                    instance_id=INSTANCE_ID,
                    scene_id=scene_id,
                    image_paths=[icon_path],
                    pictures_id=pictures_id,
                    mode="accurate",
                )
                success += 1
            except Exception as e:
                print(f"  ❌ {os.path.basename(icon_path)}: {e}")

        print(f"  ✓ 成功添加 {success}/{len(icons)} 个图标")
        total += success

    print(f"\n总计添加 {total} 个技能图标到 Vision 索引")
    return total


def build_index(sdk):
    """构建 Vision 索引"""
    print("\n" + "=" * 60)
    print("构建 Vision 索引...")
    print("=" * 60)
    try:
        result = sdk.vision_build(INSTANCE_ID, mode="accurate", full_build=True)
        threshold = result.get('threshold', 'N/A')
        threshold_2 = result.get('threshold_2', 'N/A')
        print(f"✓ Vision 索引构建完成!")
        print(f"  阈值: {threshold}")
        print(f"  阈值2: {threshold_2}")
        return True
    except Exception as e:
        print(f"❌ 索引构建失败: {e}")
        return False


def crop_live_skill_bar(frame):
    """从全屏截图裁剪技能栏(6个图标) - 使用 config.py 的坐标"""
    h, w = frame.shape[:2]
    x_min = int(w * 0.30)
    x_max = int(w * 0.70)
    y_min = int(h * 0.85)
    y_max = int(h * 0.97)
    return frame[y_min:y_max, x_min:x_max]


def split_skill_bar_icons(bar):
    """分割技能栏为6个图标"""
    h, w = bar.shape[:2]
    slot_w = w // 6
    icons = []
    for i in range(6):
        x1 = i * slot_w
        x2 = (i + 1) * slot_w if i < 5 else w
        icons.append(bar[:, x1:x2])
    return icons


def test_match(sdk):
    """测试技能栏图标匹配"""
    print("\n" + "=" * 60)
    print("测试技能栏图标匹配")
    print("=" * 60)

    # 查找有效的游戏截图
    test_images = [
        '_debug_boss_marked_latest.png',
        '_debug_boss_marked.png',
        '_debug_marked.png',
        '_debug_top_grid.png',
    ]

    tmp_dir = os.path.join(os.path.dirname(__file__), '_tmp_query_icons')
    os.makedirs(tmp_dir, exist_ok=True)

    for img_path in test_images:
        if not os.path.exists(img_path):
            continue
        img = cv2.imread(img_path)
        if img is None:
            continue

        bar = crop_live_skill_bar(img)
        if bar.std() < 5:
            print(f"\n{img_path}: 纯色区域,跳过")
            continue

        icons = split_skill_bar_icons(bar)
        print(f"\n=== {img_path} ({img.shape}) ===")
        print(f"技能栏: {bar.shape}, 6个图标每个 {icons[0].shape}")

        # 统计每个职业的匹配数
        class_hits = {cls: 0 for cls in CLASSES}
        class_scores = {cls: [] for cls in CLASSES}

        for i, icon in enumerate(icons):
            if icon.std() < 5:
                print(f"  图标{i}: 纯色,跳过")
                continue

            # 保存图标到临时文件
            icon_path = os.path.join(tmp_dir, f'query_icon_{i}.png')
            cv2.imwrite(icon_path, icon)

            try:
                results = sdk.vision_query(
                    INSTANCE_ID, icon_path, topk=5, mode='accurate'
                )
                if results:
                    print(f"  图标{i}: ", end="")
                    for r in results[:3]:
                        scene_id = r.get('scene_id', '')
                        score = r.get('score', 0)
                        print(f"{scene_id}({score:.3f}) ", end="")
                        # 统计技能图标匹配
                        for cls in CLASSES:
                            if scene_id == f'skill_icon_{cls}':
                                class_hits[cls] += 1
                                class_scores[cls].append(score)
                    print()
                else:
                    print(f"  图标{i}: 无匹配结果")
            except Exception as e:
                print(f"  图标{i}: 查询失败 - {e}")

        # 汇总结果
        print(f"\n  匹配统计:")
        for cls in CLASSES:
            hits = class_hits[cls]
            scores = class_scores[cls]
            avg_score = np.mean(scores) if scores else 0
            max_score = max(scores) if scores else 0
            print(f"    {cls:14s}: hits={hits} avg={avg_score:.3f} max={max_score:.3f}")

        # 选出最佳职业
        best_cls = max(class_hits, key=lambda c: class_hits[c])
        if class_hits[best_cls] > 0:
            print(f"  → 识别结果: {best_cls} (hits={class_hits[best_cls]})")
        else:
            # 如果没有命中，用分数最高的
            best_cls = max(class_scores, key=lambda c: max(class_scores[c]) if class_scores[c] else 0)
            best_score = max(class_scores[best_cls]) if class_scores[best_cls] else 0
            if best_score > 0:
                print(f"  → 识别结果(按分数): {best_cls} (max_score={best_score:.3f})")
            else:
                print(f"  → 未识别到职业")


def main():
    sdk = GamingAssistantSDK(SDK_URL)

    if not sdk.check_server():
        print("❌ SDK 服务器未连接")
        print(f"   请先启动 SDK 服务器: {SDK_CONFIG.get('server_path', '')}")
        return

    print(f"✓ SDK 服务器已连接: {SDK_URL}")

    if '--test' in sys.argv:
        test_match(sdk)
    else:
        # 添加图标并构建索引
        total = add_skill_icons_to_index(sdk)
        if total > 0:
            if build_index(sdk):
                print("\n✓ 索引构建成功! 可以运行 'python build_skill_icon_index.py --test' 测试匹配")
            else:
                print("\n❌ 索引构建失败")
        else:
            print("\n❌ 没有添加任何图标")


if __name__ == '__main__':
    main()
