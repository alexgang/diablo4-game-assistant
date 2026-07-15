#!/usr/bin/env python3
"""
技能池图标自动分割脚本

从 sb_*.png 截图中自动分割所有技能池图标（小正方形），
用"方形边框检测 + 网格推断"的方法。

方法:
  1. 方形边框检测: 用Canny+findContours找截图中所有完整的方形边框(技能图标的边框)
  2. 网格推断: 从检测到的方形推断行列网格布局(行列中心点)
  3. 图标定位: 优先用检测到的方形位置,漏检的用网格坐标补全
  4. 裁剪+缩放到100x100,保存到 pool/<职业>/r*_c*.png

关键: 每个技能图标都有一个方形边框,通过检测这个边框确保图标完整。

使用方法:
  python split_skill_pool_icons.py            # 分割+替换图标
  python split_skill_pool_icons.py --rebuild  # 重建Vision索引
  python split_skill_pool_icons.py --verify   # 仅验证(需先重建索引)
  python split_skill_pool_icons.py --all      # 分割+重建+验证
"""
import os
import sys
import shutil
import glob
import re
import logging

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POOL_DIR = os.path.join(BASE_DIR, 'class_icon_templates', 'pool')
BACKUP_DIR = os.path.join(BASE_DIR, 'class_icon_templates', 'pool_backup')
SHOTS_DIR = os.path.join(BASE_DIR, 'game_screenshots')

CLASS_SCREENSHOT_MAP = {
    'barbarian': 'sb_barbarian.png',
    'sorcerer': 'sb_sorcerer.png',
    'druid': 'sb_druid.png',
    'necromancer': 'sb_necromancer.png',
    'rogue': 'sb_rogue.png',
    'paladin': 'sb_paladin.png',
}

DB_ICON_SIZE = (100, 100)
TEMPLATE_SIZES = list(range(70, 111, 5))
MATCH_THRESHOLD = 0.55
OVERLAP_THRESHOLD = 0.5

# 复用 icon_preprocess 中的统一预处理函数
from icon_preprocess import preprocess_to_grayscale, preprocess_query_icon


def backup_pool():
    """备份现有 pool 目录"""
    if os.path.exists(POOL_DIR):
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
        shutil.copytree(POOL_DIR, BACKUP_DIR)
        logger.info(f"已备份 pool -> {BACKUP_DIR}")


def load_existing_icons(class_name):
    """加载某职业的现有图标,返回 [(filename, image, row, col), ...]"""
    cls_dir = os.path.join(POOL_DIR, class_name)
    if not os.path.isdir(cls_dir):
        return []
    icons = []
    for f in sorted(glob.glob(os.path.join(cls_dir, 'r*_c*.png'))):
        m = re.match(r'r(\d+)_c(\d+)', os.path.basename(f))
        if not m:
            continue
        img = cv2.imread(f)
        if img is not None:
            icons.append((os.path.basename(f), img, int(m.group(1)), int(m.group(2))))
    return icons


