"""
场景模板一键采集工具

使用方法:
1. 先启动游戏助手(确保 SDK 服务器已运行)
2. 在游戏中切换到装备/技能/巅峰/地图界面
3. 运行本脚本: python capture_scene_templates.py
4. 按提示输入当前界面类型(equipment/skill/paragon/map/combat)
5. 脚本自动截图 + 保存模板 + 重建 Vision 索引
6. 切换到下一个界面,重复操作

采集完成后,游戏助手就能识别这些场景了。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np

from config import SDK_SERVER_PATH, SDK_SERVER_WORK_DIR
from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_screenshots')
INSTANCE_ID = SDK_CONFIG['instance_id']

# 场景模板文件名映射(与 gui.py _orb_template_match 中的路径一致)
SCENE_TEMPLATES = {
    'equipment': 'my_equipment_realtime2.png',
    'paragon': 'my_paragon_realtime.png',
    'skill': 'my_skill_realtime.png',
    'map': 'my_map_realtime.png',
    'combat': 'my_combat_realtime.png',
}


def capture_game_screen():
    """截取游戏所在显示器的画面"""
    # 方式1: dxcam
    try:
        import dxcam
        cam = dxcam.create(output_color="BGR")
        if cam is not None:
            frame = cam.grab()
            if frame is not None and frame.size > 0:
                return frame
    except Exception as e:
        print(f"  dxcam 失败: {e}")

    # 方式2: mss 截全屏
    try:
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # 主显示器
            sct_img = sct.grab(monitor)
            frame = np.array(sct_img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            return frame
    except Exception as e:
        print(f"  mss 失败: {e}")

    return None


def resize_to_1920(frame):
    """缩放到 1920 宽度(与 Vision 查询时一致)"""
    if frame is None:
        return None
    h, w = frame.shape[:2]
    if w > 1920:
        scale = 1920 / w
        frame = cv2.resize(frame, (1920, int(h * scale)), interpolation=cv2.INTER_AREA)
    return frame


def main():
    print("=" * 60)
    print("场景模板一键采集工具")
    print("=" * 60)

    sdk = GamingAssistantSDK()
    if not sdk.check_server():
        print("SDK 服务器未连接,请先启动游戏助手")
        return

    print(f"SDK 服务器已连接: {sdk.base_url}")
    print()

    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    print("可采集的场景:")
    for scene_type, filename in SCENE_TEMPLATES.items():
        exists = os.path.exists(os.path.join(SCREENSHOTS_DIR, filename))
        mark = "[已存在]" if exists else "[待采集]"
        print(f"  {scene_type:12s} -> {filename}  {mark}")
    print()

    # 初始化 Vision 实例
    try:
        sdk.vision_init(INSTANCE_ID)
        print(f"Vision 实例已初始化: {INSTANCE_ID}")
    except Exception as e:
        if "has existed" in str(e):
            print(f"Vision 实例已存在: {INSTANCE_ID}")
        else:
            print(f"Vision 初始化失败: {e}")
    print()

    while True:
        print("-" * 60)
        print("请在游戏中切换到目标界面,然后输入场景类型")
        print("输入 'quit' 退出,输入 'list' 查看已采集模板")
        user_input = input("场景类型 (equipment/skill/paragon/map/combat): ").strip().lower()

        if user_input == 'quit' or user_input == 'q':
            break
        if user_input == 'list':
            print("\n已采集模板:")
            for scene_type, filename in SCENE_TEMPLATES.items():
                path = os.path.join(SCREENSHOTS_DIR, filename)
                exists = os.path.exists(path)
                size = f"{os.path.getsize(path)//1024}KB" if exists else "-"
                print(f"  {scene_type:12s} {filename:35s} {'[OK]' if exists else '[缺失]'} {size}")
            continue
        if user_input not in SCENE_TEMPLATES:
            print(f"  未知场景: {user_input},请输入 equipment/skill/paragon/map/combat")
            continue

        filename = SCENE_TEMPLATES[user_input]
        print(f"\n正在采集 [{user_input}] 场景...")
        print("3秒后截图,请确保游戏界面已切换到位!")
        for i in range(3, 0, -1):
            print(f"  {i}...", end='', flush=True)
            time.sleep(1)
        print(" 截图!")

        frame = capture_game_screen()
        if frame is None or frame.size == 0:
            print("  截图失败!")
            continue

        print(f"  截图成功: shape={frame.shape}")

        # 缩放到 1920 宽度
        frame = resize_to_1920(frame)
        if frame is None:
            print("  缩放失败!")
            continue

        # 保存模板
        tpl_path = os.path.join(SCREENSHOTS_DIR, filename)
        cv2.imwrite(tpl_path, frame)
        print(f"  已保存模板: {tpl_path}")

        # 同时插入 Vision 索引
        scene_id = f'my_{user_input}'
        pictures_id = f'my_{user_input}_pic'
        try:
            sdk.vision_insert_scene(
                instance_id=INSTANCE_ID,
                scene_id=scene_id,
                image_paths=[tpl_path],
                pictures_id=pictures_id,
                mode="accurate",
            )
            print(f"  Vision 索引已插入: {scene_id}")
        except Exception as e:
            print(f"  Vision 插入失败: {e}")

    # 重建 Vision 索引
    print("\n" + "=" * 60)
    print("采集完成,正在重建 Vision 索引...")
    print("=" * 60)
    try:
        result = sdk.vision_build(INSTANCE_ID, mode="accurate", full_build=True)
        threshold = result.get('threshold', 'N/A')
        threshold_2 = result.get('threshold_2', 'N/A')
        print(f"Vision 索引构建完成!")
        print(f"  阈值: {threshold}")
        print(f"  阈值2: {threshold_2}")
    except Exception as e:
        print(f"索引构建失败: {e}")

    print("\n现在可以启动游戏助手,场景识别应该能正常工作了!")
    print("已采集的模板:")
    for scene_type, filename in SCENE_TEMPLATES.items():
        path = os.path.join(SCREENSHOTS_DIR, filename)
        if os.path.exists(path):
            print(f"  [OK] {scene_type}: {filename}")


if __name__ == "__main__":
    main()
