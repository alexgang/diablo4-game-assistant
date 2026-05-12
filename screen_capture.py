import struct
import ctypes
from ctypes import wintypes
import numpy as np
import cv2
import logging
from config import SCREEN_REGION

logger = logging.getLogger(__name__)

DXCAM_AVAILABLE = False
try:
    import dxcam
    DXCAM_AVAILABLE = True
except Exception:
    logger.warning("dxcam not available, using mss")


class ScreenCapture:

    def __init__(self):
        self.game_monitor = None
        self.game_hwnd = None
        self._device_idx = 0
        self._output_idx = None
        self._dxcam = None
        self._detect_game_monitor()

    def _detect_game_monitor(self):
        game_names = ["暗黑破坏神IV", "Diablo IV", "Diablo IV (Direct3D 11)"]
        hwnd = None
        for name in game_names:
            hwnd = ctypes.windll.user32.FindWindowW(None, name)
            if hwnd:
                logger.info(f"找到游戏窗口: {name} (hwnd={hwnd})")
                break

        if hwnd:
            self.game_hwnd = hwnd
            rect = wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            cx = (rect.left + rect.right) // 2
            cy = (rect.top + rect.bottom) // 2

            MONITOR_DEFAULTTONEAREST = 2
            hMonitor = ctypes.windll.user32.MonitorFromPoint(
                wintypes.POINT(cx, cy), MONITOR_DEFAULTTONEAREST
            )

            class MONITORINFOEX(ctypes.Structure):
                _fields_ = [
                    ('cbSize', ctypes.c_uint32),
                    ('rcMonitor', wintypes.RECT),
                    ('rcWork', wintypes.RECT),
                    ('dwFlags', ctypes.c_uint32),
                    ('szDevice', ctypes.c_wchar * 32),
                ]

            mi = MONITORINFOEX()
            mi.cbSize = ctypes.sizeof(MONITORINFOEX)
            ctypes.windll.user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))

            dev_name = mi.szDevice

            if DXCAM_AVAILABLE:
                self._try_dxcam_for_monitor(dev_name, mi.rcMonitor)

            import mss
            with mss.MSS() as sct:
                for i, mon in enumerate(sct.monitors[1:], 1):
                    if mon['left'] <= cx < mon['left'] + mon['width'] and \
                       mon['top'] <= cy < mon['top'] + mon['height']:
                        self.game_monitor = {
                            'top': mon['top'],
                            'left': mon['left'],
                            'width': mon['width'],
                            'height': mon['height'],
                        }
                        logger.info(f"游戏在显示器 [{i}]: {mon.get('name', '?')} ({mon['width']}x{mon['height']})")
                        return

        logger.warning("未找到游戏窗口，使用主显示器")

        import mss
        with mss.MSS() as sct:
            monitors = sct.monitors
            if len(monitors) > 1:
                primary = monitors[1]
                self.game_monitor = {
                    'top': primary['top'],
                    'left': primary['left'],
                    'width': primary['width'],
                    'height': primary['height'],
                }
                logger.info(f"使用主显示器: {primary.get('name', 'primary')} ({primary['width']}x{primary['height']})")
            else:
                self.game_monitor = {
                    'top': SCREEN_REGION['top'],
                    'left': SCREEN_REGION['left'],
                    'width': SCREEN_REGION['width'],
                    'height': SCREEN_REGION['height'],
                }

    def _try_dxcam_for_monitor(self, dev_name, mon_rect):
        try:
            region = (mon_rect.left, mon_rect.top,
                     mon_rect.right - mon_rect.left,
                     mon_rect.bottom - mon_rect.top)
            best_camera = None
            best_unique = 0
            best_out_idx = None
            best_frame = None

            for out_idx in range(4):
                try:
                    camera = dxcam.create(
                        device_idx=0, output_idx=out_idx,
                        region=region, output_color="BGR"
                    )
                    frame = camera.grab()
                    if frame is not None and frame.size > 0:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        unique = len(np.unique(gray))
                        logger.debug(f"dxcam output={out_idx}: shape={frame.shape}, unique={unique}")
                        if unique > best_unique:
                            best_unique = unique
                            best_camera = camera
                            best_out_idx = out_idx
                            best_frame = frame
                    else:
                        camera.release()
                except (ValueError, IndexError, Exception) as e:
                    logger.debug(f"dxcam output={out_idx} 失败: {e}")

            if best_unique > 10 and best_camera is not None:
                self._dxcam = best_camera
                self._output_idx = best_out_idx
                self.game_monitor = {
                    'top': mon_rect.top,
                    'left': mon_rect.left,
                    'width': mon_rect.right - mon_rect.left,
                    'height': mon_rect.bottom - mon_rect.top,
                }
                logger.info(f"dxcam 初始化成功: output_idx={best_out_idx}, shape={best_frame.shape}, unique={best_unique}")
        except Exception as e:
            logger.debug(f"dxcam 检测失败: {e}")

    def _get_dxcam_frame(self):
        if self._dxcam is None:
            return None
        try:
            frame = self._dxcam.grab()
            if frame is None:
                frame = self._dxcam.get_frame()
            return frame
        except Exception as e:
            logger.debug(f"dxcam grab 失败: {e}")
            return None

    def capture_full_screen(self, max_size=1280):
        if self._dxcam is not None:
            frame = self._get_dxcam_frame()
            if frame is not None and frame.size > 0:
                return self._resize_if_needed(frame, max_size)

        mon = self.game_monitor
        if not mon:
            return np.zeros((100, 100, 3), dtype=np.uint8)

        try:
            frame = self._printwindow_capture(self.game_hwnd, mon['width'], mon['height'])
            if frame is not None and frame.size > 0 and frame.mean() > 1:
                return self._resize_if_needed(frame, max_size)
        except Exception as e:
            logger.debug(f"PrintWindow失败: {e}")

        try:
            import mss
            with mss.MSS() as sct:
                sct_img = sct.grab(mon)
                img = np.array(sct_img)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            if img.mean() > 1:
                return self._resize_if_needed(img, max_size)
        except Exception as e:
            logger.debug(f"mss截图失败: {e}")

        h, w = mon['height'], mon['width']
        return np.zeros((h, w, 3), dtype=np.uint8)

    def _resize_if_needed(self, img, max_size):
        h, w = img.shape[:2]
        if max(h, w) <= max_size:
            return img
        scale = max_size / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def _printwindow_capture(self, hwnd, width, height):
        if not hwnd:
            return None

        user32 = ctypes.windll.user32
        PW_CLIENTONLY = 1

        hwndDC = user32.GetWindowDC(hwnd)
        if not hwndDC:
            return None

        try:
            mfcDC = ctypes.windll.gdi32.CreateCompatibleDC(hwndDC)
            if not mfcDC:
                return None

            try:
                saveBitMap = ctypes.windll.gdi32.CreateCompatibleBitmap(hwndDC, width, height)
                if not saveBitMap:
                    return None

                try:
                    oldBitMap = ctypes.windll.gdi32.SelectObject(mfcDC, saveBitMap)

                    try:
                        user32.PrintWindow(hwnd, mfcDC, PW_CLIENTONLY)

                        buf_size = width * height * 4
                        bmp_data = ctypes.create_string_buffer(buf_size)

                        class BITMAPINFOHEADER(ctypes.Structure):
                            _fields_ = [
                                ('biSize', ctypes.c_uint32),
                                ('biWidth', ctypes.c_int),
                                ('biHeight', ctypes.c_int),
                                ('biPlanes', ctypes.c_short),
                                ('biBitCount', ctypes.c_short),
                                ('biCompression', ctypes.c_uint32),
                                ('biSizeImage', ctypes.c_uint32),
                                ('biXPelsPerMeter', ctypes.c_long),
                                ('biYPelsPerMeter', ctypes.c_long),
                                ('biClrUsed', ctypes.c_uint32),
                                ('biClrImportant', ctypes.c_uint32),
                            ]

                        bmi = BITMAPINFOHEADER()
                        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                        bmi.biWidth = width
                        bmi.biHeight = -height
                        bmi.biPlanes = 1
                        bmi.biBitCount = 32
                        bmi.biCompression = 0

                        scan = ctypes.windll.gdi32.GetDIBits(
                            mfcDC, saveBitMap, 0, height,
                            bmp_data, ctypes.byref(bmi), 0, 1
                        )

                        if not scan:
                            return None

                        img = np.frombuffer(bmp_data.raw, dtype=np.uint8)
                        img = img.reshape((height, width, 4))
                        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                        return img

                    finally:
                        ctypes.windll.gdi32.SelectObject(mfcDC, oldBitMap)
                finally:
                    ctypes.windll.gdi32.DeleteObject(saveBitMap)
            finally:
                ctypes.windll.gdi32.DeleteDC(mfcDC)
        finally:
            user32.ReleaseDC(hwnd, hwndDC)

        return None

    def capture_region(self, region):
        try:
            import mss
            with mss.MSS() as sct:
                monitor = {
                    'top': region['top'],
                    'left': region['left'],
                    'width': region['width'],
                    'height': region['height']
                }
                sct_img = sct.grab(monitor)
                img = np.array(sct_img)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return img
        except Exception as e:
            logger.error(f"区域截图失败: {e}")
            return np.zeros((region['height'], region['width'], 3), dtype=np.uint8)

    def capture_game_window(self):
        return self.capture_full_screen()

    def save_screenshot(self, path):
        img = self.capture_full_screen()
        cv2.imwrite(path, img)
        return img

    def __del__(self):
        if self._dxcam is not None:
            try:
                self._dxcam.release()
            except Exception:
                pass
