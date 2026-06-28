#!/usr/bin/env python3
"""
暗黑破坏神4 - 在线攻略搜索 + LLM 汇总

流程:
1. 用 requests 抓取 Bing 搜索结果页面
2. 解析出标题/URL/摘要
3. 调用智谱 GLM 对搜索结果进行汇总归纳
4. 返回最匹配的攻略 URL + LLM 汇总说明

使用方式:
    from online_quest_searcher import search_and_summarize
    result = search_and_summarize('山上黄昏')
    if result:
        print(result['url'])       # 最佳攻略 URL
        print(result['summary'])   # LLM 汇总
        print(result['title'])     # 攻略标题
"""

import json
import logging
import re
import urllib.parse

import requests

from config import LLM_CONFIG

logger = logging.getLogger(__name__)

# Bing 搜索请求头(模拟浏览器,避免被识别为爬虫)
BING_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# 游戏攻略可信来源(LLM 评分时参考)
TRUSTED_DOMAINS = [
    'gamersky.com',
    'd2core.com',
    'bilibili.com',
    'zhihu.com',
    'tieba.baidu.com',
    'nga.cn',
    '17173.com',
    '3dmgame.com',
]


def _search_bing(keyword, max_results=None):
    """抓取 Bing 搜索结果

    Args:
        keyword: 搜索关键词
        max_results: 最多返回的结果数(默认用 LLM_CONFIG 配置)

    Returns:
        list[dict]: 每项包含 title/url/snippet
    """
    if max_results is None:
        max_results = LLM_CONFIG.get('max_search_results', 8)

    search_query = f"暗黑4 {keyword} 攻略"
    encoded = urllib.parse.quote(search_query)
    url = f"https://www.bing.com/search?q={encoded}&count={max_results * 2}"

    logger.info(f"[OnlineSearch] Bing 搜索: '{search_query}'")

    try:
        resp = requests.get(url, headers=BING_HEADERS, timeout=10)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        logger.warning(f"[OnlineSearch] Bing 搜索请求失败: {e}")
        return []

    results = _parse_bing_results(html)
    logger.info(f"[OnlineSearch] Bing 解析出 {len(results)} 条结果")
    return results[:max_results]


def _parse_bing_results(html):
    """解析 Bing 搜索结果 HTML,提取标题/URL/摘要

    Bing 搜索结果结构(cn.bing.com 实测):
      <li class="b_algo" data-id iid=SERP.5333>
        <h2 class=""><a target="_blank" href="..." h="...">标题</a></h2>
        <p>摘要...</p>
      </li>
    """
    results = []

    # 匹配每个搜索结果块(允许 li 标签有额外属性如 data-id iid=SERP.xxx)
    blocks = re.findall(
        r'<li[^>]*class="b_algo"[^>]*>(.*?)</li>',
        html,
        re.DOTALL,
    )

    for block in blocks:
        try:
            # 提取 URL 和标题(h2 > a,允许 a 有多个属性)
            title_match = re.search(
                r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                block,
                re.DOTALL,
            )
            if not title_match:
                continue

            link_url = title_match.group(1)
            title_html = title_match.group(2)
            title = _strip_html_tags(title_html).strip()

            # 跳过 Bing 内部链接
            if 'bing.com/aclk' in link_url or 'go.microsoft.com' in link_url:
                continue

            # 提取摘要(可能在 <p> 或 class="b_caption" 里)
            snippet = ''
            snippet_match = re.search(
                r'<p[^>]*>(.*?)</p>',
                block,
                re.DOTALL,
            )
            if snippet_match:
                snippet = _strip_html_tags(snippet_match.group(1)).strip()

            if title and link_url:
                results.append({
                    'title': title,
                    'url': link_url,
                    'snippet': snippet,
                })
        except Exception:
            continue

    return results


def _strip_html_tags(text):
    """去除 HTML 标签,保留纯文本"""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    return text


