#!/usr/bin/env python3
"""
从 Blizzard 官方下载 Diablo 4 截图

来源: https://blizzard.gamespress.com/zh-CN/Diablo-IV/Focus/Diablo-IV-screenshots-66323
"""

import os
import sys
import requests
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), 'game_screenshots')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Season of Blood Screenshots - 从 GamesPress 提取的真实 URL
SCREENSHOTS = [
    # Erys 角色头像
    ("Diablo4_Season_of_Blood_Erys_Headshot", "https://blizzard.gamespress.com/Files/File?url=Q81XdHF0AZe4uWM4lLOQQd7x8HGL%2baOSgQvmSqo3pyIvT%2fvnzXhGwKr7g4vg2vwNy%2fdAHqTzwVUEXJsGtqRcfal76kQZAVlPMBhe5winJNaxVGYUwdtHWkaj0pmMOA4E7T5hG5pGW0zt0ghgLs1cN%2bVuyBZP7CKXbvTW%2fewKCF58pF%2bAWcn6zl%2bl%2fWdI3ySAnp3RY6rmdTImViPe5aNz5jjuseCQxopw3eUmpTMHUTgU4xDAtvCtAgkf%2fHUS18TiTAj6fg6rwIf7TShpjAVawReSkTkFr%2bXsEBDXxPdY7NU6bNIBz2tLaHykC8WkRn3z07unQWdaHJkgeV9FdxEfOBPejWDrHxsaNcr2UsvFfPAY1pLeat3AEawnmxWub9mpsWUPPGARPZz%2bWNgFbZ5QM6em56F3iMqAULwTUMKygKa0JG9kcu7%2bdTJeC%2bXBKnIl5IX6JpkYGBP5lGg%2bWLntMnZhrFL2K2ateBNxrmHh6CZ7LuopgTyE0M2WJlvzFoom180sE9HxP1sZg70a%2blH13%2b%2fO7AUJVoPGJ5aIHqjnQf4%3d"),
    
    # Blood Pact 01
    ("Diablo4_Season_of_Blood_Blood_Pact_01", "https://blizzard.gamespress.com/Files/File?url=Q81XdHF0AZe4uWM4lLOQQd7x8HGL%2baOSgQvmSqo3pyIvT%2fvnzXhGwKr7g4vg2vwNy%2fdAHqTzwVUEXJsGtqRcfal76kQZAVlPMBhe5winJNaxVGYUwdtHWkaj0pmMOA4E7T5hG5pGW0zt0ghgLs1cN9IwlWBFu%2fToqqOZ61nACSf%2bMe0sFXuiMYsWbjS9GcFQmtEiGl9av6In94mKt65%2fcLuPbDatAvCmjnWfitL%2bmyEONtD0DCTUXQ5szhsku5ioBWta9j7DeXt2McSxNj5w77B%2bqCzbqpJ5vzgc7PlOjx6pSXkSpJ7aFSO6HFBM8uuQmSB%2b044BwUMSgkYgbvyELJTXzxvhkIisnOM7G34FnNiuagpcMAgn0el4eBXfYe6vf5aQ0Vhdok%2fJzWxLxqzOqUHnBG0Lwq4NOw6Hqdm0NfwJk9IW%2bfL%2f7wSJcjuYyblITap8OYdnmnPfyFHKBhjT6YqZ5XfBAWavbrTH%2bMjgbheMECCsmA9Svm7CoLsghRN1XMiOJ2a8ALEiKKx8gLcSUjWLd7fzH6TbFiR9aOyhOUgZxTauqS9i21t6CzYyUmim"),
    
    # Blood Pact 02
    ("Diablo4_Season_of_Blood_Blood_Pact_02", "https://blizzard.gamespress.com/Files/File?url=Q81XdHF0AZe4uWM4lLOQQd7x8HGL%2baOSgQvmSqo3pyIvT%2fvnzXhGwKr7g4vg2vwNy%2fdAHqTzwVUEXJsGtqRcfal76kQZAVlPMBhe5winJNaxVGYUwdtHWkaj0pmMOA4E7T5hG5pGW0zt0ghgLs1cN9IwlWBFu%2fToqqOZ61nACSfKBASImSbedVfD3wsUukdMGATdhP9JZrPgM8AQWMOJxi1I7IfOCt2NraYlOIG%2bfzq1o3r2CKpsxvxfPnVrx1699cpl2rhMPwlEWqQH7hehT%2b%2fvRaxPDTITe1dmIDJwIu%2bikwGjrfK8TFsWA90QMf0Mh0sjjdwR3X8eeb7a%2bO4kg1S2MNKvCTISYOHkUME%2bXopom8CLslqq43iUDLt0JAlJV2OVhCNm7lz6%2fDRbU80RyCS6YDmNbK2%2fMDYnQA9%2fjYZPYZ3wYgswdon%2fx7p0JOZqtbdScEgY%2bBDk899ZmwlhoOCn2e0k6gr9%2b9Hqri3lDNIAqtm4LLzMl9qgD4O4EmAMMhn1NTYvi6KBD9VBPuNGh%2fU36z7FnrtmuuGtaBQK9yyeg9C3DUjXEvMlTnRYXNz%2f"),
    
    # Dungeon World 01
    ("Diablo4_Season_of_Blood_Dungeon_World_01", "https://blizzard.gamespress.com/Files/File?url=Q81XdHF0AZe4uWM4lLOQQd7x8HGL%2baOSgQvmSqo3pyIvT%2fvnzXhGwKr7g4vg2vwNy%2fdAHqTzwVUEXJsGtqRcfal76kQZAVlPMBhe5winJNaxVGYUwdtHWkaj0pmMOA4E7T5hG5pGW0zt0ghgLs1cN9IwlWBFu%2fToqqOZ61nACScCI9tavKa9jfu6f97pdo1t5BgvmFkF5V35NK95wp1yj59A%2fhCb5JVBHok056xXkMYx0P5dwg05AWdYjKV5GG1SGHBaB5hcyk5ahbkpdMoiK28Jm9Rz2pPJi00SJ5EGgTklhbxb6s%2fSlT46CT5pWDSPTD8b6dwNpddJYWfiBhvBBDBiADdgWoQK1L92cOuP%2f8Km96xr04Wo1uC5vf5OQEMaeVsS5FzEZJTcCI2pRV9QB6K6ueKzLcq0AWSe%2f4TdMmhoqUQ%2fPVuNdJ85%2by9iq57LLMbqPHHiIMPNHZn21VdI6D%2bBp35C%2f6F%2f5vDz3guh8PUfDOYChowx%2fUz9%2bFo6G5QZ2QjJpio%2bQguexGzIQ8C21TWwRZGu64hGBQlze3Kr4jyvwGNueUbOtUYepGbMXtPg"),
    
    # Dungeon World 02
    ("Diablo4_Season_of_Blood_Dungeon_World_02", "https://blizzard.gamespress.com/Files/File?url=Q81XdHF0AZe4uWM4lLOQQd7x8HGL%2baOSgQvmSqo3pyIvT%2fvnzXhGwKr7g4vg2vwNy%2fdAHqTzwVUEXJsGtqRcfal76kQZAVlPMBhe5winJNaxVGYUwdtHWkaj0pmMOA4E7T5hG5pGW0zt0ghgLs1cN9IwlWBFu%2fToqqOZ61nACScCI9tavKa9jfu6f97pdo1tMF6EhndFuvQmFkpONtx8MZYVY617GO%2f8oyDTJShpQjxKNpUiTr0xIKvG9ySGHE%2fGDPs4M36iDdrbZBwA3AxIsRM9jc35B28L%2fQdPfR8OY03qJLh6Uu1MskN1NJqUoRGwgLtPf4NjrCFu1BOJUVsmSpqZkoBZdaT27RHgxkQILzZPxRalt9JqmCYNnPZqNxPpQEIBZqWd22XIfhZLybLcj0gKW3lvHOPncbF7%2bp8UgULMTz6ryKYsmFhLdD%2bkltxEAbJjJBFfWi7f6RKR7JK8XifZUZgTnI9fY64secw%2fqe4n3LShau%2fsowQHiiFsRs%2fIOvFjcz5i4MmfGU3ow%2futoZcsN4SQLt8x6EcIqazfP8SgH2TBnK%2bKN4UtHuQY7OSX"),
]

