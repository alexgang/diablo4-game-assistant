#!/usr/bin/env python3
"""
暗黑助手图形叠加层 - 游戏风格的可视化叠加层

功能：
1. 技能树面板 - 可视化技能节点与连线
2. 巅峰盘面板 - 网格式巅峰节点
3. 装备布局面板 - 角色轮廓与装备槽位
4. 可拖拽、可调透明度、快捷键切换面板
"""

import re

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QScrollArea, QFrame, QGridLayout,
)
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QRadialGradient,
    QPainterPath,
)
from PyQt5.QtCore import Qt, QRectF, pyqtSignal

try:
    from config import OVERLAY_CONFIG
except ImportError:
    OVERLAY_CONFIG = {}

RARITY_COLORS = {
    '暗金': '#ff8000',
    '传奇': '#bf642f',
    '套装': '#00ff00',
    '稀有': '#ffff00',
    '魔法': '#4169e1',
    '普通': '#ffffff',
}

SLOT_ORDER = [
    '头盔', '胸甲', '手套', '裤子', '靴子',
    '主手武器', '副手武器', '双手武器',
    '护符', '戒指1', '戒指2',
]

SLOT_DISPLAY = {
    '头盔': '🪖', '胸甲': '🛡️', '手套': '🧤', '裤子': '👖',
    '靴子': '👢', '主手武器': '⚔️', '副手武器': '🛡️', '双手武器': '⚔️',
    '护符': '📿', '戒指1': '💍', '戒指2': '💍', '武器': '⚔️',
}

CLASS_COLORS = {
    '野蛮人': '#ff4444', '法师': '#4488ff', '游侠': '#44ff44',
    '死灵法师': '#aa44ff', '德鲁伊': '#ff8844', '圣骑士': '#ffff44',
}

CATEGORY_COLORS = {
    '核心': '#ff6b35', '防御': '#4169e1', '终极': '#ffd700', '被动': '#888888',
}

NODE_RADIUS = 12
NODE_SPACING_X = 70
NODE_SPACING_Y = 55
PARAGON_COLS = 8
PARAGON_ROWS = 6
PARAGON_NODE_SIZE = 8
PARAGON_RARE_SIZE = 10


