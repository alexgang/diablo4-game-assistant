
import sys
sys.path.insert(0, '.')
from sdk_client import GamingAssistantSDK
from config import SDK_CONFIG
from scene_classifier import classify_scene
import dxcam
import cv2
import os

print("=== 测试 dxcam 截图 ===")
frame = None
selected_out_idx = None
for out_idx in [0, 1, 2, 3]:
    print(f"Trying output_idx={out_idx}...")
    try:
        camera = dxcam.create(output_idx=out_idx)
        frame = camera.grab()
        camera.release()
        if frame is not None:
            print(f"  ✓ Success: shape={frame.shape}, mean={frame.mean():.2f}")
            selected_out_idx = out_idx
            break
        else:
            print(f"  ✗ Frame is None")
    except Exception as e:
        print(f"  ✗ Error: {e}")

if frame is None:
    print("❌ 无法截取任何画面")
    sys.exit(1)

os.makedirs('game_screenshots', exist_ok=True)
test_path = 'game_screenshots/test_scene_final.png'
cv2.imwrite(test_path, frame)
print(f"✓ 保存到 {test_path}")

print("\n=== 测试 Vision Query ===")
sdk = GamingAssistantSDK(SDK_CONFIG['server_url'])
instance_id = SDK_CONFIG['instance_id']
print(f"Instance: {instance_id}")

results = sdk.vision_query(instance_id, test_path, topk=5, mode='basic')
print(f"Query results: {results}")

if not results:
    print("✗ 无结果，尝试 accurate 模式")
    results = sdk.vision_query(instance_id, test_path, topk=5, mode='accurate')
    print(f"Accurate results: {results}")

if results:
    top = results[0]
    scene_id = top['scene_id']
    score = top['score']
    cat = classify_scene(scene_id)
    print(f"\n✓ 识别结果: {scene_id} ({score*100:.0f}%) -> {cat.value}")
else:
    print("\n❌ 未能识别场景")
