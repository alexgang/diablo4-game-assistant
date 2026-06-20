"""
测试职业推荐系统集成
"""
import sys
import os
sys.path.insert(0, '.')

print("=== 测试 1: 职业识别 ===")
from class_recommender import (
    D4Class, CLASS_NAMES, detect_class_from_text,
    get_class_display_name, get_class_color, get_class_icon,
    DEFAULT_BUILDS,
)

test_texts = [
    '我的野蛮人在用先祖之锤',
    'Necromancer 钢铁傀儡 build',
    'Druid 大地熊',
    '游侠箭雨',
    '法师冰法',
    '灵巫虎掌猛击',
    '这是一个无关的文本',
]
for text in test_texts:
    cls = detect_class_from_text(text)
    name = get_class_display_name(cls) if cls else '未识别'
    icon = get_class_icon(cls) if cls else '❓'
    color = get_class_color(cls) if cls else '#888'
    print(f'  "{text}" -> {icon} {name} ({color})')

print("\n=== 测试 2: BD 默认数据 ===")
for cls in D4Class:
    builds = DEFAULT_BUILDS.get(cls, [])
    print(f'  {get_class_icon(cls)} {get_class_display_name(cls)}: {len(builds)} 个BD')
    for build in builds:
        print(f'    - {build.build_name} ({build.season})')

print("\n=== 测试 3: GUI 集成 ===")
try:
    import gui
    print(f'  ✓ gui.py 加载成功')

    # 检查 MainWindow 是否有相关方法
    from gui import MainWindow
    methods_to_check = [
        '_on_class_changed', '_on_bd_changed', '_refresh_class_info',
        '_update_bd_combo', '_show_build_images', '_set_class_from_ocr',
        '_trigger_class_ocr', '_do_class_ocr', '_refresh_build_images',
    ]
    for m in methods_to_check:
        if hasattr(MainWindow, m):
            print(f'  ✓ MainWindow.{m} 存在')
        else:
            print(f'  ✗ MainWindow.{m} 缺失')

    # 检查是否有 BuildFetcherThread
    from gui import BuildFetcherThread
    print(f'  ✓ BuildFetcherThread 已定义')

    # 检查 SceneVisionWorker 仍然存在
    from gui import SceneVisionWorker
    print(f'  ✓ SceneVisionWorker 仍然存在')

except Exception as e:
    print(f'  ✗ GUI 集成测试失败: {e}')
    import traceback
    traceback.print_exc()

print("\n=== 所有测试完成 ===")
