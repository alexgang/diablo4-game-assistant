#!/usr/bin/env python3
"""
暗黑破坏神4 - 技能树图片生成器
"""

from PIL import Image, ImageDraw, ImageFont
import os

SKILL_TREES = [
    ['振奋打击', '穿刺', '穿刺·强化', '穿刺·精通'],
    ['强力箭矢', '穿心箭', '穿心箭·强化', '穿心箭·精通'],
    ['扭转回刃', '扭转回刃·强化', '快刀乱刺', '快刀乱刺·强化', '快刀乱刺·精通'],
    ['钉爪刺', '剧毒陷阱', '死亡陷阱', '死亡陷阱·终极'],
    ['暗影步伐', '隐匿', '暗影帷幕', '暗影复制体'],
    ['毒素灌注', '毒素灌注·强化', '暗影灌注', '暗影灌注·强化', '冰寒灌注'],
]

PARENTS = [
    [None, '振奋打击', '穿刺', '穿刺·强化'],
    [None, '强力箭矢', '穿心箭', '穿心箭·强化'],
    [None, '扭转回刃', '扭转回刃', '快刀乱刺', '快刀乱刺·强化'],
    [None, '钉爪刺', '剧毒陷阱', '死亡陷阱'],
    [None, '暗影步伐', '隐匿', '暗影帷幕'],
    [None, '毒素灌注', '毒素灌注', '暗影灌注', '冰寒灌注'],
]

TYPES = [
    ['basic', 'core', 'advanced', 'ultimate'],
    ['basic', 'core', 'advanced', 'ultimate'],
    ['basic', 'advanced', 'core', 'advanced', 'ultimate'],
    ['basic', 'core', 'advanced', 'ultimate'],
    ['basic', 'core', 'advanced', 'ultimate'],
    ['basic', 'advanced', 'core', 'advanced', 'ultimate'],
]

DESCRIPTIONS = {
    '振奋打击': '快速刺击，冷却极短',
    '穿刺': '穿透飞刀，范围伤害',
    '穿刺·强化': '穿刺留下伤口，持续流血',
    '穿刺·精通': '穿刺弹射更多敌人',
    '强力箭矢': '强力箭矢，较高伤害',
    '穿心箭': '精准射击，单体高伤',
    '穿心箭·强化': '穿心箭破碎护甲',
    '穿心箭·精通': '穿心箭必定暴击',
    '扭转回刃': '旋转刃舞，范围伤害（毒刃舞核心）',
    '扭转回刃·强化': '扭转回刃减速敌人',
    '快刀乱刺': '快速连续刺击',
    '快刀乱刺·强化': '快刀乱刺几率昏迷',
    '快刀乱刺·精通': '快刀乱刺最后攻击必暴',
    '钉爪刺': '布置陷阱，敌人减速',
    '剧毒陷阱': '毒云陷阱，持续中毒（核心）',
    '死亡陷阱': '陷阱触发后再布置',
    '死亡陷阱·终极': '死亡陷阱爆炸伤害',
    '暗影步伐': '快速位移到敌后',
    '隐匿': '进入隐身，增伤',
    '暗影帷幕': '隐身留下暗影区域',
    '暗影复制体': '召唤暗影协助作战',
    '毒素灌注': '武器注入毒素，持续毒伤',
    '毒素灌注·强化': '毒素伤害增加',
    '暗影灌注': '武器注入暗影（核心）',
    '暗影灌注·强化': '暗影伤害增加',
    '冰寒灌注': '武器注入冰霜之力',
}

COL_TYPES = {
    'basic': '#68d391',
    'core': '#f6ad55',
    'advanced': '#63b3ed',
    'ultimate': '#ed64a6',
}

COL_LABELS = ['穿刺', '穿心箭', '刃舞', '毒陷阱', '暗影', '灌注']

BD_BLIND_DANCE = {
    '振奋打击': 1,
    '扭转回刃': 5,
    '扭转回刃·强化': 3,
    '快刀乱刺': 2,
    '钉爪刺': 3,
    '剧毒陷阱': 5,
    '死亡陷阱': 3,
    '死亡陷阱·终极': 1,
    '毒素灌注': 3,
    '暗影灌注': 5,
    '暗影灌注·强化': 3,
    '冰寒灌注': 1,
    '暗影步伐': 2,
    '隐匿': 3,
}