def download_image(name, url):
    save_path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")

    if os.path.exists(save_path):
        size = os.path.getsize(save_path) / 1024 / 1024
        if size > 0.1:
            print(f"  已存在: {name}.png ({size:.1f} MB)")
            return True
        else:
            os.remove(save_path)
            print(f"  删除无效文件: {name}.png")

    print(f"  下载中: {name}...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Referer': 'https://blizzard.gamespress.com/',
        }
        response = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
        response.raise_for_status()

        if len(response.content) < 10000:
            print(f"  ✗ 文件太小，可能是错误页面: {len(response.content)} bytes")
            return False

        with open(save_path, 'wb') as f:
            f.write(response.content)

        size = os.path.getsize(save_path) / 1024 / 1024
        print(f"  ✓ 已保存: {name}.png ({size:.1f} MB)")
        return True
    except Exception as e:
        print(f"  ✗ 下载失败: {e}")
        return False

def main():
    print("=" * 60)
    print("Diablo 4 官方截图下载工具")
    print("=" * 60)
    print(f"\n保存目录: {SCREENSHOTS_DIR}")
    print(f"截图数量: {len(SCREENSHOTS)}")

    success = 0
    failed = 0

    for name, url in SCREENSHOTS:
        if download_image(name, url):
            success += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"下载完成: 成功 {success}, 失败 {failed}")
    print("=" * 60)

    if success > 0:
        print("\n现在可以运行 build_vision_index.py 构建 Vision 索引")
        print(f"\n已下载的截图保存在: {SCREENSHOTS_DIR}")

if __name__ == "__main__":
    main()
