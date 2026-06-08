#!/usr/bin/env python3
"""非交互式测试游戏助手核心功能"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG

print("=" * 60)
print("  游戏助手核心功能测试")
print("=" * 60)

sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
print(f"\n[1] SDK服务器: {'✓ 已连接' if sdk.check_server() else '✗ 未连接'}")

if not sdk.check_server():
    print("无法继续测试，请先启动SDK服务器")
    sys.exit(1)

instance_id = SDK_CONFIG['instance_id']
print(f"[2] Instance ID: {instance_id}")

print("\n[3] 测试 Vision 服务...")
try:
    sdk.vision_init(instance_id)
    print("    ✓ Vision 初始化成功")
except Exception as e:
    if "has existed" in str(e):
        print("    ✓ Vision 实例已存在")
    else:
        print(f"    ✗ Vision 失败: {e}")

print("\n[4] 测试知识库服务...")
try:
    sdk.knowledge_init(instance_id)
    print("    ✓ Knowledge 初始化成功")
except Exception as e:
    if "has existed" in str(e):
        print("    ✓ Knowledge 实例已存在")
    else:
        print(f"    ✗ Knowledge 失败: {e}")

print("\n[5] 测试截图能力...")
try:
    import dxcam
    import ctypes
    from ctypes import wintypes
    import numpy as np

    game_names = ['暗黑破坏神IV', 'Diablo IV']
    hwnd = None
    for name in game_names:
        hwnd = ctypes.windll.user32.FindWindowW(None, name)
        if hwnd:
            print(f"    ✓ 找到游戏窗口: {name} (hwnd={hwnd})")
            break

    if hwnd:
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        print(f"    窗口位置: ({rect.left}, {rect.top}) -> ({rect.right}, {rect.bottom})")

        camera = dxcam.create(device_idx=0, output_idx=1, output_color="BGR")
        frame = camera.grab()
        camera.release()

        if frame is not None and frame.size > 0:
            print(f"    ✓ dxcam 截图成功: shape={frame.shape}, mean={frame.mean():.1f}")
        else:
            print("    ✗ 截图失败")
    else:
        print("    ✗ 未找到游戏窗口")
except Exception as e:
    print(f"    ✗ 截图测试失败: {e}")

print("\n[6] 测试 Vision 查询...")
import os
test_img = None
for f in os.listdir('game_screenshots'):
    if f.endswith('.png'):
        full_path = os.path.join('game_screenshots', f)
        size = os.path.getsize(full_path) / 1024 / 1024
        if size > 0.5:
            test_img = full_path
            print(f"    使用测试图片: {f} ({size:.1f} MB)")
            break

if test_img:
    try:
        result = sdk.vision_query(instance_id, test_img)
        print(f"    ✓ Vision 查询成功")
        print(f"    结果: {result}")
    except Exception as e:
        print(f"    ✗ Vision 查询失败: {e}")

print("\n[7] 测试 Knowledge 查询...")
try:
    result = sdk.knowledge_query(instance_id, "暗黑破坏神4 游侠技能")
    print(f"    ✓ Knowledge 查询成功")
    print(f"    结果: {str(result)[:200]}")
except Exception as e:
    print(f"    ✗ Knowledge 查询失败: {e}")

print("\n" + "=" * 60)
print("  测试完成")
print("=" * 60)
