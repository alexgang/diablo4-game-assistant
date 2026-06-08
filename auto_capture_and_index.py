#!/usr/bin/env python3
"""
自动截图并加入 Vision 索引（无需用户交互）

流程：
1. 截取游戏当前画面
2. 截取若干个不同位置（装备面板/技能面板/地图面板）
3. 每个截图用合适的 scene_id 加入 Vision 索引
4. 重新构建 Vision 索引
5. 测试识别效果
"""

import os
import sys
import time
import logging
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import dxcam
import ctypes
from ctypes import wintypes
import mss
import numpy as np

from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG
from scene_classifier import classify_scene, get_category_display_name

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_screenshots')

logger = logging.getLogger(__name__)


def capture_full_screen():
    """截取游戏所在显示器的整个画面"""
    game_names = ['暗黑破坏神IV', 'Diablo IV']
    hwnd = None
    for name in game_names:
        hwnd = ctypes.windll.user32.FindWindowW(None, name)
        if hwnd:
            break

    if not hwnd:
        print("  ✗ 未找到游戏窗口")
        return None

    rect = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    cx = (rect.left + rect.right) // 2
    cy = (rect.top + rect.bottom) // 2

    region = None
    with mss.MSS() as sct:
        for i, mon in enumerate(sct.monitors[1:], 1):
            if mon['left'] <= cx < mon['left'] + mon['width']:
                region = (mon['left'], mon['top'], mon['width'], mon['height'])
                break

    for out_idx in range(4):
        try:
            if region:
                camera = dxcam.create(device_idx=0, output_idx=out_idx,
                                      region=region, output_color="BGR")
            else:
                camera = dxcam.create(device_idx=0, output_idx=out_idx,
                                      output_color="BGR")
            frame = camera.grab()
            camera.release()
            if frame is not None and frame.size > 0 and frame.mean() > 1:
                print(f"  ✓ 截图成功: shape={frame.shape}, mean={frame.mean():.1f}")
                return frame
        except Exception as e:
            pass
    print("  ✗ 所有 dxcam output_idx 失败")
    return None


def main():
    print("=" * 60)
    print("  自动截图并加入 Vision 索引")
    print("=" * 60)

    sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
    if not sdk.check_server():
        print("✗ SDK 未连接")
        return
    print(f"✓ SDK 已连接 (instance: {SDK_CONFIG['instance_id']})")

    print("\n[1/4] 截取当前游戏画面（装备界面）...")
    frame = capture_full_screen()
    if frame is None:
        return

    cv2.imwrite(os.path.join(SCREENSHOTS_DIR, "my_equipment_realtime.png"), frame)
    print("  ✓ 已保存: my_equipment_realtime.png")

    print("\n[2/4] 添加到 Vision 索引...")
    insert_targets = [
        ("my_equipment_realtime.png", "my_equipment", "my_equipment_pic"),
        ("Diablo4_S4_Inventory_Itemization_Before.png", "my_equipment_2", "my_equipment_pic2"),
        ("Diablo4_S4_Codex_of_Power.png", "my_equipment_3", "my_equipment_pic3"),
        ("Diablo4_S4_Tempering.png", "my_equipment_4", "my_equipment_pic4"),
        ("Diablo4_S4_Masterworking.png", "my_equipment_5", "my_equipment_pic5"),
        ("Diablo4_S4_Skill_Tree_01.png", "my_skill", "my_skill_pic"),
    ]

    for filename, scene_id, picture_id in insert_targets:
        path = os.path.join(SCREENSHOTS_DIR, filename)
        if not os.path.exists(path):
            print(f"  ⊘ 跳过: {filename} (不存在)")
            continue
        try:
            result = sdk.vision_insert_scene(
                SDK_CONFIG['instance_id'],
                scene_id,
                [path],
                picture_id,
            )
            print(f"  ✓ 插入: {filename} -> {result}")
        except Exception as e:
            print(f"  ✗ 插入失败: {filename}: {e}")

    print("\n[3/4] 重新构建 Vision 索引...")
    try:
        result = sdk.vision_build(SDK_CONFIG['instance_id'])
        print(f"  ✓ 索引构建完成: {result}")
    except Exception as e:
        print(f"  ✗ 构建失败: {e}")
        return

    print("\n[4/4] 测试查询当前游戏画面...")
    try:
        results = sdk.vision_query(SDK_CONFIG['instance_id'],
                                   os.path.join(SCREENSHOTS_DIR, "my_equipment_realtime.png"),
                                   topk=5, mode='basic')
        if results:
            print(f"  ✓ 查询成功，找到 {len(results)} 个匹配:")
            for i, r in enumerate(results, 1):
                scene_id = r.get('scene_id', '')
                score = r.get('score', 0)
                cat = classify_scene(scene_id)
                print(f"    [{i}] {scene_id} ({score*100:.1f}%) -> {get_category_display_name(cat)}")
        else:
            print("  ⚠ 仍然无匹配，需要更多样本")
    except Exception as e:
        print(f"  ✗ 查询失败: {e}")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
