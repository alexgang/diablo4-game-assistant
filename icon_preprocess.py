"""
图标预处理工具函数

提供彩色图标转黑白灰度图的统一接口,用于:
  1. 技能池图标入库前预处理(消除彩色激活技能的边框颜色干扰)
  2. 技能栏图标查询前预处理(让查询图标和入库图标在同一色彩空间)
"""
import cv2


def preprocess_to_grayscale(img):
    """将彩色BGR图像转为黑白(BGR三通道等值的灰度图)

    目的: 消除彩色激活技能(金色/绿色/蓝色边框)对图标匹配的干扰,
    让入库图标和查询图标处于同一色彩空间,提高Vision匹配准确率。

    处理步骤:
      1. 转灰度(单通道)
      2. 直方图均衡化(增强对比度,统一不同图标的亮度)
      3. 转回3通道BGR(Vision接口要求彩色图像)

    Args:
        img: BGR 图像 (H, W, 3) 或灰度 (H, W)

    Returns:
        BGR 图像 (H, W, 3),三通道等值的灰度图
    """
    if img is None:
        return None
    if len(img.shape) == 2:
        gray = img
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_eq = cv2.equalizeHist(gray)
    return cv2.cvtColor(gray_eq, cv2.COLOR_GRAY2BGR)


def preprocess_query_icon(icon_bgr, target_size=(100, 100)):
    """技能栏图标查询预处理: 缩放 + 转灰度

    用于从技能栏裁剪的彩色图标,转成与入库图标一致的格式后入库查询。

    Args:
        icon_bgr: 技能栏裁剪的彩色图标 (任意尺寸 BGR)
        target_size: 目标尺寸,默认与入库图标一致 (100, 100)

    Returns:
        处理后的 BGR 图标 (target_size, 3),可直接用于 Vision 索引查询
    """
    if icon_bgr is None or icon_bgr.size == 0:
        return None
    icon_resized = cv2.resize(icon_bgr, target_size, interpolation=cv2.INTER_AREA)
    return preprocess_to_grayscale(icon_resized)