#!/usr/bin/env python3
"""
游戏叠加层模块 - 在游戏画面上显示半透明的攻略信息

功能：
1. 装备推荐叠加：显示当前职业的推荐装备列表
2. 技能加点叠加：显示技能树加点方案
3. 巅峰点数叠加：显示巅峰盘推荐
4. 雇佣兵叠加：显示雇佣兵推荐
5. 可拖拽、可调整透明度、可切换显示
"""

import logging
import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QScrollArea, QFrame, QSizePolicy,
)
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal

try:
    from config import OVERLAY_CONFIG
except ImportError:
    OVERLAY_CONFIG = {}

logger = logging.getLogger(__name__)

STYLE_SHEET = """
OverlayTabWidget {
    background: transparent;
}
OverlayTabWidget::pane {
    border: 1px solid rgba(139, 0, 0, 150);
    background: rgba(10, 10, 30, 200);
    border-radius: 4px;
}
OverlayTabWidget::tab-bar {
    alignment: left;
}
OverlayTabWidget QTabBar::tab {
    background: rgba(30, 30, 60, 200);
    color: #aaa;
    padding: 4px 10px;
    border: 1px solid #333;
    border-bottom: none;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    font-size: 11px;
    min-width: 50px;
}
OverlayTabWidget QTabBar::tab:selected {
    background: rgba(10, 10, 30, 220);
    color: #ff6b35;
    border-color: #8b0000;
}
OverlayTabWidget QTabBar::tab:hover:!selected {
    background: rgba(40, 40, 80, 200);
    color: #ddd;
}
"""

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
    '头盔': '🪖 头盔',
    '胸甲': '🛡️ 胸甲',
    '手套': '🧤 手套',
    '裤子': '👖 裤子',
    '靴子': '👢 靴子',
    '主手武器': '⚔️ 主手',
    '副手武器': '🛡️ 副手',
    '双手武器': '⚔️ 双手',
    '护符': '📿 护符',
    '戒指1': '💍 戒指1',
    '戒指2': '💍 戒指2',
    '武器': '⚔️ 武器',
}


