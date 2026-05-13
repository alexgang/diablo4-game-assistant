#!/usr/bin/env python3

import math
import re

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QScrollArea, QFrame, QGridLayout, QSizePolicy,
)
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QRadialGradient,
    QLinearGradient, QPainterPath, QPixmap, QPolygonF,
)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal

try:
    from config import OVERLAY_CONFIG
except ImportError:
    OVERLAY_CONFIG = {}

RARITY_COLORS = {
    '暗金': '#ff8000', '传奇': '#bf642f', '套装': '#00ff00',
    '稀有': '#ffff00', '魔法': '#4169e1', '普通': '#ffffff',
    '神话暗金': '#ff4444',
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
    '核心': '#ff6b35', 'core': '#ff6b35',
    '防御': '#4169e1', 'defensive': '#4169e1',
    '终极': '#ffd700', 'ultimate': '#ffd700',
    '被动': '#888888', 'passive': '#888888',
    '武器精通': '#cc44ff', 'weapon_mastery': '#cc44ff',
    '火焰': '#ff4444', 'fire': '#ff4444',
    '冰霜': '#44aaff', 'ice': '#44aaff',
    '闪电': '#ffff44', 'lightning': '#ffff44',
    '召唤': '#aa44ff', 'conjuration': '#aa44ff',
    '敏捷': '#44ff44', 'agility': '#44ff44',
    '诡计': '#ff8844', 'subterfuge': '#ff8844',
    '连击': '#ff6b35', 'combo': '#ff6b35',
    '尸体': '#aa44ff', 'corpse': '#aa44ff',
    '鲜血': '#ff4444', 'blood': '#ff4444',
    '骨骼': '#cccccc', 'bone': '#cccccc',
    '大地': '#ff8844', 'earth': '#ff8844',
    '风暴': '#44aaff', 'storm': '#44aaff',
    '狼人': '#ff4444', 'werewolf': '#ff4444',
    '熊人': '#ff8844', 'werebear': '#ff8844',
    '伙伴': '#44ff44', 'companion': '#44ff44',
}

CATEGORY_CN = {
    'core': '核心', 'defensive': '防御', 'ultimate': '终极',
    'passive': '被动', 'weapon_mastery': '武器精通',
    'fire': '火焰', 'ice': '冰霜', 'lightning': '闪电',
    'conjuration': '召唤', 'agility': '敏捷',
    'subterfuge': '诡计', 'combo': '连击',
    'corpse': '尸体', 'blood': '鲜血', 'bone': '骨骼',
    'earth': '大地', 'storm': '风暴', 'werewolf': '狼人',
    'werebear': '熊人', 'companion': '伙伴',
}


