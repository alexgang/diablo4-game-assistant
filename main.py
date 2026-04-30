#!/usr/bin/env python3
"""
暗黑破坏神游戏助手 - 主入口文件

实时游戏辅助工具，功能：
1. 屏幕捕获 + OCR文字识别
2. 识别游戏状态（任务、BOSS、位置、职业）
3. 内容索引匹配 + 智能推荐
4. 网站数据爬虫（装备/技能/构筑）

用法：
  python main.py              # GUI模式
  python main.py --web        # 启用网站数据
  python main.py --ocr=paddleocr  # 指定OCR引擎
  python main.py --no-ocr     # 禁用OCR（模拟模式）
  python main.py --cli        # 命令行模式
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )

    print("=" * 50)
    print("    暗黑破坏神游戏助手")
    print("=" * 50)
    print("\n正在初始化...")

    use_web = '--web' in sys.argv
    use_cli = '--cli' in sys.argv
    use_ocr = '--no-ocr' not in sys.argv
    ocr_engine = None

    for arg in sys.argv:
        if arg.startswith('--ocr='):
            ocr_engine = arg.split('=')[1]

    if use_cli:
        run_cli_mode(use_web, use_ocr, ocr_engine)
    else:
        run_gui_mode(use_web, ocr_engine)


def run_gui_mode(use_web=False, ocr_engine=None):
    """GUI模式"""
    try:
        from gui import MainWindow
        from PyQt5.QtWidgets import QApplication

        print("启动图形界面...")
        app = QApplication(sys.argv)
        window = MainWindow(use_web_data=use_web, ocr_engine=ocr_engine)
        window.show()
        print("游戏助手已启动！")
        sys.exit(app.exec_())

    except ImportError as e:
        print(f"GUI模块导入失败: {e}")
        print("正在启动命令行模式...")
        run_cli_mode(use_web, True, ocr_engine)


def run_cli_mode(use_web=False, use_ocr=True, ocr_engine=None):
    """命令行模式"""
    from realtime_assistant import RealTimeAssistant

    assistant = RealTimeAssistant(
        use_web_data=use_web,
        use_ocr=use_ocr,
        ocr_engine=ocr_engine,
    )

    ocr_status = assistant.get_ocr_status()
    if ocr_status['available']:
        print(f"OCR引擎: {ocr_status['engine']}")
    else:
        print("OCR引擎: 不可用（模拟模式）")

    if '--continuous' in sys.argv:
        interval = 5
        for arg in sys.argv:
            if arg.startswith('--interval='):
                try:
                    interval = int(arg.split('=')[1])
                except ValueError:
                    pass
        assistant.continuous_monitor(interval)
    else:
        while True:
            try:
                print("\n--- 游戏状态分析 ---")
                result = assistant.analyze_and_report()

                cmd = input("\n按回车继续 (q=退出, s=搜索, u=更新数据): ").strip().lower()
                if cmd == 'q':
                    break
                elif cmd == 's':
                    query = input("搜索关键词: ").strip()
                    if query:
                        results = assistant.search(query)
                        for r in results:
                            print(f"  [{r['category']}] (相关度: {r['score']:.0%}) {r['data']}")
                elif cmd == 'u':
                    assistant.update_web_data()

            except KeyboardInterrupt:
                print("\n游戏助手已退出")
                break


if __name__ == "__main__":
    main()
