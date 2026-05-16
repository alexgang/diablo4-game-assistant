#!/usr/bin/env python3
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from graphical_overlay import GraphicalOverlay

TEST_SKILLS = {
    '基础技能': [
        {'name': '狂乱', 'points': 5, 'max_points': 5, 'active': True},
        {'name': '战斗怒吼', 'points': 1, 'max_points': 1, 'active': True},
        {'name': '强化狂乱', 'points': 1, 'max_points': 1, 'active': True},
    ],
    '核心技能': [
        {'name': '旋风斩', 'points': 5, 'max_points': 5, 'active': True},
        {'name': '强化旋风斩', 'points': 1, 'max_points': 1, 'active': True},
        {'name': '狂暴旋风', 'points': 3, 'max_points': 3, 'active': True},
        {'name': '暴力', 'points': 3, 'max_points': 3, 'active': True},
    ],
    '特性技能': [
        {'name': '战吼', 'points': 1, 'max_points': 1, 'active': True},
        {'name': '挑战怒吼', 'points': 1, 'max_points': 1, 'active': True},
        {'name': '先祖召唤', 'points': 1, 'max_points': 1, 'active': True},
        {'name': '钢筋铁骨', 'points': 3, 'max_points': 3, 'active': True},
    ],
    '终极技能': [
        {'name': '狂战士之怒', 'points': 1, 'max_points': 1, 'active': True},
        {'name': '无尽怒火', 'points': 1, 'max_points': 1, 'active': True},
    ],
}

TEST_EQUIPMENT = [
    {'name': '谐角之冠', 'slot': '头盔', 'rarity': '神话暗金', 'stats': '+4 全技能'},
    {'name': '涌血创痕', 'slot': '胸甲', 'rarity': '暗金', 'stats': '+生命值'},
    {'name': '碎骨者', 'slot': '手套', 'rarity': '传奇', 'stats': '+暴击率'},
    {'name': '深渊行者', 'slot': '裤子', 'rarity': '传奇', 'stats': '+移速转攻'},
    {'name': '铁血战靴', 'slot': '靴子', 'rarity': '传奇', 'stats': '+闪避'},
    {'name': '风暴之弓', 'slot': '远程武器', 'rarity': '暗金', 'stats': '+攻速'},
    {'name': '泰瑞尔之力', 'slot': '护符', 'rarity': '神话暗金', 'stats': '+全属性'},
    {'name': '毁灭之戒', 'slot': '戒指1', 'rarity': '暗金', 'stats': '+暴击伤害'},
    {'name': '元素之环', 'slot': '戒指2', 'rarity': '传奇', 'stats': '+元素伤'},
    {'name': '祖父', 'slot': '双持武器1', 'rarity': '神话暗金', 'stats': '+暴击伤害'},
    {'name': '末日使者', 'slot': '双持武器2', 'rarity': '暗金', 'stats': '+暗影伤'},
]

TEST_PARAGON = [
    {
        'name': '起始',
        'rotation': 0,
        'nodes': {
            'legendary': (3, 4),
            'rare': [(1, 2), (5, 6), (2, 7)],
            'magic': [(1, 3), (2, 3), (4, 5), (5, 5)],
            'glyph': (4, 4),
        }
    },
    {
        'name': '卑鄙招数',
        'rotation': 3,
        'nodes': {
            'legendary': (3, 3),
            'rare': [(1, 1), (5, 2), (6, 5)],
            'magic': [(2, 2), (4, 2), (3, 5), (5, 4)],
            'glyph': (3, 4),
        }
    },
    {
        'name': '屠戮者',
        'rotation': 1,
        'nodes': {
            'legendary': (4, 3),
            'rare': [(2, 1), (6, 2), (1, 5)],
            'magic': [(3, 2), (5, 3), (2, 5), (4, 6)],
            'glyph': (3, 3),
        }
    },
    {
        'name': '致命精准',
        'rotation': 2,
        'nodes': {
            'legendary': (3, 2),
            'rare': [(1, 3), (5, 5), (6, 3)],
            'magic': [(2, 1), (4, 1), (3, 6), (5, 6)],
            'glyph': (4, 4),
        }
    },
    {
        'name': '血腥盛宴',
        'rotation': 0,
        'nodes': {
            'legendary': (4, 4),
            'rare': [(2, 2), (6, 4), (1, 6)],
            'magic': [(3, 3), (5, 5), (2, 6), (6, 6)],
            'glyph': (3, 3),
        }
    },
]


def main():
    logging.basicConfig(level=logging.WARNING)
    app = QApplication(sys.argv)

    overlay = GraphicalOverlay(opacity=0.92)
    overlay.show_at_game_position(1920, 1200)

    class_name = '野蛮人'

    overlay.update_skills(class_name, TEST_SKILLS)

    overlay.update_equipment(class_name, {
        'equipment': TEST_EQUIPMENT,
        'title': '旋风斩尘魔BD',
    })

    overlay.update_paragon(class_name, {'boards': TEST_PARAGON})

    print("UI test running. Close the overlay window to exit.")

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