class D4SkillTreeWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._skills = {}
        self._class_color = '#ff6b35'
        self._class_name = ''
        self._node_positions = {}
        self._connections = []
        self._categories = []
        self.setMinimumHeight(500)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_skills(self, skills, class_name=''):
        self._skills = skills if isinstance(skills, dict) else {}
        self._class_color = CLASS_COLORS.get(class_name, '#ff6b35')
        self._class_name = class_name
        self._layout_nodes()
        self.update()

    def _parse_skill(self, skill):
        if isinstance(skill, dict):
            return skill.get('name', ''), str(skill.get('points', ''))
        if not isinstance(skill, str):
            return str(skill), ''
        match = re.match(r'(.+?)\s+(\d+)$', skill.strip())
        if match:
            return match.group(1).strip(), match.group(2)
        return skill.strip(), ''

    def _layout_nodes(self):
        self._node_positions = {}
        self._connections = []
        self._categories = []

        if not self._skills:
            return

        w = max(self.width(), 440)
        h = max(self.height(), 500)
        cx, cy = w / 2, 50

        self._node_positions['center'] = {
            'x': cx, 'y': cy, 'name': '基础技能', 'points': '',
            'active': True, 'category': 'center',
        }

        categories = list(self._skills.keys())
        n = len(categories)
        if n == 0:
            return

        branch_length = min(280, h - 120)
        start_angle = -90

        for i, cat in enumerate(categories):
            skill_list = self._skills[cat]
            if not isinstance(skill_list, list):
                continue

            angle_deg = start_angle + (i * 360 / n)
            angle_rad = math.radians(angle_deg)

            cat_cn = CATEGORY_CN.get(cat, cat)
            self._categories.append((cat, cat_cn, angle_deg))

            n_skills = len(skill_list)
            for j, skill in enumerate(skill_list):
                name, points = self._parse_skill(skill)
                dist = 80 + j * 60
                nx = cx + dist * math.cos(angle_rad)
                ny = cy + dist * math.sin(angle_rad)

                key = (cat, j)
                self._node_positions[key] = {
                    'x': nx, 'y': ny, 'name': name, 'points': points,
                    'active': points != '' and points != '0',
                    'category': cat,
                }

                if j == 0:
                    self._connections.append(('center', key))
                else:
                    self._connections.append(((cat, j - 1), key))

    def resizeEvent(self, event):
        super().resizeEvent(event)
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

        for start_key, end_key in self._connections:
            if start_key in self._node_positions and end_key in self._node_positions:
                p1 = self._node_positions[start_key]
                p2 = self._node_positions[end_key]
                both_active = p1.get('active', False) and p2.get('active', False)

                if both_active:
                    glow_pen = QPen(QColor(255, 50, 30, 60), 6)
                    painter.setPen(glow_pen)
                    painter.drawLine(int(p1['x']), int(p1['y']), int(p2['x']), int(p2['y']))
                    line_pen = QPen(QColor(255, 80, 50, 200), 2.5)
                else:
                    line_pen = QPen(QColor(80, 80, 100, 100), 1.5)

                painter.setPen(line_pen)
                painter.drawLine(int(p1['x']), int(p1['y']), int(p2['x']), int(p2['y']))

        for cat, cat_cn, angle_deg in self._categories:
            cat_color = CATEGORY_COLORS.get(cat, '#888888')
            first_key = (cat, 0)
            if first_key in self._node_positions:
                node = self._node_positions[first_key]
                label_x = node['x']
                label_y = node['y'] - 28
                painter.setPen(QColor(cat_color))
                painter.setFont(QFont('Microsoft YaHei', 8, QFont.Bold))
                painter.drawText(QRectF(label_x - 40, label_y - 8, 80, 16),
                                 Qt.AlignCenter, cat_cn)

        for key, node in self._node_positions.items():
            self._draw_skill_node(painter, node)

        painter.end()

    def _draw_skill_node(self, painter, node):
        cx, cy = node['x'], node['y']
        is_active = node.get('active', False)
        is_center = node.get('category') == 'center'
        size = 18 if is_center else 14

        if is_active:
            glow = QRadialGradient(cx, cy, size + 12)
            glow.setColorAt(0, QColor(self._class_color + 'a0'))
            glow.setColorAt(0.6, QColor(self._class_color + '40'))
            glow.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QRectF(cx - size - 12, cy - size - 12,
                                       (size + 12) * 2, (size + 12) * 2))

        if is_center:
            fill = QLinearGradient(cx - size, cy - size, cx + size, cy + size)
            fill.setColorAt(0, QColor(self._class_color))
            fill.setColorAt(1, QColor(self._class_color).darker(150))
            painter.setBrush(QBrush(fill))
            painter.setPen(QPen(QColor(255, 100, 50), 2))
        elif is_active:
            fill = QLinearGradient(cx - size, cy - size, cx + size, cy + size)
            fill.setColorAt(0, QColor(self._class_color).lighter(120))
            fill.setColorAt(1, QColor(self._class_color).darker(130))
            painter.setBrush(QBrush(fill))
            painter.setPen(QPen(QColor(255, 80, 50, 200), 2))
        else:
            painter.setBrush(QBrush(QColor(30, 30, 50)))
            painter.setPen(QPen(QColor(70, 70, 90), 1.5, Qt.DashLine))

        rect = QRectF(cx - size, cy - size, size * 2, size * 2)
        painter.drawRoundedRect(rect, 3, 3)

        if node['points']:
            painter.setPen(QColor(255, 255, 255) if is_active else QColor(120, 120, 120))
            painter.setFont(QFont('Microsoft YaHei', 8, QFont.Bold))
            painter.drawText(rect, Qt.AlignCenter, node['points'])

        painter.setPen(QColor(220, 220, 220) if is_active else QColor(100, 100, 100))
        painter.setFont(QFont('Microsoft YaHei', 7))
        name = node['name']
        if len(name) > 5:
            name = name[:4] + '..'
        painter.drawText(QRectF(cx - 32, cy + size + 2, 64, 14),
                         Qt.AlignCenter, name)


