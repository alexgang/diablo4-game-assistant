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
  python main.py --ocr=easyocr    # 指定OCR引擎(easyocr/tesseract)
  python main.py --no-ocr         # 禁用OCR（模拟模式）
  python main.py --no-voice       # 禁用语音
  python main.py --stt=google     # 指定语音识别引擎
  python main.py --tts=edge_tts   # 指定语音播报引擎
  python main.py --voice          # CLI语音交互模式
  python main.py --cli            # 命令行模式
"""

import sys
import os
import io
import logging
import subprocess
import time

if sys.stdout and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from config import SDK_CONFIG, SDK_SERVER_PATH, SDK_SERVER_WORK_DIR

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def ensure_sdk_server():
    """确保 SDK 服务器已启动，如未启动则自动拉起"""
    from sdk_client import GamingAssistantSDK
    sdk_url = SDK_CONFIG['server_url']
    sdk = GamingAssistantSDK(sdk_url)

    if sdk.check_server():
        print(f"SDK服务器已连接: {sdk_url}")
        return True

    # 自动拉起 SDK 服务器(后台运行,不阻塞主程序)
    if SDK_SERVER_PATH and os.path.exists(SDK_SERVER_PATH):
        print(f"正在自动启动 SDK 服务器: {os.path.basename(SDK_SERVER_PATH)}")
        try:
            # CREATE_NO_WINDOW: 后台运行无窗口
            # 不重定向 stdio(重定向会导致 uvicorn lifespan 被 CancelledError 中断)
            subprocess.Popen(
                [SDK_SERVER_PATH],
                cwd=SDK_SERVER_WORK_DIR,
                creationflags=0x08000000,
            )
        except Exception as e:
            print(f"启动 SDK 服务器失败: {e}")
    else:
        print(f"SDK服务器程序未找到: {SDK_SERVER_PATH}")

    print("等待 SDK 服务器初始化(约90秒)...", end='', flush=True)
    # 等待服务器就绪(最多 120 秒,模型加载需要时间)
    for i in range(120):
        time.sleep(1)
        print('.', end='', flush=True)
        if sdk.check_server():
            print(f" 已连接 (等待{i + 1}秒)")
            return True

    print("\nSDK服务器未就绪,将使用本地模式运行(功能不受影响)")
    return False


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
    # 从 config 读取默认 OCR/TTS 引擎(命令行参数 --ocr=xxx 可覆盖)
    try:
        from config import OCR_CONFIG, VOICE_CONFIG
        ocr_engine = OCR_CONFIG.get('engine')
        stt_engine = VOICE_CONFIG.get('stt_engine', 'google')
        tts_engine = VOICE_CONFIG.get('tts_engine', 'auto')
    except ImportError:
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
        elif arg.startswith('--sdk-url='):
            SDK_CONFIG['server_url'] = arg.split('=', 1)[1]

    if use_cli:
        run_cli_mode(use_web, use_ocr, ocr_engine, use_voice, stt_engine, tts_engine)
    else:
        run_gui_mode(use_web, use_ocr, ocr_engine, stt_engine, tts_engine)


def run_gui_mode(use_web=False, use_ocr=True, ocr_engine=None, stt_engine='google', tts_engine='auto'):
    """GUI模式"""
    try:
        # WebEngine(d2core网页构筑)需要的设置:必须在 QApplication 前设
        from PyQt5.QtCore import Qt, QCoreApplication
        try:
            QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
        except Exception:
            pass
        # 软件渲染回退:部分机器/远程会话 GPU OpenGL 不可用时,避免 WebEngine 黑屏/崩溃
        if os.environ.get('D4_SOFTWARE_GL') == '1':
            try:
                QCoreApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)
            except Exception:
                pass
        # WebEngine 用户数据目录重定向到项目内(避免沙箱/AppData 写入限制导致崩溃)
        _webengine_data = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.webengine_data')
        os.makedirs(_webengine_data, exist_ok=True)
        _existing_flags = os.environ.get('QTWEBENGINE_CHROMIUM_FLAGS', '')
        _user_data_flag = f'--user-data-dir="{_webengine_data}"'
        if _user_data_flag not in _existing_flags:
            os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = (
                f'{_existing_flags} {_user_data_flag}'.strip()
            )

        from gui import MainWindow
        from PyQt5.QtWidgets import QApplication

        sdk_url = SDK_CONFIG['server_url']
        try:
            ensure_sdk_server()
        except Exception:
            pass
        app = QApplication(sys.argv)
        window = MainWindow(
            use_web_data=use_web,
            use_ocr=use_ocr,
            ocr_engine=ocr_engine,
            stt_engine=stt_engine,
            tts_engine=tts_engine,
        )
        # 启动时只显示小图标(不显示全尺寸主窗口),识别到场景后再自动展开
        window.mini_icon.show()
        window.mini_icon.raise_()
        print("游戏助手已启动！(小图标模式,识别到场景自动展开,单击小图标可手动展开)")
        sys.exit(app.exec_())

    except ImportError as e:
        print(f"GUI模块导入失败: {e}")
        print("正在启动命令行模式...")
        run_cli_mode(use_web, True, ocr_engine, True, stt_engine, tts_engine)


def run_cli_mode(use_web=False, use_ocr=True, ocr_engine=None,
                 use_voice=True, stt_engine='google', tts_engine='auto'):
    """命令行模式"""
    from realtime_assistant import RealTimeAssistant

    try:
        ensure_sdk_server()
        print(f"SDK服务器已连接: {SDK_CONFIG['server_url']}")
    except Exception:
        print(f"SDK服务器不可用: {SDK_CONFIG['server_url']}，将使用本地模式")

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
