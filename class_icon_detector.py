"""
角色职业自动识别模块

策略：
1. 主方案：截取右上角的"职业图标"（位于装备/技能/巅峰3图标的中间），
   通过 SDK Vision 模板匹配识别
2. 辅助方案：右侧面板 OCR 提取主属性（力量/敏捷/智力/意志），
   反推职业（力量→野蛮人，敏捷→游侠，智力→巫师/死灵，意志→德鲁伊）
3. 兜底方案：原有的 OCR 关键词匹配

职业图标位置（相对坐标）：
- D4 巅峰/技能/装备界面右上角通常有 3 个并排图标
- 中间一个是当前职业图标（弩+箭=游侠，闪电=巫师，狼=德鲁伊，等）
- 相对全屏坐标：x ≈ 0.96~0.98 * w, y ≈ 0.029~0.065 * h
- 图标尺寸约 50x50 像素（在 1440p 下）

使用：
    from class_icon_detector import ClassIconDetector
    detector = ClassIconDetector(sdk=sdk_instance, instance_id='d4_assistant')
    cls = detector.detect_class(frame)  # 返回 D4Class 或 None
"""
import logging
import os
from typing import Optional, Tuple

import cv2
import numpy as np

from class_recommender import D4Class

logger = logging.getLogger(__name__)


# ============== 职业图标在 Vision 索引中的 scene_id ==============
# 当首次识别到职业时，应将该图标插入索引（命名为 class_icon_<职业>）
ICON_SCENE_PREFIX = "class_icon_"
CLASS_FROM_SCENE_ID = {
    f"{ICON_SCENE_PREFIX}barbarian": D4Class.BARBARIAN,
    f"{ICON_SCENE_PREFIX}rogue": D4Class.ROGUE,
    f"{ICON_SCENE_PREFIX}sorcerer": D4Class.SORCERER,
    f"{ICON_SCENE_PREFIX}druid": D4Class.DRUID,
    f"{ICON_SCENE_PREFIX}necromancer": D4Class.NECROMANCER,
    f"{ICON_SCENE_PREFIX}spiritborn": D4Class.SPIRITBORN,
}


# ============== 主属性 → 职业映射（用于 OCR 辅助识别） ==============
# D4 只有 4 种核心属性：力量/敏捷/智力/意志。
# 灵巫(Spiritborn)没有独占主属性，无法靠主属性反推，须依赖角色名/图标识别。
PRIMARY_ATTRIBUTE_TO_CLASS = {
    '力量': D4Class.BARBARIAN,
    'strength': D4Class.BARBARIAN,
    '敏捷': D4Class.ROGUE,
    'dexterity': D4Class.ROGUE,
    '智力': D4Class.SORCERER,  # 巫师/死灵共享智力，需要其他线索区分
    'intelligence': D4Class.SORCERER,
    '意志': D4Class.DRUID,
    'willpower': D4Class.DRUID,
}


def crop_class_icon_region(frame: np.ndarray) -> Optional[np.ndarray]:
    """
    从全屏截图中裁出"右上角职业图标"区域

    使用相对坐标，适配不同分辨率：
    - 横向：右侧 4% ~ 2% 边缘附近
    - 纵向：顶部 3% ~ 7% 附近
    - 经验值：在 3440x1440 下，对应 (3308, 42)~(3361, 94) 约 53x52 像素

    Args:
        frame: BGR 全屏截图

    Returns:
        裁剪后的图标区域（约 53x52 像素），或 None
    """
    if frame is None or frame.size == 0:
        return None
    h, w = frame.shape[:2]

    # 相对坐标（2560x1600 角色/装备界面实测校准）
    # 角色界面右上角职业徽记(红底纹章) chosen=(0.942,0.035,0.963,0.078)
    # 此处略放宽边距以容错不同分辨率/界面
    x_min = int(w * 0.938)
    x_max = int(w * 0.967)
    y_min = int(h * 0.030)
    y_max = int(h * 0.082)
    if x_max <= x_min or y_max <= y_min:
        return None
    icon = frame[y_min:y_max, x_min:x_max]
    return icon if icon.size > 0 else None


def crop_class_icon_top_center(frame: np.ndarray) -> Optional[np.ndarray]:
    """
    裁剪"顶部中央"职业图标（用于 D4 技能树界面）

    技能树界面职业图标在"技能树 / 巅峰"Tab 标签的左上方
    相对全屏坐标：x ≈ 0.435~0.510 * w, y ≈ 0.030~0.075 * h

    Args:
        frame: BGR 全屏截图

    Returns:
        裁剪后的图标区域（约 60x60 像素），或 None
    """
    if frame is None or frame.size == 0:
        return None
    h, w = frame.shape[:2]
    x_min = int(w * 0.435)
    x_max = int(w * 0.510)
    y_min = int(h * 0.028)
    y_max = int(h * 0.078)
    if x_max <= x_min or y_max <= y_min:
        return None
    icon = frame[y_min:y_max, x_min:x_max]
    return icon if icon.size > 0 else None


