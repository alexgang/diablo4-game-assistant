#!/usr/bin/env python3
"""
游戏截图工具 - 系统托盘截图

功能：
- 点击托盘图标截图
- 右下角托盘图标，安静不打扰

使用方法：
  python screenshot_tool.py
"""

import os
import sys
import signal
import datetime
import threading
import tkinter as tk
from tkinter import messagebox, filedialog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from screen_capture import ScreenCapture
from config import SDK_CONFIG

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), 'game_screenshots')


class ScreenshotTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()

        self.screenshot_dir = SCREENSHOTS_DIR
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)

        self.capture = ScreenCapture()
        self._exiting = False
        self._use_tray = False

        self.create_tray_icon()

    def _do_exit(self):
        if self._exiting:
            return
        self._exiting = True
        print("\n正在退出...")

        if self._use_tray:
            threading.Thread(target=self._stop_tray, daemon=True).start()

        try:
            self.root.after(100, self._destroy_root)
        except Exception:
            pass

    def _stop_tray(self):
        try:
            self.icon.stop()
        except Exception:
            pass

    def _destroy_root(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)

    def create_tray_icon(self):
        try:
            import pystray
            from PIL import Image
        except ImportError:
            self.create_simple_gui()
            return

        self._use_tray = True

        image = Image.new('RGB', (64, 64), color=(46, 204, 113))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
        draw.rectangle((20, 20, 44, 44), fill=(46, 204, 113))

        def on_click(icon, item):
            if str(item) == "截图":
                self.save_screenshot()
            elif str(item) == "截图(选择位置)":
                self.save_screenshot_with_dialog()
            elif str(item) == "退出":
                self._do_exit()

        menu = pystray.Menu(
            pystray.MenuItem("📸 截图", on_click),
            pystray.MenuItem("💾 截图(选择位置)", on_click),
            pystray.MenuItem("📁 打开截图目录", lambda i, e: os.startfile(self.screenshot_dir)),
            pystray.MenuItem("---", None),
            pystray.MenuItem("❌ 退出", on_click),
        )

        self.icon = pystray.Icon("游戏截图", image, "游戏截图工具", menu)

        print("=" * 60)
        print("游戏截图工具已启动")
        print("=" * 60)
        print(f"\n截图保存目录: {self.screenshot_dir}")
        print("\n使用方法:")
        print("  右键托盘图标 -> 选择截图")
        print("  右键托盘图标 -> 退出")
        print("\n按 Ctrl+C 退出程序")

    def create_simple_gui(self):
        self._use_tray = False

        self.window = tk.Toplevel(self.root)
        self.window.title("游戏截图工具")
        self.window.geometry("300x150")
        self.window.resizable(False, False)
        self.window.attributes("-topmost", True)

        try:
            self.window.iconbitmap(default='')
        except Exception:
            pass

        label = tk.Label(
            self.window,
            text="🎮 游戏截图工具",
            font=("微软雅黑", 14, "bold"),
            pady=10
        )
        label.pack()

        btn_screenshot = tk.Button(
            self.window,
            text="📸 截图 (F12)",
            font=("微软雅黑", 10),
            command=self.save_screenshot,
            width=20,
            height=2
        )
        btn_screenshot.pack(pady=5)

        btn_quit = tk.Button(
            self.window,
            text="❌ 退出",
            font=("微软雅黑", 9),
            command=self._do_exit,
            width=20
        )
        btn_quit.pack(pady=5)

        self.window.bind('<F12>', lambda e: self.save_screenshot())
        self.window.protocol('WM_DELETE_WINDOW', self._do_exit)

        print("=" * 60)
        print("游戏截图工具已启动")
        print("=" * 60)
        print(f"\n截图保存目录: {self.screenshot_dir}")
        print("\n按 F12 截图 或 点击窗口按钮")

    def _capture_game_screen(self):
        try:
            import dxcam
            import ctypes
            from ctypes import wintypes

            game_names = ['暗黑破坏神IV', 'Diablo IV']
            hwnd = None
            for name in game_names:
                hwnd = ctypes.windll.user32.FindWindowW(None, name)
                if hwnd:
                    break

            if hwnd:
                rect = wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                cx = (rect.left + rect.right) // 2
                cy = (rect.top + rect.bottom) // 2

                import mss
                with mss.MSS() as sct:
                    for i, mon in enumerate(sct.monitors[1:], 1):
                        if mon['left'] <= cx < mon['left'] + mon['width']:
                            output_idx = i - 1
                            region = (mon['left'], mon['top'],
                                     mon['width'], mon['height'])
                            break
                    else:
                        output_idx = 0
                        region = None

                for out_idx in range(4):
                    try:
                        if region:
                            camera = dxcam.create(device_idx=0, output_idx=out_idx,
                                                  region=region, output_color="BGR")
                        else:
                            camera = dxcam.create(device_idx=0, output_idx=out_idx,
                                                  output_color="BGR")
                        frame = camera.grab()
                        camera.release()
                        if frame is not None and frame.size > 0 and frame.mean() > 1:
                            return frame
                    except Exception:
                        pass
        except ImportError:
            pass

        screenshot = self.capture.capture_full_screen(max_size=0)
        if screenshot is not None and screenshot.mean() > 1:
            return screenshot

        return None

    def save_screenshot(self, custom_name=None):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        screenshot = self._capture_game_screen()
        if screenshot is None:
            messagebox.showerror("截图失败", "无法获取屏幕")
            return False

        if custom_name:
            filename = custom_name
        else:
            scene_name = self.ask_scene_name()
            if scene_name:
                filename = scene_name
            else:
                filename = f"scene_{timestamp}"

        save_path = os.path.join(self.screenshot_dir, f"{filename}.png")

        if os.path.exists(save_path):
            overwrite = messagebox.askyesno("文件已存在", f"是否覆盖现有文件?\n{save_path}")
            if not overwrite:
                save_path = os.path.join(self.screenshot_dir, f"{filename}_{timestamp}.png")

        try:
            import cv2
            from PIL import Image

            img_pil = Image.fromarray(cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB))
            img_pil.save(save_path, 'PNG')
            messagebox.showinfo("截图成功", f"截图已保存!\n{filename}.png")
            print(f"✓ 截图已保存: {save_path}")
            return True
        except Exception as e:
            messagebox.showerror("保存失败", str(e))
            return False

    def ask_scene_name(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("保存截图")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)

        label = tk.Label(dialog, text="请输入场景名称:", font=("微软雅黑", 11))
        label.pack(pady=10)

        entry = tk.Entry(dialog, font=("微软雅黑", 12), width=30)
        entry.pack(pady=5)
        entry.focus_force()

        result = {"name": None}

        def on_ok():
            result["name"] = entry.get().strip()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        ok_btn = tk.Button(button_frame, text="保存", command=on_ok, width=10)
        ok_btn.pack(side=tk.LEFT, padx=5)

        cancel_btn = tk.Button(button_frame, text="取消", command=on_cancel, width=10)
        cancel_btn.pack(side=tk.LEFT, padx=5)

        dialog.bind('<Return>', lambda e: on_ok())
        dialog.bind('<Escape>', lambda e: on_cancel())

        dialog.lift()
        dialog.focus_force()

        self.root.wait_window(dialog)

        return result["name"]

    def save_screenshot_with_dialog(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        screenshot = self._capture_game_screen()
        if screenshot is None:
            messagebox.showerror("截图失败", "无法获取屏幕")
            return False

        filetypes = [
            ("PNG 图片", "*.png"),
            ("JPEG 图片", "*.jpg"),
            ("BMP 图片", "*.bmp"),
            ("所有文件", "*.*")
        ]

        default_name = f"screenshot_{timestamp}.png"
        save_path = filedialog.asksaveasfilename(
            title="保存截图",
            initialdir=self.screenshot_dir,
            initialfile=default_name,
            filetypes=filetypes
        )

        if save_path:
            try:
                import cv2
                from PIL import Image

                img_pil = Image.fromarray(cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB))
                img_pil.save(save_path, 'PNG')
                messagebox.showinfo("截图成功", f"截图已保存!\n{save_path}")
                print(f"✓ 截图已保存: {save_path}")
                return True
            except Exception as e:
                messagebox.showerror("保存失败", str(e))
                return False

        return False

    def run(self):
        signal.signal(signal.SIGINT, lambda sig, frame: self._do_exit())

        if self._use_tray:
            self.icon.run()
        else:
            self.window.mainloop()

        if not self._exiting:
            self._do_exit()


def main():
    tool = ScreenshotTool()
    tool.run()


if __name__ == "__main__":
    main()
