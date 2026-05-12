#!/usr/bin/env python3
"""探索d2core.com网站结构，找到所有数据页面"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    print("=== 探索首页导航 ===")
    driver.get('https://www.d2core.com/d4')
    time.sleep(8)

    nav_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/d4/"]')
    seen = set()
    for link in nav_links:
        href = link.get_attribute('href') or ''
        text = link.text.strip()
        if href and href not in seen and text:
            seen.add(href)
            print(f"  [{text}] -> {href}")

    print(f"\n=== 探索数据库页面 ===")
    db_urls = [
        'https://www.d2core.com/d4/data/uniqueItem',
        'https://www.d2core.com/d4/data/legendaryItem',
        'https://www.d2core.com/d4/data/setItem',
        'https://www.d2core.com/d4/data/skill',
        'https://www.d2core.com/d4/data/class',
        'https://www.d2core.com/d4/data/aspect',
    ]

    for url in db_urls:
        print(f"\n尝试: {url}")
        try:
            driver.get(url)
            time.sleep(5)
            title = driver.title
            body_text = driver.find_element(By.TAG_NAME, 'body').text[:200]
            print(f"  标题: {title}")
            print(f"  内容: {body_text[:150]}...")
        except Exception as e:
            print(f"  失败: {e}")

    print("\n=== 探索首页所有链接 ===")
    driver.get('https://www.d2core.com/d4')
    time.sleep(8)
    all_links = driver.find_elements(By.TAG_NAME, 'a')
    for link in all_links:
        href = link.get_attribute('href') or ''
        text = link.text.strip()
        if text and len(text) > 1 and '/d4/' in href:
            print(f"  [{text[:50]}] -> {href}")

    print("\n=== 探索导航栏/菜单 ===")
    nav_elements = driver.find_elements(By.CSS_SELECTOR, 'nav a, .nav a, .menu a, .sidebar a, [class*="nav"] a, [class*="menu"] a')
    for el in nav_elements:
        href = el.get_attribute('href') or ''
        text = el.text.strip()
        if text and href:
            print(f"  [{text}] -> {href}")

finally:
    driver.quit()
