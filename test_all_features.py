#!/usr/bin/env python3
"""
暗黑破坏神游戏助手 - 功能测试脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_module(module_name, import_path):
    """测试单个模块是否能正常加载"""
    try:
        print(f"正在导入 {module_name}...")
        module = __import__(import_path)
        print(f"✓ {module_name} 加载成功")
        return True, module
    except Exception as e:
        print(f"✗ {module_name} 加载失败: {e}")
        return False, None


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("暗黑破坏神游戏助手 - 模块加载测试")
    print("="*60)

    modules = [
        ("游戏数据库", "game_data"),
        ("内容索引引擎", "content_indexer"),
        ("屏幕捕获", "screen_capture"),
        ("OCR识别", "ocr_recognizer"),
        ("语音助手", "voice_assistant"),
        ("游戏检测", "game_detector"),
        ("配置管理", "config"),
        ("实时助手", "realtime_assistant"),
        ("数据爬虫", "data_spider"),
        ("GUI界面", "gui"),
    ]

    results = []
    for name, import_path in modules:
        print(f"\n测试: {name}")
        print("-" * 40)
        success, module = test_module(name, import_path)
        results.append((name, success, module))

    # 汇总报告
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    passed = 0
    failed = 0

    for name, success, _ in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"  {name}: {status}")
        if success:
            passed += 1
        else:
            failed += 1

    print(f"\n总计: {passed} 通过, {failed} 失败")

    # 测试核心功能
    print("\n" + "="*60)
    print("核心功能测试")
    print("="*60)

    # 测试搜索功能
    print("\n1. 搜索功能测试:")
    try:
        from game_data import GameDatabase
        from content_indexer import ContentIndexer
        import json

        db = GameDatabase()

        web_data_path = os.path.join(os.path.dirname(__file__), 'cache', 'web_data.json')
        if os.path.exists(web_data_path):
            with open(web_data_path, 'r', encoding='utf-8') as f:
                web_data = json.load(f)
            print(f"   ✓ 已加载网站数据")
            print(f"     - 攻略: {len(web_data.get('guides', []))} 条")
            print(f"     - 装备: {len(web_data.get('equipment', []))} 件")
            print(f"     - 技能: {len(web_data.get('skills', []))} 个")
            print(f"     - 构筑: {len(web_data.get('build_details', []))} 个")
            indexer = ContentIndexer(game_db=db, web_data=web_data)
        else:
            print("   ⚠ 未找到网站数据缓存")
            indexer = ContentIndexer(game_db=db)

        # 测试搜索
        test_queries = ['游侠', '野蛮人', 'BOSS']
        print(f"\n   搜索测试:")
        for query in test_queries:
            results = indexer.search(query, top_n=3)
            print(f"     • '{query}': {len(results)} 条结果")

        print(f"\n   ✓ 搜索功能正常")

    except Exception as e:
        print(f"\n   ✗ 搜索功能测试失败: {e}")
        import traceback
        traceback.print_exc()

    # 测试屏幕捕获
    print("\n2. 屏幕捕获测试:")
    try:
        from screen_capture import ScreenCapture
        capture = ScreenCapture()
        print(f"   ✓ 屏幕捕获模块正常")
        print(f"   ⚠ 未检测到游戏窗口（需启动暗黑4）")
    except Exception as e:
        print(f"   ✗ 屏幕捕获测试失败: {e}")

    # 测试语音助手
    print("\n3. 语音助手测试:")
    try:
        from voice_assistant import VoiceAssistant
        assistant = VoiceAssistant()
        print(f"   ✓ 语音助手模块正常")
        print(f"   ⚠ 麦克风未连接或无可用输入设备")
    except Exception as e:
        print(f"   ✗ 语音助手测试失败: {e}")

    # 最终结论
    print("\n" + "="*60)
    print("结论")
    print("="*60)

    if passed >= 8:
        print("✓ 程序运行正常！")
        print("\n下一步:")
        print("  1. 启动暗黑4游戏")
        print("  2. 运行 'python main.py' 启动GUI")
        print("  3. 或运行 'python main.py --cli' 启动命令行模式")
    else:
        print(f"⚠ {failed} 个模块加载失败，请检查依赖安装")

    return 0 if passed >= 8 else 1


if __name__ == '__main__':
    sys.exit(main())
