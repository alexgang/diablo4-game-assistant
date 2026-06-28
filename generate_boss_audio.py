#!/usr/bin/env python3
"""预生成所有 BOSS 的攻略音频(按阶段切分)

为每个 BOSS 生成以下音频文件:
  {key}_intro.mp3    - 位置与召唤 + 战斗机制总览(进入 BOSS 战时播放)
  {key}_phase1.mp3   - 第1阶段机制与打法(血量 100-66%)
  {key}_phase2.mp3   - 第2阶段机制与打法(血量 66-33%)
  {key}_phase3.mp3   - 第3阶段机制与打法(血量 33-0%)
  {key}_outro.mp3    - 装备建议(BOSS 战结束时播放)

同时生成 audio_index.json 记录每个 BOSS 的音频文件列表。

用法:
  python generate_boss_audio.py          # 生成全部
  python generate_boss_audio.py 齐尔大人  # 只生成指定 BOSS
"""
import asyncio
import json
import os
import re
import sys
import hashlib

import edge_tts

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, 'resources', 'audio', 'bosses')
BOSS_DATA_PATH = os.path.join(BASE_DIR, 'boss_data.json')
INDEX_PATH = os.path.join(AUDIO_DIR, 'audio_index.json')

TTS_VOICE = 'zh-CN-XiaoxiaoNeural'


def markdown_to_plain_text(md_text):
    """Markdown 转纯文本(TTS 播报用)"""
    text = md_text
    text = re.sub(r'^#{1,4}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[\U0001f300-\U0001f9ff\U00002600-\U000027bf]', '', text)
    # 英文术语本地化
    text = re.sub(r'Phase\s*(\d)', r'第\1阶段', text, flags=re.IGNORECASE)
    text = re.sub(r'(?<![A-Za-z])P(\d)(?![0-9])', r'第\1阶段', text)
    text = re.sub(r'范围AOE', '范围攻击', text, flags=re.IGNORECASE)
    text = re.sub(r'AOE', '范围攻击', text, flags=re.IGNORECASE)
    text = re.sub(r'Uber', '极品', text, flags=re.IGNORECASE)
    # 去掉括号内英文原名
    text = re.sub(r'\s*\([A-Za-z\s,]+\)\s*', '', text)
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()


def split_guide_sections(guide_md):
    """将攻略 Markdown 按 ### 标题切分成章节

    Returns:
        dict: {章节标题(去emoji): 章节内容(Markdown)}
    """
    sections = {}
    current_title = None
    current_lines = []

    for line in guide_md.split('\n'):
        m = re.match(r'^###\s+(.+)$', line.strip())
        if m:
            if current_title is not None:
                sections[current_title] = '\n'.join(current_lines).strip()
            # 去掉所有非中文/英文/数字字符(包括 emoji 和变体选择符 U+FE0F)
            title = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', m.group(1))
            current_title = title
            current_lines = []
        elif line.startswith('## '):
            # 主标题(BOSS 名),跳过
            continue
        else:
            if current_title is not None:
                current_lines.append(line)

    if current_title is not None:
        sections[current_title] = '\n'.join(current_lines).strip()

    return sections


def find_section(sections, *keywords):
    """在 sections 里查找包含任一关键词的章节

    Args:
        sections: split_guide_sections 返回的 dict
        *keywords: 关键词列表,任一匹配即返回

    Returns:
        str: 章节内容(未找到返回空字符串)
    """
    for title, content in sections.items():
        for kw in keywords:
            if kw in title:
                return content
    return ''


def split_phases_from_mechanics(mechanics_md):
    """从"战斗机制"章节里按 Phase N 切分成多个阶段

    Args:
        mechanics_md: 战斗机制章节的 Markdown 文本

    Returns:
        dict: {阶段编号(int): 阶段内容(Markdown)}
    """
    phases = {}
    current_phase = None
    current_lines = []

    for line in mechanics_md.split('\n'):
        # 匹配 "- **Phase 1 (100-66%):**" 或 "- **Phase 1:**"
        m = re.match(r'^[-*]\s*\*\*Phase\s*(\d)', line, re.IGNORECASE)
        if m:
            if current_phase is not None:
                phases[current_phase] = '\n'.join(current_lines).strip()
            current_phase = int(m.group(1))
            current_lines = [line]
        else:
            if current_phase is not None:
                current_lines.append(line)

    if current_phase is not None:
        phases[current_phase] = '\n'.join(current_lines).strip()

    return phases