class SkillTreeWidget(QWidget):
    """技能树绘制控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._skills = {}
        self._class_color = '#ff6b35'
        self._active_skills = set()
        self._node_positions = {}
        self._connections = []
        self.setMinimumHeight(400)

    def set_skills(self, skills, class_name=''):
        self._skills = skills if isinstance(skills, dict) else {}
        self._class_color = CLASS_COLORS.get(class_name, '#ff6b35')
        self._active_skills = set()
        self._node_positions = {}
        self._connections = []
        self._layout_nodes()
        self.update()

    def _layout_nodes(self):
        if not self._skills:
            return
        y_offset = 30
        for category, skill_list in self._skills.items():
            if not isinstance(skill_list, list):
                continue
            count = len(skill_list)
            total_width = max(count - 1, 1) * NODE_SPACING_X
            start_x = max((self.width() - total_width) // 2, NODE_SPACING_X) if self.width() > 0 else NODE_SPACING_X
            prev_positions = []
            for i, skill in enumerate(skill_list):
                name, points = self._parse_skill(skill)
                x = start_x + i * NODE_SPACING_X
                y = y_offset
                self._node_positions[(category, i)] = {
                    'x': x, 'y': y, 'name': name, 'points': points,
                    'active': points != '' and points != '0',
                }
                if points and points != '0':
                    self._active_skills.add((category, i))
                if prev_positions:
                    for pp in prev_positions:
                        self._connections.append((pp, (category, i)))
                prev_positions.append((category, i))
            y_offset += NODE_SPACING_Y + 20

    def _parse_skill(self, skill):
        if isinstance(skill, dict):
            name = skill.get('name', '')
            points = str(skill.get('points', ''))
            return name, points
        if not isinstance(skill, str):
            return str(skill), ''
        match = re.match(r'(.+?)\s+(\d+)$', skill.strip())
        if match:
            return match.group(1).strip(), match.group(2)
        return skill.strip(), ''

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._node_positions = {}
        self._connections = []
        self._layout_nodes()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        if not self._skills:
            painter.setPen(QColor(102, 102, 102))
            painter.setFont(QFont('Microsoft YaHei', 10))
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无技能数据")
            painter.end()
            return

        for conn_start, conn_end in self._connections:
            if conn_start in self._node_positions and conn_end in self._node_positions:
                p1 = self._node_positions[conn_start]
                p2 = self._node_positions[conn_end]
                pen = QPen(QColor(255, 255, 255, 60), 2)
                painter.setPen(pen)
                painter.drawLine(int(p1['x']), int(p1['y']), int(p2['x']), int(p2['y']))

        current_category = None
        for key, node in self._node_positions.items():
            category = key[0]
            if category != current_category:
                current_category = category
                cat_color = CATEGORY_COLORS.get(category, '#888888')
                painter.setPen(QColor(cat_color))
                painter.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
                for k2, n2 in self._node_positions.items():
                    if k2[0] == category:
                        painter.drawText(
                            int(n2['x'] - 60), int(n2['y'] - NODE_RADIUS - 14),
                            120, 16, Qt.AlignCenter, category
                        )
                        break

            is_active = node['active']
            cx, cy = node['x'], node['y']

            if is_active:
                glow = QRadialGradient(cx, cy, NODE_RADIUS + 8)
                glow.setColorAt(0, QColor(self._class_color))
                glow.setColorAt(0.5, QColor(self._class_color + '80') if len(self._class_color) == 7 else QColor(self._class_color))
                glow.setColorAt(1, QColor(0, 0, 0, 0))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(glow))
                painter.drawEllipse(QRectF(cx - NODE_RADIUS - 8, cy - NODE_RADIUS - 8,
                                           (NODE_RADIUS + 8) * 2, (NODE_RADIUS + 8) * 2))

            fill_color = QColor(self._class_color) if is_active else QColor(40, 40, 60)
            border_color = QColor('#ff6b35') if is_active else QColor(80, 80, 100)

            painter.setPen(QPen(border_color, 2))
            painter.setBrush(QBrush(fill_color))
            painter.drawEllipse(QRectF(cx - NODE_RADIUS, cy - NODE_RADIUS,
                                       NODE_RADIUS * 2, NODE_RADIUS * 2))

            if node['points']:
                painter.setPen(QColor(255, 255, 255) if is_active else QColor(150, 150, 150))
                painter.setFont(QFont('Microsoft YaHei', 8, QFont.Bold))
                painter.drawText(QRectF(cx - NODE_RADIUS, cy - NODE_RADIUS,
                                        NODE_RADIUS * 2, NODE_RADIUS * 2),
                                 Qt.AlignCenter, node['points'])

            painter.setPen(QColor(220, 220, 220) if is_active else QColor(120, 120, 120))
            painter.setFont(QFont('Microsoft YaHei', 7))
            name = node['name']
            if len(name) > 6:
                name = name[:5] + '..'
            painter.drawText(QRectF(cx - 35, cy + NODE_RADIUS + 2, 70, 14),
                             Qt.AlignCenter, name)

        painter.end()

    def sizeHint(self):
        row_count = len(self._skills) if isinstance(self._skills, dict) else 1
        return QWidget.sizeHint(self)


class ParagonBoardWidget(QWidget):
    """巅峰盘绘制控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._boards = []
        self._class_color = '#ff6b35'
        self.setMinimumHeight(300)

    def set_boards(self, boards, class_name=''):
        self._boards = boards if isinstance(boards, list) else []
        self._class_color = CLASS_COLORS.get(class_name, '#ff6b35')
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        if not self._boards:
            painter.setPen(QColor(102, 102, 102))
            painter.setFont(QFont('Microsoft YaHei', 10))
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无巅峰数据")
            painter.end()
            return

        y_offset = 0
        spacing = 22
        cell_w = 38
        cell_h = 22

        for board_idx, board in enumerate(self._boards):
            if isinstance(board, dict):
                board_name = board.get('name', f'巅峰盘 {board_idx + 1}')
                rare_node = board.get('rare_node', '')
            else:
                board_name = str(board)
                rare_node = ''

            painter.setPen(QColor('#ffd700'))
            painter.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
            painter.drawText(10, y_offset + 12, board_name)
            y_offset += 18

            grid_start_x = max((self.width() - PARAGON_COLS * cell_w) // 2, 10) if self.width() > 0 else 10

            center_row = PARAGON_ROWS // 2
            center_col = PARAGON_COLS // 2

            for row in range(PARAGON_ROWS):
                for col in range(PARAGON_COLS):
                    cx = grid_start_x + col * cell_w + cell_w // 2
                    cy = y_offset + row * cell_h + cell_h // 2

                    is_center = (row == center_row and col == center_col)
                    is_rare = (abs(row - center_row) <= 1 and abs(col - center_col) <= 1 and not is_center)

                    if is_center:
                        size = PARAGON_RARE_SIZE
                        color = QColor(self._class_color)
                        border = QColor('#ff6b35')
                    elif is_rare:
                        size = PARAGON_RARE_SIZE
                        color = QColor('#ffd700')
                        border = QColor('#ffd700')
                    else:
                        size = PARAGON_NODE_SIZE
                        color = QColor(60, 60, 80)
                        border = QColor(100, 100, 120)

                    self._draw_diamond(painter, cx, cy, size, color, border)

            y_offset += PARAGON_ROWS * cell_h + 8

            if rare_node:
                painter.setPen(QColor('#ffd700'))
                painter.setFont(QFont('Microsoft YaHei', 8))
                painter.drawText(10, y_offset + 10, f"★ {rare_node}")
                y_offset += 16

            if board_idx < len(self._boards) - 1:
                pen = QPen(QColor(139, 0, 0, 100), 1)
                painter.setPen(pen)
                painter.drawLine(10, y_offset + 2, self.width() - 10, y_offset + 2)
                y_offset += 8

        painter.end()

    def _draw_diamond(self, painter, cx, cy, size, fill, border):
        path = QPainterPath()
        path.moveTo(cx, cy - size)
        path.lineTo(cx + size, cy)
        path.lineTo(cx, cy + size)
        path.lineTo(cx - size, cy)
        path.closeSubpath()
        painter.setPen(QPen(border, 1.5))
        painter.setBrush(QBrush(fill))
        painter.drawPath(path)


class EquipmentSlotWidget(QWidget):
    """单个装备槽位控件"""

    def __init__(self, slot_name, parent=None):
        super().__init__(parent)
        self._slot_name = slot_name
        self._item_name = ''
        self._rarity = ''
        self._is_empty = True
        self.setFixedSize(80, 36)

    def set_item(self, name='', rarity=''):
        self._item_name = name
        self._rarity = rarity
        self._is_empty = not name
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rarity_color = RARITY_COLORS.get(self._rarity, '#ffffff')
        border_color = QColor(rarity_color) if not self._is_empty else QColor(80, 80, 100, 150)

        if self._is_empty:
            painter.setPen(QPen(QColor(80, 80, 100, 150), 1, Qt.DashLine))
            painter.setBrush(QBrush(QColor(20, 20, 40, 120)))
        else:
            bg = QColor(rarity_color)
            bg.setAlpha(30)
            painter.setPen(QPen(border_color, 1.5))
            painter.setBrush(QBrush(bg))

        rect = QRectF(0, 0, self.width() - 1, self.height() - 1)
        painter.drawRoundedRect(rect, 4, 4)

        icon = SLOT_DISPLAY.get(self._slot_name, '')
        painter.setFont(QFont('Microsoft YaHei', 7))
        painter.setPen(QColor(150, 150, 150))
        painter.drawText(QRectF(3, 0, 20, self.height()), Qt.AlignVCenter | Qt.AlignLeft, icon)

        if self._is_empty:
            painter.setPen(QColor(80, 80, 100))
            painter.setFont(QFont('Microsoft YaHei', 8))
            painter.drawText(QRectF(22, 0, self.width() - 25, self.height()),
                             Qt.AlignVCenter | Qt.AlignLeft, "空")
        else:
            display_name = self._item_name
            if len(display_name) > 5:
                display_name = display_name[:4] + '..'
            painter.setPen(QColor(rarity_color))
            painter.setFont(QFont('Microsoft YaHei', 8, QFont.Bold))
            painter.drawText(QRectF(22, 0, self.width() - 25, self.height()),
                             Qt.AlignVCenter | Qt.AlignLeft, display_name)

        painter.end()


class CharacterSilhouetteWidget(QWidget):
    """角色轮廓与装备槽位布局"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = {}
        self._slot_widgets = {}
        self._init_slots()

    def _init_slots(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._slot_widgets['头盔'] = EquipmentSlotWidget('头盔')
        layout.addWidget(self._slot_widgets['头盔'], 0, 1, 1, 1, Qt.AlignCenter)

        self._slot_widgets['主手武器'] = EquipmentSlotWidget('主手武器')
        layout.addWidget(self._slot_widgets['主手武器'], 1, 0, 1, 1, Qt.AlignCenter)

        self._silhouette = _SilhouetteWidget()
        self._silhouette.setFixedSize(100, 140)
        layout.addWidget(self._silhouette, 1, 1, 3, 1, Qt.AlignCenter)

        self._slot_widgets['副手武器'] = EquipmentSlotWidget('副手武器')
        layout.addWidget(self._slot_widgets['副手武器'], 1, 2, 1, 1, Qt.AlignCenter)

        self._slot_widgets['胸甲'] = EquipmentSlotWidget('胸甲')
        layout.addWidget(self._slot_widgets['胸甲'], 2, 1, 1, 1, Qt.AlignCenter)

        self._slot_widgets['手套'] = EquipmentSlotWidget('手套')
        layout.addWidget(self._slot_widgets['手套'], 3, 0, 1, 1, Qt.AlignCenter)

        self._slot_widgets['裤子'] = EquipmentSlotWidget('裤子')
        layout.addWidget(self._slot_widgets['裤子'], 3, 2, 1, 1, Qt.AlignCenter)

        self._slot_widgets['靴子'] = EquipmentSlotWidget('靴子')
        layout.addWidget(self._slot_widgets['靴子'], 4, 1, 1, 1, Qt.AlignCenter)

        self._slot_widgets['护符'] = EquipmentSlotWidget('护符')
        layout.addWidget(self._slot_widgets['护符'], 5, 1, 1, 1, Qt.AlignCenter)

        self._slot_widgets['戒指1'] = EquipmentSlotWidget('戒指1')
        layout.addWidget(self._slot_widgets['戒指1'], 5, 0, 1, 1, Qt.AlignCenter)

        self._slot_widgets['戒指2'] = EquipmentSlotWidget('戒指2')
        layout.addWidget(self._slot_widgets['戒指2'], 5, 2, 1, 1, Qt.AlignCenter)

    def set_items(self, items):
        self._items = {}
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    slot = item.get('slot', item.get('type', ''))
                    name = item.get('name', '')
                    rarity = item.get('rarity', '传奇')
                    if slot:
                        self._items[slot] = {'name': name, 'rarity': rarity}
        elif isinstance(items, dict):
            self._items = items

        for slot_name, widget in self._slot_widgets.items():
            if slot_name in self._items:
                data = self._items[slot_name]
                widget.set_item(data.get('name', ''), data.get('rarity', ''))
            else:
                widget.set_item('', '')

        if '双手武器' in self._items and '主手武器' not in self._items:
            data = self._items['双手武器']
            self._slot_widgets['主手武器'].set_item(data.get('name', ''), data.get('rarity', ''))


class _SilhouetteWidget(QWidget):
    """角色轮廓绘制"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        pen = QPen(QColor(100, 80, 120, 120), 1.5)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(30, 20, 40, 80)))

        head_r = min(w, h) * 0.12
        cx = w / 2
        head_cy = head_r + 5
        painter.drawEllipse(QRectF(cx - head_r, head_cy - head_r, head_r * 2, head_r * 2))

        body_path = QPainterPath()
        body_top = head_cy + head_r + 2
        shoulder_w = w * 0.35
        waist_w = w * 0.25
        hip_w = w * 0.3
        body_bottom = h * 0.65

        body_path.moveTo(cx - shoulder_w, body_top)
        body_path.lineTo(cx + shoulder_w, body_top)
        body_path.lineTo(cx + waist_w, body_bottom * 0.7)
        body_path.lineTo(cx + hip_w, body_bottom)
        body_path.lineTo(cx - hip_w, body_bottom)
        body_path.lineTo(cx - waist_w, body_bottom * 0.7)
        body_path.closeSubpath()
        painter.drawPath(body_path)

        arm_w = w * 0.08
        arm_top = body_top + 2
        arm_bottom = body_bottom * 0.75

        left_arm = QPainterPath()
        left_arm.moveTo(cx - shoulder_w, arm_top)
        left_arm.lineTo(cx - shoulder_w - arm_w * 3, arm_bottom)
        left_arm.lineTo(cx - shoulder_w - arm_w * 3 + arm_w, arm_bottom)
        left_arm.lineTo(cx - shoulder_w + arm_w, arm_top)
        left_arm.closeSubpath()
        painter.drawPath(left_arm)

        right_arm = QPainterPath()
        right_arm.moveTo(cx + shoulder_w, arm_top)
        right_arm.lineTo(cx + shoulder_w + arm_w * 3, arm_bottom)
        right_arm.lineTo(cx + shoulder_w + arm_w * 3 - arm_w, arm_bottom)
        right_arm.lineTo(cx + shoulder_w - arm_w, arm_top)
        right_arm.closeSubpath()
        painter.drawPath(right_arm)

        leg_w = w * 0.1
        leg_top = body_bottom
        leg_bottom = h - 5

        left_leg = QPainterPath()
        left_leg.moveTo(cx - hip_w + 2, leg_top)
        left_leg.lineTo(cx - leg_w, leg_bottom)
        left_leg.lineTo(cx - leg_w + leg_w * 2, leg_bottom)
        left_leg.lineTo(cx - 2, leg_top)
        left_leg.closeSubpath()
        painter.drawPath(left_leg)

        right_leg = QPainterPath()
        right_leg.moveTo(cx + 2, leg_top)
        right_leg.lineTo(cx + leg_w - leg_w * 2, leg_bottom)
        right_leg.lineTo(cx + leg_w, leg_bottom)
        right_leg.lineTo(cx + hip_w - 2, leg_top)
        right_leg.closeSubpath()
        painter.drawPath(right_leg)

        painter.end()


class GraphicalOverlay(QWidget):
    """暗黑助手图形叠加层"""

    closed = pyqtSignal()
    visibility_changed = pyqtSignal(bool)

    def __init__(self, parent=None, opacity=None):
        super().__init__(parent)
        self._cfg = OVERLAY_CONFIG
        self.opacity = opacity if opacity is not None else self._cfg.get('opacity', 0.85)
        self._dragging = False
        self._drag_pos = None
        self._current_panel = 'skill'
        self._class_name = ''

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._container = QWidget()
        self._container.setObjectName("graphicalOverlayContainer")
        self._container.setStyleSheet(
            "#graphicalOverlayContainer {"
            "  background: rgba(10, 10, 30, 200);"
            "  border: 1px solid rgba(139, 0, 0, 180);"
            "  border-radius: 6px;"
            "}"
        )
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(6, 4, 6, 6)
        container_layout.setSpacing(4)

        self._build_control_bar(container_layout)
        self._build_stacked_panels(container_layout)

        main_layout.addWidget(self._container)
        self.setFixedSize(400, 600)
        self.setWindowOpacity(self.opacity)

    def _build_control_bar(self, parent_layout):
        bar = QWidget()
        bar.setStyleSheet("background: rgba(20, 10, 30, 220); border-radius: 3px;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(6, 3, 6, 3)
        bar_layout.setSpacing(4)

        title = QLabel("暗黑助手")
        title.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        title.setStyleSheet(
            "color: #ff6b35; "
            "background: transparent; "
        )
        bar_layout.addWidget(title)

        bar_layout.addStretch()

        self._panel_btns = {}
        for key, label in [('skill', '技能'), ('paragon', '巅峰'), ('equipment', '装备')]:
            btn = QPushButton(label)
            btn.setFixedSize(42, 22)
            btn.setFont(QFont('Microsoft YaHei', 9))
            btn.setStyleSheet(self._panel_btn_style(key == self._current_panel))
            btn.clicked.connect(lambda checked, k=key: self.show_panel(k))
            bar_layout.addWidget(btn)
            self._panel_btns[key] = btn

        bar_layout.addSpacing(6)

        opacity_btn = QPushButton("👁")
        opacity_btn.setFixedSize(22, 22)
        opacity_btn.setStyleSheet(
            "QPushButton { color: #aaa; background: transparent; border: none; font-size: 13px; }"
            "QPushButton:hover { color: #ff6b35; }"
        )
        opacity_btn.clicked.connect(self.toggle_opacity)
        bar_layout.addWidget(opacity_btn)

        minimize_btn = QPushButton("—")
        minimize_btn.setFixedSize(22, 22)
        minimize_btn.setStyleSheet(
            "QPushButton { color: #aaa; background: transparent; border: none; font-size: 13px; }"
            "QPushButton:hover { color: #ff6b35; }"
        )
        minimize_btn.clicked.connect(self._on_minimize)
        bar_layout.addWidget(minimize_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet(
            "QPushButton { color: #ff6b35; background: transparent; border: none; font-size: 13px; }"
            "QPushButton:hover { color: #ff4444; }"
        )
        close_btn.clicked.connect(self._on_close)
        bar_layout.addWidget(close_btn)

        parent_layout.addWidget(bar)

    def _panel_btn_style(self, active):
        if active:
            return (
                "QPushButton { color: #ff6b35; background: rgba(139, 0, 0, 150); "
                "border: 1px solid #8b0000; border-radius: 3px; font-weight: bold; }"
                "QPushButton:hover { background: rgba(139, 0, 0, 200); }"
            )
        return (
            "QPushButton { color: #aaa; background: rgba(30, 30, 60, 150); "
            "border: 1px solid #333; border-radius: 3px; }"
            "QPushButton:hover { color: #ff6b35; background: rgba(50, 50, 80, 180); }"
        )

    def _build_stacked_panels(self, parent_layout):
        self._stack = QStackedWidget()

        self._skill_panel = self._build_skill_panel()
        self._paragon_panel = self._build_paragon_panel()
        self._equipment_panel = self._build_equipment_panel()

        self._stack.addWidget(self._skill_panel)
        self._stack.addWidget(self._paragon_panel)
        self._stack.addWidget(self._equipment_panel)

        parent_layout.addWidget(self._stack, 1)

    def _build_skill_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._skill_class_label = QLabel("职业: --")
        self._skill_class_label.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
        self._skill_class_label.setStyleSheet("color: #9b59b6; background: transparent;")
        layout.addWidget(self._skill_class_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: rgba(139, 0, 0, 100);")
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #555; border-radius: 2px; }"
        )

        self._skill_tree_widget = SkillTreeWidget()
        scroll.setWidget(self._skill_tree_widget)
        layout.addWidget(scroll, 1)

        return panel

    def _build_paragon_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._paragon_class_label = QLabel("职业: --")
        self._paragon_class_label.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
        self._paragon_class_label.setStyleSheet("color: #9b59b6; background: transparent;")
        layout.addWidget(self._paragon_class_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: rgba(139, 0, 0, 100);")
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #555; border-radius: 2px; }"
        )

        self._paragon_board_widget = ParagonBoardWidget()
        scroll.setWidget(self._paragon_board_widget)
        layout.addWidget(scroll, 1)

        return panel

    def _build_equipment_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._equip_class_label = QLabel("职业: --")
        self._equip_class_label.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
        self._equip_class_label.setStyleSheet("color: #9b59b6; background: transparent;")
        layout.addWidget(self._equip_class_label)

        self._equip_build_label = QLabel("构筑: --")
        self._equip_build_label.setFont(QFont('Microsoft YaHei', 8))
        self._equip_build_label.setStyleSheet("color: #aaa; background: transparent;")
        layout.addWidget(self._equip_build_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: rgba(139, 0, 0, 100);")
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #555; border-radius: 2px; }"
        )

        self._character_layout = CharacterSilhouetteWidget()
        scroll.setWidget(self._character_layout)
        layout.addWidget(scroll, 1)

        return panel

    def update_skills(self, class_name, skill_data):
        """
        更新技能树可视化

        Args:
            class_name: 职业名
            skill_data: 技能数据 dict，包含各分支技能
        """
        self._class_name = class_name
        self._skill_class_label.setText(f"职业: {class_name or '--'}")

        skills = {}
        if isinstance(skill_data, dict):
            skills = skill_data.get('skills', skill_data)

        if isinstance(skills, list):
            skills = {'技能': skills}

        self._skill_tree_widget.set_skills(skills, class_name)

    def update_paragon(self, class_name, paragon_data):
        """
        更新巅峰盘可视化

        Args:
            class_name: 职业名
            paragon_data: 巅峰数据 dict
        """
        self._paragon_class_label.setText(f"职业: {class_name or '--'}")

        boards = []
        if isinstance(paragon_data, dict):
            boards = paragon_data.get('boards', [])

        if not boards and isinstance(paragon_data, dict):
            aspects = paragon_data.get('aspects', [])
            if aspects:
                boards = [{'name': f'威能盘 {i+1}', 'rare_node': a} for i, a in enumerate(aspects) if isinstance(a, str)]

        self._paragon_board_widget.set_boards(boards, class_name)

    def update_equipment(self, class_name, build_data):
        """
        更新装备布局可视化

        Args:
            class_name: 职业名
            build_data: 构筑数据 dict，包含 equipment/items 列表
        """
        self._equip_class_label.setText(f"职业: {class_name or '--'}")

        title = build_data.get('title', '') if isinstance(build_data, dict) else ''
        self._equip_build_label.setText(f"构筑: {title or '--'}")

        equipment = []
        if isinstance(build_data, dict):
            equipment = build_data.get('equipment', [])
            if not equipment:
                equipment = build_data.get('items', [])

        self._character_layout.set_items(equipment)

    def update_from_build(self, class_name, build_detail):
        """
        从构筑详情数据一次性更新所有面板

        Args:
            class_name: 职业名
            build_detail: 构筑详情 dict
        """
        if not isinstance(build_detail, dict):
            return

        self.update_equipment(class_name, build_detail)

        skill_data = {'skills': build_detail.get('skills', [])}
        self.update_skills(class_name, skill_data)

        paragon_data = {
            'boards': build_detail.get('boards', []),
            'aspects': build_detail.get('aspects', []),
        }
        self.update_paragon(class_name, paragon_data)

    def update_from_search_results(self, results, class_name=None):
        """
        从搜索结果更新叠加层

        Args:
            results: 搜索结果列表
            class_name: 职业名
        """
        if not results:
            return

        for result in results:
            category = result.get('category', '')
            data = result.get('data', {})

            if category == 'build_details':
                self.update_from_build(class_name, data)
                return
            elif category == 'equipment':
                equip_data = {
                    'equipment': [data],
                    'title': data.get('name', '装备推荐'),
                }
                self.update_equipment(class_name, equip_data)
            elif category == 'web_skills':
                skill_data = {
                    'skills': data.get('skills', {}),
                }
                self.update_skills(class_name, skill_data)

    def show_panel(self, panel_name):
        """
        切换面板显示

        Args:
            panel_name: 'skill' / 'paragon' / 'equipment'
        """
        panel_map = {'skill': 0, 'paragon': 1, 'equipment': 2}
        idx = panel_map.get(panel_name, 0)
        self._current_panel = panel_name
        self._stack.setCurrentIndex(idx)

        for key, btn in self._panel_btns.items():
            btn.setStyleSheet(self._panel_btn_style(key == panel_name))

    def toggle_opacity(self):
        """循环切换透明度: 0.85 → 0.5 → 0.2"""
        if self.opacity > 0.7:
            self.opacity = 0.5
        elif self.opacity > 0.3:
            self.opacity = 0.2
        else:
            self.opacity = 0.85
        self.setWindowOpacity(self.opacity)

    def show_at_game_position(self, screen_width=1920, screen_height=1080):
        """定位到游戏画面旁边"""
        cfg = OVERLAY_CONFIG
        position = cfg.get('position', 'right')

        if position == 'right':
            x = screen_width - self.width() - 10
            y = (screen_height - self.height()) // 2
        elif position == 'left':
            x = 10
            y = (screen_height - self.height()) // 2
        elif position == 'top-right':
            x = screen_width - self.width() - 10
            y = 10
        elif position == 'top-left':
            x = 10
            y = 10
        else:
            x = screen_width - self.width() - 10
            y = (screen_height - self.height()) // 2

        self.move(x, y)
        self.show()

    def _on_minimize(self):
        self._container.hide()

    def _on_close(self):
        self.hide()
        self.closed.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
