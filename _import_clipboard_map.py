"""从剪贴板导入地图场景模板(临时脚本)

读取剪贴板中的截图(Win+Shift+S / PrintScreen),自动识别多显示器拼接,
裁剪出游戏所在区域,缩放到 1920 宽度,保存为 my_map_realtime.png
并插入 Vision 索引、重建索引。
"""
import os
import sys
import cv2
import numpy as np
from PIL import ImageGrab, Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_screenshots')
INSTANCE_ID = SDK_CONFIG['instance_id']
TPL_PATH = os.path.join(SCREENSHOTS_DIR, 'my_map_realtime.png')


def crop_game_region(frame):
    """从多显示器拼接截图中裁剪游戏所在区域

    实测显示器布局:
      Monitor 1(主): left=0,    2560x1600  (IDE/桌面)
      Monitor 2(游戏): left=2560, 3440x1440 (D4 游戏在这)
    全屏截图总宽 6000,游戏画面在 x=2560~6000 区域(3440 宽)。
    """
    h, w = frame.shape[:2]
    print(f"  原始截图尺寸: {w}x{h}")

    # 多显示器拼接:总宽 6000,游戏在右侧 Monitor 2 (x=2560, w=3440)
    GAME_MONITOR_LEFT = 2560
    GAME_MONITOR_WIDTH = 3440
    if w > 3000:
        x1 = GAME_MONITOR_LEFT
        x2 = min(GAME_MONITOR_LEFT + GAME_MONITOR_WIDTH, w)
        cropped = frame[:, x1:x2]
        print(f"  检测到多显示器拼接,裁剪游戏显示器区域 x=[{x1}:{x2}] ({x2-x1}x{h})")
        return cropped

    # 单显示器:直接使用
    return frame


def main():
    print("=" * 60)
    print("从剪贴板导入地图场景模板")
    print("=" * 60)

    # 1. 读取剪贴板
    print("正在读取剪贴板...")
    img = ImageGrab.grabclipboard()
    if img is None:
        print("错误: 剪贴板中没有图片!")
        print("请先按 Win+Shift+S 或 PrintScreen 截图,再运行本脚本")
        return 1
    if isinstance(img, list):
        if not img:
            print("错误: 剪贴板文件列表为空")
            return 1
        print(f"  剪贴板文件: {img[0]}")
        img = Image.open(img[0])
    img = img.convert('RGB')
    frame = np.array(img)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    print(f"  剪贴板读取成功: shape={frame.shape}")

    # 2. 裁剪游戏所在区域(处理多显示器拼接)
    frame = crop_game_region(frame)

    # 3. 缩放到 1920 宽度(与 Vision 查询时一致)
    h, w = frame.shape[:2]
    if w > 1920:
        scale = 1920 / w
        frame = cv2.resize(frame, (1920, int(h * scale)), interpolation=cv2.INTER_AREA)
        print(f"  已缩放到 1920 宽度: shape={frame.shape}")

    # 4. 保存模板
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    cv2.imwrite(TPL_PATH, frame)
    print(f"  已保存模板: {TPL_PATH}")

    # 5. 插入 Vision 索引并重建
    sdk = GamingAssistantSDK()
    if not sdk.check_server():
        print("警告: SDK 服务器未连接,跳过索引重建")
        return 0

    try:
        sdk.vision_init(INSTANCE_ID)
    except Exception as e:
        if "has existed" not in str(e):
            print(f"  Vision 初始化警告: {e}")

    print("插入 Vision 索引...")
    try:
        sdk.vision_insert_scene(
            instance_id=INSTANCE_ID,
            scene_id='my_map',
            image_paths=[TPL_PATH],
            pictures_id='my_map_pic',
            mode="accurate",
        )
        print("  索引已插入: my_map")
    except Exception as e:
        print(f"  索引插入失败: {e}")

    print("重建 Vision 索引(full_build)...")
    try:
        result = sdk.vision_build(INSTANCE_ID, mode="accurate", full_build=True)
        print(f"  索引构建完成! threshold={result.get('threshold')}, threshold_2={result.get('threshold_2')}")
    except Exception as e:
        print(f"  索引构建失败: {e}")

    print()
    print("完成! 现在可以启动游戏助手,切到地图界面测试场景识别 + QuestOCR 攻略加载")
    return 0


if __name__ == "__main__":
    sys.exit(main())