class D4ParagonBoardWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._boards = []
        self._class_color = '#ff6b35'
        self.setMinimumHeight(400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_boards(self, boards, class_name=''):
        self._boards = boards if isinstance(boards, list) else []
        self._class_color = CLASS_COLORS.get(class_name, '#ff6b35')
        self.update()

    def _hex_pointy(self, cx, cy, size):
        points = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            points.append(QPointF(cx + size * math.cos(angle),
                                  cy + size * math.sin(angle)))
        return points

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

        w = max(self.width(), 440)
        cols = 9
        rows = 7
        hex_size = 14
        h_spacing = hex_size * 1.8
        v_spacing = hex_size * 1.55
        board_w = cols * h_spacing
        board_h = rows * v_spacing

        total_boards = len(self._boards)
        boards_per_row = min(total_boards, 2)
        total_w = boards_per_row * board_w + (boards_per_row - 1) * 30
        start_x = max((w - total_w) / 2, 10)
        y_offset = 10

        for board_idx, board in enumerate(self._boards):
            if isinstance(board, dict):
                board_name = board.get('name', f'巅峰盘 {board_idx + 1}')
                rare_node = board.get('rare_node', '')
            else:
                board_name = str(board)
                rare_node = ''

            col_in_row = board_idx % boards_per_row
            row_idx = board_idx // boards_per_row
            bx = start_x + col_in_row * (board_w + 30)
            by = y_offset + row_idx * (board_h + 50)

            painter.setPen(QColor('#ffd700'))
            painter.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
            painter.drawText(int(bx), int(by), board_name)
            by += 18

            center_r = rows // 2
            center_c = cols // 2

            for r in range(rows):
                for c in range(cols):
                    hx = bx + c * h_spacing + (h_spacing / 2 if r % 2 else 0) + h_spacing / 2
                    hy = by + r * v_spacing + v_spacing / 2

                    dist = abs(r - center_r) + abs(c - center_c)
                    is_center = (r == center_r and c == center_c)
                    is_legendary = (dist == 2 and (r + c) % 3 == 0)
                    is_rare = (dist <= 2 and not is_center)
                    is_glyph = (dist == 1 and (r + c) % 4 == 0)

                    if is_center:
                        self._draw_hex(painter, hx, hy, hex_size + 4,
                                       QColor(self._class_color), QColor('#ff6b35'), 2)
                    elif is_legendary:
                        glow = QRadialGradient(hx, hy, hex_size + 6)
                        glow.setColorAt(0, QColor(255, 215, 0, 80))
                        glow.setColorAt(1, QColor(0, 0, 0, 0))
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(QBrush(glow))
                        painter.drawEllipse(QRectF(hx - hex_size - 6, hy - hex_size - 6,
                                                   (hex_size + 6) * 2, (hex_size + 6) * 2))
                        self._draw_hex(painter, hx, hy, hex_size + 2,
                                       QColor(255, 215, 0), QColor('#ffd700'), 2)
                        painter.setPen(QColor('#ffd700'))
                        painter.setFont(QFont('Microsoft YaHei', 6, QFont.Bold))
                        painter.drawText(QRectF(hx - 12, hy - 4, 24, 8), Qt.AlignCenter, "传奇")
                    elif is_glyph:
                        painter.setPen(QPen(QColor(100, 200, 255), 1.5))
                        painter.setBrush(QBrush(QColor(20, 40, 60)))
                        painter.drawEllipse(QRectF(hx - hex_size + 2, hy - hex_size + 2,
                                                   (hex_size - 2) * 2, (hex_size - 2) * 2))
                        painter.setPen(QColor(100, 200, 255))
                        painter.setFont(QFont('Microsoft YaHei', 5))
                        painter.drawText(QRectF(hx - 8, hy - 3, 16, 6), Qt.AlignCenter, "雕纹")
                    elif is_rare:
                        self._draw_hex(painter, hx, hy, hex_size,
                                       QColor(60, 80, 120), QColor('#4488cc'), 1.5)
                    else:
                        self._draw_hex(painter, hx, hy, hex_size - 2,
                                       QColor(35, 35, 50), QColor(60, 60, 80), 1)

            if rare_node:
                painter.setPen(QColor('#4488cc'))
                painter.setFont(QFont('Microsoft YaHei', 7))
                painter.drawText(int(bx), int(by + board_h + 4), f"★ {rare_node}")

            if col_in_row == boards_per_row - 1 or board_idx == total_boards - 1:
                y_offset += board_h + 60

        painter.end()

    def _draw_hex(self, painter, cx, cy, size, fill, border, width=1.5):
        points = self._hex_pointy(cx, cy, size)
        polygon = QPolygonF(points)
        painter.setPen(QPen(border, width))
        painter.setBrush(QBrush(fill))
        painter.drawPolygon(polygon)


class D4EquipmentPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = {}
        self._class_name = ''
        self._build_title = ''
        self._stats = {}
        self.setMinimumHeight(400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_items(self, items, class_name='', build_title=''):
        self._items = {}
        self._class_name = class_name
        self._build_title = build_title
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    slot = item.get('slot', item.get('type', ''))
                    if slot:
                        self._items[slot] = item
        elif isinstance(items, dict):
            self._items = items
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        w = self.width()
        h = self.height()

        stats_w = min(140, w * 0.32)
        equip_x = stats_w + 10
        equip_w = w - stats_w - 20

        self._draw_stats_panel(painter, 4, 4, stats_w - 8, h - 8)
        self._draw_equipment_area(painter, equip_x, 4, equip_w, h - 8)

        painter.end()

    def _draw_stats_panel(self, painter, x, y, w, h):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(15, 12, 25, 200)))
        painter.drawRoundedRect(QRectF(x, y, w, h), 4, 4)

        painter.setPen(QPen(QColor(80, 60, 100, 100), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(QRectF(x, y, w, h), 4, 4)

        ty = y + 8
        painter.setPen(QColor('#ff6b35'))
        painter.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
        painter.drawText(x + 6, ty + 10, "属性面板")
        ty += 18

        painter.setPen(QPen(QColor(80, 60, 100, 80), 1))
        painter.drawLine(x + 6, ty, x + w - 6, ty)
        ty += 6

        stat_items = [
            ("伤害", "1,234", '#ff6b35'),
            ("生命", "8,500", '#44ff44'),
            ("护甲", "3,200", '#4488ff'),
            ("全抗性", "52%", '#aa44ff'),
            ("", "", ''),
            ("暴击率", "32.5%", '#ffff44'),
            ("暴击伤害", "175%", '#ff8844'),
            ("攻速", "1.45", '#44ffaa'),
            ("", "", ''),
            ("伤害减免", "45%", '#4488ff'),
            ("屏障", "2,000", '#66ddff'),
        ]

        for label, value, color in stat_items:
            if not label:
                ty += 6
                continue
            painter.setPen(QColor(150, 150, 160))
            painter.setFont(QFont('Microsoft YaHei', 7))
            painter.drawText(x + 8, ty + 9, label)

            painter.setPen(QColor(color))
            painter.setFont(QFont('Microsoft YaHei', 7, QFont.Bold))
            painter.drawText(x + w - 8 - painter.fontMetrics().width(value), ty + 9, value)
            ty += 16

    def _draw_equipment_area(self, painter, x, y, w, h):
        slot_w = 52
        slot_h = 52
        gap = 6
        col_x = x + (w - slot_w) / 2

        slots_layout = [
            ('头盔', 0),
            ('胸甲', 1),
            ('主手武器', 2),
            ('副手武器', 2),
            ('手套', 3),
            ('裤子', 3),
            ('靴子', 4),
            ('护符', 5),
            ('戒指1', 5),
            ('戒指2', 5),
        ]

        row_slots = {}
        for slot_name, row in slots_layout:
            if row not in row_slots:
                row_slots[row] = []
            row_slots[row].append(slot_name)

        ty = y + 4

        if self._class_name:
            painter.setPen(QColor(CLASS_COLORS.get(self._class_name, '#ff6b35')))
            painter.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
            painter.drawText(x, ty + 10, self._class_name)
        if self._build_title:
            painter.setPen(QColor(150, 150, 160))
            painter.setFont(QFont('Microsoft YaHei', 7))
            painter.drawText(x, ty + 22, self._build_title)
        ty += 30

        for row_idx in sorted(row_slots.keys()):
            slots_in_row = row_slots[row_idx]
            n = len(slots_in_row)
            total_w = n * slot_w + (n - 1) * gap
            sx = x + (w - total_w) / 2

            for i, slot_name in enumerate(slots_in_row):
                item = self._items.get(slot_name, {})
                if not item and slot_name == '主手武器' and '双手武器' in self._items:
                    item = self._items['双手武器']
                self._draw_equip_slot(painter, sx + i * (slot_w + gap), ty,
                                      slot_w, slot_h, slot_name, item)

            ty += slot_h + gap

        skill_bar_y = ty + 10
        painter.setPen(QColor(100, 80, 120, 80))
        painter.setFont(QFont('Microsoft YaHei', 7))
        painter.drawText(x, skill_bar_y, "技能栏")

        skill_bar_y += 14
        skill_w = 38
        skill_h = 38
        n_skills = 6
        total_sw = n_skills * skill_w + (n_skills - 1) * 4
        skill_sx = x + (w - total_sw) / 2

        for i in range(n_skills):
            sx = skill_sx + i * (skill_w + 4)
            painter.setPen(QPen(QColor(60, 60, 80), 1))
            painter.setBrush(QBrush(QColor(20, 20, 35, 180)))
            painter.drawRoundedRect(QRectF(sx, skill_bar_y, skill_w, skill_h), 3, 3)
            painter.setPen(QColor(80, 80, 100))
            painter.setFont(QFont('Microsoft YaHei', 6))
            painter.drawText(QRectF(sx, skill_bar_y, skill_w, skill_h),
                             Qt.AlignCenter, str(i + 1))

    def _draw_equip_slot(self, painter, x, y, w, h, slot_name, item):
        rarity = item.get('rarity', '') if isinstance(item, dict) else ''
        name = item.get('name', '') if isinstance(item, dict) else ''
        rarity_color = RARITY_COLORS.get(rarity, '#ffffff')

        if name:
            if rarity in ('神话暗金',):
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(255, 50, 30, 30)))
                painter.drawRoundedRect(QRectF(x - 2, y - 2, w + 4, h + 4), 5, 5)
                painter.setPen(QPen(QColor(rarity_color), 3))
                painter.setBrush(QBrush(QColor(30, 15, 15, 200)))
                painter.drawRoundedRect(QRectF(x, y, w, h), 4, 4)
                self._draw_corner_ornaments(painter, x, y, w, h, rarity_color)
            elif rarity == '暗金':
                painter.setPen(QPen(QColor(rarity_color), 2.5))
                painter.setBrush(QBrush(QColor(30, 20, 10, 200)))
                painter.drawRoundedRect(QRectF(x, y, w, h), 4, 4)
                painter.setPen(QPen(QColor(rarity_color + '80'), 1))
                painter.drawRoundedRect(QRectF(x + 2, y + 2, w - 4, h - 4), 3, 3)
            elif rarity == '传奇':
                painter.setPen(QPen(QColor(rarity_color), 2))
                painter.setBrush(QBrush(QColor(25, 15, 15, 200)))
                painter.drawRoundedRect(QRectF(x, y, w, h), 4, 4)
            else:
                painter.setPen(QPen(QColor(rarity_color), 1.5))
                painter.setBrush(QBrush(QColor(20, 20, 30, 200)))
                painter.drawRoundedRect(QRectF(x, y, w, h), 4, 4)

            icon = SLOT_DISPLAY.get(slot_name, '')
            painter.setPen(QColor(rarity_color))
            painter.setFont(QFont('Microsoft YaHei', 14))
            painter.drawText(QRectF(x, y + 2, w, h - 16), Qt.AlignCenter, icon)

            display_name = name if len(name) <= 4 else name[:3] + '..'
            painter.setPen(QColor(rarity_color))
            painter.setFont(QFont('Microsoft YaHei', 6, QFont.Bold))
            painter.drawText(QRectF(x, y + h - 16, w, 14), Qt.AlignCenter, display_name)
        else:
            painter.setPen(QPen(QColor(60, 60, 80, 120), 1, Qt.DashLine))
            painter.setBrush(QBrush(QColor(15, 15, 25, 150)))
            painter.drawRoundedRect(QRectF(x, y, w, h), 4, 4)

            icon = SLOT_DISPLAY.get(slot_name, '')
            painter.setPen(QColor(60, 60, 80))
            painter.setFont(QFont('Microsoft YaHei', 10))
            painter.drawText(QRectF(x, y + 4, w, h - 18), Qt.AlignCenter, icon)

            painter.setPen(QColor(60, 60, 80))
            painter.setFont(QFont('Microsoft YaHei', 6))
            painter.drawText(QRectF(x, y + h - 16, w, 14), Qt.AlignCenter, slot_name)

    def _draw_corner_ornaments(self, painter, x, y, w, h, color):
        pen = QPen(QColor(color), 2)
        painter.setPen(pen)
        s = 6
        painter.drawLine(int(x), int(y), int(x + s), int(y))
        painter.drawLine(int(x), int(y), int(x), int(y + s))
        painter.drawLine(int(x + w), int(y), int(x + w - s), int(y))
        painter.drawLine(int(x + w), int(y), int(x + w), int(y + s))
        painter.drawLine(int(x), int(y + h), int(x + s), int(y + h))
        painter.drawLine(int(x), int(y + h), int(x), int(y + h - s))
        painter.drawLine(int(x + w), int(y + h), int(x + w - s), int(y + h))
        painter.drawLine(int(x + w), int(y + h), int(x + w), int(y + h - s))


