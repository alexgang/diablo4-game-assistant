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
    print("=== 暗金装备元素结构 ===")
    driver.get('https://www.d2core.com/d4/data/uniqueItem')
    time.sleep(10)
    driver.execute_script("window.scrollTo(0, 300);")
    time.sleep(2)

    items = driver.find_elements(By.CSS_SELECTOR, '.d4-db-item')
    if items:
        item = items[0]
        html = item.get_attribute('innerHTML')
        print(f"第一个装备HTML:\n{html[:800]}")

        print("\n子元素class列表:")
        children = item.find_elements(By.XPATH, './/*')
        for child in children[:15]:
            cls = child.get_attribute('class') or ''
            text = child.text.strip()[:50]
            tag = child.tag_name
            print(f"  <{tag} class='{cls}'> {text}")

    print("\n\n=== 技能元素结构 ===")
    driver.get('https://www.d2core.com/d4/data/skill')
    time.sleep(10)
    driver.execute_script("window.scrollTo(0, 300);")
    time.sleep(2)

    skills = driver.find_elements(By.CSS_SELECTOR, '.d4-db-item')
    if skills:
        skill = skills[0]
        html = skill.get_attribute('innerHTML')
        print(f"第一个技能HTML:\n{html[:800]}")

        print("\n子元素class列表:")
        children = skill.find_elements(By.XPATH, './/*')
        for child in children[:15]:
            cls = child.get_attribute('class') or ''
            text = child.text.strip()[:50]
            tag = child.tag_name
            print(f"  <{tag} class='{cls}'> {text}")

    print("\n\n=== 构筑详情页结构 ===")
    driver.get('https://www.d2core.com/d4/planner?bd=1STz')
    time.sleep(10)

    print("技能相关元素:")
    skill_els = driver.find_elements(By.CSS_SELECTOR, '[class*="skill"]')
    for el in skill_els[:10]:
        cls = el.get_attribute('class') or ''
        text = el.text.strip()[:60]
        tag = el.tag_name
        print(f"  <{tag} class='{cls[:40]}'> {text}")

    print("\n装备相关元素:")
    equip_els = driver.find_elements(By.CSS_SELECTOR, '[class*="item"], [class*="equip"], [class*="gear"], [class*="slot"]')
    for el in equip_els[:15]:
        cls = el.get_attribute('class') or ''
        text = el.text.strip()[:60]
        tag = el.tag_name
        print(f"  <{tag} class='{cls[:40]}'> {text}")

    print("\n威能相关元素:")
    aspect_els = driver.find_elements(By.CSS_SELECTOR, '[class*="aspect"], [class*="affix"], [class*="power"]')
    for el in aspect_els[:10]:
        cls = el.get_attribute('class') or ''
        text = el.text.strip()[:60]
        tag = el.tag_name
        print(f"  <{tag} class='{cls[:40]}'> {text}")

finally:
    driver.quit()
