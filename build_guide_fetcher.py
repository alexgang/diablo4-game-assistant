"""
攻略图片抓取模块
从 3DM/灰机/MAXROLL 等社区抓取 D4 职业攻略图片
"""
import os
import re
import requests
import hashlib
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from class_recommender import D4Class, ClassBuildGuide, DEFAULT_BUILDS


# 缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build_guides_cache')
os.makedirs(CACHE_DIR, exist_ok=True)


class BuildGuideFetcher:
    """攻略图片抓取器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

    def fetch_guide_images(self, guide: ClassBuildGuide, max_images: int = 5) -> List[str]:
        """
        抓取攻略中的图片
        返回本地保存的图片路径列表
        """
        try:
            print(f'📥 抓取攻略: {guide.build_name} ({guide.source_url})')
            resp = self.session.get(guide.source_url, timeout=10)
            if resp.status_code != 200:
                print(f'  ✗ HTTP {resp.status_code}')
                return []

            # 解析 HTML，提取图片
            soup = BeautifulSoup(resp.content, 'html.parser')

            # 查找正文区域图片
            images = []
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src') or img.get('data-original')
                if not src:
                    continue
                # 过滤小图标
                if any(x in src.lower() for x in ['icon', 'logo', 'avatar', 'btn', 'button']):
                    continue
                # 转为绝对URL
                abs_url = urljoin(guide.source_url, src)
                # 只保留 http(s) URL
                if not abs_url.startswith(('http://', 'https://')):
                    continue
                images.append(abs_url)
                if len(images) >= max_images:
                    break

            # 下载图片到本地缓存
            saved_paths = []
            for i, img_url in enumerate(images):
                local_path = self._download_image(img_url, guide.class_type, guide.build_name, i)
                if local_path:
                    saved_paths.append(local_path)

            return saved_paths
        except Exception as e:
            print(f'  ✗ 抓取失败: {e}')
            return []

    def _download_image(self, url: str, class_type: D4Class, build_name: str, idx: int) -> Optional[str]:
        """下载并缓存图片"""
        try:
            # 缓存路径
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            safe_build = re.sub(r'[^\w\u4e00-\u9fff]', '_', build_name)[:20]
            ext = os.path.splitext(urlparse(url).path)[1] or '.jpg'
            filename = f'{class_type.value}_{safe_build}_{idx}_{url_hash}{ext}'
            local_path = os.path.join(CACHE_DIR, filename)

            # 已存在则跳过
            if os.path.exists(local_path) and os.path.getsize(local_path) > 1024:
                return local_path

            # 下载
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200 and len(resp.content) > 1024:
                with open(local_path, 'wb') as f:
                    f.write(resp.content)
                print(f'  ✓ 保存: {os.path.basename(local_path)} ({len(resp.content)//1024}KB)')
                return local_path
        except Exception as e:
            print(f'  ✗ 下载失败 {url[:50]}: {e}')
        return None

    def get_or_fetch_builds(self, class_type: D4Class) -> List[ClassBuildGuide]:
        """获取或抓取职业的推荐 BD"""
        builds = DEFAULT_BUILDS.get(class_type, [])

        for build in builds:
            # 如果没有缓存图片，尝试抓取
            if not build.image_paths:
                images = self.fetch_guide_images(build, max_images=4)
                if images:
                    # 归类图片
                    if len(images) >= 1:
                        build.image_paths['main'] = images[0]
                    if len(images) >= 2:
                        build.image_paths['skills'] = images[1]
                    if len(images) >= 3:
                        build.image_paths['gear'] = images[2]
                    if len(images) >= 4:
                        build.image_paths['paragon'] = images[3]

        return builds


def get_cached_images(class_type: D4Class) -> List[str]:
    """获取职业的所有缓存图片"""
    prefix = f'{class_type.value}_'
    if not os.path.exists(CACHE_DIR):
        return []
    files = []
    for f in os.listdir(CACHE_DIR):
        if f.startswith(prefix):
            files.append(os.path.join(CACHE_DIR, f))
    return sorted(files)


if __name__ == '__main__':
    # 测试抓取
    fetcher = BuildGuideFetcher()

    # 测试一个职业
    print('=== 测试抓取死灵法师攻略 ===')
    builds = fetcher.get_or_fetch_builds(D4Class.NECROMANCER)
    for build in builds:
        print(f'  {build.build_name}: {len(build.image_paths)} 张图片')
        for k, v in build.image_paths.items():
            print(f'    {k}: {v}')

    # 查看缓存
    print('\n=== 缓存目录 ===')
    if os.path.exists(CACHE_DIR):
        for f in os.listdir(CACHE_DIR):
            size = os.path.getsize(os.path.join(CACHE_DIR, f)) // 1024
            print(f'  {f} ({size}KB)')
