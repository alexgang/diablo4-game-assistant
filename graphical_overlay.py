#!/usr/bin/env python3

import math
import random
import logging

import numpy as np
import cv2

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QScrollArea, QFrame, QSizePolicy,
)
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QRadialGradient,
    QLinearGradient, QPainterPath, QPixmap, QImage,
)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication

try:
    from screen_capture import ScreenCapture
except ImportError:
    ScreenCapture = None

try:
    from config import OVERLAY_CONFIG
except ImportError:
    OVERLAY_CONFIG = {}

logger = logging.getLogger(__name__)

_BASE_DPI = 1080


def _scale():
    screen = QApplication.primaryScreen()
    if screen:
        h = screen.geometry().height()
        if h > 0:
            return h / _BASE_DPI
    return 1.0


_S = _scale()


def _font(family, size, weight=-1):
    return QFont(family, max(1, round(size * _S)), weight)


def _px(base):
    return max(1, round(base * _S))


RARITY_COLORS = {
    '暗金': '#ff8000', '传奇': '#bf642f', '套装': '#00ff00',
    '稀有': '#ffff00', '魔法': '#4169e1', '普通': '#ffffff',
    '神话暗金': '#ff4444',
}

CLASS_COLORS = {
    '野蛮人': '#ff4444', '法师': '#4488ff', '游侠': '#44ff44',
    '死灵法师': '#aa44ff', '德鲁伊': '#ff8844', '圣骑士': '#ffff44',
}

D4_UI_REGIONS = {
    'skill': {
        '1920x1080': {'x': 260, 'y': 80, 'w': 1400, 'h': 920},
        '1920x1200': {'x': 260, 'y': 100, 'w': 1400, 'h': 1000},
        '2560x1440': {'x': 350, 'y': 110, 'w': 1860, 'h': 1220},
        '3840x2160': {'x': 520, 'y': 160, 'w': 2800, 'h': 1840},
    },
    'paragon': {
        '1920x1080': {'x': 260, 'y': 80, 'w': 1400, 'h': 920},
        '1920x1200': {'x': 260, 'y': 100, 'w': 1400, 'h': 1000},
        '2560x1440': {'x': 350, 'y': 110, 'w': 1860, 'h': 1220},
        '3840x2160': {'x': 520, 'y': 160, 'w': 2800, 'h': 1840},
    },
    'equipment': {
        '1920x1080': {'x': 460, 'y': 60, 'w': 1000, 'h': 960},
        '1920x1200': {'x': 460, 'y': 75, 'w': 1000, 'h': 1050},
        '2560x1440': {'x': 610, 'y': 80, 'w': 1340, 'h': 1280},
        '3840x2160': {'x': 920, 'y': 120, 'w': 2000, 'h': 1920},
    },
}


def _get_ui_region(panel, screen_w, screen_h):
    key = f'{screen_w}x{screen_h}'
    regions = D4_UI_REGIONS.get(panel, {})
    if key in regions:
        return regions[key]
    scale_x = screen_w / 1920
    scale_y = screen_h / 1080
    base = regions.get('1920x1080', {'x': 260, 'y': 80, 'w': 1400, 'h': 920})
    return {
        'x': int(base['x'] * scale_x),
        'y': int(base['y'] * scale_y),
        'w': int(base['w'] * scale_x),
        'h': int(base['h'] * scale_y),
    }


def _cv2_to_qpixmap(cv_img):
    if cv_img is None:
        return QPixmap()
    if len(cv_img.shape) == 2:
        h, w = cv_img.shape
        bytes_per_line = w
    else:
        h, w, ch = cv_img.shape
        if ch == 4:
            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGRA2RGBA)
        elif ch == 3:
            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGBA)
        bytes_per_line = w * 4
    q_img = QImage(cv_img.data, w, h, bytes_per_line, QImage.Format_RGBA8888)
    return QPixmap.fromImage(q_img.copy())


def _draw_highlight_rect(painter, rect, color='#ff6b35', border_width=3, glow_radius=12):
    c = QColor(color)
    for i in range(glow_radius, 0, -2):
        alpha = int(40 * (1 - i / glow_radius))
        painter.setPen(QPen(QColor(c.red(), c.green(), c.blue(), alpha), border_width + i))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(-i, -i, i, i), 4, 4)

    painter.setPen(QPen(c, border_width))
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(rect, 4, 4)


def _draw_recommend_badge(painter, cx, cy, text, color='#ffd700'):
    badge_w = _px(40)
    badge_h = _px(18)
    rect = QRectF(cx - badge_w / 2, cy - badge_h / 2, badge_w, badge_h)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
    painter.drawRoundedRect(rect, 3, 3)

    painter.setPen(QPen(QColor(color), 1.5))
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(rect, 3, 3)

    painter.setPen(QColor(color))
    painter.setFont(_font('Segoe UI', 7, QFont.Bold))
    painter.drawText(rect, Qt.AlignCenter, text)


def _draw_arrow(painter, x1, y1, x2, y2, color='#ffd700', width=2):
    painter.setPen(QPen(QColor(color), width))
    painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    angle = math.atan2(y2 - y1, x2 - x1)
    arrow_len = _px(10)
    arrow_angle = math.pi / 6

    ax = x2 - arrow_len * math.cos(angle - arrow_angle)
    ay = y2 - arrow_len * math.sin(angle - arrow_angle)
    bx = x2 - arrow_len * math.cos(angle + arrow_angle)
    by = y2 - arrow_len * math.sin(angle + arrow_angle)

    path = QPainterPath()
    path.moveTo(x2, y2)
    path.lineTo(ax, ay)
    path.lineTo(bx, by)
    path.closeSubpath()

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(color)))
    painter.drawPath(path)


def _draw_pulse_ring(painter, cx, cy, radius, color='#ff6b35', phase=0):
    c = QColor(color)
    for i in range(3):
        r = radius + i * _px(4) + phase * _px(2)
        alpha = max(10, int(120 * (1 - i / 3) * (0.5 + 0.5 * math.sin(phase + i))))
        painter.setPen(QPen(QColor(c.red(), c.green(), c.blue(), alpha), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), r, r)


def _draw_slot_silhouette(painter, cx, cy, slot_type, size):
    s = size / 2
    path = QPainterPath()

    if slot_type in ('头盔',):
        path.moveTo(cx, cy - s * 0.9)
        path.cubicTo(cx - s * 0.3, cy - s * 0.9, cx - s * 0.7, cy - s * 0.5, cx - s * 0.7, cy - s * 0.2)
        path.lineTo(cx - s * 0.7, cy + s * 0.1)
        path.lineTo(cx + s * 0.7, cy + s * 0.1)
        path.lineTo(cx + s * 0.7, cy - s * 0.2)
        path.cubicTo(cx + s * 0.7, cy - s * 0.5, cx + s * 0.3, cy - s * 0.9, cx, cy - s * 0.9)
        visor = QPainterPath()
        visor.moveTo(cx - s * 0.6, cy - s * 0.15)
        visor.lineTo(cx + s * 0.6, cy - s * 0.15)
        visor.lineTo(cx + s * 0.5, cy + s * 0.05)
        visor.lineTo(cx - s * 0.5, cy + s * 0.05)
        visor.closeSubpath()
        path.addPath(visor)
    elif slot_type in ('胸甲',):
        path.moveTo(cx - s * 0.5, cy - s * 0.7)
        path.lineTo(cx + s * 0.5, cy - s * 0.7)
        path.lineTo(cx + s * 0.6, cy - s * 0.4)
        path.lineTo(cx + s * 0.55, cy + s * 0.5)
        path.lineTo(cx + s * 0.3, cy + s * 0.8)
        path.lineTo(cx - s * 0.3, cy + s * 0.8)
        path.lineTo(cx - s * 0.55, cy + s * 0.5)
        path.lineTo(cx - s * 0.6, cy - s * 0.4)
        path.closeSubpath()
        collar = QPainterPath()
        collar.addEllipse(QPointF(cx, cy - s * 0.7), s * 0.15, s * 0.1)
        path.addPath(collar)
    elif slot_type in ('手套',):
        path.moveTo(cx - s * 0.4, cy + s * 0.6)
        path.lineTo(cx - s * 0.4, cy - s * 0.2)
        path.lineTo(cx - s * 0.35, cy - s * 0.6)
        path.lineTo(cx - s * 0.15, cy - s * 0.7)
        path.lineTo(cx, cy - s * 0.5)
        path.lineTo(cx + s * 0.15, cy - s * 0.7)
        path.lineTo(cx + s * 0.35, cy - s * 0.6)
        path.lineTo(cx + s * 0.4, cy - s * 0.2)
        path.lineTo(cx + s * 0.4, cy + s * 0.6)
        path.closeSubpath()
    elif slot_type in ('裤子',):
        path.moveTo(cx - s * 0.45, cy - s * 0.7)
        path.lineTo(cx + s * 0.45, cy - s * 0.7)
        path.lineTo(cx + s * 0.4, cy + s * 0.0)
        path.lineTo(cx + s * 0.15, cy + s * 0.8)
        path.lineTo(cx + s * 0.05, cy + s * 0.8)
        path.lineTo(cx, cy + s * 0.1)
        path.lineTo(cx - s * 0.05, cy + s * 0.8)
        path.lineTo(cx - s * 0.15, cy + s * 0.8)
        path.lineTo(cx - s * 0.4, cy + s * 0.0)
        path.closeSubpath()
    elif slot_type in ('靴子',):
        path.moveTo(cx - s * 0.3, cy - s * 0.7)
        path.lineTo(cx + s * 0.3, cy - s * 0.7)
        path.lineTo(cx + s * 0.3, cy + s * 0.3)
        path.lineTo(cx + s * 0.7, cy + s * 0.5)
        path.lineTo(cx + s * 0.7, cy + s * 0.7)
        path.lineTo(cx - s * 0.3, cy + s * 0.7)
        path.lineTo(cx - s * 0.3, cy - s * 0.7)
        path.closeSubpath()
    elif slot_type in ('主手武器', '副手武器', '双手武器'):
        path.moveTo(cx, cy - s * 0.9)
        path.lineTo(cx + s * 0.1, cy - s * 0.5)
        path.lineTo(cx + s * 0.4, cy - s * 0.45)
        path.lineTo(cx + s * 0.4, cy - s * 0.3)
        path.lineTo(cx + s * 0.1, cy - s * 0.25)
        path.lineTo(cx + s * 0.08, cy + s * 0.7)
        path.lineTo(cx - s * 0.08, cy + s * 0.7)
        path.lineTo(cx - s * 0.1, cy - s * 0.25)
        path.lineTo(cx - s * 0.4, cy - s * 0.3)
        path.lineTo(cx - s * 0.4, cy - s * 0.45)
        path.lineTo(cx - s * 0.1, cy - s * 0.5)
        path.closeSubpath()
    elif slot_type in ('护符',):
        path.moveTo(cx, cy - s * 0.6)
        path.lineTo(cx + s * 0.3, cy - s * 0.3)
        path.lineTo(cx + s * 0.3, cy + s * 0.1)
        path.lineTo(cx, cy + s * 0.7)
        path.lineTo(cx - s * 0.3, cy + s * 0.1)
        path.lineTo(cx - s * 0.3, cy - s * 0.3)
        path.closeSubpath()
    elif slot_type in ('戒指1', '戒指2', '戒指'):
        path.addEllipse(QPointF(cx, cy), s * 0.5, s * 0.5)
        inner = QPainterPath()
        inner.addEllipse(QPointF(cx, cy), s * 0.3, s * 0.3)
        path -= inner
    else:
        path.addRoundedRect(QRectF(cx - s * 0.5, cy - s * 0.5, s, s), 3, 3)

    painter.drawPath(path)


