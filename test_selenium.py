import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


@pytest.fixture(scope='module')
def driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        d = webdriver.Chrome(service=service, options=options)
    except Exception:
        pytest.skip('Chrome/ChromeDriver不可用')
        return
    yield d
    d.quit()


@pytest.mark.skipif(
    not pytest.importorskip('selenium', reason='selenium未安装'),
    reason='selenium未安装'
)
class TestSeleniumCrawl:
    BASE_URL = 'https://www.d2core.com/d4'

    def test_page_loads(self, driver):
        driver.get(f'{self.BASE_URL}/data/uniqueItem')
        assert driver.title, '页面标题不应为空'

    def test_links_exist(self, driver):
        driver.get(f'{self.BASE_URL}/data/uniqueItem')
        links = driver.find_elements(By.TAG_NAME, 'a')
        visible_links = [l for l in links if l.text.strip() and len(l.text.strip()) > 1]
        assert len(visible_links) > 0, '页面应包含可见链接'

    def test_item_elements_exist(self, driver):
        driver.get(f'{self.BASE_URL}/data/uniqueItem')
        selectors = [
            '[class*="item"]',
            '[class*="unique"]',
            '[class*="equipment"]',
        ]
        found = False
        for sel in selectors:
            items = driver.find_elements(By.CSS_SELECTOR, sel)
            visible = [i for i in items if i.text.strip()]
            if visible:
                found = True
                break
        assert found, '页面应包含物品相关元素'
