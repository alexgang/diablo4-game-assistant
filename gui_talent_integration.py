#!/usr/bin/env python3
"""
GUI天赋树集成模块
在现有GUI中添加天赋树查看功能
"""

from PyQt5.QtWidgets import QPushButton, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QWidget, QApplication
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from talent_tree_widget import TalentTreeWidget


class BuildSelectorDialog(QDialog):
    """构筑选择对话框"""
    
    def __init__(self, parent=None, builds=None):
        super().__init__(parent)
        self.setWindowTitle("选择构筑查看天赋树")
        self.setMinimumSize(400, 200)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a202c;
            }
            QLabel {
                color: #e2e8f0;
            }
            QComboBox {
                background-color: #2d3748;
                color: #e2e8f0;
                border: 1px solid #4a5568;
                padding: 5px;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #4299e1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3182ce;
            }
        """)
        
        self.builds = builds or []
        self.selected_build = None
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("选择要查看的构筑")
        title.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        title.setStyleSheet("color: #fbbf24;")
        layout.addWidget(title)
        
        # 构筑选择下拉框
        self.build_combo = QComboBox()
        if self.builds:
            for build in self.builds:
                name = build.get('title', '未命名构筑')
                author = build.get('author', '')
                display = f"{name} - {author}" if author else name
                self.build_combo.addItem(display, build)
        else:
            # 使用示例构筑
            self.build_combo.addItem("游侠 - 穿刺流", {'class': 'rogue', 'build': 'piercing'})
            self.build_combo.addItem("游侠 - 暗影流", {'class': 'rogue', 'build': 'shadow'})
            self.build_combo.addItem("野蛮人 - 旋风斩", {'class': 'barbarian', 'build': 'whirlwind'})
            self.build_combo.addItem("法师 - 电球", {'class': 'sorcerer', 'build': 'lightning'})
            
        layout.addWidget(self.build_combo)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        self.view_btn = QPushButton("查看天赋树")
        self.view_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.view_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #718096;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4a5568;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
    def get_selected_build(self):
        """获取选中的构筑"""
        return self.build_combo.currentData()


class TalentTreeWindow(QDialog):
    """天赋树显示窗口"""
    
    def __init__(self, parent=None, build_data=None):
        super().__init__(parent)
        self.setWindowTitle("暗黑4 天赋树")
        self.setMinimumSize(900, 700)
        self.setStyleSheet("background-color: #1a202c;")
        
        self.build_data = build_data or {}
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题栏
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        title = QLabel(f"天赋树 - {self.build_data.get('title', '未命名构筑')}")
        title.setFont(QFont('Microsoft YaHei', 16, QFont.Bold))
        title.setStyleSheet("color: #fbbf24;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #e2e8f0;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #f56565;
            }
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        
        layout.addWidget(header)
        
        # 天赋树组件
        self.talent_tree = TalentTreeWidget(self)
        self.talent_tree.load_build(self.build_data)
        layout.addWidget(self.talent_tree)
        
    def load_build(self, build_data):
        """加载构筑数据"""
        self.build_data = build_data
        self.talent_tree.load_build(build_data)


def show_talent_tree_dialog(parent=None, builds=None):
    """显示天赋树选择对话框（独立函数）"""
    dialog = BuildSelectorDialog(parent, builds)
    
    if dialog.exec_() == QDialog.Accepted:
        selected_build = dialog.get_selected_build()
        if selected_build:
            # 显示天赋树窗口
            talent_window = TalentTreeWindow(parent, selected_build)
            talent_window.show()
            return talent_window
    return None


# 使用示例
if __name__ == '__main__':
    import sys
    
    app = QApplication(sys.argv)
    
    # 直接显示天赋树窗口（使用示例数据）
    window = TalentTreeWindow()
    window.setWindowTitle("暗黑4 天赋树 - 游侠示例")
    window.show()
    
    sys.exit(app.exec_())
