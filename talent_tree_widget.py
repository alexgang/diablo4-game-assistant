#!/usr/bin/env python3
"""
暗黑破坏神4 - 技能树可视化组件（S13赛季热门BD：盲眼毒刃舞）
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolTip, QPushButton, QComboBox
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QRadialGradient
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
import math


class SkillNode:
    def __init__(self, name, skill_type='basic', max_points=5, current_points=0, 
                 description='', column=0, row=0, parent_skill=None):
        self.name = name
        self.skill_type = skill_type
        self.max_points = max_points
        self.current_points = current_points
        self.description = description
        self.column = column
        self.row = row
        self.parent_skill = parent_skill
        self.x = 0
        self.y = 0
        
    def is_active(self):
        return self.current_points > 0
        
    def is_maxed(self):
        return self.current_points >= self.max_points


class TalentTreeWidget(QWidget):
    skill_clicked = pyqtSignal(object)
    
    TYPE_COLORS = {
        'basic': {'bg': '#2d3748', 'active': '#68d391', 'border': '#276749'},
        'core': {'bg': '#744210', 'active': '#f6ad55', 'border': '#975a16'},
        'advanced': {'bg': '#2c5282', 'active': '#63b3ed', 'border': '#1a365d'},
        'ultimate': {'bg': '#702459', 'active': '#ed64a6', 'border': '#97266d'},
    }
    
    # S13热门BD配置
    BD_CONFIGS = {
        'blind_blade_dance': {
            'name': '盲眼毒刃舞（S13最强）',
            'description': 'S13赛季最热门的游侠BD，围绕盲眼套装+毒刃舞体系构建，通过高频中毒与技能循环实现稳定刷图',
            'skills': {
                '振奋打击': 1,      # 基础技
                '扭转回刃': 5,      # 核心输出
                '扭转回刃·强化': 3, # 强化
                '快刀乱刺': 2,      # 辅助
                '钉爪刺': 3,        # 陷阱
                '剧毒陷阱': 5,      # 核心
                '死亡陷阱': 3,      # 进阶
                '死亡陷阱·终极': 1, # 终极
                '毒素灌注': 3,      # 灌注
                '暗影灌注': 5,      # 核心
                '暗影灌注·强化': 3, # 强化
                '冰寒灌注': 1,      # 辅助
                '暗影步伐': 2,      # 位移
                '隐匿': 3,          # 隐身
            }
        },
        'arrow_rain': {
            'name': '箭雨游侠',
            'description': '箭雨作为主要AOE技能，配合穿甲射击进行单体输出，机动性强',
            'skills': {
                '强力箭矢': 3,
                '穿心箭': 5,
                '穿心箭·强化': 3,
                '穿心箭·精通': 1,
                '振奋打击': 2,
                '毒素灌注': 5,
                '毒素灌注·强化': 3,
            }
        },
        'piercing': {
            'name': '穿刺游侠',
            'description': '穿刺作为核心输出技能，配合穿刺强化实现范围伤害',
            'skills': {
                '振奋打击': 3,
                '穿刺': 5,
                '穿刺·强化': 3,
                '穿刺·精通': 1,
                '毒素灌注': 3,
            }
        }
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(950, 850)
        self.setStyleSheet("background-color: #1a202c;")
        
        self.skills = {}
        self.columns = {}
        self.node_width = 120
        self.node_height = 50
        self.column_spacing = 30
        self.row_spacing = 20
        self.margin = 40
        self.current_bd = 'blind_blade_dance'
        
        self.setMouseTracking(True)
        
        self.canvas = SkillTreeCanvas(self)
        self._create_skill_tree()
        self._apply_bd_config(self.current_bd)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # BD选择器
        bd_selector = QHBoxLayout()
        bd_label = QLabel("选择BD:")
        bd_label.setStyleSheet("color: #c9a227; font-size: 14px;")
        bd_selector.addWidget(bd_label)
        
        self.bd_combo = QComboBox()
        self.bd_combo.addItem('盲眼毒刃舞（S13最强）', 'blind_blade_dance')
        self.bd_combo.addItem('箭雨游侠', 'arrow_rain')
        self.bd_combo.addItem('穿刺游侠', 'piercing')
        self.bd_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d3748;
                color: #ffd700;
                border: 1px solid #4a5568;
                padding: 5px 10px;
                border-radius: 4px;
                min-width: 200px;
            }
            QComboBox:hover {
                border-color: #c9a227;
            }
        """)
        self.bd_combo.currentIndexChanged.connect(self._on_bd_changed)
        bd_selector.addWidget(self.bd_combo)
        bd_selector.addStretch()
        
        layout.addLayout(bd_selector)
        
        # BD描述
        bd = self.BD_CONFIGS[self.current_bd]
        self.bd_desc = QLabel(bd['description'])
        self.bd_desc.setFont(QFont('Microsoft YaHei', 11))
        self.bd_desc.setStyleSheet("color: #718096; padding: 5px; background-color: #161b22; border-radius: 4px;")
        self.bd_desc.setWordWrap(True)
        layout.addWidget(self.bd_desc)
        
        # 标题
        header = QLabel(f"游侠 - {bd['name']}")
        header.setFont(QFont('Microsoft YaHei', 20, QFont.Bold))
        header.setStyleSheet("color: #c9a227; padding: 10px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # 技能树画布
        self.canvas = SkillTreeCanvas(self)
        self.canvas.setMinimumSize(930, 500)
        self.canvas.setStyleSheet("background-color: #0d1117; border: 2px solid #30363d; border-radius: 8px;")
        layout.addWidget(self.canvas)
        
        # 详情面板
        self.detail_panel = SkillDetailPanel(self)
        layout.addWidget(self.detail_panel)
        
    def _on_bd_changed(self, index):
        bd_key = self.bd_combo.currentData()
        self._apply_bd_config(bd_key)
        
        # 更新标题和描述
        bd = self.BD_CONFIGS[bd_key]
        self.findChild(QLabel, "").setText(f"游侠 - {bd['name']}")
        
        # 更新canvas
        self.canvas.skills = self.skills
        self.canvas.columns = self.columns
        self._calculate_positions()
        self.canvas.update()
        
    def _apply_bd_config(self, bd_key):
        """应用BD配置"""
        bd = self.BD_CONFIGS.get(bd_key, {})
        skill_config = bd.get('skills', {})
        
        # 重置所有技能
        for skill in self.skills.values():
            skill.current_points = 0
            
        # 应用BD配置
        for skill_name, points in skill_config.items():
            if skill_name in self.skills:
                self.skills[skill_name].current_points = points
                
    def _create_skill_tree(self):
        """创建游侠技能树"""
        skill_trees = [
            ['振奋打击', '穿刺', '穿刺·强化', '穿刺·精通'],
            ['强力箭矢', '穿心箭', '穿心箭·强化', '穿心箭·精通'],
            ['扭转回刃', '扭转回刃·强化', '快刀乱刺', '快刀乱刺·强化', '快刀乱刺·精通'],
            ['钉爪刺', '剧毒陷阱', '死亡陷阱', '死亡陷阱·终极'],
            ['暗影步伐', '隐匿', '暗影帷幕', '暗影复制体'],
            ['毒素灌注', '毒素灌注·强化', '暗影灌注', '暗影灌注·强化', '冰寒灌注'],
        ]
        
        parents = [
            [None, '振奋打击', '穿刺', '穿刺·强化'],
            [None, '强力箭矢', '穿心箭', '穿心箭·强化'],
            [None, '扭转回刃', '扭转回刃', '快刀乱刺', '快刀乱刺·强化'],
            [None, '钉爪刺', '剧毒陷阱', '死亡陷阱'],
            [None, '暗影步伐', '隐匿', '暗影帷幕'],
            [None, '毒素灌注', '毒素灌注', '暗影灌注', '冰寒灌注'],
        ]
        
        types = [
            ['basic', 'core', 'advanced', 'ultimate'],
            ['basic', 'core', 'advanced', 'ultimate'],
            ['basic', 'advanced', 'core', 'advanced', 'ultimate'],
            ['basic', 'core', 'advanced', 'ultimate'],
            ['basic', 'core', 'advanced', 'ultimate'],
            ['basic', 'advanced', 'core', 'advanced', 'ultimate'],
        ]
        
        descriptions = {
            '振奋打击': '快速刺击敌人，伤害一般但冷却极短',
            '穿刺': '投掷穿透敌人的飞刀，对路径上的敌人造成伤害',
            '穿刺·强化': '穿刺现在会留下伤口，使敌人持续流血',
            '穿刺·精通': '穿刺现在会弹射到更多敌人身上',
            '强力箭矢': '射出一支强力的箭矢，造成较高伤害',
            '穿心箭': '精准射击，对单体敌人造成大量伤害',
            '穿心箭·强化': '穿心箭使敌人护甲破碎',
            '穿心箭·精通': '穿心箭必定暴击',
            '扭转回刃': '快速旋转，造成范围伤害（毒刃舞核心）',
            '扭转回刃·强化': '扭转回刃现在会对击中的敌人造成减速',
            '快刀乱刺': '快速连续刺击',
            '快刀乱刺·强化': '快刀乱刺有几率使敌人昏迷',
            '快刀乱刺·精通': '快刀乱刺的最后一次攻击必定暴击',
            '钉爪刺': '布置陷阱，使敌人减速',
            '剧毒陷阱': '布置毒云陷阱，使敌人持续中毒（核心）',
            '死亡陷阱': '陷阱触发后再次布置陷阱',
            '死亡陷阱·终极': '死亡陷阱造成大量爆炸伤害',
            '暗影步伐': '快速位移到敌人身后',
            '隐匿': '进入隐身状态，下次攻击造成额外伤害',
            '暗影帷幕': '隐身时留下一片暗影区域',
            '暗影复制体': '召唤暗影复制体协助作战',
            '毒素灌注': '为武器注入毒素，使攻击造成持续毒伤',
            '毒素灌注·强化': '毒素伤害增加',
            '暗影灌注': '为武器注入暗影能量（核心）',
            '暗影灌注·强化': '暗影伤害增加',
            '冰寒灌注': '为武器注入冰霜之力',
        }
        
        for col_idx, col in enumerate(skill_trees):
            self.columns[col_idx] = []
            for row_idx, skill_name in enumerate(col):
                max_pts = 1 if row_idx == len(col) - 1 and types[col_idx][row_idx] == 'ultimate' else 5
                
                skill = SkillNode(
                    skill_name,
                    types[col_idx][row_idx],
                    max_pts,
                    0,
                    descriptions.get(skill_name, f"{skill_name}技能"),
                    col_idx, row_idx,
                    parents[col_idx][row_idx]
                )
                self.skills[skill_name] = skill
                self.columns[col_idx].append(skill_name)
                
        self.canvas.skills = self.skills
        self.canvas.columns = self.columns
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._calculate_positions()
        
    def _calculate_positions(self):
        canvas_width = self.canvas.width() - 40
        canvas_height = self.canvas.height() - 40
        
        num_columns = len(self.columns)
        total_width = num_columns * self.node_width + (num_columns - 1) * self.column_spacing
        start_x = (canvas_width - total_width) / 2 + self.margin
        
        for col_idx, col_skills in self.columns.items():
            x = start_x + col_idx * (self.node_width + self.column_spacing)
            num_skills = len(col_skills)
            start_y = canvas_height - self.node_height - self.margin
            
            for row_idx, skill_name in enumerate(col_skills):
                y = start_y - row_idx * (self.node_height + self.row_spacing)
                self.skills[skill_name].x = x + self.node_width / 2
                self.skills[skill_name].y = y + self.node_height / 2
                
        if hasattr(self.canvas, 'update'):
            self.canvas.update()


class SkillTreeCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.skills = {}
        self.columns = {}
        self.setMouseTracking(True)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        painter.fillRect(self.rect(), QColor('#0d1117'))
        
        self._draw_connections(painter)
        self._draw_column_labels(painter)
        
        for name, skill in self.skills.items():
            self._draw_skill(painter, skill)
            
    def _draw_column_labels(self, painter):
        """绘制列标签"""
        font = QFont('Microsoft YaHei', 9)
        painter.setFont(font)
        
        labels = ['穿刺', '穿心箭', '刃舞', '毒陷阱', '暗影', '灌注']
        
        for col_idx, col_skills in self.columns.items():
            if col_skills:
                first_skill = self.skills.get(col_skills[0])
                if first_skill:
                    x = first_skill.x - self.parent_widget.node_width / 2
                    y = first_skill.y + self.parent_widget.node_height + 5
                    
                    painter.setPen(QPen(QColor('#ffd700')))
                    painter.drawText(QRectF(x, y, self.parent_widget.node_width, 15), 
                                   Qt.AlignCenter, labels[col_idx])
                    
    def _draw_connections(self, painter):
        for name, skill in self.skills.items():
            if skill.parent_skill and skill.parent_skill in self.skills:
                parent = self.skills[skill.parent_skill]
                self._draw_connection(painter, parent, skill)
                
    def _draw_connection(self, painter, parent, child):
        if child.is_active():
            color = QColor('#48bb78')
            width = 4
        elif parent.is_active():
            color = QColor('#4a5568')
            width = 3
        else:
            color = QColor('#2d3748')
            width = 2
            
        pen = QPen(color)
        pen.setWidth(width)
        painter.setPen(pen)
        
        start_y = parent.y + self.parent_widget.node_height / 2
        end_y = child.y - self.parent_widget.node_height / 2
        mid_y = (start_y + end_y) / 2
        
        painter.drawLine(parent.x, start_y, parent.x, mid_y)
        painter.drawLine(parent.x, mid_y, child.x, mid_y)
        painter.drawLine(child.x, mid_y, child.x, end_y)
        
    def _draw_skill(self, painter, skill):
        colors = TalentTreeWidget.TYPE_COLORS.get(skill.skill_type, TalentTreeWidget.TYPE_COLORS['basic'])
        
        w = self.parent_widget.node_width
        h = self.parent_widget.node_height
        x, y = skill.x - w/2, skill.y - h/2
        
        if skill.is_maxed():
            bg_color = QColor(colors['active'])
            border_color = QColor('#ffd700')
            border_width = 4
        elif skill.is_active():
            bg_color = QColor(colors['active'])
            border_color = QColor(colors['border'])
            border_width = 3
        else:
            bg_color = QColor(colors['bg'])
            border_color = QColor(colors['border'])
            border_width = 2
            
        if skill.is_active():
            glow_rect = QRectF(x - 5, y - 5, w + 10, h + 10)
            glow = QRadialGradient(skill.x, skill.y, max(w, h)/2 + 5)
            glow.setColorAt(0, bg_color.lighter(180))
            glow.setColorAt(1, Qt.transparent)
            painter.fillRect(glow_rect, glow)
        
        rect = QRectF(x, y, w, h)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, border_width))
        painter.drawRoundedRect(rect, 8, 8)
        
        painter.setPen(QPen(QColor('#ffffff')))
        painter.setFont(QFont('Microsoft YaHei', 10, QFont.Bold))
        
        name_rect = QRectF(x, y + 8, w, 20)
        painter.drawText(name_rect, Qt.AlignCenter, skill.name)
        
        if skill.max_points > 1:
            points_text = f"{skill.current_points}/{skill.max_points}"
            painter.setFont(QFont('Segoe UI', 9))
            painter.setPen(QPen(QColor('#ffd700')))
            painter.drawText(name_rect.adjusted(0, 18, 0, 0), Qt.AlignCenter, points_text)
        else:
            painter.setFont(QFont('Segoe UI', 12))
            painter.setPen(QPen(QColor('#ffd700')))
            star = "★" if skill.is_active() else "☆"
            painter.drawText(name_rect.adjusted(0, 18, 0, 0), Qt.AlignCenter, star)
                
    def mousePressEvent(self, event):
        clicked = self._get_skill_at(event.pos())
        if clicked:
            if clicked.parent_skill:
                parent = self.skills.get(clicked.parent_skill)
                if parent and not parent.is_active():
                    QToolTip.showText(event.globalPos(), f"<b>需要先激活【{parent.name}】</b>", self)
                    return
                    
            self.parent_widget.selected_skill = clicked
            self.parent_widget.detail_panel.show_skill(clicked)
            self.parent_widget.skill_clicked.emit(clicked)
            self.update()
            
    def mouseMoveEvent(self, event):
        hover = self._get_skill_at(event.pos())
        if hover:
            tooltip = f"<b>{hover.name}</b><br/>"
            if hover.parent_skill:
                parent = self.skills.get(hover.parent_skill)
                if parent and not parent.is_active():
                    tooltip += f"<font color='red'>前置: {parent.name}</font><br/>"
            tooltip += hover.description
            QToolTip.showText(event.globalPos(), tooltip, self)
        else:
            QToolTip.hideText()
            
    def _get_skill_at(self, pos):
        for name, skill in self.skills.items():
            dx = pos.x() - skill.x
            dy = pos.y() - skill.y
            w = self.parent_widget.node_width / 2
            h = self.parent_widget.node_height / 2
            if abs(dx) <= w and abs(dy) <= h:
                return skill
        return None


class SkillDetailPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 2px solid #30363d;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        
        self.name_label = QLabel("点击技能节点查看详情")
        self.name_label.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        self.name_label.setStyleSheet("color: #ffd700;")
        layout.addWidget(self.name_label)
        
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        layout.addWidget(self.info_label)
        
        self.desc_label = QLabel("")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #e6e6e6; font-size: 12px; line-height: 1.5;")
        self.desc_label.setMaximumHeight(60)
        layout.addWidget(self.desc_label)
        
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("+ 加点")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
            QPushButton:disabled {
                background-color: #484f58;
                color: #6e7681;
            }
        """)
        self.add_btn.clicked.connect(self._add_point)
        btn_layout.addWidget(self.add_btn)
        
        self.remove_btn = QPushButton("- 减点")
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #da3633;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f85149;
            }
            QPushButton:disabled {
                background-color: #484f58;
                color: #6e7681;
            }
        """)
        self.remove_btn.clicked.connect(self._remove_point)
        btn_layout.addWidget(self.remove_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.current_skill = None
        
    def show_skill(self, skill):
        self.current_skill = skill
        self.name_label.setText(skill.name)
        
        type_names = {
            'basic': '基础技能',
            'core': '核心技能',
            'advanced': '进阶技能',
            'ultimate': '终结技能'
        }
        type_name = type_names.get(skill.skill_type, skill.skill_type)
        
        info_parts = [f"类型: {type_name}", f"点数: {skill.current_points}/{skill.max_points}"]
        if skill.parent_skill:
            info_parts.append(f"前置: {skill.parent_skill}")
            
        self.info_label.setText(" | ".join(info_parts))
        self.desc_label.setText(skill.description)
        
        can_add = skill.current_points < skill.max_points
        if skill.parent_skill:
            parent = self.parent_widget.skills.get(skill.parent_skill)
            if parent and not parent.is_active():
                can_add = False
                
        self.add_btn.setEnabled(can_add)
        self.remove_btn.setEnabled(skill.current_points > 0)
        
    def _add_point(self):
        if self.current_skill:
            if self.current_skill.parent_skill:
                parent = self.parent_widget.skills.get(self.current_skill.parent_skill)
                if parent and not parent.is_active():
                    return
            self.current_skill.current_points += 1
            self.show_skill(self.current_skill)
            self.parent_widget.canvas.update()
            
    def _remove_point(self):
        if self.current_skill and self.current_skill.current_points > 0:
            self.current_skill.current_points -= 1
            self.show_skill(self.current_skill)
            self.parent_widget.canvas.update()


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    window = TalentTreeWidget()
    window.setWindowTitle("暗黑4 技能树 - 游侠 BD展示")
    window.resize(950, 900)
    window.show()
    
    sys.exit(app.exec_())