def find_all_squares(shot, min_area=2500, max_area=20000):
    """用轮廓检测找所有方形图标(技能图标的方形边框)

    排除左侧菱形分类图标(x<120)和底部技能栏(y>0.80h)
    用 RETR_TREE + approxPolyDP(0.02*peri) 精确找四边形

    关键改进: 在Canny前对灰度图做直方图均衡+高斯模糊,
    消除彩色激活技能的边框颜色干扰,大幅提高方形检测率。
    """
    gray = cv2.cvtColor(shot, cv2.COLOR_BGR2GRAY)
    h_shot = shot.shape[0]

    # 黑白处理: 直方图均衡 + 高斯模糊,去除彩色干扰
    gray_eq = cv2.equalizeHist(gray)
    gray_proc = cv2.GaussianBlur(gray_eq, (3, 3), 0)

    edges = cv2.Canny(gray_proc, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    squares = []
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            area = w * h
            aspect = float(w) / h if h > 0 else 0
            if 0.85 < aspect < 1.15 and min_area < area < max_area:
                if x < 120:
                    continue
                if y > h_shot * 0.80:
                    continue
                squares.append((x, y, w, h))

    # 去重:重叠度高的保留面积较大的
    squares.sort(key=lambda s: -s[2] * s[3])
    deduped = []
    for s in squares:
        overlap = False
        for d in deduped:
            if calc_overlap(s, d) > 0.3:
                overlap = True
                break
        if not overlap:
            deduped.append(s)
    deduped.sort(key=lambda s: (s[1], s[0]))
    return deduped


def infer_grid(squares):
    """从检测到的方形推断网格布局

    按y聚类成行,按x聚类成列
    返回 (row_centers, col_centers, avg_size)
    """
    if not squares:
        return [], [], (70, 70)

    # 按y聚类(间距<40px视为同一行)
    ys = sorted(set(s[1] for s in squares))
    row_clusters = []
    for y in ys:
        if row_clusters and y - row_clusters[-1][-1] < 40:
            row_clusters[-1].append(y)
        else:
            row_clusters.append([y])
    row_centers = [int(np.mean(c)) for c in row_clusters]

    # 按x聚类(间距<40px视为同一列)
    xs = sorted(set(s[0] for s in squares))
    col_clusters = []
    for x in xs:
        if col_clusters and x - col_clusters[-1][-1] < 40:
            col_clusters[-1].append(x)
        else:
            col_clusters.append([x])
    col_centers = [int(np.mean(c)) for c in col_clusters]

    avg_w = int(np.mean([s[2] for s in squares]))
    avg_h = int(np.mean([s[3] for s in squares]))
    return row_centers, col_centers, (avg_w, avg_h)


def detect_via_square_borders(shot, existing_icons):
    """
    基于方形边框检测 + 网格推断 + 模板匹配校正分割技能图标

    1. 用Canny+findContours找所有完整方形边框(黑白处理后)
    2. 推断网格布局(行列中心点)
    3. 对每个现有图标:
       - 计算其在网格中的相对位置(按行列分组后按位置排序)
       - 用模板匹配验证并校正(如果模板匹配在附近找到了方形)
    4. 新职业(无现有图标)直接用检测到的方形

    返回 [(filename, x, y, w, h, row, col), ...]
    """
    gray_shot = cv2.cvtColor(shot, cv2.COLOR_BGR2GRAY)
    h_shot = shot.shape[0]
    squares = find_all_squares(shot)
    logger.info(f"  方形边框检测: {len(squares)} 个")

    # 无现有图标时(新职业),直接用检测到的方形按行列命名
    if not existing_icons:
        if not squares:
            logger.warning("  无现有图标且未检测到方形,跳过")
            return []
        row_centers, col_centers, (avg_w, avg_h) = infer_grid(squares)
        results = []
        for x, y, w, h in squares:
            row = min(range(len(row_centers)), key=lambda i: abs(row_centers[i] - y))
            col = min(range(len(col_centers)), key=lambda i: abs(col_centers[i] - x))
            fname = f"r{row}_c{col}.png"
            results.append((fname, x, y, w, h, row, col))
        logger.info(f"  新职业直接用方形: {len(results)} 个")
        return results

    # 计算平均方形尺寸
    if squares:
        avg_w = int(np.mean([s[2] for s in squares]))
        avg_h = int(np.mean([s[3] for s in squares]))
    else:
        avg_w, avg_h = 75, 75

    # 推断网格
    row_centers, col_centers, _ = infer_grid(squares)
    n_rows = len(row_centers)
    n_cols = len(col_centers)

    if n_rows == 0 or n_cols == 0:
        logger.warning("  无法推断网格,使用模板匹配定位")
        # 回退到纯模板匹配
        results = []
        for fname, icon, orig_row, orig_col in existing_icons:
            gray_icon = cv2.cvtColor(icon, cv2.COLOR_BGR2GRAY)
            best_score = 0
            best_loc = (0, 0)
            best_sz = avg_w
            for sz in TEMPLATE_SIZES:
                icon_r = cv2.resize(gray_icon, (sz, sz), interpolation=cv2.INTER_AREA)
                res = cv2.matchTemplate(gray_shot, icon_r, cv2.TM_CCOEFF_NORMED)
                _, mx, _, loc = cv2.minMaxLoc(res)
                if mx > best_score:
                    best_score = mx
                    best_loc = loc
                    best_sz = sz
            tx, ty = best_loc
            results.append((fname, tx, ty, best_sz, best_sz, orig_row, orig_col))
        return results

    # 把现有图标按行列分组,构建位置映射
    # 现有图标的 (orig_row, orig_col) 范围: 0~max_row, 0~max_col
    # 检测到的网格行列范围: 0~n_rows, 0~n_cols
    # 需要找到最佳偏移,使现有图标的位置映射到网格位置
    max_orig_row = max(r for _, _, r, c in existing_icons)
    max_orig_col = max(c for _, _, r, c in existing_icons)

    # 网格推断的偏移(假设网格从0开始,匹配现有图标的0,0位置)
    row_offset = 0
    col_offset = 0
    # 如果网格行数 < 现有图标最大行,说明网格偏移了
    # 大多数情况: n_rows == max_orig_row + 1, 网格直接对齐
    if n_rows < max_orig_row + 1:
        # 网格可能只检测到部分行,假设从0开始
        pass

    # 给每个方形分配网格坐标
    grid_squares = {}  # (grid_row, grid_col) -> (x, y, w, h)
    for x, y, w, h in squares:
        grid_row = min(range(n_rows), key=lambda i: abs(row_centers[i] - y))
        grid_col = min(range(n_cols), key=lambda i: abs(col_centers[i] - x))
        if abs(row_centers[grid_row] - y) < 40 and abs(col_centers[grid_col] - x) < 40:
            grid_squares[(grid_row, grid_col)] = (x, y, w, h)

    # 为每个现有图标分配位置
    results = []
    filled_by_square = 0
    filled_by_grid = 0
    filled_by_template = 0

    for fname, icon, orig_row, orig_col in existing_icons:
        # 直接用 orig_row/col 作为网格坐标
        key = (orig_row, orig_col)
        if key in grid_squares:
            x, y, w, h = grid_squares[key]
            results.append((fname, x, y, w, h, orig_row, orig_col))
            filled_by_square += 1
            continue

        # 网格推断: 用行列中心点推断位置
        if orig_row < n_rows and orig_col < n_cols:
            x = col_centers[orig_col] - avg_w // 2
            y = row_centers[orig_row] - avg_h // 2
            results.append((fname, x, y, avg_w, avg_h, orig_row, orig_col))
            filled_by_grid += 1
            logger.debug(f"  网格补全 {fname}: ({x},{y}) {avg_w}x{avg_h}")
            continue

        # 模板匹配回退
        gray_icon = cv2.cvtColor(icon, cv2.COLOR_BGR2GRAY)
        best_score = 0
        best_loc = (0, 0)
        best_sz = avg_w
        for sz in TEMPLATE_SIZES:
            icon_r = cv2.resize(gray_icon, (sz, sz), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(gray_shot, icon_r, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(res)
            if mx > best_score:
                best_score = mx
                best_loc = loc
                best_sz = sz
        tx, ty = best_loc
        results.append((fname, tx, ty, best_sz, best_sz, orig_row, orig_col))
        filled_by_template += 1
        logger.debug(f"  模板回退 {fname}: ({tx},{ty}) score={best_score:.3f}")

    logger.info(f"  方形匹配: {filled_by_square} 个, 网格补全: {filled_by_grid} 个, 模板回退: {filled_by_template} 个")
    return results


def calc_overlap(box1, box2):
    """计算两个矩形的IoU"""
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    xi1 = max(x1, x2)
    yi1 = max(y1, y2)
    xi2 = min(x1 + w1, x2 + w2)
    yi2 = min(y1 + h1, y2 + h2)
    if xi2 <= xi1 or yi2 <= yi1:
        return 0
    inter = (xi2 - xi1) * (yi2 - yi1)
    area1 = w1 * h1
    area2 = w2 * h2
    return inter / (area1 + area2 - inter + 1e-6)


def crop_and_save(shot, positions, class_name):
    """裁剪并保存图标

    positions: [(filename, x, y, w, h, row, col), ...]
    确保每个图标内部包含完整正方形边框
    """
    cls_dir = os.path.join(POOL_DIR, class_name)
    if os.path.exists(cls_dir):
        shutil.rmtree(cls_dir)
    os.makedirs(cls_dir, exist_ok=True)

    saved = 0
    debug_img = shot.copy()

    for fname, x, y, w, h, row, col in positions:
        icon = shot[y:y + h, x:x + w]
        if icon.size == 0:
            continue
        try:
            if float(icon.std()) < 5:
                logger.debug(f"  {fname}: 纯色,跳过")
                continue
        except Exception:
            continue

        icon_100 = cv2.resize(icon, DB_ICON_SIZE, interpolation=cv2.INTER_AREA)
        # 入库前转黑白,消除彩色激活技能的边框颜色干扰
        icon_gray = preprocess_to_grayscale(icon_100)
        save_path = os.path.join(cls_dir, fname)
        cv2.imwrite(save_path, icon_gray)
        saved += 1

        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(debug_img, fname, (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

    debug_path = os.path.join(BASE_DIR, f'_debug_split_{class_name}.png')
    cv2.imwrite(debug_path, debug_img)

    logger.info(f"  {class_name}: 保存 {saved} 个图标 (debug -> {os.path.basename(debug_path)})")
    return saved


def split_all():
    """分割所有职业的技能池图标"""
    logger.info("=" * 60)
    logger.info("技能池图标自动分割 (方形边框检测+网格推断)")
    logger.info("=" * 60)

    backup_pool()

    total = 0
    stats = {}
    for class_name, shot_file in CLASS_SCREENSHOT_MAP.items():
        shot_path = os.path.join(SHOTS_DIR, shot_file)
        if not os.path.exists(shot_path):
            logger.warning(f"截图不存在: {shot_path}")
            continue

        shot = cv2.imread(shot_path)
        logger.info(f"\n[{class_name}] {shot_file} ({shot.shape[1]}x{shot.shape[0]})")

        icons = load_existing_icons(class_name)
        logger.info(f"  现有图标: {len(icons)} 个")

        positions = detect_via_square_borders(shot, icons)
        logger.info(f"  定位完成: {len(positions)} 个")

        saved = crop_and_save(shot, positions, class_name)
        total += saved
        stats[class_name] = (len(icons), saved)

    logger.info(f"\n总计保存 {total} 个技能池图标")
    for cls, (old, new) in stats.items():
        logger.info(f"  {cls}: {old} -> {new}")

    return total


def crop_skill_bar_from_shot(shot):
    """从技能池截图底部裁剪技能栏(6个图标)

    改进: 用方形边框检测找6个技能图标(更精确,排除资源球/数字/装饰)
    1. 截取底部 15% 区域(包含技能栏)
    2. 用 find_all_squares 检测所有方形边框(技能图标都有方形边框)
    3. 取 y 坐标最大的 6 个(底部技能栏)
    4. 按 x 排序后返回
    """
    h, w = shot.shape[:2]
    # 截取底部区域(包含底部技能栏)
    bar_region = shot[int(h * 0.75):, :]
    # 用方形检测找所有图标边框
    squares = find_all_squares(bar_region)
    if not squares:
        logger.warning("  未检测到技能栏方形边框,使用固定比例裁剪")
        # 回退到固定比例
        y_min = int(h * 0.85)
        bar = shot[y_min:, :]
        gray = cv2.cvtColor(bar, cv2.COLOR_BGR2GRAY)
        bh, bw = gray.shape
        x_exclude = int(bw * 0.15)
        col_std = np.std(gray, axis=0)
        col_std_masked = col_std.copy()
        col_std_masked[:x_exclude] = 0
        threshold = np.mean(col_std_masked[col_std_masked > 0]) if np.any(col_std_masked > 0) else 15
        active = col_std_masked > threshold * 0.7
        active_indices = np.where(active)[0]
        if len(active_indices) > 10:
            x_start = max(0, active_indices[0] - 5)
            x_end = min(bw, active_indices[-1] + 5)
        else:
            x_start = int(bw * 0.12)
            x_end = int(bw * 0.95)
        bar_crop = bar[:, x_start:x_end]
        slot_w = bar_crop.shape[1] // 6
        icons = []
        for i in range(6):
            x1 = i * slot_w
            x2 = (i + 1) * slot_w if i < 5 else bar_crop.shape[1]
            icon = bar_crop[:, x1:x2]
            if icon.size > 0:
                icons.append(icon)
        logger.info(f"  技能栏裁剪(回退): x=[{x_start},{x_end}], 每个图标宽{slot_w}")
        return icons

    # 按 y 分组(支持不同职业有不同数量的槽位,通常5-6个)
    # 用方形在 y 方向上的间距判断是否属于同一行
    if not squares:
        return []
    ys = sorted(set(s[1] for s in squares))
    # 同一行的方形 y 坐标差值 < 30
    row_groups = []
    current = [ys[0]]
    for y in ys[1:]:
        if y - current[-1] < 30:
            current.append(y)
        else:
            row_groups.append(current)
            current = [y]
    row_groups.append(current)
    # 取最大行(技能栏所在的行,有最多方形)
    best_row = max(row_groups, key=len)
    row_y = int(np.mean(best_row))
    # 过滤出该行的方形
    row_squares = [s for s in squares if abs(s[1] - row_y) < 30]
    # 按 x 排序
    row_squares.sort(key=lambda s: s[0])

    n = len(row_squares)
    if n == 0:
        return []

    # 裁剪每个方形对应的图标
    icons = []
    for x, y, bw, bh in row_squares:
        icon = bar_region[y:y + bh, x:x + bw]
        if icon.size > 0:
            icons.append(icon)
    logger.info(f"  技能栏裁剪(方形检测): {len(icons)} 个图标, 每个约{icons[0].shape[1]}x{icons[0].shape[0]}")
    return icons


def verify_match(sdk, instance_id):
    """自验证:技能栏图标 vs 技能池图标"""
    from class_icon_detector import CLASS_FROM_SKILL_ICON_SCENE_ID
    from class_recommender import D4Class

    logger.info("\n" + "=" * 60)
    logger.info("自验证: 技能栏图标 vs 技能池图标")
    logger.info("=" * 60)

    CLASS_MAP = {
        'barbarian': D4Class.BARBARIAN,
        'sorcerer': D4Class.SORCERER,
        'druid': D4Class.DRUID,
        'necromancer': D4Class.NECROMANCER,
        'rogue': D4Class.ROGUE,
        'paladin': D4Class.PALADIN,
    }

    tmp_dir = os.path.join(BASE_DIR, '_tmp_verify')
    os.makedirs(tmp_dir, exist_ok=True)

    all_pass = True
    for class_name, shot_file in CLASS_SCREENSHOT_MAP.items():
        shot_path = os.path.join(SHOTS_DIR, shot_file)
        shot = cv2.imread(shot_path)

        icons = crop_skill_bar_from_shot(shot)
        logger.info(f"\n[{class_name}] 技能栏 {len(icons)} 个图标")

        class_hits = {}
        class_scores = {}
        for i, icon in enumerate(icons):
            try:
                if float(icon.std()) < 5:
                    logger.info(f"  图标{i}: 纯色,跳过")
                    continue
            except Exception:
                continue

            # 技能栏图标查询预处理: 缩放 + 转黑白(与入库图标色彩空间一致)
            icon_proc = preprocess_query_icon(icon, DB_ICON_SIZE)
            if icon_proc is None:
                continue
            icon_path = os.path.join(tmp_dir, f'{class_name}_bar_{i}.png')
            cv2.imwrite(icon_path, icon_proc)

            try:
                results = sdk.vision_query(
                    instance_id, icon_path,
                    topk=10, threshold=0, threshold_2=0, mode='basic',
                )
                if not results:
                    results = sdk.vision_query(
                        instance_id, icon_path,
                        topk=10, threshold=0, threshold_2=0, mode='accurate',
                    )

                skill_results = [
                    r for r in results
                    if r.get('scene_id', '').startswith('skill_icon_')
                ]
                if not skill_results:
                    logger.info(f"  图标{i}: 无 skill_icon 匹配")
                    continue

                top1 = skill_results[0]
                top1_scene = top1.get('scene_id', '')
                top1_score = float(top1.get('score', 0))
                cls = CLASS_FROM_SKILL_ICON_SCENE_ID.get(top1_scene)

                top3_str = " ".join(
                    f"{r.get('scene_id', '').replace('skill_icon_', '')}({r.get('score', 0):.3f})"
                    for r in skill_results[:3]
                )
                logger.info(f"  图标{i}: {top3_str}")

                if top1_score >= 0.60 and cls:
                    class_hits[cls] = class_hits.get(cls, 0) + 1
                    class_scores.setdefault(cls, []).append(top1_score)
            except Exception as e:
                logger.debug(f"  图标{i} 查询失败: {e}")

        expected = CLASS_MAP[class_name]
        if class_hits:
            best_cls = max(class_hits, key=lambda c: class_hits[c])
            best_hits = class_hits[best_cls]
            passed = best_cls == expected
            status = "✓ 通过" if passed else "✗ 失败"
            hit_str = ", ".join(f"{c.value}={h}" for c, h in class_hits.items())
            logger.info(f"  判定: {best_cls.value} (hits={best_hits}) | 期望: {expected.value} | {status}")
            if not passed:
                all_pass = False
        else:
            logger.info(f"  判定: 无匹配 | 期望: {expected.value} | ✗ 失败")
            all_pass = False

    logger.info(f"\n{'=' * 60}")
    logger.info(f"验证结果: {'✓ 全部通过' if all_pass else '✗ 部分失败'}")
    logger.info(f"{'=' * 60}")
    return all_pass


def rebuild_index():
    """重建 Vision 索引"""
    from sdk_client import GamingAssistantSDK
    from config import SDK_CONFIG

    sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
    if not sdk.check_server():
        logger.error("SDK 服务器未连接")
        return False

    INSTANCE_ID = SDK_CONFIG['instance_id']

    try:
        sdk.vision_init(INSTANCE_ID)
        logger.info("Vision 实例已初始化")
    except Exception as e:
        if "has existed" in str(e):
            logger.info("Vision 实例已存在")
        else:
            logger.warning(f"初始化: {e}")

    total = 0
    for class_name in CLASS_SCREENSHOT_MAP:
        cls_dir = os.path.join(POOL_DIR, class_name)
        if not os.path.isdir(cls_dir):
            continue
        icons = sorted(glob.glob(os.path.join(cls_dir, '*.png')))
        scene_id = f'skill_icon_{class_name}'
        logger.info(f"[{class_name}] {len(icons)} 个图标 -> {scene_id}")

        for i, icon_path in enumerate(icons):
            pictures_id = f'{class_name}_icon_{i:02d}'
            try:
                sdk.vision_insert_scene(
                    instance_id=INSTANCE_ID,
                    scene_id=scene_id,
                    image_paths=[icon_path],
                    pictures_id=pictures_id,
                    mode="accurate",
                )
                total += 1
            except Exception as e:
                logger.error(f"  {os.path.basename(icon_path)}: {e}")

    logger.info(f"总计添加 {total} 个图标到索引")

    result = sdk.vision_build(INSTANCE_ID, mode="accurate", full_build=True)
    logger.info(f"索引构建完成: threshold={result.get('threshold')}, threshold_2={result.get('threshold_2')}")
    return True


def main():
    args = sys.argv[1:]

    if '--all' in args:
        split_all()
        if rebuild_index():
            from sdk_client import GamingAssistantSDK
            from config import SDK_CONFIG
            sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
            if sdk.check_server():
                verify_match(sdk, SDK_CONFIG['instance_id'])
    elif '--verify' in args:
        from sdk_client import GamingAssistantSDK
        from config import SDK_CONFIG
        sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
        if sdk.check_server():
            verify_match(sdk, SDK_CONFIG['instance_id'])
    elif '--rebuild' in args:
        rebuild_index()
    else:
        split_all()


if __name__ == '__main__':
    main()