def draw_skill_tree():
    width, height = 1100, 900
    img = Image.new('RGB', (width, height), '#1a202c')
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("msyh.ttc", 22)
        font_label = ImageFont.truetype("msyh.ttc", 9)
        font_name = ImageFont.truetype("msyh.ttc", 10)
    except:
        font_title = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_name = ImageFont.load_default()

    draw.rectangle([(30, 85), (width - 30, 87)], fill='#30363d')

    title = "游侠 S13 热门构筑 - 盲眼毒刃舞"
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, 18), title, fill='#ffd700', font=font_title)

    subtitle = "核心: 扭转回刃(毒刃舞) + 剧毒陷阱 + 暗影灌注"
    bbox = draw.textbbox((0, 0), subtitle, font=font_label)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, 52), subtitle, fill='#718096', font=font_label)

    col_width = 130
    col_spacing = 30
    row_spacing = 28
    start_x = (width - (len(SKILL_TREES) * col_width + (len(SKILL_TREES) - 1) * col_spacing)) // 2
    start_y = height - 100

    positions = {}
    for col_idx, col in enumerate(SKILL_TREES):
        x = start_x + col_idx * (col_width + col_spacing)
        for row_idx, skill_name in enumerate(col):
            y = start_y - row_idx * (row_spacing + 40)
            positions[skill_name] = (x + col_width // 2, y)

    for col_idx, col in enumerate(SKILL_TREES):
        x = start_x + col_idx * (col_width + col_spacing)
        label = COL_LABELS[col_idx] if col_idx < len(COL_LABELS) else ""
        bbox = draw.textbbox((0, 0), label, font=font_label)
        tw = bbox[2] - bbox[0]
        draw.text((x + col_width // 2 - tw // 2, start_y + 15), label, fill='#ffd700', font=font_label)

    for col_idx, col in enumerate(SKILL_TREES):
        for row_idx, skill_name in enumerate(col):
            parent_name = PARENTS[col_idx][row_idx]
            if parent_name and parent_name in positions:
                px, py = positions[parent_name]
                sx, sy = positions[skill_name]
                color = '#4a5568'
                if skill_name in BD_BLIND_DANCE:
                    color = '#48bb78'
                elif parent_name in BD_BLIND_DANCE:
                    color = '#4a5568'
                draw.line([(px, py - 20), (px, (py + sy) // 2 - 10), (sx, (py + sy) // 2 - 10), (sx, sy + 20)], fill=color, width=2)

    for col_idx, col in enumerate(SKILL_TREES):
        for row_idx, skill_name in enumerate(col):
            x, y = positions[skill_name]
            skill_type = TYPES[col_idx][row_idx]
            color = COL_TYPES.get(skill_type, '#68d391')
            active = skill_name in BD_BLIND_DANCE
            radius = 20 if active else 18

            if active:
                draw.ellipse([(x - radius - 3, y - radius - 3), (x + radius + 3, y + radius + 3)], fill='#2d3748', outline='#ffd700', width=2)

            draw.ellipse([(x - radius, y - radius), (x + radius, y + radius)],
                        fill=color if active else '#2d3748',
                        outline=color, width=3)

            if active:
                draw.ellipse([(x - radius + 4, y - radius + 4), (x + radius - 4, y + radius - 4)],
                           fill=color, outline='#ffffff', width=1)

            bbox = draw.textbbox((0, 0), skill_name, font=font_name)
            tw = bbox[2] - bbox[0]
            draw.text((x - tw // 2, y + radius + 4), skill_name, fill='#ffffff', font=font_name)

            if skill_name in BD_BLIND_DANCE:
                pts = BD_BLIND_DANCE[skill_name]
                pts_text = f"[{pts}]"
                bbox = draw.textbbox((0, 0), pts_text, font=font_name)
                tw = bbox[2] - bbox[0]
                draw.text((x - tw // 2, y + radius + 18), pts_text, fill='#ffd700', font=font_name)

    legend_y = 130
    draw.text((50, legend_y), "图例:", fill='#718096', font=font_label)
    items = [
        ("#ffd700", "核心/关键技能"),
        ("#68d391", "基础技能"),
        ("#f6ad55", "核心技能"),
        ("#63b3ed", "进阶技能"),
        ("#ed64a6", "终极技能"),
    ]
    for i, (color, label) in enumerate(items):
        lx = 110 + i * 190
        draw.ellipse([(lx, legend_y), (lx + 12, legend_y + 12)], fill=color, outline='#ffffff')
        draw.text((lx + 18, legend_y), label, fill='#cccccc', font=font_label)

    note = "S13赛季盲眼毒刃舞BD - 高频中毒 + 毒刃舞范围伤害 + 暗影灌注增伤"
    bbox = draw.textbbox((0, 0), note, font=font_label)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, height - 25), note, fill='#4a5568', font=font_label)

    return img

def main():
    print("=" * 60)
    print("暗黑破坏神4 技能树图片生成器")
    print("=" * 60)
    print("\n正在生成技能树图片...")

    try:
        img = draw_skill_tree()

        output_path = "c:\\Users\\63446\\game-assistant\\skill_tree_preview.png"
        img.save(output_path)
        print(f"\n✓ 图片已生成: {output_path}")

        print("✓ 正在打开图片...")
        os.startfile(output_path)

        return 0

    except Exception as e:
        print(f"\n✗ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