def build_audio_segments(boss_key, boss_data):
    """为单个 BOSS 构建音频分段

    Returns:
        list[dict]: [{'name': 'intro', 'text': '...', 'filename': 'xxx_intro.mp3'}, ...]
    """
    guide_md = boss_data.get('guide', '')
    if not guide_md:
        return []

    sections = split_guide_sections(guide_md)

    segments = []

    # 1. intro = 位置与召唤 + tips(简短总览)
    intro_parts = []
    location_md = find_section(sections, '位置', '召唤')
    if location_md:
        intro_parts.append(location_md)
    # tips 字段也加入 intro(一句话总览)
    if boss_data.get('tips'):
        intro_parts.append(boss_data['tips'])

    if intro_parts:
        segments.append({
            'name': 'intro',
            'text': markdown_to_plain_text('\n'.join(intro_parts)),
        })

    # 2. 各阶段 = 战斗机制中的 Phase N + 打法要点(整体)
    mechanics_md = find_section(sections, '战斗', '机制')

    phase_contents = split_phases_from_mechanics(mechanics_md)

    # 打法要点作为最后一个阶段的补充
    tips_md = find_section(sections, '打法', '要点')

    if phase_contents:
        for phase_num in sorted(phase_contents.keys()):
            phase_text = phase_contents[phase_num]
            # 最后一个阶段附加打法要点
            if phase_num == max(phase_contents.keys()) and tips_md:
                phase_text = phase_text + '\n\n' + tips_md
            segments.append({
                'name': f'phase{phase_num}',
                'text': markdown_to_plain_text(phase_text),
            })
    else:
        # 没有 Phase 切分的 BOSS(如屠夫单阶段),把整个战斗机制+打法要点作为 phase1
        mech_and_tips = mechanics_md
        if tips_md:
            mech_and_tips = mech_and_tips + '\n\n' + tips_md
        if mech_and_tips.strip():
            segments.append({
                'name': 'phase1',
                'text': markdown_to_plain_text(mech_and_tips),
            })

    # 3. outro = 装备建议
    outro_md = find_section(sections, '装备', '建议')
    if outro_md.strip():
        segments.append({
            'name': 'outro',
            'text': markdown_to_plain_text(outro_md),
        })

    # 生成安全文件名(用 boss_key 的 md5 前8位)
    name_hash = hashlib.md5(boss_key.encode('utf-8')).hexdigest()[:8]
    for seg in segments:
        seg['filename'] = f"{name_hash}_{seg['name']}.mp3"

    return segments


async def synthesize_segment(text, output_path):
    """用 Edge TTS 合成一段音频"""
    communicate = edge_tts.Communicate(text, TTS_VOICE)
    await communicate.save(output_path)


async def generate_boss_audio(boss_key, boss_data):
    """为单个 BOSS 生成所有音频分段"""
    segments = build_audio_segments(boss_key, boss_data)
    if not segments:
        print(f"  [跳过] {boss_key}: 无攻略文本")
        return None

    results = []
    for seg in segments:
        if not seg['text'].strip():
            continue
        output_path = os.path.join(AUDIO_DIR, seg['filename'])
        print(f"  生成 {seg['name']}: {len(seg['text'])} 字 -> {seg['filename']}", flush=True)
        await synthesize_segment(seg['text'], output_path)
        size = os.path.getsize(output_path)
        print(f"    完成: {size} 字节", flush=True)
        results.append({
            'name': seg['name'],
            'filename': seg['filename'],
            'text_length': len(seg['text']),
            'size': size,
        })

    return {
        'boss_key': boss_key,
        'aliases': boss_data.get('aliases', []),
        'phases': boss_data.get('phases', 1),
        'segments': results,
    }


async def main_async():
    # 只生成指定 BOSS 或全部
    target = sys.argv[1] if len(sys.argv) > 1 else None

    with open(BOSS_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    bosses = data.get('bosses', {})
    os.makedirs(AUDIO_DIR, exist_ok=True)

    index = {}
    for boss_key, boss_data in bosses.items():
        if target and target != boss_key:
            continue
        print(f"\n处理 BOSS: {boss_key}", flush=True)
        result = await generate_boss_audio(boss_key, boss_data)
        if result:
            index[boss_key] = result

    # 如果是全部生成,保存索引;单独生成则合并到现有索引
    if not target:
        with open(INDEX_PATH, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        print(f"\n索引已保存: {INDEX_PATH}", flush=True)
    else:
        # 合并到现有索引
        existing = {}
        if os.path.exists(INDEX_PATH):
            with open(INDEX_PATH, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        existing.update(index)
        with open(INDEX_PATH, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        print(f"\n索引已更新: {INDEX_PATH}", flush=True)

    print(f"\n完成! 共处理 {len(index)} 个 BOSS", flush=True)


def main():
    asyncio.run(main_async())


if __name__ == '__main__':
    main()
