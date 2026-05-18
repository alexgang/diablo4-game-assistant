#!/usr/bin/env python3
"""
SDK Vision 索引构建工具

用途：构建游戏场景视觉识别索引
流程：
1. 收集场景图片（您手动截取游戏画面）
2. 为每张图片指定场景名称
3. 构建索引使 SDK 能够识别当前屏幕

使用方法：
1. 在游戏中切换到不同的界面/场景
2. 按 PrintScreen 或使用截图工具截取屏幕
3. 将截图保存到 game_screenshots 目录
4. 运行本脚本
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), 'game_screenshots')
SDK_URL = SDK_CONFIG['server_url']
INSTANCE_ID = SDK_CONFIG['instance_id']

def ensure_screenshots_dir():
    if not os.path.exists(SCREENSHOTS_DIR):
        os.makedirs(SCREENSHOTS_DIR)
        print(f"✓ 已创建截图目录: {SCREENSHOTS_DIR}")

def list_screenshots():
    if not os.path.exists(SCREENSHOTS_DIR):
        return []

    images = []
    for f in os.listdir(SCREENSHOTS_DIR):
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            images.append(f)
    return sorted(images)

def main():
    print("=" * 60)
    print("SDK Vision 索引构建工具")
    print("=" * 60)

    ensure_screenshots_dir()

    sdk = GamingAssistantSDK(SDK_URL)

    if not sdk.check_server():
        print("❌ SDK服务器未连接")
        print("   请先启动 SDK 服务器:")
        print(f"   cd \"{os.path.dirname(SDK_CONFIG['server_path'])}\"")
        print(f"   .\\{os.path.basename(SDK_CONFIG['server_path'])}\"")
        return

    print(f"✓ SDK服务器已连接: {SDK_URL}")

    images = list_screenshots()

    if not images:
        print("\n📸 截图目录为空!")
        print(f"\n请按以下步骤操作:")
        print(f"  1. 打开截图目录: {SCREENSHOTS_DIR}")
        print(f"  2. 在游戏中切换到不同界面/场景")
        print(f"  3. 截取屏幕 (PrintScreen) 并保存为图片文件")
        print(f"  4. 文件命名格式: 场景名称.png")
        print(f"\n建议截图内容:")
        print("  - 角色创建界面 (野蛮人、法师、游侠、死灵、德鲁伊)")
        print("  - 主菜单界面")
        print("  - 游戏内各个章节场景")
        print("  - BOSS战界面")
        print("  - 技能界面")
        print("  - 物品栏界面")
        print(f"\n截图支持格式: PNG, JPG, BMP")
        return

    print(f"\n找到 {len(images)} 张截图:")
    for i, img in enumerate(images, 1):
        print(f"  {i}. {img}")

    print("\n" + "-" * 60)
    print("开始构建索引...")
    print("-" * 60)

    try:
        sdk.vision_init(INSTANCE_ID)
        print("✓ Vision实例已初始化")
    except Exception as e:
        if "has existed" in str(e):
            print("✓ Vision实例已存在")
        else:
            print(f"⚠️ 初始化: {e}")

    success_count = 0
    for img_file in images:
        img_path = os.path.join(SCREENSHOTS_DIR, img_file)

        scene_id = os.path.splitext(img_file)[0]

        pictures_id = f"pic_{scene_id}"

        print(f"\n[{success_count + 1}/{len(images)}] 插入场景: {scene_id}")

        try:
            sdk.vision_insert_scene(
                instance_id=INSTANCE_ID,
                scene_id=scene_id,
                image_paths=[img_path],
                pictures_id=pictures_id,
                mode="accurate"
            )
            print(f"  ✓ 成功插入")
            success_count += 1
        except Exception as e:
            print(f"  ❌ 插入失败: {e}")

    if success_count == 0:
        print("\n❌ 没有成功插入任何场景图片")
        return

    print("\n" + "-" * 60)
    print(f"正在构建索引 ({success_count} 个场景)...")
    print("-" * 60)

    try:
        result = sdk.vision_build(INSTANCE_ID, mode="accurate", full_build=True)

        threshold = result.get('threshold', 'N/A')
        threshold_2 = result.get('threshold_2', 'N/A')

        print("\n✓ Vision 索引构建完成!")
        print(f"  阈值: {threshold}")
        print(f"  阈值2: {threshold_2}")
        print(f"  场景数量: {success_count}")
        print("\n现在可以识别以下场景:")
        for img in images:
            print(f"  - {os.path.splitext(img)[0]}")

    except Exception as e:
        print(f"\n❌ 索引构建失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()