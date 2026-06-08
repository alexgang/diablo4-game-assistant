#!/usr/bin/env python3
"""
截图并添加到 Vision 索引工具

用途：
- 截取当前游戏画面
- 让用户命名场景 (装备/技能/地图/战斗)
- 自动加入 Vision 索引
- 立即生效
"""

import os
import sys
import tkinter as tk
from tkinter import simpledialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG
import cv2
import dxcam
import ctypes
from ctypes import wintypes

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_screenshots')


def capture_game_screen():
    """截取游戏屏幕（仅截游戏所在显示器）"""
    game_names = ['暗黑破坏神IV', 'Diablo IV']
    hwnd = None
    for name in game_names:
        hwnd = ctypes.windll.user32.FindWindowW(None, name)
        if hwnd:
            break

    if not hwnd:
        print("未找到游戏窗口")
        return None

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
                print(f"dxcam 截图成功: shape={frame.shape}, mean={frame.mean():.1f}")
                return frame
        except Exception:
            continue

    print("所有 dxcam output_idx 都失败")
    return None


def main():
    print("=" * 60)
    print("  截图并加入 Vision 索引")
    print("=" * 60)

    print("\n1. 截取游戏画面...")
    frame = capture_game_screen()
    if frame is None:
        print("截图失败，请确认游戏已启动")
        return

    root = tk.Tk()
    root.withdraw()

    while True:
        save_name = simpledialog.askstring(
            "保存截图",
            "请输入场景名称 (例如: my_equipment, my_skill_tree):\n(留空取消)"
        )
        if not save_name:
            print("用户取消")
            return

        save_name = save_name.strip().replace(' ', '_').replace('/', '_').replace('\\', '_')

        if not save_name:
            print("名称无效")
            continue

        save_path = os.path.join(SCREENSHOTS_DIR, f"{save_name}.png")
        if os.path.exists(save_path):
            overwrite = messagebox.askyesno("文件已存在", f"已存在 {save_name}.png，是否覆盖？")
            if not overwrite:
                continue

        cv2.imwrite(save_path, frame)
        print(f"\n2. 已保存: {save_path}")
        print(f"   文件大小: {os.path.getsize(save_path)/1024/1024:.1f} MB")

        print(f"\n3. 插入 Vision 索引...")
        sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
        if not sdk.check_server():
            print("SDK 未连接，无法插入索引")
            return

        try:
            picture_id = sdk.vision_insert_scene(SDK_CONFIG['instance_id'], save_path)
            print(f"   ✓ 插入成功: picture_id={picture_id}")
        except Exception as e:
            print(f"   ✗ 插入失败: {e}")
            return

        print(f"\n4. 重新构建 Vision 索引...")
        try:
            result = sdk.vision_build(SDK_CONFIG['instance_id'])
            print(f"   ✓ 构建完成: {result}")
        except Exception as e:
            print(f"   ✗ 构建失败: {e}")
            return

        print(f"\n5. 测试查询...")
        try:
            results = sdk.vision_query(SDK_CONFIG['instance_id'], save_path, topk=1, mode='basic')
            if results:
                top = results[0]
                print(f"   ✓ 查询成功: scene_id={top.get('scene_id')}, score={top.get('score', 0)*100:.0f}%")
            else:
                print(f"   ⚠ 查询返回空")
        except Exception as e:
            print(f"   ✗ 查询失败: {e}")

        print("\n" + "=" * 60)
        print("完成！新场景已加入 Vision 索引")
        print("=" * 60)

        another = messagebox.askyesno("继续截图", "是否再截一张图？")
        if not another:
            break

        print("\n重新截取游戏画面...")
        frame = capture_game_screen()
        if frame is None:
            print("截图失败，退出")
            break


if __name__ == "__main__":
    main()
