#!/usr/bin/env python3
"""
暗黑破坏神游戏助手 - 主入口文件

这是一个实时游戏辅助工具，能够：
1. 捕获游戏画面
2. 识别游戏状态（任务、BOSS、位置）
3. 提供实时指引和建议
"""

import sys
import os

# 添加项目路径到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """主函数"""
    print("=" * 50)
    print("    暗黑破坏神游戏助手")
    print("=" * 50)
    print("\n正在初始化游戏助手...")
    
    try:
        # 尝试导入GUI模块
        from gui import MainWindow
        from PyQt5.QtWidgets import QApplication
        
        print("启动图形界面...")
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        
        print("游戏助手已启动！")
        print("提示：窗口可以拖拽移动，点击暂停按钮可暂停分析")
        
        sys.exit(app.exec_())
        
    except ImportError as e:
        print(f"GUI模块导入失败: {e}")
        print("正在启动命令行模式...")
        
        # 命令行模式
        from game_detector import GameDetector
        
        detector = GameDetector()
        
        while True:
            try:
                print("\n--- 游戏状态分析 ---")
                analysis = detector.analyze_game_state()
                
                if 'guide' in analysis:
                    guide = analysis['guide']
                    
                    if 'quest' in guide:
                        quest = guide['quest']
                        print(f"📋 当前任务: {quest['name']}")
                        print(f"📍 任务地点: {quest['location']}")
                        print(f"💡 任务指引: {quest['guide']}")
                    
                    if 'boss' in guide:
                        boss = guide['boss']
                        print(f"\n👹 BOSS: {boss['name']}")
                        print(f"⚔️ 弱点: {', '.join(boss['weakness'])}")
                        print(f"⚠️ 技能: {', '.join(boss['skills'])}")
                        print(f"📝 攻略: {boss['guide']}")
                    
                    print(f"\n📍 当前区域: {guide.get('location', '未知')}")
                
                if 'recommendations' in analysis:
                    print("\n💬 推荐建议:")
                    for rec in analysis['recommendations']:
                        print(f"  • {rec}")
                
                # 等待用户输入
                input("\n按回车键继续分析 (输入 'q' 退出)...")
                
            except KeyboardInterrupt:
                print("\n游戏助手已退出")
                break

if __name__ == "__main__":
    main()