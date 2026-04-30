import mss
import mss.tools
import numpy as np
import cv2
from config import SCREEN_REGION


class ScreenCapture:
    """屏幕捕获类，用于捕获游戏画面"""

    def __init__(self):
        self.sct = mss.mss()
        self.monitor = {
            'top': SCREEN_REGION['top'],
            'left': SCREEN_REGION['left'],
            'width': SCREEN_REGION['width'],
            'height': SCREEN_REGION['height']
        }

    def capture_full_screen(self):
        """捕获全屏图像"""
        sct_img = self.sct.grab(self.monitor)
        img = np.array(sct_img)
        # 转换为BGR格式（OpenCV使用）
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

    def capture_region(self, region):
        """捕获指定区域"""
        monitor = {
            'top': region['top'],
            'left': region['left'],
            'width': region['width'],
            'height': region['height']
        }
        sct_img = self.sct.grab(monitor)
        img = np.array(sct_img)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

    def capture_game_window(self):
        """捕获游戏窗口（假设游戏窗口为全屏）"""
        return self.capture_full_screen()

    def save_screenshot(self, path):
        """保存截图"""
        img = self.capture_full_screen()
        cv2.imwrite(path, img)
        return img

    def __del__(self):
        self.sct.close()