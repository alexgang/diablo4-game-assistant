#!/usr/bin/env python3
"""
游戏助手快捷启动工具

提供一键启动以下功能：
1. 截图工具 - 全局热键截图
2. SDK Vision 索引构建
3. 游戏助手主程序

使用方法：
  python quick_launch.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG

def check_sdk():
    """检查 SDK 服务器状态"""
    sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
    return sdk.check_server()

def main():
    print("=" * 60)
    print("游戏助手快捷启动工具")
    print("=" * 60)

    sdk_status = "✓ 已连接" if check_sdk() else "✗ 未运行"

    print(f"\nSDK服务器状态: {sdk_status}")

    print("\n请选择功能:")
    print("  1. 截图工具 (全局热键 Ctrl+Shift+S)")
    print("  2. 构建 Vision 索引")
    print("  3. 启动游戏助手 GUI")
    print("  4. 启动游戏助手 CLI")
    print("  5. 退出")

    choice = input("\n请输入选项 (1-5): ").strip()

    if choice == "1":
        print("\n启动截图工具...")
        os.system("python screenshot_tool.py")
    elif choice == "2":
        print("\n启动 Vision 索引构建...")
        os.system("python build_vision_index.py")
    elif choice == "3":
        print("\n启动游戏助手 GUI...")
        os.system("python main.py")
    elif choice == "4":
        print("\n启动游戏助手 CLI...")
        os.system("python main.py --cli")
    else:
        print("\n退出")

if __name__ == "__main__":
    main()