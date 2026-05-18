#!/usr/bin/env python3
"""
暗黑破坏神4 - 技能树启动器
"""

import sys
import os

def check_display():
    """检查是否有可用的显示器"""
    print("\n--- 显示器检测 ---")

    if sys.platform == 'win32':
        try:
            import ctypes
            user32 = ctypes.windll.user32

            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)
            screens = user32.GetSystemMetrics(80)

            print(f"主屏幕分辨率: {width}x{height}")
            print(f"显示器数量: {screens}")

            if width > 0 and height > 0:
                print("✓ 检测到有效显示器")
                return True
            else:
                print("✗ 未检测到有效显示器")
                return False
        except Exception as e:
            print(f"检测失败: {e}")
            return True

    display = os.environ.get('DISPLAY')
    if display:
        print(f"DISPLAY={display}")
        return True

    return False

def main():
    print("=" * 60)
    print("暗黑破坏神4 技能树")
    print("=" * 60)

    has_display = check_display()

    if not has_display:
        print("\n⚠️  检测到可能无图形环境")

    if sys.platform == 'win32':
        os.environ['QT_QPA_PLATFORM'] = 'windows'

    try:
        print("\n正在加载 PyQt5...")
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        from talent_tree_widget import TalentTreeWidget

        print("✓ PyQt5加载成功")

        app = QApplication(sys.argv)
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        window = TalentTreeWidget()
        window.setWindowTitle("暗黑4 技能树 - 游侠 BD展示")
        window.resize(950, 900)

        print("✓ 窗口创建成功")

        window.show()

        print("✓ 窗口已显示")
        print("\n程序运行中，关闭窗口退出")
        sys.exit(app.exec_())

    except Exception as e:
        print(f"\n✗ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
