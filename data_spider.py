#!/usr/bin/env python3
"""
数据爬虫模块 - 从暗黑核网站获取游戏数据（扩展版）

功能：
1. 爬取全部暗金装备（306条）
2. 爬取全部技能数据（198条）
3. 爬取构筑列表及详情页（技能加点、装备推荐）
4. 爬取Boss时间表和赛季信息
5. 定期更新本地数据
"""

import json
import time
import os
from datetime import datetime

import requests
from bs4 import BeautifulSoup


class DiabloDataSpider:
    """暗黑核网站数据爬虫 - 扩展版"""

    def __init__(self):
        self.base_url = "https://www.d2core.com/d4"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.session = requests.Session()
        self.cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)

    def _init_selenium(self):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            options = Options()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--lang=zh-CN')
            options.add_argument(f'--user-agent={self.headers["User-Agent"]}')

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            print(f"Selenium初始化失败: {e}")
            return None

    def _scroll_to_bottom(self, driver, max_scrolls=15, wait=2):
        for i in range(max_scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(wait)
            height = driver.execute_script("return document.body.scrollHeight")
            prev_height = driver.execute_script("return window.pageYOffset + window.innerHeight")
            if prev_height >= height:
                break

    def fetch_all_unique_items(self):
        """爬取全部暗金装备（306条）"""
        print("  获取暗金装备数据（全部）...")
        url = f"{self.base_url}/data/uniqueItem"
        driver = self._init_selenium()
        if not driver:
            return []

        try:
            driver.get(url)
            time.sleep(10)
            self._scroll_to_bottom(driver, max_scrolls=20, wait=2)

            from selenium.webdriver.common.by import By
            items = []
            item_elements = driver.find_elements(By.CSS_SELECTOR, '.d4-db-item')
            print(f"  找到 {len(item_elements)} 个暗金装备元素")

            for item_el in item_elements:
                try:
                    title_el = item_el.find_element(By.CSS_SELECTOR, '.dbi-title')
                    name = title_el.text.strip()
                    if not name or len(name) < 2:
                        continue

                    item_type = ''
                    try:
                        type_el = item_el.find_element(By.CSS_SELECTOR, '.dbi-subtitle')
                        item_type = type_el.text.strip()
                    except Exception:
                        pass

                    stats = []
                    for css in ['.unique-drop-boss-text', '.unique-base-attrs-content', '.database-line']:
                        try:
                            el = item_el.find_element(By.CSS_SELECTOR, css)
                            text = el.text.strip()
                            if text:
                                stats.append(text)
                        except Exception:
                            pass

                    item_data = {
                        'name': name,
                        'rarity': '暗金',
                        'type': item_type,
                        'stats': stats,
                    }
                    items.append(item_data)
                except Exception:
                    continue

            print(f"  成功解析 {len(items)} 件暗金装备")
            return items

        except Exception as e:
            print(f"  暗金装备页面加载失败: {e}")
        finally:
            driver.quit()

        return []

    def fetch_all_skills(self):
        """爬取全部技能数据（198条）"""
        print("  获取技能数据（全部）...")
        url = f"{self.base_url}/data/skill"
        driver = self._init_selenium()
        if not driver:
            return []

        try:
            driver.get(url)
            time.sleep(10)
            self._scroll_to_bottom(driver, max_scrolls=15, wait=2)

            from selenium.webdriver.common.by import By
            skills = []
            skill_elements = driver.find_elements(By.CSS_SELECTOR, '.d4-db-item')
            print(f"  找到 {len(skill_elements)} 个技能元素")

            for skill_el in skill_elements:
                try:
                    title_el = skill_el.find_element(By.CSS_SELECTOR, '.dbi-title')
                    name = title_el.text.strip()
                    if not name or len(name) < 2:
                        continue

                    sub_title = ''
                    try:
                        sub_el = skill_el.find_element(By.CSS_SELECTOR, '.dbi-tag')
                        sub_title = sub_el.text.strip()
                    except Exception:
                        pass

                    tags = []
                    try:
                        tag_els = skill_el.find_elements(By.CSS_SELECTOR, '.skill-tags .dbi-tag-line')
                        for tag_el in tag_els:
                            tag_text = tag_el.text.strip()
                            if tag_text:
                                tags.append(tag_text)
                    except Exception:
                        pass
                    if not tags:
                        try:
                            tag_container = skill_el.find_element(By.CSS_SELECTOR, '.skill-tags')
                            tags = [t.strip() for t in tag_container.text.split() if t.strip()]
                        except Exception:
                            pass

                    description = ''
                    try:
                        desc_el = skill_el.find_element(By.CSS_SELECTOR, '.database-line')
                        description = desc_el.text.strip()
                    except Exception:
                        pass

                    skill_data = {
                        'name': name,
                        'class': sub_title,
                        'tags': tags,
                        'description': description,
                    }
                    skills.append(skill_data)
                except Exception:
                    continue

            print(f"  成功解析 {len(skills)} 个技能")
            return skills

        except Exception as e:
            print(f"  技能页面加载失败: {e}")
        finally:
            driver.quit()

        return []

    def fetch_build_list(self):
        """爬取构筑列表"""
        print("  获取构筑列表...")
        url = f"{self.base_url}/builds"
        driver = self._init_selenium()
        if not driver:
            return []

        try:
            driver.get(url)
            time.sleep(10)
            self._scroll_to_bottom(driver, max_scrolls=20, wait=2)

            from selenium.webdriver.common.by import By
            builds = []
            build_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/d4/planner?bd="]')

            seen = set()
            for link in build_links:
                try:
                    href = link.get_attribute('href') or ''
                    text = link.text.strip()
                    if not text or len(text) < 3 or href in seen:
                        continue
                    if text == '新建构筑':
                        continue
                    seen.add(href)

                    bd_id = ''
                    if 'bd=' in href:
                        bd_id = href.split('bd=')[-1].split('&')[0]

                    tags = []
                    try:
                        parent = link.find_element(By.XPATH, './..')
                        tag_els = parent.find_elements(By.CSS_SELECTOR, '[class*="tag"]')
                        for tag_el in tag_els:
                            tag_text = tag_el.text.strip()
                            if tag_text and tag_text != text:
                                tags.append(tag_text)
                    except Exception:
                        pass

                    builds.append({
                        'title': text,
                        'url': href,
                        'bd_id': bd_id,
                        'tags': tags,
                    })
                except Exception:
                    continue

            print(f"  找到 {len(builds)} 个构筑")
            return builds

        except Exception as e:
            print(f"  构筑列表页面加载失败: {e}")
        finally:
            driver.quit()

        return []

    def fetch_build_detail(self, bd_id):
        """爬取单个构筑详情页（技能加点、装备推荐）"""
        url = f"{self.base_url}/planner?bd={bd_id}"
        driver = self._init_selenium()
        if not driver:
            return None

        try:
            driver.get(url)
            time.sleep(10)

            from selenium.webdriver.common.by import By

            title = ''
            try:
                title_els = driver.find_elements(By.CSS_SELECTOR, '.planner-title-text')
                for t_el in title_els:
                    t = t_el.text.strip()
                    if t and len(t) > 3:
                        title = t
                        break
            except Exception:
                pass
            if not title:
                try:
                    title_el = driver.find_element(By.CSS_SELECTOR, '.planner-title-block')
                    title = title_el.text.strip().split('\n')[0].strip()
                except Exception:
                    pass

            tags = []
            try:
                tag_els = driver.find_elements(By.CSS_SELECTOR, '.planner-tag')
                for tag_el in tag_els:
                    tag_text = tag_el.text.strip()
                    if tag_text:
                        tags.append(tag_text)
            except Exception:
                pass

            author = ''
            try:
                body_text = driver.find_element(By.TAG_NAME, 'body').text
                for line in body_text.split('\n'):
                    line = line.strip()
                    if 'Lv.' in line and len(line) < 30:
                        author = line
                        break
            except Exception:
                pass

            skills = []
            try:
                skill_els = driver.find_elements(By.CSS_SELECTOR, '.skill-slot')
                for skill_el in skill_els:
                    try:
                        img_el = skill_el.find_element(By.TAG_NAME, 'img')
                        alt = img_el.get_attribute('alt') or ''
                        title = img_el.get_attribute('title') or ''
                        skill_name = title or alt
                        if skill_name:
                            skills.append(skill_name)
                    except Exception:
                        pass
            except Exception:
                pass

            equipment = []
            try:
                gear_items = driver.find_elements(By.CSS_SELECTOR, '.gear-item')
                for gear_el in gear_items:
                    gear_text = gear_el.text.strip()
                    lines = [l.strip() for l in gear_text.split('\n') if l.strip()]
                    if lines:
                        name = lines[0]
                        slot = lines[1] if len(lines) > 1 else ''
                        equipment.append({'name': name, 'slot': slot})
            except Exception:
                pass

            aspects = []
            try:
                aspect_els = driver.find_elements(By.CSS_SELECTOR, '.database-line.line-affix')
                for aspect_el in aspect_els:
                    aspect_text = aspect_el.text.strip()
                    if aspect_text:
                        aspects.append(aspect_text)
            except Exception:
                pass

            body_text = ''
            try:
                body_text = driver.find_element(By.TAG_NAME, 'body').text
            except Exception:
                pass

            detail = {
                'bd_id': bd_id,
                'title': title,
                'url': url,
                'tags': tags,
                'author': author,
                'skills': skills,
                'equipment': equipment,
                'aspects': aspects,
                'full_text': body_text[:3000],
            }

            return detail

        except Exception as e:
            print(f"  构筑详情页加载失败 ({bd_id}): {e}")
        finally:
            driver.quit()

        return None

    def fetch_build_details_batch(self, builds, max_count=30):
        """批量爬取构筑详情"""
        print(f"  开始爬取构筑详情（最多 {max_count} 个）...")
        details = []
        count = 0

        for build in builds[:max_count]:
            bd_id = build.get('bd_id', '')
            if not bd_id:
                continue

            count += 1
            print(f"    [{count}/{min(len(builds), max_count)}] {build.get('title', '')[:40]}...")
            detail = self.fetch_build_detail(bd_id)
            if detail:
                details.append(detail)
            time.sleep(1)

        print(f"  成功获取 {len(details)} 个构筑详情")
        return details

    def fetch_home_page_data(self):
        """爬取首页数据（攻略列表、Boss时间表、赛季信息）"""
        print("  获取首页数据...")
        driver = self._init_selenium()
        if not driver:
            return [], [], {}

        try:
            driver.get(self.base_url)
            time.sleep(8)

            from selenium.webdriver.common.by import By

            guides = []
            guide_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/d4/planner?bd="]')
            seen = set()
            for link in guide_links:
                href = link.get_attribute('href') or ''
                text = link.text.strip()
                if text and len(text) > 3 and href not in seen:
                    seen.add(href)
                    guides.append({'title': text, 'url': href})

            boss_schedule = []
            try:
                body_text = driver.find_element(By.TAG_NAME, 'body').text
                for line in body_text.split('\n'):
                    line = line.strip()
                    if any(k in line for k in ['世界Boss', '军团集结', '地狱狂潮']):
                        boss_schedule.append({'name': line, 'time': ''})
            except Exception:
                pass

            season_info = {'season': 'S13', 'name': '清算赛季', 'status': '进行中'}
            try:
                body_text = driver.find_element(By.TAG_NAME, 'body').text
                for line in body_text.split('\n'):
                    if 'S13' in line or '清算' in line:
                        season_info['season'] = 'S13'
                        season_info['name'] = '清算赛季'
                        break
            except Exception:
                pass

            return guides, boss_schedule, season_info

        except Exception as e:
            print(f"  首页加载失败: {e}")
        finally:
            driver.quit()

        return [], [], {}

    def update_local_database(self, max_build_details=30):
        """更新本地数据库（完整版）"""
        print("正在从网站获取最新数据（扩展版）...")
        print("=" * 60)

        guides, boss_schedule, season_info = self.fetch_home_page_data()
        print(f"  首页攻略: {len(guides)} 条")
        print(f"  Boss时间: {len(boss_schedule)} 条")

        equipment = self.fetch_all_unique_items()
        print(f"  暗金装备: {len(equipment)} 件")

        skills = self.fetch_all_skills()
        print(f"  技能数据: {len(skills)} 个")

        builds = self.fetch_build_list()
        print(f"  构筑列表: {len(builds)} 个")

        build_details = []
        if builds:
            build_details = self.fetch_build_details_batch(builds, max_count=max_build_details)
            print(f"  构筑详情: {len(build_details)} 个")

        skills_by_class = {}
        for skill in skills:
            cls = skill.get('class', '未知')
            if cls not in skills_by_class:
                skills_by_class[cls] = []
            skills_by_class[cls].append(skill)

        cache_file = os.path.join(self.cache_dir, 'web_data.json')
        data = {
            'update_time': datetime.now().isoformat(),
            'source': 'website',
            'guides': guides,
            'equipment': equipment,
            'skills': skills,
            'skills_by_class': skills_by_class,
            'builds': builds,
            'build_details': build_details,
            'boss_schedule': boss_schedule,
            'season_info': season_info,
            'stats': {
                'total_guides': len(guides),
                'total_equipment': len(equipment),
                'total_skills': len(skills),
                'total_builds': len(builds),
                'total_build_details': len(build_details),
                'total_boss_schedule': len(boss_schedule),
            }
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n数据已更新: {cache_file}")
        print(f"总计: {len(guides)} 攻略 | {len(equipment)} 装备 | {len(skills)} 技能 | {len(builds)} 构筑 | {len(build_details)} 详情")
        print("=" * 60)
        return data

    def get_cached_data(self):
        cache_file = os.path.join(self.cache_dir, 'web_data.json')
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None


class DataUpdateScheduler:
    def __init__(self, spider, update_interval=3600):
        self.spider = spider
        self.update_interval = update_interval
        self.last_update = None

    def should_update(self):
        if not self.last_update:
            return True
        elapsed = (datetime.now() - self.last_update).total_seconds()
        return elapsed >= self.update_interval

    def run_update(self):
        if self.should_update():
            self.spider.update_local_database()
            self.last_update = datetime.now()


if __name__ == "__main__":
    import sys
    max_details = 10
    if len(sys.argv) > 1:
        try:
            max_details = int(sys.argv[1])
        except ValueError:
            pass

    spider = DiabloDataSpider()
    spider.update_local_database(max_build_details=max_details)