def _build_llm_prompt(query, search_results):
    """构造 LLM 汇总 prompt(供所有 LLM provider 共用)"""
    results_text = ""
    for i, r in enumerate(search_results, 1):
        results_text += (
            f"[{i}] 标题: {r['title']}\n"
            f"    URL: {r['url']}\n"
            f"    摘要: {r['snippet']}\n\n"
        )

    trusted_str = ", ".join(TRUSTED_DOMAINS)

    prompt = (
        f"你是一个暗黑破坏神4(Diablo 4)游戏攻略助手。\n"
        f"玩家通过 OCR 识别到的任务/场景文字是: \"{query}\"\n\n"
        f"以下是 Bing 搜索到的相关网页结果:\n\n"
        f"{results_text}\n\n"
        f"请从以上搜索结果中找出最匹配这个任务的图文攻略页面,要求:\n"
        f"1. 优先选择可信游戏攻略网站(如 {trusted_str})\n"
        f"2. 内容必须是暗黑破坏神4的攻略,不要选无关页面\n"
        f"3. 优先选择图文攻略、流程攻略,而非新闻/视频\n\n"
        f"请用 JSON 格式回复(只输出 JSON,不要其他文字):\n"
        f'{{"best_index": <结果编号>, "summary": "<50字以内的攻略汇总说明>"}}'
    )
    return prompt


def _parse_llm_response(content, search_results):
    """解析 LLM 回复的 JSON,返回最佳结果

    Args:
        content: LLM 回复的文本(含 JSON)
        search_results: Bing 搜索结果列表

    Returns:
        dict: {'best_url', 'title', 'summary'} 或 None
    """
    if not content:
        return None

    content = content.strip()
    logger.info(f"[OnlineSearch] LLM 回复: {content[:200]}")

    # 容错:去掉可能的 markdown 代码块标记
    content_clean = content
    if content_clean.startswith('```'):
        content_clean = re.sub(r'^```(?:json)?\s*', '', content_clean)
        content_clean = re.sub(r'\s*```$', '', content_clean)

    try:
        parsed = json.loads(content_clean)
    except json.JSONDecodeError as e:
        logger.warning(f"[OnlineSearch] LLM 回复 JSON 解析失败: {e}")
        return None

    best_index = int(parsed.get('best_index', 0))
    summary = parsed.get('summary', '')

    if 1 <= best_index <= len(search_results):
        best = search_results[best_index - 1]
        return {
            'best_url': best['url'],
            'title': best['title'],
            'summary': summary,
        }
    logger.warning(f"[OnlineSearch] LLM 返回的 best_index={best_index} 超出范围")
    return None


def _call_gas_llm(query, search_results):
    """调用游戏助手服务端内置 LLM(Qwen3)对搜索结果进行汇总

    通过 Knowledge 服务的 query 接口调用本地 LLM,无需 API Key。
    服务端 LLM 已在 gameassistanttoolserver.json 中启用(iGPU 推理)。

    Args:
        query: 用户搜索的任务名
        search_results: Bing 搜索结果列表

    Returns:
        dict: {'best_url', 'title', 'summary'} 或 None
    """
    from config import SDK_CONFIG

    server_url = SDK_CONFIG.get('server_url', 'http://127.0.0.1:9190').rstrip('/')
    instance_id = SDK_CONFIG.get('instance_id', 'd4_assistant')
    timeout = LLM_CONFIG.get('timeout', 30)

    prompt = _build_llm_prompt(query, search_results)

    try:
        logger.info(f"[OnlineSearch] 调用游戏助手服务端 LLM (Qwen3) 汇总...")
        # Knowledge query 接口:不传 knowledge_id 时走纯 LLM 回复(SSE 流式)
        resp = requests.post(
            f"{server_url}/knowledge/service/query/{instance_id}",
            json={'text': prompt},
            stream=True,
            timeout=timeout,
        )
        resp.raise_for_status()

        # 拼接 SSE 流的 message 字段
        content = ''
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith('data: '):
                continue
            try:
                chunk = json.loads(line[len('data: '):])
            except json.JSONDecodeError:
                continue
            msg = (chunk.get('data') or {}).get('message', '')
            content += msg
            if chunk.get('fin') is True:
                break

        return _parse_llm_response(content, search_results)
    except Exception as e:
        logger.warning(f"[OnlineSearch] 游戏助手服务端 LLM 调用失败: {e}")
        return None


