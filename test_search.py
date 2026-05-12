from game_detector import GameDetector
from voice_assistant import VoiceAssistant

detector = GameDetector(use_web_data=False, use_ocr=False)
voice_assistant = VoiceAssistant(content_indexer=detector.indexer)

query = "游侠升级攻略"
print(f"=== 测试搜索: '{query}' ===")

# 模拟 manual_search 的逻辑
result = voice_assistant.process_text(query)
print(f"\n1. process_text 返回结果:")
print(f"   - text: {result.get('text', '')}")
print(f"   - intent: {result.get('intent', '')}")
print(f"   - query: {result.get('query', '')}")
print(f"   - results: {len(result.get('results', []))} 条")
print(f"   - response: {result.get('response', '')}")
print(f"   - spoken: {result.get('spoken', False)}")

# 检查 results 内容
results = result.get('results', [])
if results:
    print(f"\n2. 搜索结果详情:")
    for i, r in enumerate(results[:3], 1):
        name = r.get('data', {}).get('name', r.get('data', {}).get('title', ''))
        print(f"   [{i}] {name}")