def _draw_character_silhouette(painter, cx, cy, height, color='#554433'):
    s = height / 2
    c = QColor(color)

    body = QPainterPath()
    head_r = s * 0.12
    body.moveTo(cx, cy - s * 0.85)
    body.addEllipse(QPointF(cx, cy - s * 0.85), head_r, head_r * 1.1)

    neck = QPainterPath()
    neck.moveTo(cx - s * 0.04, cy - s * 0.74)
    neck.lineTo(cx + s * 0.04, cy - s * 0.74)
    neck.lineTo(cx + s * 0.04, cy - s * 0.68)
    neck.lineTo(cx - s * 0.04, cy - s * 0.68)
    neck.closeSubpath()
    body.addPath(neck)

    torso = QPainterPath()
    torso.moveTo(cx - s * 0.2, cy - s * 0.68)
    torso.lineTo(cx + s * 0.2, cy - s * 0.68)
    torso.lineTo(cx + s * 0.22, cy - s * 0.3)
    torso.lineTo(cx + s * 0.18, cy + s * 0.1)
    torso.lineTo(cx - s * 0.18, cy + s * 0.1)
    torso.lineTo(cx - s * 0.22, cy - s * 0.3)
    torso.closeSubpath()
    body.addPath(torso)

    l_arm = QPainterPath()
    l_arm.moveTo(cx - s * 0.2, cy - s * 0.65)
    l_arm.lineTo(cx - s * 0.38, cy - s * 0.3)
    l_arm.lineTo(cx - s * 0.35, cy - s * 0.25)
    l_arm.lineTo(cx - s * 0.18, cy - s * 0.6)
    l_arm.closeSubpath()
    body.addPath(l_arm)

    r_arm = QPainterPath()
    r_arm.moveTo(cx + s * 0.2, cy - s * 0.65)
    r_arm.lineTo(cx + s * 0.38, cy - s * 0.3)
    r_arm.lineTo(cx + s * 0.35, cy - s * 0.25)
    r_arm.lineTo(cx + s * 0.18, cy - s * 0.6)
    r_arm.closeSubpath()
    body.addPath(r_arm)

    l_leg = QPainterPath()
    l_leg.moveTo(cx - s * 0.18, cy + s * 0.1)
    l_leg.lineTo(cx - s * 0.08, cy + s * 0.1)
    l_leg.lineTo(cx - s * 0.1, cy + s * 0.7)
    l_leg.lineTo(cx - s * 0.2, cy + s * 0.7)
    l_leg.closeSubpath()
    body.addPath(l_leg)

    r_leg = QPainterPath()
    r_leg.moveTo(cx + s * 0.08, cy + s * 0.1)
    r_leg.lineTo(cx + s * 0.18, cy + s * 0.1)
    r_leg.lineTo(cx + s * 0.2, cy + s * 0.7)
    r_leg.lineTo(cx + s * 0.1, cy + s * 0.7)
    r_leg.closeSubpath()
    body.addPath(r_leg)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(c.red(), c.green(), c.blue(), 50)))
    painter.drawPath(body)

    painter.setPen(QPen(QColor(c.red(), c.green(), c.blue(), 80), 1))
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(body)