def crop_right_panel(frame: np.ndarray, ratio: float = 0.5) -> Optional[np.ndarray]:
    """
    裁剪游戏画面的右侧面板（装备/技能/巅峰 内容区）

    Args:
        frame: BGR 全屏截图
        ratio: 右侧面板宽度占比，默认 0.5（右半边）

    Returns:
        右侧面板截图，或 None
    """
    if frame is None or frame.size == 0:
        return None
    h, w = frame.shape[:2]
    x_split = int(w * (1.0 - ratio))
    panel = frame[:, x_split:]
    return panel if panel.size > 0 else None


def detect_class_from_attributes(text: str) -> Optional[D4Class]:
    """
    从右侧面板 OCR 文本中识别主属性，反推职业

    D4 巅峰/装备界面的右侧通常会显示 4 个核心属性：力量、敏捷、智力、意志
    数值最高的那个一般是当前职业的主属性。
    策略：
    1. 如果有数值上下文（如"敏捷 1500"），提取每个属性的数值，选最大的
    2. 否则兜底：找最长的"主属性"关键词
    """
    if not text:
        return None

    import re
    text_lower = text.lower()

    # 策略1：尝试提取"属性名 + 数字"形式，选数值最大的属性
    attr_pattern = re.compile(
        r'(力量|敏捷|智力|意志|strength|dexterity|intelligence|willpower)'
        r'\s*[:：]?\s*(\d{1,6})',
        re.IGNORECASE
    )
    matches = attr_pattern.findall(text)
    if matches:
        attr_values = {}
        for attr, val in matches:
            attr_lower = attr.lower()
            cls = PRIMARY_ATTRIBUTE_TO_CLASS.get(attr) or PRIMARY_ATTRIBUTE_TO_CLASS.get(attr_lower)
            if cls and cls not in attr_values:
                attr_values[cls] = int(val)
        if attr_values:
            top_cls = max(attr_values.items(), key=lambda x: x[1])[0]
            logger.info(
                f"主属性数值匹配: {attr_values} → {top_cls.value} (最高)"
            )
            return top_cls

    # 策略2：兜底——按属性优先级（德鲁伊/野蛮人 > 死灵/游侠 > 法师靠其他线索）
    # 优先匹配更具体的关键词。灵巫无独占主属性，不在此反推。
    priority_keywords = [
        ('willpower', D4Class.DRUID), ('意志', D4Class.DRUID),
        ('strength', D4Class.BARBARIAN), ('力量', D4Class.BARBARIAN),
        ('dexterity', D4Class.ROGUE), ('敏捷', D4Class.ROGUE),
        ('intelligence', D4Class.SORCERER), ('智力', D4Class.SORCERER),
    ]
    for keyword, cls in priority_keywords:
        if keyword in text_lower or keyword in text:
            logger.info(f"主属性关键词 '{keyword}' → 职业 {cls.value}")
            return cls
    return None


