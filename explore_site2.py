#!/usr/bin/env python3
"""深入探索d2core.com数据库和构筑页面"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    print("=== 1. 探索数据库总页面 ===")
    driver.get('https://www.d2core.com/d4/data')
    time.sleep(8)

    data_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/d4/data/"]')
    seen = set()
    for link in data_links:
        href = link.get_attribute('href') or ''
        text = link.text.strip()
        if href not in seen and text:
            seen.add(href)
            print(f"  [{text}] -> {href}")

    all_links = driver.find_elements(By.TAG_NAME, 'a')
    for link in all_links:
        href = link.get_attribute('href') or ''
        text = link.text.strip()
        if text and '/d4/data' in href and href not in seen:
            seen.add(href)
            print(f"  [{text}] -> {href}")

    print("\n=== 2. 探索暗金数据库 - 全部306条 ===")
    driver.get('https://www.d2core.com/d4/data/uniqueItem')
    time.sleep(10)

    for scroll_round in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    items = driver.find_elements(By.CSS_SELECTOR, '.d4-db-item')
    print(f"  暗金装备总数: {len(items)}")

    if items:
        print(f"\n  前3个装备详情:")
        for item in items[:3]:
            try:
                title = item.find_element(By.CSS_SELECTOR, '.dbi-title').text.strip()
                print(f"\n  装备名: {title}")
                all_text = item.text
                print(f"  全部文本: {all_text[:200]}")
            except Exception as e:
                print(f"  解析失败: {e}")

    print("\n=== 3. 探索技能数据库 ===")
    driver.get('https://www.d2core.com/d4/data/skill')
    time.sleep(10)

    for scroll_round in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    skills = driver.find_elements(By.CSS_SELECTOR, '.d4-db-item')
    print(f"  技能总数: {len(skills)}")

    if not skills:
        items_alt = driver.find_elements(By.CSS_SELECTOR, '[class*="skill"], [class*="db-"]')
        print(f"  备选元素: {len(items_alt)}")

    body_text = driver.find_element(By.TAG_NAME, 'body').text[:500]
    print(f"  页面内容: {body_text[:300]}")

    print("\n=== 4. 探索构筑页面 ===")
    driver.get('https://www.d2core.com/d4/builds')
    time.sleep(10)

    for scroll_round in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    build_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/d4/planner"], a[href*="/d4/builds/"]')
    seen_builds = set()
    for link in build_links:
        href = link.get_attribute('href') or ''
        text = link.text.strip()
        if href not in seen_builds and text and len(text) > 3:
            seen_builds.add(href)
            print(f"  [{text[:60]}] -> {href}")

    print(f"\n  构筑链接总数: {len(seen_builds)}")

    print("\n=== 5. 探索攻略详情页 ===")
    driver.get('https://www.d2core.com/d4/planner?bd=1STz')
    time.sleep(10)

    body_text = driver.find_element(By.TAG_NAME, 'body').text
    print(f"  页面内容前500字: {body_text[:500]}")

    skill_elements = driver.find_elements(By.CSS_SELECTOR, '[class*="skill"], [class*="point"], [class*="build"], [class*="planner"]')
    print(f"\n  技能/构筑相关元素: {len(skill_elements)}")
    for el in skill_elements[:10]:
        cls = el.get_attribute('class') or ''
        text = el.text.strip()[:80]
        if text:
            print(f"    [{cls[:30]}] {text}")

finally:
    driver.quit()
