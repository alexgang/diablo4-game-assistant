#!/usr/bin/env python3
"""
暗黑破坏神游戏助手 - 主入口文件

实时游戏辅助工具，功能：
1. 屏幕捕获 + OCR文字识别
2. 识别游戏状态（任务、BOSS、位置、职业）
3. 内容索引匹配 + 智能推荐
4. 网站数据爬虫（装备/技能/构筑）
5. 语音交互（语音输入/意图识别/语音回复）

用法：
  python main.py                  # GUI模式
  python main.py --web            # 启用网站数据
  python main.py --ocr=paddleocr  # 指定OCR引擎
  python main.py --no-ocr         # 禁用OCR（模拟模式）
  python main.py --no-voice       # 禁用语音
  python main.py --stt=google     # 指定语音识别引擎
  python main.py --tts=edge_tts   # 指定语音播报引擎
  python main.py --voice          # CLI语音交互模式
  python main.py --cli            # 命令行模式
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
    use_voice = '--no-voice' not in sys.argv
    ocr_engine = None
    stt_engine = 'google'
    tts_engine = 'auto'

    for arg in sys.argv:
        if arg.startswith('--ocr='):
            ocr_engine = arg.split('=')[1]
        elif arg.startswith('--stt='):
            stt_engine = arg.split('=')[1]
        elif arg.startswith('--tts='):
            tts_engine = arg.split('=')[1]

    if use_cli:
        run_cli_mode(use_web, use_ocr, ocr_engine, use_voice, stt_engine, tts_engine)
    else:
        run_gui_mode(use_web, ocr_engine, stt_engine, tts_engine)


def run_gui_mode(use_web=False, ocr_engine=None, stt_engine='google', tts_engine='auto'):
    """GUI模式"""
    try:
        from gui import MainWindow
        from PyQt5.QtWidgets import QApplication

        print("启动图形界面...")
        app = QApplication(sys.argv)
        window = MainWindow(
            use_web_data=use_web,
            ocr_engine=ocr_engine,
            stt_engine=stt_engine,
            tts_engine=tts_engine,
        )
        window.show()
        print("游戏助手已启动！")
        sys.exit(app.exec_())

    except ImportError as e:
        print(f"GUI模块导入失败: {e}")
        print("正在启动命令行模式...")
        run_cli_mode(use_web, True, ocr_engine, True, stt_engine, tts_engine)


def run_cli_mode(use_web=False, use_ocr=True, ocr_engine=None,
                 use_voice=True, stt_engine='google', tts_engine='auto'):
    """命令行模式"""
    from realtime_assistant import RealTimeAssistant

    assistant = RealTimeAssistant(
        use_web_data=use_web,
        use_ocr=use_ocr,
        ocr_engine=ocr_engine,
        use_voice=use_voice,
        stt_engine=stt_engine,
        tts_engine=tts_engine,
    )

    ocr_status = assistant.get_ocr_status()
    if ocr_status['available']:
        print(f"OCR引擎: {ocr_status['engine']}")
    else:
        print("OCR引擎: 不可用（模拟模式）")

    voice_status = assistant.get_voice_status()
    if voice_status['stt_available']:
        print(f"语音识别: {voice_status['stt_engine']}")
    else:
        print("语音识别: 不可用")
    if voice_status['tts_available']:
        print(f"语音播报: {voice_status['tts_engine']}")
    else:
        print("语音播报: 不可用")

    if '--voice' in sys.argv:
        print("\n语音交互模式 - 请说话...")
        while True:
            try:
                result = assistant.voice_query()
                if result['text']:
                    print(f"\n识别: {result['text']}")
                    print(f"意图: {result['intent']} | 关键词: {result['query']}")
                    print(f"回复: {result['response']}")
                    if result['results']:
                        for r in result['results'][:3]:
                            name = r['data'].get('name', r['data'].get('title', ''))
                            print(f"  [{r['category']}] {r['score']:.0%} - {name}")
                else:
                    print(".", end='', flush=True)
            except KeyboardInterrupt:
                print("\n语音模式已退出")
                break
    elif '--continuous' in sys.argv:
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

                cmd = input("\n按回车继续 (q=退出, s=搜索, v=语音, u=更新数据): ").strip().lower()
                if cmd == 'q':
                    break
                elif cmd == 's':
                    query = input("搜索关键词: ").strip()
                    if query:
                        result = assistant.text_query(query)
                        print(f"意图: {result['intent']}")
                        print(f"回复: {result['response']}")
                elif cmd == 'v':
                    print("请说话...")
                    result = assistant.voice_query()
                    if result['text']:
                        print(f"识别: {result['text']}")
                        print(f"回复: {result['response']}")
                    else:
                        print("未识别到语音")
                elif cmd == 'u':
                    assistant.update_web_data()

            except KeyboardInterrupt:
                print("\n游戏助手已退出")
                break


if __name__ == "__main__":
    main()
