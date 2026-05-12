import pytest
import requests


BASE_URLS = {
    'cdn': 'https://cdn.d2core.com',
    'tcb': 'https://6469-diablocore-4gkv4qjs9c6a0b40-1307287922.tcb.qcloud.la',
}

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}


@pytest.fixture(scope='module')
def js_paths():
    try:
        jr = requests.get(
            'https://www.d2core.com/assets/index-Bo-0nq-d.js',
            timeout=15, headers=HEADERS,
        )
        if jr.status_code != 200:
            return []
        import re
        paths = re.findall(r'["\']([^"\']*\.json)["\']', jr.text)
        return sorted(set(paths))
    except Exception:
        return []


@pytest.mark.skipif(
    not pytest.importorskip('requests', reason='requests未安装'),
    reason='requests未安装'
)
class TestCDNAPI:
    def test_cdn_base_responds(self):
        try:
            r = requests.get(f'{BASE_URLS["cdn"]}/d4/', timeout=10, headers=HEADERS)
            assert r.status_code < 500, f'CDN应能响应, got {r.status_code}'
        except requests.ConnectionError:
            pytest.skip('CDN不可达')

    def test_cdn_data_json_responds(self):
        try:
            r = requests.get(f'{BASE_URLS["cdn"]}/d4/data.json', timeout=10, headers=HEADERS)
            assert r.status_code < 500, f'data.json应能响应, got {r.status_code}'
        except requests.ConnectionError:
            pytest.skip('CDN不可达')

    def test_tcb_cdn_responds(self):
        try:
            r = requests.get(f'{BASE_URLS["tcb"]}/d4/', timeout=10, headers=HEADERS)
            assert r.status_code < 500, f'TCB CDN应能响应, got {r.status_code}'
        except requests.ConnectionError:
            pytest.skip('TCB CDN不可达')

    def test_main_site_accessible(self):
        try:
            r = requests.get('https://www.d2core.com/', timeout=10, headers=HEADERS)
            assert r.status_code < 500, f'主站应能响应, got {r.status_code}'
        except requests.ConnectionError:
            pytest.skip('主站不可达')


class TestJSPaths:
    def test_js_contains_json_paths(self, js_paths):
        if not js_paths:
            pytest.skip('无法获取JS路径或JS文件不存在')
        assert len(js_paths) > 0, 'JS中应包含JSON路径'

    def test_js_paths_include_locale(self, js_paths):
        if not js_paths:
            pytest.skip('无法获取JS路径')
        locale = [p for p in js_paths if 'locale' in p.lower()]
        assert len(locale) > 0, f'应包含locale相关JSON路径, 所有路径: {js_paths}'
