#!/usr/bin/env python3
"""测试场景分类器和 Vision 识别"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scene_classifier import SceneCategory, classify_scene, get_category_display_name
from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG

print("=" * 60)
print("场景分类器测试")
print("=" * 60)

test_cases = [
    ('diablo4_s4_inventory_itemization_before', '应该: 装备'),
    ('diablo4_s4_inventory_itemization_after', '应该: 装备'),
    ('diablo4_s4_codex_of_power', '应该: 装备'),
    ('diablo4_s4_tempering', '应该: 装备'),
    ('diablo4_s4_masterworking', '应该: 装备'),
    ('diablo4_s4_skill_tree_01', '应该: 技能'),
    ('diablo4_season_of_blood_blood_pact_01', '应该: 战斗'),
    ('diablo4_season_of_blood_dungeon_world_01', '应该: 战斗'),
    ('diablo4_s4_helltide_gameplay_001', '应该: 战斗'),
    ('diablo4_游侠', '应该: 装备'),
    ('diablo4_游侠装备', '应该: 装备'),
    ('some_random_scene', '应该: 未知/战斗'),
]

for scene_id, expected in test_cases:
    category = classify_scene(scene_id)
    display = get_category_display_name(category)
    print(f"  {scene_id:50s} -> {display}")

print("\n" + "=" * 60)
print("Vision 实时识别测试")
print("=" * 60)

sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
print(f"SDK状态: {'已连接' if sdk.check_server() else '未连接'}")

if not sdk.check_server():
    print("SDK未连接，跳过实时测试")
    sys.exit(1)

import cv2
import dxcam
import ctypes
from ctypes import wintypes

game_names = ['暗黑破坏神IV', 'Diablo IV']
hwnd = None
for name in game_names:
    hwnd = ctypes.windll.user32.FindWindowW(None, name)
    if hwnd:
        print(f"找到游戏窗口: {name}")
        break

if hwnd:
    print("\n使用 dxcam 截取游戏画面进行 Vision 识别...")
    rect = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    cx = (rect.left + rect.right) // 2
    cy = (rect.top + rect.bottom) // 2

    import mss
    region = None
    with mss.MSS() as sct:
        for i, mon in enumerate(sct.monitors[1:], 1):
            if mon['left'] <= cx < mon['left'] + mon['width']:
                region = (mon['left'], mon['top'], mon['width'], mon['height'])
                break

    frame = None
    for out_idx in range(4):
        try:
            if region:
                camera = dxcam.create(device_idx=0, output_idx=out_idx, region=region, output_color="BGR")
            else:
                camera = dxcam.create(device_idx=0, output_idx=out_idx, output_color="BGR")
            frame = camera.grab()
            camera.release()
            if frame is not None and frame.size > 0 and frame.mean() > 1:
                break
        except Exception:
            pass

    if frame is not None:
        cv2.imwrite('game_screenshots/_vision_query_test.png', frame)
        print(f"截图成功: shape={frame.shape}, mean={frame.mean():.1f}")

        try:
            results = sdk.vision_query(SDK_CONFIG['instance_id'],
                                       'game_screenshots/_vision_query_test.png',
                                       topk=3, mode='accurate')
            print(f"\nVision 查询结果 (top 3):")
            for i, r in enumerate(results, 1):
                scene_id = r.get('scene_id', '')
                score = r.get('score', 0)
                category = classify_scene(scene_id)
                display = get_category_display_name(category)
                print(f"  [{i}] {scene_id}")
                print(f"      置信度: {score*100:.1f}%  类别: {display}")
        except Exception as e:
            print(f"Vision 查询失败: {e}")
    else:
        print("截图失败")
else:
    print("未找到游戏窗口")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
