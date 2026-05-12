import os
import base64
import json
import requests
import time

TOKEN = os.environ.get("GITHUB_TOKEN", "")
OWNER = "alexgang"
REPO = "diablo4-game-assistant"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}
API = "https://api.github.com"

PROJECT_DIR = r"c:\AIPC\game assistant\demo test"

UPLOAD_FILES = [
    ".gitignore",
    "config.py",
    "content_indexer.py",
    "data_spider.py",
    "game_data.py",
    "game_detector.py",
    "gui.py",
    "index.html",
    "main.py",
    "ocr_recognizer.py",
    "realtime_assistant.py",
    "screen_capture.py",
    "script.js",
    "styles.css",
    "requirements.txt",
    "voice_assistant.py",
    "overlay.py",
    "hotkey_manager.py",
    "damage_analyzer.py",
    "README.md",
    "test_core.py",
    "test_api.py",
    "test_selenium.py",
    "test_overlay.py",
    "test_hotkey.py",
    "test_damage.py",
]


def get_file_sha(path):
    r = requests.get(
        f"{API}/repos/{OWNER}/{REPO}/contents/{path}",
        headers=HEADERS,
        params={"ref": "main"},
    )
    if r.status_code == 200:
        return r.json().get("sha")
    return None


def create_or_update_file(path, content, sha=None):
    data = {
        "message": f"update {path}" if sha else f"add {path}",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": "main",
    }
    if sha:
        data["sha"] = sha

    r = requests.put(
        f"{API}/repos/{OWNER}/{REPO}/contents/{path}",
        headers=HEADERS,
        json=data,
    )
    return r


def main():
    print("=== 通过 GitHub Contents API 推送代码 ===")

    success = 0
    fail = 0

    for i, fname in enumerate(UPLOAD_FILES):
        fpath = os.path.join(PROJECT_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  [{i+1}/{len(UPLOAD_FILES)}] 跳过: {fname}")
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        sha = get_file_sha(fname)
        action = "更新" if sha else "新建"
        print(f"  [{i+1}/{len(UPLOAD_FILES)}] {action}: {fname} ({len(content)} chars)")

        r = create_or_update_file(fname, content, sha)

        if r.status_code in (200, 201):
            success += 1
            print(f"    OK")
        else:
            fail += 1
            print(f"    失败: {r.status_code} - {r.text[:150]}")

        time.sleep(0.5)

    print(f"\n=== 完成: {success} 成功, {fail} 失败 ===")
    print(f"仓库地址: https://github.com/{OWNER}/{REPO}")


if __name__ == "__main__":
    main()