def _call_zhipu_llm(query, search_results):
    """调用智谱 GLM 对搜索结果进行汇总(provider='zhipu' 回退方案)

    Args:
        query: 用户搜索的任务名
        search_results: Bing 搜索结果列表

    Returns:
        dict: {'best_url': str, 'summary': str, 'title': str} 或 None
    """
    api_key = LLM_CONFIG.get('api_key', '')
    if not api_key:
        logger.warning("[OnlineSearch] 智谱 API Key 未配置(ZHIPU_API_KEY 环境变量)")
        return None

    prompt = _build_llm_prompt(query, search_results)

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': LLM_CONFIG.get('model', 'glm-4-flash'),
        'messages': [
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.3,
    }

    base_url = LLM_CONFIG.get(
        'base_url',
        'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    )
    timeout = LLM_CONFIG.get('timeout', 30)

    try:
        logger.info(f"[OnlineSearch] 调用智谱 GLM ({payload['model']}) 汇总...")
        resp = requests.post(base_url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        content = data['choices'][0]['message']['content']
        return _parse_llm_response(content, search_results)
    except Exception as e:
        logger.warning(f"[OnlineSearch] 智谱 GLM 调用失败: {e}")
        return None


def _fallback_best_result(query, search_results):
    """LLM 不可用时的兜底:用简单评分算法选择最佳结果

    评分规则:
      - 来源可信域名 +5
      - 标题包含"攻略"/"流程"/"图文" +3
      - 标题包含任务关键词 +2
      - 标题包含"暗黑4"/"diablo" +2
    """
    if not search_results:
        return None

    query_lower = query.lower()
    best_score = -1
    best = search_results[0]

    for r in search_results:
        score = 0
        url_lower = r['url'].lower()
        title_lower = r['title'].lower()

        for domain in TRUSTED_DOMAINS:
            if domain in url_lower:
                score += 5
                break

        for kw in ['攻略', '流程', '图文', '指南']:
            if kw in title_lower:
                score += 3
                break

        if query_lower and query_lower in title_lower:
            score += 2

        for kw in ['暗黑4', 'diablo', 'd4']:
            if kw in title_lower:
                score += 2
                break

        if score > best_score:
            best_score = score
            best = r

    return {
        'best_url': best['url'],
        'title': best['title'],
        'summary': f"(智能评分) {best['title'][:40]}",
    }


def search_and_summarize(keyword):
    """搜索任务攻略并用 LLM 汇总,返回最佳攻略信息

    Args:
        keyword: OCR 识别到的任务文字

    Returns:
        dict: {'best_url', 'title', 'summary'} 或 None
    """
    if not keyword or len(keyword) < 2:
        return None

    # 1. Bing 搜索
    results = _search_bing(keyword)
    if not results:
        logger.warning("[OnlineSearch] Bing 搜索无结果")
        return None

    # 2. 优先用 LLM 汇总(根据 provider 选择)
    provider = LLM_CONFIG.get('provider', 'gas')
    if provider == 'zhipu':
        llm_result = _call_zhipu_llm(keyword, results)
    else:
        llm_result = _call_gas_llm(keyword, results)
        # 服务端 LLM 失败时回退到智谱 GLM(若已配置 API Key)
        if llm_result is None and LLM_CONFIG.get('api_key'):
            logger.info("[OnlineSearch] 服务端 LLM 失败,回退到智谱 GLM")
            llm_result = _call_zhipu_llm(keyword, results)

    if llm_result:
        logger.info(
            f"[OnlineSearch] LLM 汇总成功: {llm_result['title']} -> {llm_result['best_url']}"
        )
        return llm_result

    # 3. LLM 不可用时兜底
    fallback = _fallback_best_result(keyword, results)
    if fallback:
        logger.info(
            f"[OnlineSearch] 兜底评分: {fallback['title']} -> {fallback['best_url']}"
        )
        return fallback

    return None