class D4SkillTreeWidget(QWidget):

    _TIER_ORDER = ['基础技能', '核心技能', '特性技能', '终极技能']

    def __init__(self, parent=None):
        super().__init__(parent)
        self._skills = {}
        self._class_name = ''
        self._phase = 0
        self._drag_offset = None
        self._pan_x = 0
        self._pan_y = 0
        self._node_positions = []
        self.setMinimumSize(_px(440), _px(500))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_skills(self, skills, class_name=''):
        if isinstance(skills, dict):
            self._skills = skills
        elif isinstance(skills, list):
            self._skills = {'技能': skills}
        else:
            self._skills = {}
        self._class_name = class_name
        self._node_positions = []
        self.update()

    def _map_to_tiers(self):
        if not self._skills:
            return []
        categories = list(self._skills.keys())
        tier_keywords = [
            ['基础', 'basic'],
            ['核心', 'core'],
            ['防御', '机动', '特性', 'defensive', 'mobility', 'key'],
            ['终极', 'ultimate'],
        ]
        mapped = {}
        unmapped = []
        for cat in categories:
            cat_l = cat.lower()
            matched = False
            for tier_idx, keywords in enumerate(tier_keywords):
                if any(kw in cat_l for kw in keywords):
                    mapped[tier_idx] = cat
                    matched = True
                    break
            if not matched:
                unmapped.append(cat)
        result = []
        for i in range(4):
            if i in mapped:
                result.append((self._TIER_ORDER[i], self._skills.get(mapped[i], [])))
        for cat in unmapped:
            tier_idx = min(len(result), len(self._TIER_ORDER) - 1)
            tier_name = self._TIER_ORDER[tier_idx] if len(result) < len(self._TIER_ORDER) else cat
            result.append((tier_name, self._skills.get(cat, [])))
        if not result:
            for cat in categories:
                result.append((cat, self._skills.get(cat, [])))
        return result

    @staticmethod
    def _parse_skill(skill):
        import re
        name = ''
        points = 0
        max_points = 5
        is_active = False
        if isinstance(skill, str):
            m = re.match(r'(.+?)\s+(\d+)/(\d+)$', skill.strip())
            if m:
                name, points, max_points = m.group(1), int(m.group(2)), int(m.group(3))
            else:
                m = re.match(r'(.+?)\s+(\d+)$', skill.strip())
                if m:
                    name, points = m.group(1), int(m.group(2))
                    max_points = max(points, 5)
                else:
                    name = skill
            is_active = points > 0
        elif isinstance(skill, dict):
            name = skill.get('name', '')
            points = int(skill.get('points', 0))
            max_points = int(skill.get('max_points', skill.get('max', max(points, 5))))
            is_active = skill.get('active', points > 0)
        return name, points, max_points, is_active

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()

        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0, QColor(22, 16, 12, 240))
        bg.setColorAt(0.3, QColor(18, 12, 10, 245))
        bg.setColorAt(0.7, QColor(15, 10, 8, 250))
        bg.setColorAt(1, QColor(22, 16, 12, 240))
        painter.fillRect(self.rect(), bg)

        rng = random.Random(42)
        painter.setPen(Qt.NoPen)
        for _ in range(80):
            tx = rng.randint(0, max(w, 1))
            ty = rng.randint(0, max(h, 1))
            alpha = rng.randint(6, 18)
            painter.setBrush(QBrush(QColor(40, 30, 20, alpha)))
            painter.drawEllipse(QPointF(tx, ty), rng.randint(2, 10), rng.randint(1, 5))

        painter.translate(self._pan_x, self._pan_y)

        if not self._skills:
            painter.setPen(QColor(80, 60, 50))
            painter.setFont(_font('Segoe UI', 10))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "暂无技能数据")
            painter.end()
            return

        cx = w / 2
        class_color = CLASS_COLORS.get(self._class_name, '#ff6b35')
        cc = QColor(class_color)

        tiers = self._map_to_tiers()
        if not tiers:
            painter.end()
            return

        self._node_positions = []

        class_cy = _px(35)
        class_r = _px(22)
        pulse = 0.5 + 0.5 * math.sin(self._phase)

        glow_r = class_r + _px(14 + 5 * pulse)
        class_glow = QRadialGradient(cx, class_cy, glow_r)
        class_glow.setColorAt(0, QColor(cc.red(), cc.green(), cc.blue(), int(130 + 40 * pulse)))
        class_glow.setColorAt(0.5, QColor(cc.red(), cc.green(), cc.blue(), int(50 + 25 * pulse)))
        class_glow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(class_glow))
        painter.drawEllipse(QPointF(cx, class_cy), glow_r, glow_r)

        ds = class_r
        diamond = QPainterPath()
        diamond.moveTo(cx, class_cy - ds)
        diamond.lineTo(cx + ds, class_cy)
        diamond.lineTo(cx, class_cy + ds)
        diamond.lineTo(cx - ds, class_cy)
        diamond.closeSubpath()
        fill = QLinearGradient(cx - ds, class_cy - ds, cx + ds, class_cy + ds)
        fill.setColorAt(0, QColor(min(255, cc.red() + 80), min(255, cc.green() + 80), min(255, cc.blue() + 80), 240))
        fill.setColorAt(1, QColor(min(255, cc.red() + 40), min(255, cc.green() + 40), min(255, cc.blue() + 40), 220))
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(cc, 2))
        painter.drawPath(diamond)

        painter.setPen(QColor(255, 255, 255, 230))
        painter.setFont(_font('Segoe UI', 8, QFont.Bold))
        painter.drawText(QRectF(cx - class_r, class_cy - class_r, class_r * 2, class_r * 2),
                         Qt.AlignCenter, self._class_name[:2] if self._class_name else 'D4')

        tier_top = class_cy + class_r + _px(18)
        available_h = h - tier_top - _px(10)
        tier_h = min(available_h / max(len(tiers), 1), _px(150))

        prev_node_y = class_cy + class_r

        for tier_idx, (tier_name, skills) in enumerate(tiers):
            if not isinstance(skills, list):
                continue

            tier_cy = tier_top + tier_idx * tier_h + tier_h * 0.5

            sep_y = tier_top + tier_idx * tier_h
            sep_grad = QLinearGradient(_px(20), sep_y, w - _px(20), sep_y)
            sep_grad.setColorAt(0, QColor(80, 50, 30, 0))
            sep_grad.setColorAt(0.2, QColor(80, 50, 30, 100))
            sep_grad.setColorAt(0.5, QColor(120, 70, 40, 140))
            sep_grad.setColorAt(0.8, QColor(80, 50, 30, 100))
            sep_grad.setColorAt(1, QColor(80, 50, 30, 0))
            painter.setPen(QPen(QBrush(sep_grad), 1))
            painter.drawLine(int(_px(20)), int(sep_y), int(w - _px(20)), int(sep_y))

            dm = _px(4)
            dm_path = QPainterPath()
            dm_path.moveTo(cx, sep_y - dm)
            dm_path.lineTo(cx + dm, sep_y)
            dm_path.lineTo(cx, sep_y + dm)
            dm_path.lineTo(cx - dm, sep_y)
            dm_path.closeSubpath()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(120, 70, 40, 160)))
            painter.drawPath(dm_path)

            painter.setPen(QColor(180, 150, 100, 220))
            painter.setFont(_font('Segoe UI', 7, QFont.Bold))
            painter.drawText(QRectF(_px(10), sep_y + _px(2), _px(70), _px(14)),
                             Qt.AlignLeft | Qt.AlignVCenter, tier_name)

            tier_has_active = any(self._parse_skill(s)[3] for s in skills) if skills else False

            if tier_has_active:
                for gi in range(4):
                    alpha = max(15, 200 - gi * 50)
                    painter.setPen(QPen(QColor(220, 50, 30, alpha), _px(4 - gi)))
                    painter.drawLine(int(cx), int(prev_node_y + _px(2)), int(cx), int(tier_cy - _px(2)))
                painter.setPen(QPen(QColor(255, 80, 40, 230), _px(1.5)))
                painter.drawLine(int(cx), int(prev_node_y + _px(2)), int(cx), int(tier_cy - _px(2)))

                flow_t = (self._phase * 0.25 + tier_idx * 0.15) % 1.0
                flow_y = prev_node_y + (tier_cy - prev_node_y) * flow_t
                pg = QRadialGradient(cx, flow_y, _px(6))
                pg.setColorAt(0, QColor(255, 120, 60, 200))
                pg.setColorAt(1, QColor(255, 50, 30, 0))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(pg))
                painter.drawEllipse(QPointF(cx, flow_y), _px(6), _px(6))
            else:
                painter.setPen(QPen(QColor(70, 60, 50, 100), _px(1), Qt.DashLine))
                painter.drawLine(int(cx), int(prev_node_y + _px(2)), int(cx), int(tier_cy - _px(2)))

            if not skills:
                prev_node_y = tier_cy
                continue

            parsed = [self._parse_skill(s) for s in skills]
            active_size = _px(40)
            passive_r = _px(10)
            gap = _px(8)

            active_items = [(i, p) for i, p in enumerate(parsed) if p[3]]
            if not active_items:
                active_items = [(0, parsed[0])]
                passive_items = [(i, p) for i, p in enumerate(parsed) if i != 0]
            else:
                passive_items = [(i, p) for i, p in enumerate(parsed) if not p[3]]

            n_act = len(active_items)
            total_act_w = n_act * active_size + (n_act - 1) * gap
            act_start_x = cx - total_act_w / 2

            act_positions = []
            for ai, (orig_i, (name, pts, max_pts, is_a)) in enumerate(active_items):
                ax = act_start_x + ai * (active_size + gap) + active_size / 2
                ay = tier_cy
                act_positions.append((ax, ay, name, pts, max_pts, orig_i))

            for ax, ay, name, pts, max_pts, orig_i in act_positions:
                half = active_size / 2
                p2 = 0.5 + 0.5 * math.sin(self._phase + ax * 0.02)

                gr = half + _px(10 + 4 * p2)
                ng = QRadialGradient(ax, ay, gr)
                ng.setColorAt(0, QColor(cc.red(), cc.green(), cc.blue(), int(110 + 50 * p2)))
                ng.setColorAt(0.5, QColor(cc.red(), cc.green(), cc.blue(), int(40 + 20 * p2)))
                ng.setColorAt(1, QColor(0, 0, 0, 0))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(ng))
                painter.drawEllipse(QPointF(ax, ay), gr, gr)

                rect = QRectF(ax - half, ay - half, active_size, active_size)
                nf = QLinearGradient(ax - half, ay - half, ax + half, ay + half)
                nf.setColorAt(0, QColor(min(255, cc.red() + 100), min(255, cc.green() + 100), min(255, cc.blue() + 100), 240))
                nf.setColorAt(1, QColor(min(255, cc.red() + 50), min(255, cc.green() + 50), min(255, cc.blue() + 50), 220))
                painter.setBrush(QBrush(nf))
                painter.setPen(QPen(cc, 2))
                painter.drawRoundedRect(rect, _px(6), _px(6))

                inner = rect.adjusted(_px(2), _px(2), -_px(2), -_px(2))
                painter.setPen(QPen(QColor(255, 255, 255, 50), 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(inner, _px(4), _px(4))

                if name:
                    painter.setPen(QColor(255, 255, 255, 240))
                    painter.setFont(_font('Segoe UI', 6, QFont.Bold))
                    painter.drawText(rect, Qt.AlignCenter, name[:4])

                if max_pts > 0:
                    painter.setPen(QColor('#ffe44d'))
                    painter.setFont(_font('Segoe UI', 6, QFont.Bold))
                    painter.drawText(QRectF(ax - half, ay + half + _px(2), active_size, _px(12)),
                                     Qt.AlignCenter, f"{pts}/{max_pts}")

                self._node_positions.append({'x': ax, 'y': ay, 'name': name, 'active': True})

            for pi, (orig_i, (name, pts, max_pts, is_a)) in enumerate(passive_items):
                parent_idx = pi % max(len(act_positions), 1)
                pax, pay, _, _, _, _ = act_positions[parent_idx]

                side = 1 if pi % 2 == 0 else -1
                branch_count = sum(1 for pp_i, _ in enumerate(passive_items)
                                   if pp_i < pi and pp_i % max(len(act_positions), 1) == parent_idx)
                h_offset = active_size / 2 + passive_r + _px(6) + branch_count * (passive_r * 2 + _px(4))
                v_offset = _px(12 + branch_count * _px(6))

                px = pax + side * h_offset
                py = pay + side * v_offset * 0.3

                if pts > 0:
                    for gi in range(2):
                        alpha = max(20, 130 - gi * 50)
                        painter.setPen(QPen(QColor(200, 50, 30, alpha), _px(2 - gi * 0.5)))
                        painter.drawLine(int(pax), int(pay), int(px), int(py))
                else:
                    painter.setPen(QPen(QColor(70, 60, 50, 90), _px(1), Qt.DotLine))
                    painter.drawLine(int(pax), int(pay), int(px), int(py))

                if pts > 0:
                    pg2 = QRadialGradient(px, py, passive_r + _px(3))
                    pg2.setColorAt(0, QColor(cc.red(), cc.green(), cc.blue(), 70))
                    pg2.setColorAt(1, QColor(0, 0, 0, 0))
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(pg2))
                    painter.drawEllipse(QPointF(px, py), passive_r + _px(3), passive_r + _px(3))

                    pf = QRadialGradient(px, py, passive_r)
                    pf.setColorAt(0, QColor(min(255, cc.red() + 60), min(255, cc.green() + 60), min(255, cc.blue() + 60), 220))
                    pf.setColorAt(1, QColor(min(255, cc.red() + 20), min(255, cc.green() + 20), min(255, cc.blue() + 20), 200))
                    painter.setBrush(QBrush(pf))
                    painter.setPen(QPen(QColor(cc.red(), cc.green(), cc.blue(), 180), 1.5))
                    painter.drawEllipse(QPointF(px, py), passive_r, passive_r)
                else:
                    pf = QRadialGradient(px, py, passive_r)
                    pf.setColorAt(0, QColor(40, 35, 30, 220))
                    pf.setColorAt(1, QColor(30, 25, 20, 240))
                    painter.setBrush(QBrush(pf))
                    painter.setPen(QPen(QColor(90, 80, 70, 130), 1, Qt.DashLine))
                    painter.drawEllipse(QPointF(px, py), passive_r, passive_r)

                if name:
                    painter.setPen(QColor(200, 190, 170, 220) if pts > 0 else QColor(120, 110, 100, 170))
                    painter.setFont(_font('Segoe UI', 5))
                    painter.drawText(QRectF(px - passive_r, py - passive_r, passive_r * 2, passive_r * 2),
                                     Qt.AlignCenter, name[:3])

                if max_pts > 0:
                    painter.setPen(QColor('#ffe44d') if pts > 0 else QColor(100, 90, 80, 150))
                    painter.setFont(_font('Segoe UI', 5, QFont.Bold))
                    painter.drawText(QRectF(px - passive_r, py + passive_r + _px(1), passive_r * 2, _px(10)),
                                     Qt.AlignCenter, f"{pts}/{max_pts}")

                self._node_positions.append({'x': px, 'y': py, 'name': name, 'active': pts > 0})

            prev_node_y = tier_cy

        self._phase += 0.08
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.pos()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None:
            delta = event.pos() - self._drag_offset
            self._pan_x += delta.x()
            self._pan_y += delta.y()
            self._drag_offset = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None


class D4ParagonBoardWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._boards = []
        self._class_name = ''
        self._phase = 0
        self.setMinimumSize(_px(440), _px(500))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_boards(self, boards, class_name=''):
        self._boards = boards if isinstance(boards, list) else []
        self._class_name = class_name
        self.update()

    def _cross_positions(self, n, bw, bh, gx, gy):
        if n == 0:
            return []
        pos = [(0, 0)]
        if n == 1:
            return pos
        pos.append((0, -(bh + gy)))
        if n == 2:
            return pos
        pos.append((-(bw + gx), -(bh + gy)))
        if n == 3:
            return pos
        pos.append((bw + gx, -(bh + gy)))
        if n == 4:
            return pos
        pos.append((0, -2 * (bh + gy)))
        for i in range(5, n):
            ring = (i - 4 + 2) // 3
            slot = (i - 4) % 3
            col = slot - 1
            pos.append((col * (bw + gx), -(ring + 1) * (bh + gy)))
        return pos

    def _draw_node_normal(self, painter, tx, ty, r):
        painter.setPen(QPen(QColor(100, 95, 110), _px(0.8)))
        painter.setBrush(QBrush(QColor(55, 50, 65, 210)))
        painter.drawEllipse(QPointF(tx, ty), r * 0.7, r * 0.7)

    def _draw_node_magic(self, painter, tx, ty, r):
        painter.setPen(Qt.NoPen)
        glow = QRadialGradient(tx, ty, r * 1.8)
        glow.setColorAt(0, QColor(60, 120, 220, 40))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPointF(tx, ty), r * 1.8, r * 1.8)
        painter.setPen(QPen(QColor(80, 140, 230), _px(1.5)))
        painter.setBrush(QBrush(QColor(35, 55, 100, 230)))
        painter.drawEllipse(QPointF(tx, ty), r * 0.9, r * 0.9)

    def _draw_node_rare(self, painter, tx, ty, r):
        painter.setPen(QPen(QColor(220, 180, 60), _px(1.5)))
        painter.setBrush(QBrush(QColor(50, 40, 25, 230)))
        painter.drawEllipse(QPointF(tx, ty), r * 0.95, r * 0.95)
        d = r * 0.35
        dp = QPainterPath()
        dp.moveTo(tx, ty - d)
        dp.lineTo(tx + d, ty)
        dp.lineTo(tx, ty + d)
        dp.lineTo(tx - d, ty)
        dp.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(220, 180, 60, 200)))
        painter.drawPath(dp)

    def _draw_node_legendary(self, painter, tx, ty, r, board_idx):
        pulse = 0.5 + 0.5 * math.sin(self._phase + board_idx * 1.3)
        glow_r = r * (2.4 + 0.6 * pulse)
        painter.setPen(Qt.NoPen)
        glow = QRadialGradient(tx, ty, glow_r)
        glow.setColorAt(0, QColor(255, 120, 30, int(80 + 60 * pulse)))
        glow.setColorAt(0.3, QColor(255, 80, 20, int(50 + 40 * pulse)))
        glow.setColorAt(0.6, QColor(200, 40, 10, int(30 + 20 * pulse)))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPointF(tx, ty), glow_r, glow_r)
        painter.setPen(QPen(QColor(255, 180, 50), _px(2)))
        painter.setBrush(QBrush(QColor(80, 50, 20, 240)))
        painter.drawEllipse(QPointF(tx, ty), r * 1.1, r * 1.1)
        painter.setPen(QColor(255, 200, 80))
        painter.setFont(_font('Segoe UI', 9, QFont.Bold))
        tr = QRectF(tx - r, ty - r, r * 2, r * 2)
        painter.drawText(tr, Qt.AlignCenter, '★')

    def _draw_node_glyph(self, painter, tx, ty, r, cc):
        painter.setPen(Qt.NoPen)
        glow = QRadialGradient(tx, ty, r * 2.2)
        glow.setColorAt(0, QColor(cc.red(), cc.green(), cc.blue(), 100))
        glow.setColorAt(0.5, QColor(cc.red(), cc.green(), cc.blue(), 40))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPointF(tx, ty), r * 2.2, r * 2.2)
        painter.setPen(QPen(QColor(180, 140, 80), _px(2)))
        painter.setBrush(QBrush(QColor(30, 25, 40, 230)))
        painter.drawEllipse(QPointF(tx, ty), r * 1.3, r * 1.3)
        inner_d = r * 0.55
        dp = QPainterPath()
        dp.moveTo(tx, ty - inner_d)
        dp.lineTo(tx + inner_d, ty)
        dp.lineTo(tx, ty + inner_d)
        dp.lineTo(tx - inner_d, ty)
        dp.closeSubpath()
        painter.setPen(QPen(QColor(200, 60, 60), _px(1)))
        painter.setBrush(QBrush(QColor(180, 50, 50, 200)))
        painter.drawPath(dp)

    def _draw_node_gate(self, painter, tx, ty, r, side):
        painter.setPen(QPen(QColor(180, 140, 70), _px(1.5)))
        painter.setBrush(QBrush(QColor(60, 45, 30, 220)))
        painter.drawEllipse(QPointF(tx, ty), r * 0.85, r * 0.85)
        a = _px(5)
        if side == 'top':
            _draw_arrow(painter, tx, ty + a, tx, ty - a, '#c8963c', 1)
        elif side == 'bottom':
            _draw_arrow(painter, tx, ty - a, tx, ty + a, '#c8963c', 1)
        elif side == 'left':
            _draw_arrow(painter, tx + a, ty, tx - a, ty, '#c8963c', 1)
        else:
            _draw_arrow(painter, tx - a, ty, tx + a, ty, '#c8963c', 1)

    def _draw_glyph_diamond(self, painter, tx, ty, radius):
        dp = QPainterPath()
        dp.moveTo(tx, ty - radius)
        dp.lineTo(tx + radius, ty)
        dp.lineTo(tx, ty + radius)
        dp.lineTo(tx - radius, ty)
        dp.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(200, 40, 40, 25)))
        painter.drawPath(dp)
        painter.setPen(QPen(QColor(200, 50, 50, 60), _px(1), Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(dp)

    def _draw_paths(self, painter, bx, by, rows, cols, spacing, center_r, center_c):
        for r in range(rows):
            for c in range(cols):
                dist = abs(r - center_r) + abs(c - center_c)
                if dist > 2:
                    continue
                tx = bx + c * spacing + spacing / 2
                ty = by + r * spacing + spacing / 2
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        ndist = abs(nr - center_r) + abs(nc - center_c)
                        if ndist <= 2:
                            ntx = bx + nc * spacing + spacing / 2
                            nty = by + nr * spacing + spacing / 2
                            is_main = (r == center_r or c == center_c)
                            if is_main:
                                lc = QColor(255, 200, 100, 180)
                                lw = _px(2.5)
                            else:
                                lc = QColor(200, 160, 80, 100)
                                lw = _px(1.5)
                            painter.setPen(QPen(lc, lw))
                            painter.drawLine(int(tx), int(ty), int(ntx), int(nty))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()

        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0, QColor(20, 14, 28, 245))
        bg.setColorAt(0.3, QColor(14, 9, 20, 250))
        bg.setColorAt(0.7, QColor(16, 11, 23, 250))
        bg.setColorAt(1, QColor(22, 16, 30, 245))
        painter.fillRect(self.rect(), bg)

        painter.setPen(Qt.NoPen)
        step = _px(48)
        for ix in range(0, w + step, step):
            for iy in range(0, h + step, step):
                v = ((ix * 7 + iy * 13) % 37)
                alpha = 3 + (v % 6)
                painter.setBrush(QBrush(QColor(40, 30, 50, alpha)))
                painter.drawRect(ix, iy, step, step)

        if not self._boards:
            painter.setPen(QColor(80, 60, 90))
            painter.setFont(_font('Segoe UI', 10))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "暂无巅峰数据")
            painter.end()
            return

        cols = 9
        rows = 7
        tile_size = _px(16)
        node_r = tile_size / 2
        spacing = tile_size + _px(5)
        board_w = cols * spacing
        board_h = rows * spacing
        n_boards = len(self._boards)
        gap_x = _px(30)
        gap_y = _px(40)
        class_color = CLASS_COLORS.get(self._class_name, '#ff6b35')
        cc = QColor(class_color)

        positions = self._cross_positions(n_boards, board_w, board_h, gap_x, gap_y)

        min_x = min(p[0] for p in positions)
        max_x = max(p[0] + board_w for p in positions)
        min_y = min(p[1] for p in positions)
        max_y = max(p[1] + board_h for p in positions)
        total_w = max_x - min_x
        total_h = max_y - min_y
        ox = (w - total_w) / 2 - min_x
        oy = (h - total_h) / 2 - min_y

        for i in range(n_boards - 1):
            x1 = positions[i][0] + ox + board_w / 2
            y1 = positions[i][1] + oy + board_h / 2
            x2 = positions[i + 1][0] + ox + board_w / 2
            y2 = positions[i + 1][1] + oy + board_h / 2
            conn = QPainterPath()
            conn.moveTo(x1, y1)
            mid_y = (y1 + y2) / 2
            conn.cubicTo(x1, mid_y, x2, mid_y, x2, y2)
            painter.setPen(QPen(QColor(120, 90, 50, 60), _px(2)))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(conn)
            _draw_arrow(painter, (x1 + x2) / 2, mid_y, x2, y2, '#8a6a3a', 1)

        center_r = rows // 2
        center_c = cols // 2

        for board_idx, board in enumerate(self._boards):
            if not isinstance(board, dict):
                continue
            bx = positions[board_idx][0] + ox
            by = positions[board_idx][1] + oy

            pad = _px(8)
            br = QRectF(bx - pad, by - pad, board_w + pad * 2, board_h + pad * 2)

            shadow = QRadialGradient(br.center().x(), br.center().y(),
                                     max(br.width(), br.height()) * 0.7)
            shadow.setColorAt(0, QColor(8, 5, 14, 220))
            shadow.setColorAt(1, QColor(4, 2, 8, 180))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(shadow))
            painter.drawRoundedRect(br, _px(6), _px(6))

            painter.setPen(QPen(QColor(70, 55, 35, 160), _px(1.5)))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(br, _px(6), _px(6))

            inner = br.adjusted(_px(2), _px(2), -_px(2), -_px(2))
            painter.setPen(QPen(QColor(50, 40, 28, 100), _px(1)))
            painter.drawRoundedRect(inner, _px(5), _px(5))

            board_name = board.get('name', f'巅峰盘 {board_idx + 1}')
            name_rect = QRectF(bx - pad, by - pad - _px(20), board_w + pad * 2, _px(18))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(10, 7, 16, 200)))
            painter.drawRoundedRect(name_rect, _px(3), _px(3))
            painter.setPen(QColor(210, 180, 120))
            painter.setFont(_font('Segoe UI', 8, QFont.Bold))
            painter.drawText(name_rect, Qt.AlignCenter, board_name)

            rotation = board.get('rotation', 0)
            if rotation:
                rot_text = f'↻{rotation}°'
                painter.setPen(QColor(140, 120, 80))
                painter.setFont(_font('Segoe UI', 6))
                rr = QRectF(bx + board_w - _px(30), by - pad - _px(18), _px(28), _px(14))
                painter.drawText(rr, Qt.AlignCenter, rot_text)

            self._draw_paths(painter, bx, by, rows, cols, spacing, center_r, center_c)

            glyph_tx = bx + center_c * spacing + spacing / 2
            glyph_ty = by + center_r * spacing + spacing / 2
            self._draw_glyph_diamond(painter, glyph_tx, glyph_ty, 3.2 * spacing)

            for r in range(rows):
                for c in range(cols):
                    tx = bx + c * spacing + spacing / 2
                    ty = by + r * spacing + spacing / 2
                    dist = abs(r - center_r) + abs(c - center_c)
                    is_center = (r == center_r and c == center_c)
                    is_gate = (dist == 3 and
                               (r == 0 or r == rows - 1 or c == 0 or c == cols - 1))
                    is_legendary = (dist == 3 and not is_gate and (r + c) % 3 == 0)
                    is_rare = (dist == 2 and not is_legendary and not is_gate)
                    is_magic = (dist == 1 and not is_center)

                    if is_center:
                        self._draw_node_glyph(painter, tx, ty, node_r, cc)
                    elif is_gate:
                        if r == 0:
                            side = 'top'
                        elif r == rows - 1:
                            side = 'bottom'
                        elif c == 0:
                            side = 'left'
                        else:
                            side = 'right'
                        self._draw_node_gate(painter, tx, ty, node_r, side)
                    elif is_legendary:
                        self._draw_node_legendary(painter, tx, ty, node_r, board_idx)
                    elif is_rare:
                        self._draw_node_rare(painter, tx, ty, node_r)
                    elif is_magic:
                        self._draw_node_magic(painter, tx, ty, node_r)
                    else:
                        self._draw_node_normal(painter, tx, ty, node_r)

        self._phase += 0.08
        painter.end()


