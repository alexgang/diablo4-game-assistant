#!/usr/bin/env python3
"""详细检测暗黑4窗口"""
import ctypes
from ctypes import wintypes
import time

def get_window_info(hwnd):
    """获取窗口详细信息"""
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    title = ""
    if length > 0:
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value

    class RECT(ctypes.Structure):
        _fields_ = [("left", wintypes.LONG),
                    ("top", wintypes.LONG),
                    ("right", wintypes.LONG),
                    ("bottom", wintypes.LONG)]

    rect = RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))

    return {
        'hwnd': hwnd,
        'title': title,
        'rect': (rect.left, rect.top, rect.right, rect.bottom),
        'width': rect.right - rect.left,
        'height': rect.bottom - rect.top
    }

def get_all_windows():
    """获取所有窗口"""
    windows = []

    def callback(hwnd, lParam):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            info = get_window_info(hwnd)
            if info['title'].strip() and info['width'] > 100 and info['height'] > 100:
                windows.append(info)
        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int)
    )
    ctypes.windll.user32.EnumWindows(EnumWindowsProc(callback), 0)

    return windows

print("="*60)
print("详细窗口检测")
print("="*60)

# 等待2秒确保窗口已加载
print("\n正在扫描窗口...")
time.sleep(1)

windows = get_all_windows()

# 查找可能与游戏相关的窗口
game_keywords = ['暗黑', 'diablo', 'Diablo', 'D4', 'IV', '战网', 'battle', 'Battle', 'Blizzard', 'BLIZZARD', 'game', 'Game']

print(f"\n找到 {len(windows)} 个可见窗口:\n")

game_windows = []
for win in windows:
    title = win['title']
    is_game = False

    for keyword in game_keywords:
        if keyword.lower() in title.lower():
            is_game = True
            break

    marker = "🎮 " if is_game else "   "
    print(f"{marker}[{win['hwnd']}] {win['width']}x{win['height']}")
    print(f"    标题: {title[:80]}")

    if is_game:
        game_windows.append(win)

print("\n" + "="*60)
print("游戏相关窗口")
print("="*60)

if game_windows:
    print(f"\n找到 {len(game_windows)} 个可能的游戏窗口:\n")
    for win in game_windows:
        print(f"  窗口句柄: {win['hwnd']}")
        print(f"  窗口标题: {win['title']}")
        print(f"  窗口大小: {win['width']}x{win['height']}")
        print(f"  位置: {win['rect']}")
        print()
else:
    print("\n⚠️ 未找到明显的游戏窗口")
    print("\n可能的原因:")
    print("  1. 暗黑4还在启动中（请等待进入主界面）")
    print("  2. 暗黑4以全屏模式运行（窗口可能被隐藏）")
    print("  3. 游戏窗口使用了不同的标题")

print("\n" + "="*60)
print("提示")
print("="*60)
print("\n请确保:")
print("  ✓ 暗黑4已经完全启动并进入游戏主界面")
print("  ✓ 暗黑4不是以全屏独占模式运行")
print("  ✓ 窗口没有被最小化")
