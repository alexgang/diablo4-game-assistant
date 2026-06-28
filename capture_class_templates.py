"""
职业技能栏模板一键采集工具

使用方法:
1. 先启动游戏助手(确保 SDK 服务器已运行)
2. 在游戏中切换到任意职业(技能栏在所有界面都可见)
3. 运行本脚本: python capture_class_templates.py
4. 按提示输入当前职业(barbarian/rogue/sorcerer/druid/necromancer/spiritborn)
5. 脚本自动截图 + 裁剪技能栏 + 保存模板
6. 切换到下一个职业,重复操作

采集完成后,游戏助手就能通过技能栏图标识别职业了。
也支持从剪贴板导入: 先按 Win+Shift+S 框选游戏画面,再运行 paste <职业>。

注意: 采集时技能栏的技能配置不影响识别(模板匹配基于图标整体布局,
玩家自定义的技能键位/天赋搭配不会改变职业技能图标的固有样式)。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'class_icon_templates')

# 6 个职业(与 class_recommender.py D4Class 一致)
CLASS_LIST = [
    ('barbarian', '野蛮人'),
    ('rogue', '游侠'),
    ('sorcerer', '法师'),
    ('druid', '德鲁伊'),
    ('necromancer', '死灵法师'),
    ('spiritborn', '灵巫'),
]


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


def capture_from_clipboard():
    """从剪贴板读取截图(Win+Shift+S / PrintScreen 截图后直接粘贴)"""
    try:
        from PIL import ImageGrab, Image
        img = ImageGrab.grabclipboard()
        if img is None:
            print("  剪贴板中没有图片!")
            print("  请先按 Win+Shift+S 截图(或 PrintScreen),然后再运行本步骤")
            return None
        if isinstance(img, list):
            if not img:
                return None
            img = Image.open(img[0])
        img = img.convert('RGB')
        frame = np.array(img)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        print(f"  从剪贴板读取成功: shape={frame.shape}")
        return frame
    except Exception as e:
        print(f"  剪贴板读取失败: {e}")
        return None


def crop_skill_bar(frame):
    """裁剪技能池+技能栏合并区域(与 class_icon_detector.crop_skill_bar 一致)

    模板布局(752x768):
    - 上方 75% = 技能池(5行技能图标,该职业所有可用技能)
    - 下方 25% = 技能栏(6个当前装备的技能图标)

    相对坐标(2560x1600 实测校准):
    - 横向: 13% ~ 43%
    - 纵向: 50% ~ 97%
    """
    if frame is None or frame.size == 0:
        return None
    h, w = frame.shape[:2]
    x_min = int(w * 0.13)
    x_max = int(w * 0.43)
    y_min = int(h * 0.50)
    y_max = int(h * 0.97)
    if x_max <= x_min or y_max <= y_min:
        return None
    bar = frame[y_min:y_max, x_min:x_max]
    return bar if bar.size > 0 else None


def main():
    print("=" * 60)
    print("职业技能栏模板一键采集工具")
    print("=" * 60)
    print()
    print("采集说明:")
    print("  - 技能栏在所有游戏界面都可见(战斗/城镇/地图)")
    print("  - 6 个职业的技能图标各不相同,是识别职业的可靠依据")
    print("  - 玩家自定义的技能键位/天赋搭配不影响识别")
    print()

    os.makedirs(TEMPLATES_DIR, exist_ok=True)

    print("可采集的职业:")
    for eng, chn in CLASS_LIST:
        tpl = f'skill_bar_{eng}.png'
        exists = os.path.exists(os.path.join(TEMPLATES_DIR, tpl))
        mark = "[已存在]" if exists else "[待采集]"
        print(f"  {eng:14s} ({chn})  -> {tpl}  {mark}")
    print()

    while True:
        print("-" * 60)
        print("请在游戏中切换到目标职业,然后输入职业英文名")
        print("输入 'quit' 退出,输入 'list' 查看已采集模板")
        print("提示: 先按 Win+Shift+S 或 PrintScreen 截图,再输入 'paste <职业>' 从剪贴板导入")
        user_input = input("职业 (barbarian/rogue/sorcerer/druid/necromancer/spiritborn): ").strip().lower()

        if user_input == 'quit' or user_input == 'q':
            break
        if user_input == 'list':
            print("\n已采集模板:")
            for eng, chn in CLASS_LIST:
                path = os.path.join(TEMPLATES_DIR, f'skill_bar_{eng}.png')
                exists = os.path.exists(path)
                size = f"{os.path.getsize(path)//1024}KB" if exists else "-"
                print(f"  {eng:14s} ({chn})  {'[OK]' if exists else '[缺失]'} {size}")
            continue

        # 解析 paste 模式: "paste barbarian" 等
        use_clipboard = False
        if user_input.startswith('paste'):
            parts = user_input.split(maxsplit=1)
            if len(parts) < 2:
                print("  用法: paste <职业>,例如: paste druid")
                continue
            user_input = parts[1].strip()
            use_clipboard = True

        # 校验职业名
        class_names = [eng for eng, _ in CLASS_LIST]
        if user_input not in class_names:
            print(f"  未知职业: {user_input},请输入 {'/'.join(class_names)}")
            continue

        eng = user_input
        chn = next(c for e, c in CLASS_LIST if e == eng)
        print(f"\n正在采集 [{eng}] ({chn}) 技能栏模板...")

        if use_clipboard:
            # 剪贴板模式:直接读取
            print("从剪贴板读取截图...")
            frame = capture_from_clipboard()
        else:
            # 自动截图模式:3秒倒计时
            print("3秒后截图,请确保游戏画面中技能栏可见!")
            for i in range(3, 0, -1):
                print(f"  {i}...", end='', flush=True)
                time.sleep(1)
            print(" 截图!")
            frame = capture_game_screen()

        if frame is None or frame.size == 0:
            print("  截图失败!")
            continue

        print(f"  截图成功: shape={frame.shape}")

        # 裁剪技能栏
        skill_bar = crop_skill_bar(frame)
        if skill_bar is None or skill_bar.size == 0:
            print("  技能栏裁剪失败!")
            continue

        print(f"  技能栏裁剪成功: shape={skill_bar.shape}")

        # 保存模板
        tpl_path = os.path.join(TEMPLATES_DIR, f'skill_bar_{eng}.png')
        cv2.imwrite(tpl_path, skill_bar)
        print(f"  已保存模板: {tpl_path}")

        # 同时保存全屏截图(调试用,便于复查)
        debug_path = os.path.join(TEMPLATES_DIR, f'_debug_{eng}_full.png')
        cv2.imwrite(debug_path, frame)
        print(f"  已保存调试截图: {debug_path}")

    # 汇总
    print("\n" + "=" * 60)
    print("采集完成,当前模板库:")
    print("=" * 60)
    collected = 0
    for eng, chn in CLASS_LIST:
        path = os.path.join(TEMPLATES_DIR, f'skill_bar_{eng}.png')
        if os.path.exists(path):
            size = f"{os.path.getsize(path)//1024}KB"
            print(f"  [OK]   {eng:14s} ({chn})  {size}")
            collected += 1
        else:
            print(f"  [缺失] {eng:14s} ({chn})")
    print(f"\n已采集 {collected}/{len(CLASS_LIST)} 个职业技能栏模板")

    if collected == len(CLASS_LIST):
        print("\n所有职业技能栏模板已采集完毕!")
        print("现在可以启动游戏助手,职业识别将通过技能栏图标自动识别。")
    else:
        missing = len(CLASS_LIST) - collected
        print(f"\n还缺 {missing} 个职业模板,请切换到对应职业后继续采集。")


if __name__ == '__main__':
    main()
