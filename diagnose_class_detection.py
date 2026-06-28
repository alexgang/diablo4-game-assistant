#!/usr/bin/env python3
"""
职业识别诊断工具 —— 在真机上逐策略体检，定位"识别不出职业"的断点。

背景:职业识别是 4 级降级链(见 gui.py 的 ClassWorker):
  策略0 角色名 OCR  →  策略1 技能栏图标 Vision 匹配(主方案)
  →  策略2 主属性 OCR  →  策略3 关键词 OCR
任一级失效都会让整链退化。本脚本对一张游戏截图逐级体检,打印每级
的输入/输出/失败原因,一眼看出断在哪。

用法:
  # 用一张游戏截图诊断(推荐先在角色界面或战斗中截图)
  python diagnose_class_detection.py <screenshot.png>

  # 不传图则实时截当前游戏画面(需游戏在前台)
  python diagnose_class_detection.py

诊断结论会标注每级状态:
  ✅ 命中   ⚠️ 可用但未命中   ❌ 依赖缺失(无法工作)
"""
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger('diagnose')

try:
    import cv2
    import numpy as np
except ImportError as e:
    print(f"❌ 缺少 opencv/numpy: {e}\n   请在真机环境(已装依赖)运行本脚本。")
    sys.exit(1)


def _section(title):
    print("\n" + "=" * 64)
    print(f"  {title}")
    print("=" * 64)


def _load_frame(path):
    """加载截图;无路径则实时截屏。"""
    if path:
        if not os.path.exists(path):
            print(f"❌ 截图不存在: {path}")
            sys.exit(1)
        img = cv2.imread(path)
        if img is None:
            print(f"❌ 无法读取图片(格式损坏?): {path}")
            sys.exit(1)
        print(f"✅ 已加载截图: {path}  shape={img.shape}")
        return img
    # 实时截屏
    try:
        from screen_capture import ScreenCapture
        cap = ScreenCapture()
        img = cap.capture_full_screen()
        if img is None or img.size == 0:
            print("❌ 实时截屏为空(游戏是否在前台?)")
            sys.exit(1)
        print(f"✅ 实时截屏成功  shape={img.shape}")
        # 存一份供事后查看
        out = os.path.join(os.path.dirname(__file__), '_diag_frame.png')
        cv2.imwrite(out, img)
        print(f"   已保存到 {out}")
        return img
    except Exception as e:
        print(f"❌ 实时截屏失败: {e}")
        sys.exit(1)


def diag_resources():
    """体检:静态资源是否齐备(决定了哪些策略有可能工作)。"""
    _section("0. 资源体检 — 各策略的依赖是否到位")
    base = os.path.dirname(os.path.abspath(__file__))

    # 技能图标库(策略1 Vision 主方案依赖)
    pool = os.path.join(base, 'class_icon_templates', 'pool')
    if os.path.isdir(pool):
        classes = [d for d in os.listdir(pool) if os.path.isdir(os.path.join(pool, d))]
        counts = {c: len([f for f in os.listdir(os.path.join(pool, c)) if f.endswith('.png')])
                  for c in classes}
        if counts:
            print(f"✅ 技能图标库存在: {counts}")
        else:
            print(f"⚠️ 技能图标库目录存在但为空: {pool}")
    else:
        print(f"❌ 技能图标库缺失: {pool}")
        print("   → 策略1(Vision 图标匹配,即'主方案')无法工作。")
        print("   → 需先用 capture_class_templates.py 采集图标,再 build_skill_icon_index.py 建索引。")

    # 本地模板(策略1 的本地回退 + 整图回退)
    tpl_dir = os.path.join(base, 'class_icon_templates')
    if os.path.isdir(tpl_dir):
        skill_bar_tpls = [f for f in os.listdir(tpl_dir) if f.startswith('skill_bar_')]
        icon_tpls = [f for f in os.listdir(tpl_dir)
                     if f.endswith('.png') and not f.startswith(('skill_bar_', '_query', '_diag'))]
        print(f"{'✅' if skill_bar_tpls else '⚠️'} 技能栏整图模板: {len(skill_bar_tpls)} 个 {skill_bar_tpls}")
        print(f"{'✅' if icon_tpls else '⚠️'} 职业图标模板: {len(icon_tpls)} 个 {icon_tpls}")
    else:
        print(f"⚠️ 模板目录不存在(将由检测器自动创建): {tpl_dir}")

    # 角色名映射(策略0)
    try:
        from class_recommender import CHARACTER_NAME_TO_CLASS, AMBIGUOUS_CHARACTER_NAMES
        print(f"ℹ️ 角色名映射: {len(CHARACTER_NAME_TO_CLASS)} 个确定 + "
              f"{len(AMBIGUOUS_CHARACTER_NAMES)} 个重名(需消歧)")
        print(f"   注意:此表为硬编码,仅覆盖 {list(CHARACTER_NAME_TO_CLASS.keys())},换角色需手工维护。")
    except Exception as e:
        print(f"⚠️ 读取角色名映射失败: {e}")