class D4EquipmentPanel(QWidget):

    _SLOT_SILHOUETTE_MAP = {
        '远程武器': '主手武器',
        '双持武器1': '主手武器',
        '双持武器2': '副手武器',
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = {}
        self._class_name = ''
        self._title = ''
        self._phase = 0
        self.setMinimumSize(_px(520), _px(580))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_items(self, items, class_name='', title=''):
        self._items = items if isinstance(items, (list, dict)) else {}
        self._class_name = class_name
        self._title = title
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()

        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0, QColor(18, 12, 8, 245))
        bg.setColorAt(0.3, QColor(12, 8, 5, 250))
        bg.setColorAt(0.7, QColor(15, 10, 6, 250))
        bg.setColorAt(1, QColor(18, 12, 8, 245))
        painter.fillRect(self.rect(), bg)

        painter.setPen(Qt.NoPen)
        for i in range(0, h, _px(40)):
            alpha = 8 + int(6 * math.sin(i * 0.1))
            painter.setBrush(QBrush(QColor(40, 30, 20, alpha)))
            painter.drawRect(0, i, w, _px(1))

        items = self._items
        if isinstance(items, dict):
            items = list(items.values())
        if not isinstance(items, list):
            items = []

        if not items:
            painter.setPen(QColor(100, 80, 60))
            painter.setFont(_font('Segoe UI', 10))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "暂无装备数据")
            painter.end()
            return

        stats_w = _px(130)
        skill_bar_h = _px(56)
        margin = _px(10)

        equip_area_w = w - stats_w - margin * 3
        equip_area_h = h - skill_bar_h - margin * 2
        equip_area_x = margin
        equip_area_y = margin

        if self._title:
            painter.setPen(QColor(200, 180, 140))
            painter.setFont(_font('Segoe UI', 10, QFont.Bold))
            painter.drawText(QRectF(equip_area_x, _px(2), equip_area_w, _px(20)),
                             Qt.AlignCenter, self._title)

        left_slots = ['头盔', '胸甲', '手套', '裤子', '靴子', '远程武器']
        right_slots = ['护符', '戒指1', '戒指2', '双持武器1', '双持武器2']

        slot_size = _px(48)
        slot_gap = _px(8)
        name_w = _px(80)
        row_h = slot_size + slot_gap

        left_col_x = equip_area_x + _px(8)
        right_col_x = equip_area_x + equip_area_w - slot_size - name_w - _px(8)
        center_x = equip_area_x + equip_area_w / 2

        char_h = min(equip_area_h - _px(40), _px(260))
        char_cy = equip_area_y + char_h / 2 + _px(20)

        _draw_character_silhouette(painter, center_x, char_cy, char_h, QColor(60, 45, 30))

        overlay = QRadialGradient(center_x, char_cy, char_h * 0.6)
        overlay.setColorAt(0, QColor(30, 20, 10, 40))
        overlay.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(overlay))
        painter.drawEllipse(QPointF(center_x, char_cy), char_h * 0.6, char_h * 0.6)

        item_by_slot = {}
        for item in items:
            if isinstance(item, dict):
                slot = item.get('slot', item.get('type', ''))
                item_by_slot[slot] = item

        left_start_y = equip_area_y + _px(24)
        for i, slot_name in enumerate(left_slots):
            sy = left_start_y + i * row_h
            item_data = item_by_slot.get(slot_name, {})
            self._draw_equip_slot(painter, left_col_x, sy, slot_size, slot_size,
                                  slot_name, item_data, name_w)

        right_start_y = equip_area_y + _px(24)
        for i, slot_name in enumerate(right_slots):
            sy = right_start_y + i * row_h
            item_data = item_by_slot.get(slot_name, {})
            self._draw_equip_slot(painter, right_col_x, sy, slot_size, slot_size,
                                  slot_name, item_data, name_w)

        stats_x = w - stats_w - margin
        stats_y = margin
        stats_h = h - skill_bar_h - margin * 2
        self._draw_stats_panel(painter, stats_x, stats_y, stats_w, stats_h, items)

        skill_bar_y = h - skill_bar_h
        skill_keys = ['1', '2', '3', '4', 'L', 'R']
        skill_slot_size = _px(40)
        skill_gap = _px(6)
        n_skills = len(skill_keys)
        total_skill_w = n_skills * skill_slot_size + (n_skills - 1) * skill_gap
        skill_start_x = equip_area_x + (equip_area_w - total_skill_w) / 2

        painter.setPen(QColor(120, 100, 70, 150))
        painter.setFont(_font('Segoe UI', 7))
        painter.drawText(QRectF(equip_area_x, skill_bar_y - _px(14), equip_area_w, _px(12)),
                         Qt.AlignCenter, '技能栏')

        bar_bg = QRectF(skill_start_x - _px(6), skill_bar_y - _px(2),
                        total_skill_w + _px(12), skill_slot_size + _px(4))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(10, 8, 5, 180)))
        painter.drawRoundedRect(bar_bg, 4, 4)
        painter.setPen(QPen(QColor(80, 60, 30, 100), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(bar_bg, 4, 4)

        for i, key in enumerate(skill_keys):
            sx = skill_start_x + i * (skill_slot_size + skill_gap)
            rect = QRectF(sx, skill_bar_y, skill_slot_size, skill_slot_size)

            slot_bg = QLinearGradient(sx, skill_bar_y, sx, skill_bar_y + skill_slot_size)
            slot_bg.setColorAt(0, QColor(25, 20, 12, 200))
            slot_bg.setColorAt(1, QColor(15, 12, 8, 200))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(slot_bg))
            painter.drawRoundedRect(rect, 3, 3)

            painter.setPen(QPen(QColor(90, 70, 40, 160), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 3, 3)

            key_rect = QRectF(sx + _px(2), skill_bar_y + _px(2), _px(14), _px(12))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
            painter.drawRoundedRect(key_rect, 2, 2)
            painter.setPen(QColor(180, 160, 120))
            painter.setFont(_font('Segoe UI', 6, QFont.Bold))
            painter.drawText(key_rect, Qt.AlignCenter, key)

        self._phase += 0.08
        painter.end()

    def _draw_stats_panel(self, painter, x, y, w, h, items):
        painter.setPen(Qt.NoPen)
        bg = QLinearGradient(x, y, x, y + h)
        bg.setColorAt(0, QColor(15, 10, 6, 220))
        bg.setColorAt(0.5, QColor(10, 7, 4, 230))
        bg.setColorAt(1, QColor(15, 10, 6, 220))
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(QRectF(x, y, w, h), 5, 5)

        painter.setPen(QPen(QColor(80, 60, 30, 120), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(QRectF(x, y, w, h), 5, 5)

        inner = QRectF(x + _px(2), y + _px(2), w - _px(4), h - _px(4))
        painter.setPen(QPen(QColor(50, 38, 20, 80), 1))
        painter.drawRoundedRect(inner, 4, 4)

        painter.setPen(QColor(200, 175, 120, 230))
        painter.setFont(_font('Segoe UI', 9, QFont.Bold))
        painter.drawText(QRectF(x + _px(8), y + _px(8), w - _px(16), _px(18)),
                         Qt.AlignLeft, '属性')

        sep_y = y + _px(28)
        painter.setPen(QPen(QColor(80, 60, 30, 100), 1))
        painter.drawLine(int(x + _px(8)), int(sep_y), int(x + w - _px(8)), int(sep_y))

        attrs = [
            ('力量', 0), ('智力', 0), ('敏捷', 0), ('意志', 0),
            ('暴击率', 0), ('暴击伤害', 0), ('攻速', 0),
        ]

        for item in items:
            if isinstance(item, dict):
                for attr_name in ['力量', '智力', '敏捷', '意志', '暴击率', '暴击伤害', '攻速']:
                    val = item.get(attr_name, item.get(attr_name.lower(), 0))
                    if val:
                        for i, (a, v) in enumerate(attrs):
                            if a == attr_name:
                                attrs[i] = (attr_name, v + (val if isinstance(val, (int, float)) else 0))
                                break

        ay = sep_y + _px(8)
        for attr_name, val in attrs:
            painter.setPen(QColor(160, 145, 110))
            painter.setFont(_font('Segoe UI', 7))
            painter.drawText(QRectF(x + _px(10), ay, w * 0.55, _px(14)),
                             Qt.AlignLeft | Qt.AlignVCenter, attr_name)

            val_color = QColor(255, 220, 100) if val > 0 else QColor(90, 75, 55)
            painter.setPen(val_color)
            painter.setFont(_font('Segoe UI', 7, QFont.Bold))
            val_text = str(val) if val else '-'
            painter.drawText(QRectF(x + w * 0.55, ay, w * 0.4, _px(14)),
                             Qt.AlignRight | Qt.AlignVCenter, val_text)
            ay += _px(18)

        if self._class_name:
            class_color = CLASS_COLORS.get(self._class_name, '#ff6b35')
            cc = QColor(class_color)
            painter.setPen(QColor(cc.red(), cc.green(), cc.blue(), 180))
            painter.setFont(_font('Segoe UI', 8, QFont.Bold))
            painter.drawText(QRectF(x + _px(8), y + h - _px(24), w - _px(16), _px(18)),
                             Qt.AlignCenter, self._class_name)

    def _draw_equip_slot(self, painter, x, y, sw, sh, slot_name, item_data, name_w=0):
        rect = QRectF(x, y, sw, sh)
        rarity = item_data.get('rarity', '') if isinstance(item_data, dict) else ''
        name = item_data.get('name', '') if isinstance(item_data, dict) else ''
        rarity_color = RARITY_COLORS.get(rarity, '#555')
        rc = QColor(rarity_color)

        slot_bg = QLinearGradient(x, y, x + sw, y + sh)
        slot_bg.setColorAt(0, QColor(20, 16, 10, 220))
        slot_bg.setColorAt(1, QColor(14, 10, 6, 220))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(slot_bg))
        painter.drawRoundedRect(rect, 3, 3)

        if rarity == '神话暗金':
            pulse = 0.5 + 0.5 * math.sin(self._phase * 2)
            for gi in range(4):
                alpha = max(15, int((120 - gi * 30) * (0.6 + 0.4 * pulse)))
                painter.setPen(QPen(QColor(255, 60, 40, alpha), _px(3 - gi * 0.5)))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(rect.adjusted(-_px(2 + gi), -_px(2 + gi),
                                                       _px(2 + gi), _px(2 + gi)), 4, 4)

            bg_grad = QLinearGradient(x, y, x + sw, y + sh)
            bg_grad.setColorAt(0, QColor(100, 20, 15, 240))
            bg_grad.setColorAt(1, QColor(70, 15, 20, 240))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(bg_grad))
            painter.drawRoundedRect(rect, 3, 3)

            crown_h = _px(10)
            crown_path = QPainterPath()
            crown_path.moveTo(x + sw * 0.15, y)
            crown_path.lineTo(x + sw * 0.2, y - crown_h)
            crown_path.lineTo(x + sw * 0.35, y - crown_h * 0.4)
            crown_path.lineTo(x + sw * 0.5, y - crown_h * 1.1)
            crown_path.lineTo(x + sw * 0.65, y - crown_h * 0.4)
            crown_path.lineTo(x + sw * 0.8, y - crown_h)
            crown_path.lineTo(x + sw * 0.85, y)
            painter.setPen(QPen(QColor(255, 80, 40), 1))
            painter.setBrush(QBrush(QColor(255, 80, 40, 180)))
            painter.drawPath(crown_path)

            for gem_x_ratio in [0.2, 0.5, 0.8]:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(255, 200, 60, 220)))
                painter.drawEllipse(QPointF(x + sw * gem_x_ratio, y - crown_h * 0.7),
                                    _px(1.5), _px(1.5))

            corner_len = _px(7)
            for cx, cy, dx, dy in [(x, y, 1, 1), (x + sw, y, -1, 1),
                                    (x, y + sh, 1, -1), (x + sw, y + sh, -1, -1)]:
                path = QPainterPath()
                path.moveTo(cx, cy)
                path.cubicTo(cx + dx * corner_len * 0.3, cy + dy * corner_len * 0.8,
                             cx + dx * corner_len * 0.8, cy + dy * corner_len * 0.3,
                             cx + dx * corner_len, cy + dy * corner_len)
                painter.setPen(QPen(QColor(255, 100, 50), 1.5))
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(path)

                for dot_i in range(3):
                    dot_x = cx + dx * _px(2 + dot_i * 2)
                    dot_y = cy + dy * _px(2 + dot_i * 2)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(QColor(255, 100, 50, 180)))
                    painter.drawEllipse(QPointF(dot_x, dot_y), _px(1), _px(1))

        elif rarity == '暗金':
            glow = QRadialGradient(x + sw / 2, y + sh / 2, max(sw, sh) * 0.8)
            glow.setColorAt(0, QColor(255, 140, 30, 40))
            glow.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QPointF(x + sw / 2, y + sh / 2), sw * 0.8, sh * 0.8)

            bg_grad = QLinearGradient(x, y, x, y + sh)
            bg_grad.setColorAt(0, QColor(90, 55, 15, 240))
            bg_grad.setColorAt(1, QColor(70, 40, 10, 240))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(bg_grad))
            painter.drawRoundedRect(rect, 3, 3)

            painter.setPen(QPen(QColor(255, 160, 40), 2.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 3, 3)
            inner = rect.adjusted(_px(3), _px(3), -_px(3), -_px(3))
            painter.setPen(QPen(QColor(255, 160, 40, 160), 1))
            painter.drawRoundedRect(inner, 2, 2)

            bracket_len = _px(6)
            for cx, cy, dx, dy in [(x, y, 1, 1), (x + sw, y, -1, 1),
                                    (x, y + sh, 1, -1), (x + sw, y + sh, -1, -1)]:
                painter.setPen(QPen(QColor(255, 160, 40), 1.5))
                painter.drawLine(int(cx), int(cy), int(cx + dx * bracket_len), int(cy))
                painter.drawLine(int(cx), int(cy), int(cx), int(cy + dy * bracket_len))

                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(255, 160, 40, 170)))
                painter.drawEllipse(QPointF(cx + dx * _px(2), cy + dy * _px(2)), _px(1), _px(1))

        elif rarity == '传奇':
            glow = QRadialGradient(x + sw / 2, y + sh / 2, max(sw, sh))
            glow.setColorAt(0, QColor(rc.red(), rc.green(), rc.blue(), 35))
            glow.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QPointF(x + sw / 2, y + sh / 2), sw, sh)

            bg_grad = QLinearGradient(x, y, x + sw, y + sh)
            bg_grad.setColorAt(0, QColor(60, 38, 18, 240))
            bg_grad.setColorAt(1, QColor(45, 28, 12, 240))
            painter.setBrush(QBrush(bg_grad))
            painter.drawRoundedRect(rect, 3, 3)

            painter.setPen(QPen(QColor(210, 130, 50), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 3, 3)

            tick_len = _px(5)
            for cx, cy, dx, dy in [(x, y, 1, 1), (x + sw, y, -1, 1),
                                    (x, y + sh, 1, -1), (x + sw, y + sh, -1, -1)]:
                painter.setPen(QPen(QColor(210, 130, 50), 1))
                painter.drawLine(int(cx), int(cy), int(cx + dx * tick_len), int(cy))
                painter.drawLine(int(cx), int(cy), int(cx), int(cy + dy * tick_len))

        elif rarity == '稀有':
            painter.setPen(QPen(QColor(255, 255, 100), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 3, 3)
        else:
            painter.setPen(QPen(QColor(60, 50, 35, 180), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 3, 3)

        silhouette_color = rarity_color if rarity else '#5a5a50'
        sc = QColor(silhouette_color)
        bright_silhouette = QColor(min(255, sc.red() + 60), min(255, sc.green() + 60),
                                   min(255, sc.blue() + 60))
        painter.setPen(QPen(bright_silhouette, 1))
        painter.setBrush(QBrush(QColor(bright_silhouette.red(), bright_silhouette.green(),
                                       bright_silhouette.blue(), 220)))
        sil_slot = self._SLOT_SILHOUETTE_MAP.get(slot_name, slot_name)
        _draw_slot_silhouette(painter, x + sw / 2, y + sh / 2 - _px(4), sil_slot, min(sw, sh) * 0.6)

        if name_w > 0 and name:
            name_x = x + sw + _px(6)
            name_y = y + sh / 2 - _px(8)
            painter.setPen(QColor(rarity_color))
            painter.setFont(_font('Segoe UI', 7, QFont.Bold))
            display = name if len(name) <= 8 else name[:7] + '..'
            painter.drawText(QRectF(name_x, name_y, name_w, _px(14)),
                             Qt.AlignLeft | Qt.AlignVCenter, display)

            painter.setPen(QColor(100, 85, 60))
            painter.setFont(_font('Segoe UI', 6))
            painter.drawText(QRectF(name_x, name_y + _px(13), name_w, _px(12)),
                             Qt.AlignLeft | Qt.AlignVCenter, slot_name)
        elif name:
            painter.setPen(QColor(rarity_color))
            painter.setFont(_font('Segoe UI', 6, QFont.Bold))
            display = name if len(name) <= 5 else name[:4] + '..'
            painter.drawText(QRectF(x, y + sh - _px(14), sw, _px(14)),
                             Qt.AlignCenter, display)

        if rarity in ('神话暗金', '暗金'):
            _draw_recommend_badge(painter, x + sw / 2, y - _px(10), '推荐', rarity_color)
        elif rarity == '传奇':
            _draw_recommend_badge(painter, x + sw / 2, y - _px(8), '推荐', rarity_color)


class GameCapturePanel(QWidget):

    def __init__(self, panel_type='skill', parent=None):
        super().__init__(parent)
        self._panel_type = panel_type
        self._bg_pixmap = QPixmap()
        self._annotations = []
        self._capture = None
        self._auto_capture = False
        self._capture_interval = 2000
        self._phase = 0
        self._class_name = ''
        self._skill_data = {}
        self._paragon_data = {}
        self._equipment_data = {}

        self.setMinimumHeight(_px(400))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if panel_type == 'skill':
            self._paint_widget = D4SkillTreeWidget()
        elif panel_type == 'paragon':
            self._paint_widget = D4ParagonBoardWidget()
        elif panel_type == 'equipment':
            self._paint_widget = D4EquipmentPanel()
        else:
            self._paint_widget = D4SkillTreeWidget()

        layout.addWidget(self._paint_widget)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer)

    def init_capture(self, screen_capture=None):
        if screen_capture:
            self._capture = screen_capture
        elif ScreenCapture is not None:
            try:
                self._capture = ScreenCapture()
            except Exception as e:
                logger.warning(f"屏幕捕获初始化失败: {e}")

    def set_auto_capture(self, enabled, interval_ms=2000):
        self._auto_capture = enabled
        self._capture_interval = interval_ms
        if enabled:
            self._timer.start(interval_ms)
        else:
            self._timer.stop()

    def capture_game_ui(self):
        if self._capture is None:
            logger.debug("屏幕捕获未初始化")
            return False

        try:
            mon = self._capture.game_monitor
            if not mon:
                return False

            screen_w = mon['width']
            screen_h = mon['height']

            region = _get_ui_region(self._panel_type, screen_w, screen_h)
            capture_region = {
                'top': mon['top'] + region['y'],
                'left': mon['left'] + region['x'],
                'width': region['w'],
                'height': region['h'],
            }

            img = self._capture.capture_region(capture_region)
            if img is not None and img.size > 0:
                self._bg_pixmap = _cv2_to_qpixmap(img)
                self._rebuild_annotations()
                self._paint_widget.hide()
                self.update()
                return True
        except Exception as e:
            logger.debug(f"游戏UI捕获失败: {e}")

        return False

    def clear_capture(self):
        self._bg_pixmap = QPixmap()
        self._annotations = []
        self._paint_widget.show()
        self.update()

    def set_skill_data(self, skills, class_name=''):
        self._skill_data = skills if isinstance(skills, dict) else {}
        self._class_name = class_name
        if isinstance(self._paint_widget, D4SkillTreeWidget):
            self._paint_widget.set_skills(skills, class_name)
        self._rebuild_annotations()
        self.update()

    def set_paragon_data(self, boards, class_name=''):
        self._paragon_data = boards if isinstance(boards, list) else []
        self._class_name = class_name
        if isinstance(self._paint_widget, D4ParagonBoardWidget):
            self._paint_widget.set_boards(boards, class_name)
        self._rebuild_annotations()
        self.update()

    def set_equipment_data(self, items, class_name='', title=''):
        self._equipment_data = items if isinstance(items, (list, dict)) else {}
        self._class_name = class_name
        if isinstance(self._paint_widget, D4EquipmentPanel):
            self._paint_widget.set_items(items, class_name, title)
        self._rebuild_annotations()
        self.update()

    def _rebuild_annotations(self):
        self._annotations = []

        if self._panel_type == 'skill':
            self._build_skill_annotations()
        elif self._panel_type == 'paragon':
            self._build_paragon_annotations()
        elif self._panel_type == 'equipment':
            self._build_equipment_annotations()

    def _build_skill_annotations(self):
        if not self._skill_data or self._bg_pixmap.isNull():
            return

        w = max(self.width(), 440)
        h = max(self.height(), 400)

        n_skills = sum(len(v) for v in self._skill_data.values() if isinstance(v, list))
        n_recommended = 0
        for skills in self._skill_data.values():
            if isinstance(skills, list):
                for s in skills:
                    pts = ''
                    if isinstance(s, str):
                        import re
                        m = re.match(r'.+?\s+(\d+)$', s.strip())
                        if m:
                            pts = m.group(1)
                    elif isinstance(s, dict):
                        pts = str(s.get('points', ''))
                    if pts and pts != '0':
                        n_recommended += 1

        if n_recommended > 0:
            self._annotations.append({
                'type': 'text_overlay',
                'x': w - _px(10),
                'y': _px(10),
                'text': f'推荐加点: {n_recommended}/{n_skills}',
                'color': '#ffd700',
                'anchor': 'top-right',
            })

    def _build_paragon_annotations(self):
        if not self._paragon_data or self._bg_pixmap.isNull():
            return

        w = max(self.width(), 440)
        h = max(self.height(), 400)

        n_boards = len(self._paragon_data)
        if n_boards > 0:
            self._annotations.append({
                'type': 'text_overlay',
                'x': w - _px(10),
                'y': _px(10),
                'text': f'推荐巅峰盘: {n_boards}个',
                'color': '#ffd700',
                'anchor': 'top-right',
            })

    def _build_equipment_annotations(self):
        if not self._equipment_data or self._bg_pixmap.isNull():
            return

        w = max(self.width(), 440)
        h = max(self.height(), 400)

        items = self._equipment_data
        if isinstance(items, dict):
            items = list(items.values())
        if not isinstance(items, list):
            return

        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get('name', '')
            rarity = item.get('rarity', '')
            rarity_color = RARITY_COLORS.get(rarity, '#ffffff')
            self._annotations.append({
                'type': 'equip_marker',
                'x': 0, 'y': 0,
                'color': rarity_color,
                'label': name,
                'rarity': rarity,
            })

        if items:
            self._annotations.append({
                'type': 'text_overlay',
                'x': w - _px(10),
                'y': _px(10),
                'text': f'推荐装备: {len(items)}件',
                'color': '#ffd700',
                'anchor': 'top-right',
            })

    def _on_timer(self):
        self.capture_game_ui()

    def paintEvent(self, event):
        if self._bg_pixmap.isNull():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        scaled = self._bg_pixmap.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x_offset = (w - scaled.width()) // 2
        y_offset = (h - scaled.height()) // 2
        painter.drawPixmap(x_offset, y_offset, scaled)

        dim = QColor(0, 0, 0, 60)
        painter.fillRect(self.rect(), dim)

        self._phase += 0.15
        self._draw_annotations(painter)

        painter.end()

    def _draw_annotations(self, painter):
        for ann in self._annotations:
            ann_type = ann.get('type', '')

            if ann_type == 'highlight_node':
                self._draw_highlight_node(painter, ann)
            elif ann_type == 'equip_slot':
                self._draw_equip_slot_annotation(painter, ann)
            elif ann_type == 'equip_marker':
                pass
            elif ann_type == 'text_overlay':
                self._draw_text_overlay(painter, ann)

    def _draw_highlight_node(self, painter, ann):
        cx, cy = ann['x'], ann['y']
        radius = ann.get('radius', _px(14))
        color = ann.get('color', '#ff6b35')
        label = ann.get('label', '')
        points = ann.get('points', '')

        _draw_pulse_ring(painter, cx, cy, radius, color, self._phase)

        c = QColor(color)
        glow = QRadialGradient(cx, cy, radius + _px(8))
        glow.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 80))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPointF(cx, cy), radius + _px(8), radius + _px(8))

        fill = QLinearGradient(cx - radius, cy - radius, cx + radius, cy + radius)
        fill.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 200))
        fill.setColorAt(1, QColor(c.red() // 2, c.green() // 2, c.blue() // 2, 200))
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(c, 2))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        if label:
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(_font('Segoe UI', 7, QFont.Bold))
            painter.drawText(QRectF(cx - radius, cy - radius, radius * 2, radius * 2),
                             Qt.AlignCenter, label[:4])

        if points:
            painter.setPen(QColor('#ffd700'))
            painter.setFont(_font('Segoe UI', 6, QFont.Bold))
            painter.drawText(QRectF(cx - radius, cy + radius + 2, radius * 2, _px(14)),
                             Qt.AlignCenter, points)

    def _draw_equip_slot_annotation(self, painter, ann):
        x, y = ann['x'], ann['y']
        sw, sh = ann['w'], ann['h']
        color = ann.get('color', '#ffffff')
        label = ann.get('label', '')
        rarity = ann.get('rarity', '')

        rect = QRectF(x, y, sw, sh)

        if rarity in ('神话暗金', '暗金'):
            _draw_highlight_rect(painter, rect, color, border_width=3, glow_radius=14)
            _draw_recommend_badge(painter, x + sw / 2, y - _px(10), '推荐', color)
        elif rarity == '传奇':
            _draw_highlight_rect(painter, rect, color, border_width=2, glow_radius=8)
            _draw_recommend_badge(painter, x + sw / 2, y - _px(10), '推荐', color)
        else:
            _draw_highlight_rect(painter, rect, color, border_width=1, glow_radius=4)

        painter.setPen(QColor(255, 255, 255, 220))
        painter.setFont(_font('Segoe UI', 6, QFont.Bold))
        display = label if len(label) <= 5 else label[:4] + '..'
        painter.drawText(QRectF(x, y + sh - _px(14), sw, _px(14)),
                         Qt.AlignCenter, display)

    def _draw_text_overlay(self, painter, ann):
        x, y = ann['x'], ann['y']
        text = ann.get('text', '')
        color = ann.get('color', '#ffd700')
        anchor = ann.get('anchor', 'top-left')

        painter.setFont(_font('Segoe UI', 9, QFont.Bold))
        fm = painter.fontMetrics()
        tw = fm.width(text) + _px(16)
        th = fm.height() + _px(8)

        if anchor == 'top-right':
            rx = x - tw
            ry = y
        elif anchor == 'top-left':
            rx = x
            ry = y
        else:
            rx = x - tw / 2
            ry = y

        rect = QRectF(rx, ry, tw, th)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
        painter.drawRoundedRect(rect, 4, 4)

        c = QColor(color)
        painter.setPen(QPen(c, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 4, 4)

        painter.setPen(c)
        painter.drawText(rect, Qt.AlignCenter, text)


class D4ContainerWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("d4OverlayContainer")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        s = _px(14)
        t = 2

        gold = QColor(180, 130, 50, 200)
        dark_red = QColor(120, 40, 20, 160)

        for corner_data in [
            (0, 0, 1, 1), (w, 0, -1, 1), (0, h, 1, -1), (w, h, -1, -1),
        ]:
            cx, cy, dx, dy = corner_data

            painter.setPen(QPen(gold, t + 1))
            painter.drawLine(int(cx), int(cy), int(cx + dx * s), int(cy))
            painter.drawLine(int(cx), int(cy), int(cx), int(cy + dy * s))

            painter.setPen(QPen(dark_red, t))
            inner_s = s - _px(4)
            ix = cx + dx * _px(3)
            iy = cy + dy * _px(3)
            painter.drawLine(int(ix), int(iy), int(ix + dx * inner_s), int(iy))
            painter.drawLine(int(ix), int(iy), int(ix), int(iy + dy * inner_s))

        painter.end()


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

        self._container = D4ContainerWidget()
        self._container.setStyleSheet(
            "#d4OverlayContainer {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "    stop:0 rgba(20, 12, 8, 220), stop:0.5 rgba(12, 8, 15, 230), "
            "    stop:1 rgba(20, 12, 8, 220));"
            "  border: 2px solid rgba(120, 40, 20, 180);"
            "  border-radius: 4px;"
            "}"
        )
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(_px(6), _px(4), _px(6), _px(6))
        container_layout.setSpacing(_px(4))

        self._build_control_bar(container_layout)
        self._build_stacked_panels(container_layout)

        main_layout.addWidget(self._container)
        self.setFixedSize(_px(480), _px(700))
        self.setWindowOpacity(self.opacity)

    def _build_control_bar(self, parent_layout):
        bar = QWidget()
        bar.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                         "stop:0 rgba(25, 12, 8, 240), stop:1 rgba(15, 8, 12, 240)); "
                         "border-radius: 3px;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(_px(8), _px(4), _px(8), _px(4))
        bar_layout.setSpacing(_px(4))

        title = QLabel("暗黑助手")
        title.setFont(_font('Georgia', 12, QFont.Bold))
        title.setStyleSheet("color: #ff6b35; background: transparent;")
        bar_layout.addWidget(title)

        bar_layout.addStretch()

        self._panel_btns = {}
        for key, label in [('skill', '技能'), ('paragon', '巅峰'), ('equipment', '装备')]:
            btn = QPushButton(label)
            btn.setFixedSize(_px(48), _px(24))
            btn.setFont(_font('Segoe UI', 9))
            btn.setStyleSheet(self._panel_btn_style(key == self._current_panel))
            btn.clicked.connect(lambda checked, k=key: self.show_panel(k))
            bar_layout.addWidget(btn)
            self._panel_btns[key] = btn

        bar_layout.addSpacing(_px(4))

        capture_btn = QPushButton("📷")
        capture_btn.setFixedSize(_px(28), _px(24))
        fs = _px(14)
        capture_btn.setStyleSheet(
            "QPushButton { color: #aaa; background: transparent; border: none; font-size: %dpx; }"
            "QPushButton:hover { color: #ffd700; }" % fs
        )
        capture_btn.setToolTip("捕获游戏界面")
        capture_btn.clicked.connect(self._manual_capture)
        bar_layout.addWidget(capture_btn)

        auto_btn = QPushButton("🔄")
        auto_btn.setFixedSize(_px(28), _px(24))
        auto_btn.setStyleSheet(
            "QPushButton { color: #666; background: transparent; border: none; font-size: %dpx; }"
            "QPushButton:hover { color: #ffd700; }" % fs
        )
        auto_btn.setToolTip("自动捕获开关")
        auto_btn.clicked.connect(self._toggle_auto_capture)
        self._auto_btn = auto_btn
        bar_layout.addWidget(auto_btn)

        opacity_btn = QPushButton("👁")
        opacity_btn.setFixedSize(_px(24), _px(24))
        opacity_btn.setStyleSheet(
            "QPushButton { color: #aaa; background: transparent; border: none; font-size: %dpx; }"
            "QPushButton:hover { color: #ff6b35; }" % fs
        )
        opacity_btn.clicked.connect(self.toggle_opacity)
        bar_layout.addWidget(opacity_btn)

        minimize_btn = QPushButton("—")
        minimize_btn.setFixedSize(_px(24), _px(24))
        minimize_btn.setStyleSheet(
            "QPushButton { color: #aaa; background: transparent; border: none; font-size: %dpx; }"
            "QPushButton:hover { color: #ff6b35; }" % fs
        )
        minimize_btn.clicked.connect(self._on_minimize)
        bar_layout.addWidget(minimize_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(_px(24), _px(24))
        close_btn.setStyleSheet(
            "QPushButton { color: #ff6b35; background: transparent; border: none; font-size: %dpx; }"
            "QPushButton:hover { color: #ff4444; }" % fs
        )
        close_btn.clicked.connect(self._on_close)
        bar_layout.addWidget(close_btn)

        parent_layout.addWidget(bar)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(120, 40, 20, 100);")
        parent_layout.addWidget(sep)

    def _panel_btn_style(self, active):
        if active:
            return (
                "QPushButton { color: #ffd700; background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                "stop:0 rgba(120, 30, 10, 200), stop:1 rgba(80, 20, 8, 220)); "
                "border: 1px solid rgba(200, 80, 20, 180); border-radius: 3px; font-weight: bold; }"
                "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                "stop:0 rgba(150, 40, 15, 220), stop:1 rgba(100, 25, 10, 240)); }"
            )
        return (
            "QPushButton { color: #999; background: rgba(20, 15, 18, 180); "
            "border: 1px solid rgba(80, 50, 40, 100); border-radius: 3px; }"
            "QPushButton:hover { color: #ffd700; background: rgba(35, 25, 20, 200); }"
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
        layout.setContentsMargins(_px(4), _px(4), _px(4), _px(4))
        layout.setSpacing(_px(2))

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(_px(4), _px(2), _px(4), _px(2))
        self._skill_class_label = QLabel("职业: --")
        self._skill_class_label.setFont(_font('Segoe UI', 9, QFont.Bold))
        self._skill_class_label.setStyleSheet("color: #9b59b6; background: transparent;")
        header_layout.addWidget(self._skill_class_label)
        self._skill_points_label = QLabel("可用技能点: 0")
        self._skill_points_label.setFont(_font('Segoe UI', 8))
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

        self._skill_capture_panel = GameCapturePanel('skill')
        scroll.setWidget(self._skill_capture_panel)
        layout.addWidget(scroll, 1)

        return panel

    def _build_paragon_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(_px(4), _px(4), _px(4), _px(4))
        layout.setSpacing(_px(2))

        self._paragon_class_label = QLabel("职业: --")
        self._paragon_class_label.setFont(_font('Segoe UI', 9, QFont.Bold))
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

        self._paragon_capture_panel = GameCapturePanel('paragon')
        scroll.setWidget(self._paragon_capture_panel)
        layout.addWidget(scroll, 1)

        return panel

    def _build_equipment_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(_px(4), _px(4), _px(4), _px(4))
        layout.setSpacing(_px(2))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #555; border-radius: 2px; }"
        )

        self._equipment_capture_panel = GameCapturePanel('equipment')
        scroll.setWidget(self._equipment_capture_panel)
        layout.addWidget(scroll, 1)

        return panel

    def init_capture(self, screen_capture=None):
        self._skill_capture_panel.init_capture(screen_capture)
        self._paragon_capture_panel.init_capture(screen_capture)
        self._equipment_capture_panel.init_capture(screen_capture)

    def _manual_capture(self):
        panel_map = {
            'skill': self._skill_capture_panel,
            'paragon': self._paragon_capture_panel,
            'equipment': self._equipment_capture_panel,
        }
        panel = panel_map.get(self._current_panel)
        if panel:
            success = panel.capture_game_ui()
            if success:
                logger.info(f"成功捕获 {self._current_panel} 面板")
            else:
                logger.warning(f"捕获 {self._current_panel} 面板失败")

    def _toggle_auto_capture(self):
        panel_map = {
            'skill': self._skill_capture_panel,
            'paragon': self._paragon_capture_panel,
            'equipment': self._equipment_capture_panel,
        }
        panel = panel_map.get(self._current_panel)
        if panel:
            is_auto = panel._auto_capture
            panel.set_auto_capture(not is_auto)
            if not is_auto:
                self._auto_btn.setStyleSheet(
                    "QPushButton { color: #ffd700; background: transparent; border: none; font-size: %dpx; }"
                    "QPushButton:hover { color: #ff6b35; }" % _px(14)
                )
            else:
                panel.clear_capture()
                self._auto_btn.setStyleSheet(
                    "QPushButton { color: #666; background: transparent; border: none; font-size: %dpx; }"
                    "QPushButton:hover { color: #ffd700; }" % _px(14)
                )

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

        self._skill_capture_panel.set_skill_data(skills, class_name)

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

        self._paragon_capture_panel.set_paragon_data(boards, class_name)

    def update_equipment(self, class_name, build_data):
        title = build_data.get('title', '') if isinstance(build_data, dict) else ''

        equipment = []
        if isinstance(build_data, dict):
            equipment = build_data.get('equipment', [])
            if not equipment:
                equipment = build_data.get('items', [])

        self._equipment_capture_panel.set_equipment_data(equipment, class_name, title)

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

        self._update_auto_btn_state()

    def _update_auto_btn_state(self):
        panel_map = {
            'skill': self._skill_capture_panel,
            'paragon': self._paragon_capture_panel,
            'equipment': self._equipment_capture_panel,
        }
        panel = panel_map.get(self._current_panel)
        if panel and panel._auto_capture:
            self._auto_btn.setStyleSheet(
                "QPushButton { color: #ffd700; background: transparent; border: none; font-size: %dpx; }"
                "QPushButton:hover { color: #ff6b35; }" % _px(14)
            )
        else:
            self._auto_btn.setStyleSheet(
                "QPushButton { color: #666; background: transparent; border: none; font-size: %dpx; }"
                "QPushButton:hover { color: #ffd700; }" % _px(14)
            )

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