class ClassIconDetector:
    """通过 Vision SDK 模板匹配识别职业图标"""

    def __init__(self, sdk=None, instance_id: str = 'd4_assistant',
                 templates_dir: Optional[str] = None):
        """
        Args:
            sdk: GamingAssistantSDK 实例（用于 Vision 查询）
            instance_id: Vision 实例 ID
            templates_dir: 本地模板目录（用于 OpenCV 模板匹配的回退方案）
        """
        self.sdk = sdk
        self.instance_id = instance_id
        self.templates_dir = templates_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'class_icon_templates',
        )
        os.makedirs(self.templates_dir, exist_ok=True)

    def detect_via_vision(self, icon: np.ndarray, threshold: float = 0.5) -> Optional[D4Class]:
        """
        通过 SDK Vision 查询职业图标

        Args:
            icon: 53x52 左右的职业图标 BGR 图
            threshold: 匹配得分阈值

        Returns:
            D4Class 或 None
        """
        if self.sdk is None or icon is None or icon.size == 0:
            return None

        # 保存到临时文件
        tmp_path = os.path.join(self.templates_dir, '_query_class_icon.png')
        cv2.imwrite(tmp_path, icon)

        try:
            results = self.sdk.vision_query(
                self.instance_id, tmp_path, topk=3, mode='basic'
            )
            if not results:
                results = self.sdk.vision_query(
                    self.instance_id, tmp_path, topk=3, mode='accurate'
                )
            if not results:
                return None

            for r in results:
                scene_id = r.get('scene_id', '')
                score = r.get('score', 0)
                if score < threshold:
                    continue
                cls = CLASS_FROM_SCENE_ID.get(scene_id)
                if cls:
                    logger.info(
                        f"Vision 职业图标识别: {scene_id} "
                        f"({score*100:.0f}%) → {cls.value}"
                    )
                    return cls
        except Exception as e:
            logger.debug(f"Vision 职业图标查询失败: {e}")
        return None

    def detect_via_template(self, icon: np.ndarray, threshold: float = 0.7) -> Optional[D4Class]:
        """
        通过 OpenCV 本地模板匹配识别职业图标（不依赖 SDK 服务）

        Args:
            icon: 待识别的图标
            threshold: 匹配阈值

        Returns:
            D4Class 或 None
        """
        if icon is None or icon.size == 0:
            return None

        best_class = None
        best_score = -1.0
        for class_name, cls in [
            ('barbarian', D4Class.BARBARIAN),
            ('rogue', D4Class.ROGUE),
            ('sorcerer', D4Class.SORCERER),
            ('druid', D4Class.DRUID),
            ('necromancer', D4Class.NECROMANCER),
            ('spiritborn', D4Class.SPIRITBORN),
        ]:
            tpl_path = os.path.join(self.templates_dir, f'{class_name}.png')
            if not os.path.exists(tpl_path):
                continue
            tpl = cv2.imread(tpl_path)
            if tpl is None or tpl.size == 0:
                continue
            # 调整为相同尺寸
            try:
                tpl_resized = cv2.resize(tpl, (icon.shape[1], icon.shape[0]))
                # 用归一化相关系数法
                result = cv2.matchTemplate(icon, tpl_resized, cv2.TM_CCOEFF_NORMED)
                score = float(result.max())
                logger.debug(f"模板 {class_name}: score={score:.3f}")
                if score > best_score:
                    best_score = score
                    best_class = cls
            except Exception as e:
                logger.debug(f"模板匹配 {class_name} 失败: {e}")

        if best_class and best_score >= threshold:
            logger.info(
                f"模板匹配职业图标: {best_class.value} (score={best_score:.2f})"
            )
            return best_class
        if best_class:
            logger.debug(
                f"最佳模板匹配 {best_class.value} score={best_score:.2f} 未达阈值 {threshold}"
            )
        return None

    def detect_class(self, frame: np.ndarray) -> Optional[D4Class]:
        """
        主入口：从全屏截图识别当前角色职业

        优先级：
        1. SDK Vision 查询（如果可用且已建索引）
        2. 本地模板匹配（如果有模板文件）

        Args:
            frame: BGR 全屏截图

        Returns:
            D4Class 或 None
        """
        # 多个可能的图标位置（D4 不同界面下职业图标位置不同）
        crop_funcs = [
            ('top_right', crop_class_icon_region),     # 装备/巅峰界面：右上角
            ('top_center', crop_class_icon_top_center),  # 技能树界面：顶部中央
        ]
        logger.info(f"开始职业图标识别 (frame shape={frame.shape})")
        for region_name, crop_func in crop_funcs:
            icon = crop_func(frame)
            if icon is None or icon.size == 0:
                logger.debug(f"  {region_name}: 裁剪失败")
                continue
            logger.info(f"  {region_name}: 裁剪成功 shape={icon.shape}")
            # 方案1：SDK Vision
            cls = self.detect_via_vision(icon)
            if cls:
                logger.info(f"在 {region_name} 区域识别到职业: {cls.value}")
                return cls
            # 方案2：本地模板匹配
            cls = self.detect_via_template(icon)
            if cls:
                logger.info(f"在 {region_name} 区域（模板）识别到职业: {cls.value}")
                return cls
            logger.info(f"  {region_name}: 未匹配")

        logger.info("所有区域都未能识别职业")
        return None

    def save_template(self, frame: np.ndarray, class_type: D4Class) -> Optional[str]:
        """
        保存当前帧的职业图标作为模板（用于首次建立模板库）

        Args:
            frame: 全屏截图
            class_type: 该截图对应的职业

        Returns:
            保存的模板路径或 None
        """
        icon = crop_class_icon_region(frame)
        if icon is None:
            return None
        path = os.path.join(self.templates_dir, f'{class_type.value}.png')
        cv2.imwrite(path, icon)
        logger.info(f"已保存职业图标模板: {class_type.value} → {path}")
        return path


if __name__ == "__main__":
    """独立测试：从给定截图识别职业图标"""
    import sys
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    if len(sys.argv) < 2:
        print("用法: python class_icon_detector.py <screenshot.png> [save_as_class]")
        sys.exit(1)

    img_path = sys.argv[1]
    img = cv2.imread(img_path)
    if img is None:
        print(f"无法读取图片: {img_path}")
        sys.exit(1)

    icon = crop_class_icon_region(img)
    if icon is None:
        print("裁剪图标失败")
        sys.exit(1)

    out = os.path.join(os.path.dirname(img_path), '_cropped_class_icon.png')
    cv2.imwrite(out, icon)
    print(f"裁剪图标 shape={icon.shape}, 保存到: {out}")

    # 如果指定了职业，保存为模板
    if len(sys.argv) >= 3:
        cls_name = sys.argv[2].lower()
        for cls in D4Class:
            if cls.value == cls_name:
                detector = ClassIconDetector()
                p = detector.save_template(img, cls)
                print(f"已保存模板: {p}")
                break
        else:
            print(f"未知职业: {cls_name}")
            print(f"支持: {[c.value for c in D4Class]}")
