# -*- coding: utf-8 -*-
"""
构筑图自动截图工具 (在【目标机】用 Edge 跑)
================================================
d2core / maxroll 的技能树/巅峰盘/装备图都是 JS 懒加载,无法静态下载。
本脚本用 Selenium 驱动 Edge 渲染页面后截图,产出到 resources/images/builds/。

依赖(目标机执行一次):
    pip install selenium

驱动:Selenium 4.6+ 自带 Selenium Manager,会自动下载匹配的 msedgedriver,无需手动装驱动。
若公司网下载驱动失败,见文末"离线驱动"说明。

用法:
    python fetch_build_images.py                 # 截 builds_config.py 里所有构筑
    python fetch_build_images.py --class rogue   # 只截游侠
    python fetch_build_images.py --headful       # 显示浏览器窗口(调试/手动登录用)
    python fetch_build_images.py --full-page     # 整页截图(默认只截内容区)

配置:编辑 builds_config.py 里每个构筑的 url 和截图区域选择器。
"""
import argparse
import io
import os
import sys
import time

# SSH/重定向环境下 stdout 可能是 cp1252,强制 UTF-8 避免中文 print 崩溃
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "resources", "images", "builds")


def make_driver(headful: bool):
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options
    opts = Options()
    if not headful:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1600,2200")     # 高一点,容纳长构筑页
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--lang=zh-CN")
    # 公司网可能要代理;Edge 默认走系统代理,通常无需设置
    driver = webdriver.Edge(options=opts)
    driver.set_page_load_timeout(60)
    return driver


def shoot(driver, url: str, out_path: str, wait: float, selector: str | None,
          full_page: bool):
    """渲染 url 并截图到 out_path。selector 指定则只截该元素,否则截可视区/整页。"""
    from selenium.webdriver.common.by import By
    print(f"  打开 {url}")
    driver.get(url)
    time.sleep(wait)                                  # 等 JS 渲染 + 图片懒加载
    # 滚动到底再回顶,触发懒加载
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
    except Exception:
        pass

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    if selector:
        try:
            el = driver.find_element(By.CSS_SELECTOR, selector)
            el.screenshot(out_path)
            print(f"    [元素截图] {out_path}")
            return True
        except Exception as e:
            print(f"    元素 '{selector}' 未找到,改用整页: {repr(e)[:60]}")

    if full_page:
        # 整页截图:把窗口高度调到页面实际高度
        try:
            h = driver.execute_script("return document.body.scrollHeight")
            driver.set_window_size(1600, min(h + 200, 8000))
            time.sleep(1)
        except Exception:
            pass
    driver.save_screenshot(out_path)
    print(f"    [整页截图] {out_path}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="cls", default=None, help="只截某职业 (rogue/sorcerer/...)")
    ap.add_argument("--headful", action="store_true", help="显示浏览器窗口")
    ap.add_argument("--full-page", action="store_true", help="整页截图")
    ap.add_argument("--wait", type=float, default=6.0, help="每页等待渲染秒数")
    args = ap.parse_args()

    try:
        from builds_config import BUILD_SHOTS
    except ImportError:
        print("缺少 builds_config.py,请先创建(见仓库)。")
        sys.exit(1)

    driver = make_driver(args.headful)
    ok = fail = 0
    try:
        for shot in BUILD_SHOTS:
            if args.cls and shot["class"] != args.cls:
                continue
            print(f"[{shot['class']}] {shot['name']} - {shot['kind']}")
            out = os.path.join(OUT_DIR, shot["file"])
            try:
                shoot(driver, shot["url"], out, args.wait,
                      shot.get("selector"), args.full_page)
                ok += 1
            except Exception as e:
                print(f"    失败: {repr(e)[:100]}")
                fail += 1
    finally:
        driver.quit()
    print(f"\n完成:{ok} 成功,{fail} 失败。图片在 {OUT_DIR}")


if __name__ == "__main__":
    main()
