import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QFrame, QScrollArea
)
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from game_detector import GameDetector


class GuideWidget(QWidget):
    """指引显示组件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        self.title_label = QLabel("游戏指引")
        self.title_label.setFont(QFont('Arial', 14, QFont.Bold))
        self.title_label.setStyleSheet("color: #ff6b35;")
        layout.addWidget(self.title_label)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #8b0000;")
        layout.addWidget(line)
        
        # 当前任务
        self.quest_group = QWidget()
        quest_layout = QVBoxLayout()
        self.quest_title = QLabel("当前任务")
        self.quest_title.setFont(QFont('Arial', 12, QFont.Bold))
        self.quest_title.setStyleSheet("color: #ffd700;")
        quest_layout.addWidget(self.quest_title)
        self.quest_content = QTextEdit()
        self.quest_content.setReadOnly(True)
        self.quest_content.setStyleSheet("background-color: rgba(0,0,0,0.5); color: #e0e0e0; border: none;")
        quest_layout.addWidget(self.quest_content)
        self.quest_group.setLayout(quest_layout)
        layout.addWidget(self.quest_group)
        
        # BOSS信息
        self.boss_group = QWidget()
        boss_layout = QVBoxLayout()
        self.boss_title = QLabel("BOSS信息")
        self.boss_title.setFont(QFont('Arial', 12, QFont.Bold))
        self.boss_title.setStyleSheet("color: #ff6b35;")
        boss_layout.addWidget(self.boss_title)
        self.boss_content = QTextEdit()
        self.boss_content.setReadOnly(True)
        self.boss_content.setStyleSheet("background-color: rgba(0,0,0,0.5); color: #e0e0e0; border: none;")
        boss_layout.addWidget(self.boss_content)
        self.boss_group.setLayout(boss_layout)
        layout.addWidget(self.boss_group)
        
        # 推荐建议
        self.recommend_group = QWidget()
        recommend_layout = QVBoxLayout()
        self.recommend_title = QLabel("推荐建议")
        self.recommend_title.setFont(QFont('Arial', 12, QFont.Bold))
        self.recommend_title.setStyleSheet("color: #4ade80;")
        recommend_layout.addWidget(self.recommend_title)
        self.recommend_content = QTextEdit()
        self.recommend_content.setReadOnly(True)
        self.recommend_content.setStyleSheet("background-color: rgba(0,0,0,0.5); color: #e0e0e0; border: none;")
        recommend_layout.addWidget(self.recommend_content)
        self.recommend_group.setLayout(recommend_layout)
        layout.addWidget(self.recommend_group)
        
        self.setLayout(layout)
    
    def update_guide(self, guide_data):
        """更新指引内容"""
        # 更新任务信息
        if 'quest' in guide_data:
            quest = guide_data['quest']
            content = f"名称：{quest['name']}\n地点：{quest['location']}\n指引：{quest['guide']}"
            self.quest_content.setPlainText(content)
            self.quest_group.show()
        else:
            self.quest_group.hide()
        
        # 更新BOSS信息
        if 'boss' in guide_data:
            boss = guide_data['boss']
            content = f"名称：{boss['name']}\n弱点：{', '.join(boss['weakness'])}\n技能：{', '.join(boss['skills'])}\n攻略：{boss['guide']}"
            self.boss_content.setPlainText(content)
            self.boss_group.show()
        else:
            self.boss_group.hide()
        
        # 更新推荐建议
        if 'recommendations' in guide_data:
            content = "\n".join([f"• {rec}" for rec in guide_data['recommendations']])
            self.recommend_content.setPlainText(content)
            self.recommend_group.show()
        else:
            self.recommend_group.hide()


class MainWindow(QMainWindow):
    """主窗口"""
    
    update_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.detector = GameDetector()
        self.init_ui()
        self.start_analysis()
    
    def init_ui(self):
        # 窗口设置
        self.setWindowTitle("暗黑破坏神游戏助手")
        self.setGeometry(100, 100, 300, 500)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # 透明背景
        self.setWindowOpacity(0.9)
        palette = QPalette()
        palette.setColor(QPalette.Background, QColor(20, 20, 40))
        self.setPalette(palette)
        
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 头部
        header = QWidget()
        header_layout = QHBoxLayout(header)
        self.title_label = QLabel("暗黑破坏神助手")
        self.title_label.setFont(QFont('Arial', 12, QFont.Bold))
        self.title_label.setStyleSheet("color: #ff6b35;")
        header_layout.addWidget(self.title_label)
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setStyleSheet("color: #ff6b35; background: transparent; border: none;")
        self.close_btn.clicked.connect(self.close)
        header_layout.addWidget(self.close_btn)
        
        layout.addWidget(header)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #8b0000;")
        layout.addWidget(line)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.guide_widget = GuideWidget()
        scroll_area.setWidget(self.guide_widget)
        layout.addWidget(scroll_area)
        
        # 控制按钮
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setStyleSheet("background-color: #8b0000; color: white; border: none; padding: 5px 10px;")
        self.pause_btn.clicked.connect(self.toggle_pause)
        control_layout.addWidget(self.pause_btn)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setStyleSheet("background-color: #0066cc; color: white; border: none; padding: 5px 10px;")
        self.refresh_btn.clicked.connect(self.manual_refresh)
        control_layout.addWidget(self.refresh_btn)
        
        layout.addWidget(control_widget)
        
        # 拖拽移动
        self.dragging = False
        self.drag_position = None
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.dragging = False
    
    def start_analysis(self):
        """开始定时分析"""
        self.is_paused = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_guide)
        self.timer.start(2000)  # 每2秒更新一次
    
    def toggle_pause(self):
        """暂停/继续分析"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.setText("继续")
            self.timer.stop()
        else:
            self.pause_btn.setText("暂停")
            self.timer.start(2000)
    
    def manual_refresh(self):
        """手动刷新"""
        self.update_guide()
    
    def update_guide(self):
        """更新指引内容"""
        if not self.is_paused:
            analysis = self.detector.analyze_game_state()
            self.guide_widget.update_guide(analysis)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())