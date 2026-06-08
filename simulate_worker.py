#!/usr/bin/env python3
"""
模拟 GUI 的 SceneVisionWorker 测试
验证 5秒/次 自动检测 + Tab 切换逻辑
"""
import os
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG
from scene_classifier import classify_scene, get_category_display_name

import cv2
import dxcam
import ctypes
from ctypes import wintypes
import mss


def capture():
    game_names = ['暗黑破坏神IV', 'Diablo IV']
    hwnd = None
    for name in game_names:
        hwnd = ctypes.windll.user32.FindWindowW(None, name)
        if hwnd:
            break
    if not hwnd:
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
                return frame
        except Exception:
            continue
    return None


def main():
    print("=" * 60)
    print("  模拟 SceneVisionWorker 5秒/次自动检测")
    print("=" * 60)
    sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
    if not sdk.check_server():
        print("SDK未连接")
        return

    print("\n将连续运行3次检测 (5秒/次)，模拟GUI行为\n")
    last_category = None
    for i in range(3):
        print(f"\n--- 检测轮次 {i+1}/3 ---")
        t_start = time.time()
        frame = capture()
        if frame is None:
            print("  截图失败")
            time.sleep(5)
            continue
        tmp_path = f'game_screenshots/_worker_test_round_{i+1}.png'
        cv2.imwrite(tmp_path, frame)
        print(f"  截图: {frame.shape}, mean={frame.mean():.1f}")

        try:
            results = sdk.vision_query(SDK_CONFIG['instance_id'], tmp_path, topk=5, mode='basic')
            if not results:
                results = sdk.vision_query(SDK_CONFIG['instance_id'], tmp_path, topk=5, mode='accurate')
            if results:
                top = results[0]
                scene_id = top.get('scene_id', '')
                score = top.get('score', 0)
                if score >= 0.3:
                    category = classify_scene(scene_id)
                    display = get_category_display_name(category)
                    tab_index_map = {
                        'combat': 0, 'equipment': 1, 'skill': 2, 'map': 3, 'unknown': 0,
                    }
                    tab_idx = tab_index_map.get(category.value, 0)
                    tab_names = ['⚔ 战斗', '🛡 装备', '🔮 技能', '🗺 地图']
                    print(f"  ✓ Vision 识别: {scene_id} ({score*100:.0f}%)")
                    print(f"  ✓ 类别: {display}")
                    print(f"  → 应该切换到 Tab [{tab_idx}]: {tab_names[tab_idx]}")
                    if category != last_category:
                        print(f"  → 🔄 Tab 切换: {last_category} -> {category.value}")
                        last_category = category
                    else:
                        print(f"  → Tab 保持 (同一类别)")
                else:
                    print(f"  ⚠ 置信度过低: {score*100:.0f}% < 30%")
            else:
                print("  ⚠ Vision 无匹配")
        except Exception as e:
            print(f"  ✗ Vision 失败: {e}")

        elapsed = time.time() - t_start
        wait = max(0, 5 - elapsed)
        if i < 2:
            print(f"  等待 {wait:.1f} 秒...")
            time.sleep(wait)

    print("\n" + "=" * 60)
    print(f"  模拟完成，Tab 锁定在: {get_category_display_name(last_category) if last_category else '未知'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