def diag_sdk():
    """体检:SDK 服务与 Vision 索引(策略1 主方案的运行时依赖)。"""
    _section("1. SDK 服务 & Vision 索引体检")
    try:
        from sdk_client import GamingAssistantSDK
        from config import SDK_CONFIG
    except Exception as e:
        print(f"❌ 导入 sdk_client 失败: {e}")
        return None

    sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
    if not sdk.check_server():
        print(f"❌ SDK 服务未运行: {SDK_CONFIG['server_url']}")
        print("   → 策略1 的 Vision 匹配全部失效。请先启动 GameAssistantToolServer。")
        return None
    print(f"✅ SDK 服务在线: {SDK_CONFIG['server_url']}")

    # 探测 skill_icon_* 场景是否已建索引:用一张随机噪声图低阈值查询,看返回的 scene_id
    try:
        probe = (np.random.rand(100, 100, 3) * 255).astype('uint8')
        tmp = os.path.join(os.path.dirname(__file__), '_diag_probe.png')
        cv2.imwrite(tmp, probe)
        results = sdk.vision_query(SDK_CONFIG['instance_id'], tmp,
                                   topk=20, threshold=0, threshold_2=0, mode='basic')
        scene_ids = {r.get('scene_id', '') for r in (results or [])}
        skill_scenes = {s for s in scene_ids if s.startswith('skill_icon_')}
        os.path.exists(tmp) and os.remove(tmp)
        if skill_scenes:
            print(f"✅ Vision 索引含技能图标场景: {sorted(skill_scenes)}")
        else:
            print(f"❌ Vision 索引中未发现 skill_icon_* 场景(当前返回: {sorted(scene_ids) or '空'})")
            print("   → 策略1 主方案无索引可匹配。请运行 build_skill_icon_index.py。")
    except Exception as e:
        print(f"⚠️ 探测 Vision 索引失败: {e}")
    return sdk


def diag_skill_bar(frame, sdk):
    """体检:技能栏裁剪 + 6 图标分割 + 逐图标 Vision 匹配(策略1 核心)。"""
    _section("2. 技能栏识别链路体检(策略1 主方案)")
    from class_icon_detector import crop_skill_bar, split_skill_bar_icons, ClassIconDetector
    from config import SDK_CONFIG

    bar = crop_skill_bar(frame)
    if bar is None or bar.size == 0:
        print("❌ 技能栏裁剪失败")
        return
    print(f"✅ 技能栏裁剪: shape={bar.shape}, std={bar.std():.1f}")
    out = os.path.join(os.path.dirname(__file__), '_diag_skillbar.png')
    cv2.imwrite(out, bar)
    print(f"   已保存 {out} — 请人工核对:这块区域是否真的框住了底部6个技能图标?")
    if bar.std() < 5:
        print("⚠️ 技能栏为近纯色(std<5),可能裁错位置或当前界面无技能栏。")

    icons = split_skill_bar_icons(bar, num_icons=6)
    print(f"ℹ️ 分割出 {len(icons)} 个图标,各 std: "
          f"{[round(float(i.std()), 1) for i in icons]}")

    if sdk is None:
        print("⚠️ SDK 离线,跳过逐图标 Vision 匹配。")
        return

    det = ClassIconDetector(sdk=sdk, instance_id=SDK_CONFIG['instance_id'])
    print("\n逐图标 Vision 匹配明细:")
    cls = det.detect_via_skill_bar_icons(bar)
    print(f"\n→ 策略1 技能栏图标匹配结果: {cls.value if cls else '未命中'}")


def diag_full_chain(frame, sdk):
    """跑完整 detect_class,给出最终结论。"""
    _section("3. 完整识别链结论")
    from class_icon_detector import ClassIconDetector
    from config import SDK_CONFIG
    det = ClassIconDetector(sdk=sdk, instance_id=SDK_CONFIG['instance_id'])
    cls = det.detect_class(frame)
    src = getattr(det, 'last_detect_source', None)
    if cls:
        print(f"✅ 最终识别: {cls.value}  (来源: {src})")
    else:
        print("❌ 完整链未识别出职业 — 见上方各级体检定位断点。")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    print("职业识别诊断工具")
    frame = _load_frame(path)
    diag_resources()
    sdk = diag_sdk()
    diag_skill_bar(frame, sdk)
    diag_full_chain(frame, sdk)
    _section("诊断完成")
    print("把上面的完整输出贴给我,我据此精准修复对应的失效环节。")


if __name__ == '__main__':
    main()
