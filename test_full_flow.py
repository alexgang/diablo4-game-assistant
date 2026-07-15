"""
完整功能流程测试
- 启动 SDK
- 模拟 Vision 场景识别
- 测试职业识别
- 测试 BD 推荐显示
"""
import sys
import os
sys.path.insert(0, '.')

import dxcam
import cv2
from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG
from class_recommender import (
    D4Class, CLASS_NAMES, detect_class_from_text,
    get_class_display_name, get_class_color, get_class_icon,
    DEFAULT_BUILDS,
)
from scene_classifier import classify_scene, SceneCategory

print("=== 完整流程测试 ===\n")

# 1. 测试截屏
print("1. 测试 dxcam 截屏")
camera = dxcam.create(output_idx=0)
frame = camera.grab()
camera.release()
print(f"  ✓ 截屏: shape={frame.shape}, mean={frame.mean():.2f}")
os.makedirs('game_screenshots', exist_ok=True)
test_path = 'game_screenshots/test_full.png'
cv2.imwrite(test_path, frame)

# 2. 测试 Vision 场景识别
print("\n2. 测试 Vision 场景识别")
sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
results = sdk.vision_query(SDK_CONFIG['instance_id'], test_path, topk=5, mode='basic')
print(f"  ✓ 查询到 {len(results)} 个匹配:")
for r in results:
    scene_id = r['scene_id']
    score = r['score']
    cat = classify_scene(scene_id)
    print(f"    - {scene_id} ({score*100:.0f}%) -> {cat.value}")

# 3. 测试职业识别（模拟 OCR 文本）
print("\n3. 测试职业识别（模拟 OCR）")
test_scenarios = [
    ('野蛮人', '测试我的野蛮人'),
    ('necromancer', 'Necromancer 钢铁傀儡'),
    ('rogue', '我的游侠在用穿刺'),
    ('sorcerer', '冰法正在输出'),
    ('druid', '德鲁伊大地熊'),
    ('paladin', '圣骑士祝福光环'),
]
for name, text in test_scenarios:
    cls = detect_class_from_text(text)
    icon = get_class_icon(cls) if cls else '❓'
    cname = get_class_display_name(cls) if cls else '未识别'
    print(f"  ✓ {name:15s} -> {icon} {cname}")

# 4. 测试职业的BD推荐数据
print("\n4. 测试职业的BD推荐数据")
for cls in D4Class:
    builds = DEFAULT_BUILDS.get(cls, [])
    icon = get_class_icon(cls)
    name = get_class_display_name(cls)
    print(f"  {icon} {name}: {len(builds)} 个BD推荐")
    for build in builds:
        print(f"    - {build.build_name} ({build.season})")

# 5. 测试 GUI 集成（仅检查方法存在）
print("\n5. 测试 GUI 集成")
import gui
from gui import MainWindow, BuildFetcherThread, SceneVisionWorker

methods = [
    '_on_class_changed', '_on_bd_changed', '_refresh_class_info',
    '_update_bd_combo', '_show_build_images', '_set_class_from_ocr',
    '_trigger_class_ocr', '_do_class_ocr', '_refresh_build_images',
    '_on_fetch_finished',
]
for m in methods:
    if hasattr(MainWindow, m):
        print(f"  ✓ MainWindow.{m}")
    else:
        print(f"  ✗ MainWindow.{m} 缺失")

print("\n=== 完整流程测试完成 ===")