class OverlayPanel(QWidget):
    """半透明叠加层面板"""

    closed = pyqtSignal()
    visibility_changed = pyqtSignal(bool)

    def __init__(self, parent=None, opacity=None):
        super().__init__(parent)
        cfg = OVERLAY_CONFIG
        self.opacity = opacity if opacity is not None else cfg.get('opacity', 0.85)
        self._dragging = False
        self._drag_pos = None
        self._visible = True

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
        self._container.setObjectName("overlayContainer")
        self._container.setStyleSheet(
            "#overlayContainer {"
            "  background: rgba(10, 10, 30, 220);"
            "  border: 1px solid rgba(139, 0, 0, 180);"
            "  border-radius: 6px;"
            "}"
        )
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(6, 4, 6, 6)
        container_layout.setSpacing(4)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        self._title_label = QLabel("📋 攻略叠加")
        self._title_label.setFont(QFont('Microsoft YaHei', 10, QFont.Bold))
        self._title_label.setStyleSheet("color: #ff6b35;")
        header_layout.addWidget(self._title_label)

        header_layout.addStretch()

        self._opacity_btn = QPushButton("👁")
        self._opacity_btn.setFixedSize(22, 22)
        self._opacity_btn.setStyleSheet(
            "QPushButton { color: #aaa; background: transparent; border: none; font-size: 13px; }"
            "QPushButton:hover { color: #ff6b35; }"
        )
        self._opacity_btn.clicked.connect(self._toggle_opacity)
        header_layout.addWidget(self._opacity_btn)

        self._hide_btn = QPushButton("—")
        self._hide_btn.setFixedSize(22, 22)
        self._hide_btn.setStyleSheet(
            "QPushButton { color: #aaa; background: transparent; border: none; font-size: 13px; }"
            "QPushButton:hover { color: #ff6b35; }"
        )
        self._hide_btn.clicked.connect(self.toggle_visibility)
        header_layout.addWidget(self._hide_btn)

        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(22, 22)
        self._close_btn.setStyleSheet(
            "QPushButton { color: #ff6b35; background: transparent; border: none; font-size: 13px; }"
            "QPushButton:hover { color: #ff4444; }"
        )
        self._close_btn.clicked.connect(self._on_close)
        header_layout.addWidget(self._close_btn)

        container_layout.addWidget(header)

        self._tab_widget = QTabWidget()
        self._tab_widget.setObjectName("OverlayTabWidget")
        self._tab_widget.setStyleSheet(STYLE_SHEET)

        self._equip_tab = self._create_equip_tab()
        self._skill_tab = self._create_skill_tab()
        self._paragon_tab = self._create_paragon_tab()
        self._merc_tab = self._create_merc_tab()

        self._tab_widget.addTab(self._equip_tab, "⚔️ 装备")
        self._tab_widget.addTab(self._skill_tab, "🔮 技能")
        self._tab_widget.addTab(self._paragon_tab, "🌟 巅峰")
        self._tab_widget.addTab(self._merc_tab, "🗡️ 雇佣")

        container_layout.addWidget(self._tab_widget)

        main_layout.addWidget(self._container)

        w = cfg.get('width', 320)
        h = cfg.get('height', 480)
        self.setFixedSize(w, h)

    def _create_equip_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self._equip_class_label = QLabel("职业: --")
        self._equip_class_label.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
        self._equip_class_label.setStyleSheet("color: #9b59b6;")
        layout.addWidget(self._equip_class_label)

        self._equip_build_label = QLabel("构筑: --")
        self._equip_build_label.setFont(QFont('Microsoft YaHei', 9))
        self._equip_build_label.setStyleSheet("color: #aaa;")
        layout.addWidget(self._equip_build_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #333;")
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #555; border-radius: 2px; }"
        )

        self._equip_content = QWidget()
        self._equip_content_layout = QVBoxLayout(self._equip_content)
        self._equip_content_layout.setContentsMargins(0, 0, 0, 0)
        self._equip_content_layout.setSpacing(3)
        self._equip_content_layout.addStretch()

        scroll.setWidget(self._equip_content)
        layout.addWidget(scroll)

        return widget

    def _create_skill_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self._skill_class_label = QLabel("职业: --")
        self._skill_class_label.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
        self._skill_class_label.setStyleSheet("color: #9b59b6;")
        layout.addWidget(self._skill_class_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #333;")
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #555; border-radius: 2px; }"
        )

        self._skill_content = QWidget()
        self._skill_content_layout = QVBoxLayout(self._skill_content)
        self._skill_content_layout.setContentsMargins(0, 0, 0, 0)
        self._skill_content_layout.setSpacing(3)
        self._skill_content_layout.addStretch()

        scroll.setWidget(self._skill_content)
        layout.addWidget(scroll)

        return widget

    def _create_paragon_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self._paragon_class_label = QLabel("职业: --")
        self._paragon_class_label.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
        self._paragon_class_label.setStyleSheet("color: #9b59b6;")
        layout.addWidget(self._paragon_class_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #333;")
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #555; border-radius: 2px; }"
        )

        self._paragon_content = QWidget()
        self._paragon_content_layout = QVBoxLayout(self._paragon_content)
        self._paragon_content_layout.setContentsMargins(0, 0, 0, 0)
        self._paragon_content_layout.setSpacing(3)
        self._paragon_content_layout.addStretch()

        scroll.setWidget(self._paragon_content)
        layout.addWidget(scroll)

        return widget

    def _create_merc_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self._merc_class_label = QLabel("职业: --")
        self._merc_class_label.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
        self._merc_class_label.setStyleSheet("color: #9b59b6;")
        layout.addWidget(self._merc_class_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #333;")
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #555; border-radius: 2px; }"
        )

        self._merc_content = QWidget()
        self._merc_content_layout = QVBoxLayout(self._merc_content)
        self._merc_content_layout.setContentsMargins(0, 0, 0, 0)
        self._merc_content_layout.setSpacing(3)
        self._merc_content_layout.addStretch()

        scroll.setWidget(self._merc_content)
        layout.addWidget(scroll)

        return widget

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _make_item_row(self, slot_name, item_name, rarity='传奇', extra=''):
        row = QWidget()
        row.setStyleSheet(
            "QWidget { background: rgba(30, 30, 60, 150); border-radius: 3px; }"
            "QWidget:hover { background: rgba(50, 50, 80, 180); }"
        )
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(6, 3, 6, 3)
        row_layout.setSpacing(4)

        slot_display = SLOT_DISPLAY.get(slot_name, f"🔹 {slot_name}")
        slot_label = QLabel(slot_display)
        slot_label.setFixedWidth(65)
        slot_label.setFont(QFont('Microsoft YaHei', 9))
        slot_label.setStyleSheet("color: #888;")
        row_layout.addWidget(slot_label)

        color = RARITY_COLORS.get(rarity, '#ffffff')
        name_label = QLabel(item_name)
        name_label.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
        name_label.setStyleSheet(f"color: {color};")
        name_label.setWordWrap(True)
        row_layout.addWidget(name_label, 1)

        if extra:
            extra_label = QLabel(extra)
            extra_label.setFont(QFont('Microsoft YaHei', 8))
            extra_label.setStyleSheet("color: #666;")
            extra_label.setWordWrap(True)
            row_layout.addWidget(extra_label)

        return row

    def _make_skill_row(self, category, skill_name, points=''):
        row = QWidget()
        row.setStyleSheet(
            "QWidget { background: rgba(30, 30, 60, 150); border-radius: 3px; }"
            "QWidget:hover { background: rgba(50, 50, 80, 180); }"
        )
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(6, 3, 6, 3)
        row_layout.setSpacing(4)

        cat_label = QLabel(category)
        cat_label.setFixedWidth(50)
        cat_label.setFont(QFont('Microsoft YaHei', 8))
        cat_label.setStyleSheet("color: #888;")
        row_layout.addWidget(cat_label)

        name_label = QLabel(skill_name)
        name_label.setFont(QFont('Microsoft YaHei', 9))
        name_label.setStyleSheet("color: #4ade80;")
        name_label.setWordWrap(True)
        row_layout.addWidget(name_label, 1)

        if points:
            pts_label = QLabel(points)
            pts_label.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
            pts_label.setStyleSheet("color: #ff6b35;")
            pts_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row_layout.addWidget(pts_label)

        return row

    def _make_section_header(self, text):
        label = QLabel(text)
        label.setFont(QFont('Microsoft YaHei', 9, QFont.Bold))
        label.setStyleSheet("color: #ff6b35; padding: 2px 0;")
        return label

    def update_equipment(self, class_name, build_data):
        """
        更新装备叠加层

        Args:
            class_name: 职业名
            build_data: 构筑数据 dict，包含 equipment 列表
        """
        self._equip_class_label.setText(f"职业: {class_name or '--'}")

        title = build_data.get('title', '') if isinstance(build_data, dict) else ''
        self._equip_build_label.setText(f"构筑: {title or '--'}")

        self._clear_layout(self._equip_content_layout)

        equipment = []
        if isinstance(build_data, dict):
            equipment = build_data.get('equipment', [])
            if not equipment:
                equipment = build_data.get('items', [])

        if not equipment:
            no_data = QLabel("暂无装备数据\n请先搜索构筑或使用 --web 爬取")
            no_data.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
            no_data.setAlignment(Qt.AlignCenter)
            self._equip_content_layout.insertWidget(0, no_data)
            self._equip_content_layout.addStretch()
            return

        sorted_items = self._sort_equipment(equipment)

        for item in sorted_items:
            if isinstance(item, dict):
                name = item.get('name', '')
                slot = item.get('slot', item.get('type', ''))
                rarity = item.get('rarity', '传奇')
                extra = item.get('stats', '')
                if isinstance(extra, list):
                    extra = extra[0] if extra else ''
                extra = extra[:30] + '...' if len(extra) > 30 else extra
            else:
                name = str(item)
                slot = ''
                rarity = ''
                extra = ''

            if name:
                row = self._make_item_row(slot, name, rarity, extra)
                self._equip_content_layout.insertWidget(
                    self._equip_content_layout.count() - 1, row
                )

    def update_skills(self, class_name, skill_data):
        """
        更新技能加点叠加层

        Args:
            class_name: 职业名
            skill_data: 技能数据 dict，包含各分支技能
        """
        self._skill_class_label.setText(f"职业: {class_name or '--'}")
        self._clear_layout(self._skill_content_layout)

        skills = {}
        if isinstance(skill_data, dict):
            skills = skill_data.get('skills', skill_data)

        if not skills:
            no_data = QLabel("暂无技能数据\n请先搜索构筑或使用 --web 爬取")
            no_data.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
            no_data.setAlignment(Qt.AlignCenter)
            self._skill_content_layout.insertWidget(0, no_data)
            self._skill_content_layout.addStretch()
            return

        if isinstance(skills, dict):
            for category, skill_list in skills.items():
                header = self._make_section_header(f"▸ {category}")
                self._skill_content_layout.insertWidget(
                    self._skill_content_layout.count() - 1, header
                )
                if isinstance(skill_list, list):
                    for skill in skill_list:
                        skill_name, points = self._parse_skill_entry(skill)
                        row = self._make_skill_row(category, skill_name, points)
                        self._skill_content_layout.insertWidget(
                            self._skill_content_layout.count() - 1, row
                        )
                elif isinstance(skill_list, str):
                    row = self._make_skill_row(category, skill_list)
                    self._skill_content_layout.insertWidget(
                        self._skill_content_layout.count() - 1, row
                    )
        elif isinstance(skills, list):
            for skill in skills:
                if isinstance(skill, str):
                    skill_name, points = self._parse_skill_entry(skill)
                    row = self._make_skill_row('技能', skill_name, points)
                    self._skill_content_layout.insertWidget(
                        self._skill_content_layout.count() - 1, row
                    )

    def update_paragon(self, class_name, paragon_data):
        """
        更新巅峰点数叠加层

        Args:
            class_name: 职业名
            paragon_data: 巅峰数据 dict
        """
        self._paragon_class_label.setText(f"职业: {class_name or '--'}")
        self._clear_layout(self._paragon_content_layout)

        if not paragon_data:
            no_data = QLabel("暂无巅峰数据\n请先搜索构筑或使用 --web 爬取")
            no_data.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
            no_data.setAlignment(Qt.AlignCenter)
            self._paragon_content_layout.insertWidget(0, no_data)
            self._paragon_content_layout.addStretch()
            return

        boards = paragon_data.get('boards', []) if isinstance(paragon_data, dict) else []
        aspects = paragon_data.get('aspects', []) if isinstance(paragon_data, dict) else []

        if boards:
            header = self._make_section_header("▸ 巅峰盘")
            self._paragon_content_layout.insertWidget(
                self._paragon_content_layout.count() - 1, header
            )
            for board in boards:
                if isinstance(board, dict):
                    name = board.get('name', '')
                    rare = board.get('rare_node', '')
                    text = name
                    if rare:
                        text += f" → {rare}"
                else:
                    text = str(board)
                row = self._make_skill_row('巅峰', text)
                self._paragon_content_layout.insertWidget(
                    self._paragon_content_layout.count() - 1, row
                )

        if aspects:
            header = self._make_section_header("▸ 威能")
            self._paragon_content_layout.insertWidget(
                self._paragon_content_layout.count() - 1, header
            )
            for aspect in aspects:
                text = aspect if isinstance(aspect, str) else str(aspect)
                if len(text) > 50:
                    text = text[:50] + '...'
                row = self._make_skill_row('威能', text)
                self._paragon_content_layout.insertWidget(
                    self._paragon_content_layout.count() - 1, row
                )

        if not boards and not aspects:
            if isinstance(paragon_data, dict):
                for key, val in paragon_data.items():
                    if key in ('class_name', 'title'):
                        continue
                    header = self._make_section_header(f"▸ {key}")
                    self._paragon_content_layout.insertWidget(
                        self._paragon_content_layout.count() - 1, header
                    )
                    if isinstance(val, list):
                        for item in val:
                            text = item if isinstance(item, str) else str(item)
                            if len(text) > 50:
                                text = text[:50] + '...'
                            row = self._make_skill_row(key, text)
                            self._paragon_content_layout.insertWidget(
                                self._paragon_content_layout.count() - 1, row
                                )
                    elif isinstance(val, str):
                        row = self._make_skill_row(key, val)
                        self._paragon_content_layout.insertWidget(
                            self._paragon_content_layout.count() - 1, row
                        )

    def update_mercenary(self, class_name, merc_data):
        """
        更新雇佣兵叠加层

        Args:
            class_name: 职业名
            merc_data: 雇佣兵数据 dict
        """
        self._merc_class_label.setText(f"职业: {class_name or '--'}")
        self._clear_layout(self._merc_content_layout)

        if not merc_data:
            no_data = QLabel("暂无雇佣兵数据\n请先搜索构筑或使用 --web 爬取")
            no_data.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
            no_data.setAlignment(Qt.AlignCenter)
            self._merc_content_layout.insertWidget(0, no_data)
            self._merc_content_layout.addStretch()
            return

        mercenaries = merc_data.get('mercenaries', []) if isinstance(merc_data, dict) else []

        if mercenaries:
            header = self._make_section_header("▸ 推荐雇佣兵")
            self._merc_content_layout.insertWidget(
                self._merc_content_layout.count() - 1, header
            )
            for merc in mercenaries:
                if isinstance(merc, dict):
                    name = merc.get('name', '')
                    skill = merc.get('skill', '')
                    text = name
                    if skill:
                        text += f" - {skill}"
                else:
                    text = str(merc)
                row = self._make_skill_row('雇佣', text)
                self._merc_content_layout.insertWidget(
                    self._merc_content_layout.count() - 1, row
                )

        reinforce = merc_data.get('reinforce', []) if isinstance(merc_data, dict) else []
        if reinforce:
            header = self._make_section_header("▸ 增援技能")
            self._merc_content_layout.insertWidget(
                self._merc_content_layout.count() - 1, header
            )
            for r in reinforce:
                text = r if isinstance(r, str) else str(r)
                row = self._make_skill_row('增援', text)
                self._merc_content_layout.insertWidget(
                    self._merc_content_layout.count() - 1, row
                )

        if not mercenaries and not reinforce:
            if isinstance(merc_data, dict):
                for key, val in merc_data.items():
                    if key in ('class_name', 'title'):
                        continue
                    header = self._make_section_header(f"▸ {key}")
                    self._merc_content_layout.insertWidget(
                        self._merc_content_layout.count() - 1, header
                    )
                    if isinstance(val, list):
                        for item in val:
                            text = item if isinstance(item, str) else str(item)
                            row = self._make_skill_row(key, text)
                            self._merc_content_layout.insertWidget(
                                self._merc_content_layout.count() - 1, row
                            )
                    elif isinstance(val, str):
                        row = self._make_skill_row(key, val)
                        self._merc_content_layout.insertWidget(
                            self._merc_content_layout.count() - 1, row
                        )

    def update_from_build(self, class_name, build_detail):
        """
        从构筑详情数据一次性更新所有叠加层

        Args:
            class_name: 职业名
            build_detail: 构筑详情 dict (来自 data_spider 或 content_indexer)
        """
        if not isinstance(build_detail, dict):
            return

        self.update_equipment(class_name, build_detail)

        skill_data = {'skills': build_detail.get('skills', [])}
        self.update_skills(class_name, skill_data)

        paragon_data = {
            'aspects': build_detail.get('aspects', []),
        }
        self.update_paragon(class_name, paragon_data)

        merc_data = build_detail.get('mercenary', None)
        self.update_mercenary(class_name, merc_data)

        title = build_detail.get('title', '')
        if title:
            self._title_label.setText(f"📋 {title}")

    def update_from_search_results(self, results, class_name=None):
        """
        从搜索结果更新叠加层

        Args:
            results: 搜索结果列表 (来自 content_indexer.search)
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

    def _sort_equipment(self, equipment):
        """按装备槽位排序"""
        def sort_key(item):
            if isinstance(item, dict):
                slot = item.get('slot', item.get('type', ''))
                for i, s in enumerate(SLOT_ORDER):
                    if s in slot:
                        return i
            return len(SLOT_ORDER)
        return sorted(equipment, key=sort_key)

    def _parse_skill_entry(self, skill):
        """解析技能条目，分离名称和点数"""
        if not isinstance(skill, str):
            return str(skill), ''

        import re
        match = re.match(r'(.+?)\s+(\d+)$', skill.strip())
        if match:
            return match.group(1).strip(), match.group(2)
        return skill.strip(), ''

    def _toggle_opacity(self):
        """切换透明度"""
        if self.opacity > 0.7:
            self.opacity = 0.5
        elif self.opacity > 0.3:
            self.opacity = 0.2
        else:
            self.opacity = 0.85
        self.setWindowOpacity(self.opacity)

    def toggle_visibility(self):
        """切换显示/隐藏"""
        self._visible = not self._visible
        if self._visible:
            self._container.show()
            self._hide_btn.setText("—")
        else:
            self._container.hide()
            self._hide_btn.setText("□")
        self.visibility_changed.emit(self._visible)

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
