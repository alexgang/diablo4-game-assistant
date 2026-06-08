#!/usr/bin/env python3
"""
简化版技能树测试
"""

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt

def main():
    app = QApplication(sys.argv)
    
    window = QWidget()
    window.setWindowTitle("测试窗口")
    window.setMinimumSize(800, 600)
    
    layout = QVBoxLayout(window)
    
    label = QLabel("技能树测试")
    label.setAlignment(Qt.AlignCenter)
    layout.addWidget(label)
    
    btn = QPushButton("关闭")
    btn.clicked.connect(window.close)
    layout.addWidget(btn)
    
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