class GraphicalOverlay(QWidget):

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
        self._container.setObjectName("d4OverlayContainer")
        self._container.setStyleSheet(
            "#d4OverlayContainer {"
            "  background: rgba(8, 8, 20, 210);"
            "  border: 1px solid rgba(139, 0, 0, 160);"
            "  border-radius: 6px;"
            "}"
        )
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(6, 4, 6, 6)
        container_layout.setSpacing(4)

        self._build_control_bar(container_layout)
        self._build_stacked_panels(container_layout)

        main_layout.addWidget(self._container)
        self.setFixedSize(480, 700)
        self.setWindowOpacity(self.opacity)

    def _build_control_bar(self, parent_layout):
        bar = QWidget()
        bar.setStyleSheet("background: rgba(15, 8, 25, 230); border-radius: 3px;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(8, 4, 8, 4)
        bar_layout.setSpacing(4)

        title = QLabel("暗黑助手")
        title.setFont(QFont('Georgia', 12, QFont.Bold))
        title.setStyleSheet("color: #ff6b35; background: transparent;")
        bar_layout.addWidget(title)

        bar_layout.addStretch()

        self._panel_btns = {}
        for key, label in [('skill', '技能'), ('paragon', '巅峰'), ('equipment', '装备')]:
            btn = QPushButton(label)
            btn.setFixedSize(48, 24)
            btn.setFont(QFont('Microsoft YaHei', 9))
            btn.setStyleSheet(self._panel_btn_style(key == self._current_panel))
            btn.clicked.connect(lambda checked, k=key: self.show_panel(k))
            bar_layout.addWidget(btn)
            self._panel_btns[key] = btn

        bar_layout.addSpacing(8)

        opacity_btn = QPushButton("👁")
        opacity_btn.setFixedSize(24, 24)
        opacity_btn.setStyleSheet(
            "QPushButton { color: #aaa; background: transparent; border: none; font-size: 14px; }"
            "QPushButton:hover { color: #ff6b35; }"
        )
        opacity_btn.clicked.connect(self.toggle_opacity)
        bar_layout.addWidget(opacity_btn)

        minimize_btn = QPushButton("—")
        minimize_btn.setFixedSize(24, 24)
        minimize_btn.setStyleSheet(
            "QPushButton { color: #aaa; background: transparent; border: none; font-size: 14px; }"
            "QPushButton:hover { color: #ff6b35; }"
        )
        minimize_btn.clicked.connect(self._on_minimize)
        bar_layout.addWidget(minimize_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(
            "QPushButton { color: #ff6b35; background: transparent; border: none; font-size: 14px; }"
            "QPushButton:hover { color: #ff4444; }"
        )
        close_btn.clicked.connect(self._on_close)
        bar_layout.addWidget(close_btn)

        parent_layout.addWidget(bar)

    def _panel_btn_style(self, active):
        if active:
            return (
                "QPushButton { color: #fff; background: rgba(139, 0, 0, 180); "
                "border: 1px solid #8b0000; border-radius: 3px; font-weight: bold; }"
                "QPushButton:hover { background: rgba(180, 0, 0, 200); }"
            )
        return (
            "QPushButton { color: #999; background: rgba(25, 25, 50, 150); "
            "border: 1px solid #333; border-radius: 3px; }"
            "QPushButton:hover { color: #ff6b35; background: rgba(40, 40, 70, 180); }"
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
        layout.setSpacing(2)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 2, 4, 2)
        self._skill_class_label = QLabel("职业: --")
        self._skill_class_label.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
        self._skill_class_label.setStyleSheet("color: #9b59b6; background: transparent;")
        header_layout.addWidget(self._skill_class_label)
        self._skill_points_label = QLabel("可用技能点: 0")
        self._skill_points_label.setFont(QFont('Microsoft YaHei', 8))
        self._skill_points_label.setStyleSheet("color: #ffd700; background: transparent;")
        header_layout.addWidget(self._skill_points_label)
        header_layout.addStretch()
        layout.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: rgba(139, 0, 0, 80);")
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #555; border-radius: 2px; }"
        )

        self._skill_tree_widget = D4SkillTreeWidget()
        scroll.setWidget(self._skill_tree_widget)
        layout.addWidget(scroll, 1)

        return panel

    def _build_paragon_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self._paragon_class_label = QLabel("职业: --")
        self._paragon_class_label.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
        self._paragon_class_label.setStyleSheet("color: #9b59b6; background: transparent;")
        layout.addWidget(self._paragon_class_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: rgba(139, 0, 0, 80);")
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #555; border-radius: 2px; }"
        )

        self._paragon_board_widget = D4ParagonBoardWidget()
        scroll.setWidget(self._paragon_board_widget)
        layout.addWidget(scroll, 1)

        return panel

    def _build_equipment_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #555; border-radius: 2px; }"
        )

        self._equipment_widget = D4EquipmentPanel()
        scroll.setWidget(self._equipment_widget)
        layout.addWidget(scroll, 1)

        return panel

    def update_skills(self, class_name, skill_data):
        self._class_name = class_name
        self._skill_class_label.setText(f"职业: {class_name or '--'}")
        color = CLASS_COLORS.get(class_name, '#ff6b35')
        self._skill_class_label.setStyleSheet(f"color: {color}; background: transparent;")

        skills = {}
        if isinstance(skill_data, dict):
            skills = skill_data.get('skills', skill_data)

        if isinstance(skills, list):
            skills = {'技能': skills}

        self._skill_tree_widget.set_skills(skills, class_name)

    def update_paragon(self, class_name, paragon_data):
        self._paragon_class_label.setText(f"职业: {class_name or '--'}")
        color = CLASS_COLORS.get(class_name, '#ff6b35')
        self._paragon_class_label.setStyleSheet(f"color: {color}; background: transparent;")

        boards = []
        if isinstance(paragon_data, dict):
            boards = paragon_data.get('boards', [])

        if not boards and isinstance(paragon_data, dict):
            aspects = paragon_data.get('aspects', [])
            if aspects:
                boards = [{'name': f'威能盘 {i+1}', 'rare_node': a}
                          for i, a in enumerate(aspects) if isinstance(a, str)]

        self._paragon_board_widget.set_boards(boards, class_name)

    def update_equipment(self, class_name, build_data):
        title = build_data.get('title', '') if isinstance(build_data, dict) else ''

        equipment = []
        if isinstance(build_data, dict):
            equipment = build_data.get('equipment', [])
            if not equipment:
                equipment = build_data.get('items', [])

        self._equipment_widget.set_items(equipment, class_name, title)

    def update_from_build(self, class_name, build_detail):
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
                skill_data = {'skills': data.get('skills', {})}
                self.update_skills(class_name, skill_data)

    def show_panel(self, panel_name):
        panel_map = {'skill': 0, 'paragon': 1, 'equipment': 2}
        idx = panel_map.get(panel_name, 0)
        self._current_panel = panel_name
        self._stack.setCurrentIndex(idx)

        for key, btn in self._panel_btns.items():
            btn.setStyleSheet(self._panel_btn_style(key == panel_name))

    def toggle_opacity(self):
        if self.opacity > 0.7:
            self.opacity = 0.5
        elif self.opacity > 0.3:
            self.opacity = 0.2
        else:
            self.opacity = 0.85
        self.setWindowOpacity(self.opacity)

    def show_at_game_position(self, screen_width=1920, screen_height=1080):
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
