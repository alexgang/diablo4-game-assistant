#!/usr/bin/env python3
"""
暗黑破坏神4 - 任务图文攻略嵌入式网页组件

在主窗口内嵌 QWebEngineView 加载游民星空攻略页面。
参考 web_overlay.py 的嵌入式模式,但简化为纯攻略展示组件:
  - 无独立浮窗/工具栏(由 gui.py 菜单驱动)
  - 支持加载游民星空攻略 URL
  - 注入 CSS 优化阅读体验(隐藏广告/侧栏/推荐阅读)
"""

import logging
import urllib.parse

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore import Qt, QUrl, QTimer

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False

from quest_guide_config import GAMERSKY_D4_HOME, search_guide, get_guide_url

logger = logging.getLogger(__name__)

# 注入 CSS:隐藏游民星空页面的广告/侧栏/推荐阅读/评论等干扰元素
# 优化正文阅读体验,适配暗色主题
INJECT_CSS = """
(function(){
  var STYLE_ID = '__d4_quest_inject_style';
  function apply(){
    var style = document.getElementById(STYLE_ID);
    if(!style){
      style = document.createElement('style');
      style.id = STYLE_ID;
      document.head.appendChild(style);
    }
    style.textContent = `
      /* 隐藏广告/侧栏/推荐阅读/评论/导航等干扰元素 */
      .ad, .ads, .ad-box, .ad-banner, .ad-container,
      [class*="ad-"], [class*="-ad"], [class*="_ad_"],
      .sidebar, .side-bar, .right-sidebar, .left-sidebar,
      .recommend, .recommend-read, .related-read, .hot-read,
      .comment, .comments, .comment-area, .comment-list,
      .navbar, .nav-bar, .header-nav, .top-nav, .bottom-nav,
      .footer, .page-footer, .site-footer,
      .qrcode, .QRCode, .download-app, .app-download,
      .share, .share-bar, .social-share,
      .breadcrumb, .crumb,
      .article-nav, .page-nav-tip,
      .copyright, .friend-link,
      /* 游民星空特有元素 */
      .gs-qr, .gs-app, .gs-download,
      .Mid2L, .Mid2R, .MmainL, .MmainR,
      .g Artic, .gArticQrcode,
      .Tags, .Tags14,
      .DivComment, .DivCommentList,
      .page3, .page3_fy,
      .relativenews, .relativeNews,
      .bk01, .bk02, .bk03,
      .db1, .db2, .db3,
      .youmaybelike, .youMayBeLike {
        display: none !important;
      }
      /* 正文区:撑满宽度,暗色背景,适合游戏助手浮窗阅读 */
      body, html {
        background: #1a1a2e !important;
        color: #e0e0e0 !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 8px !important;
      }
      .Mid, .Mid2L, .Mmain, .MmainL {
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        float: none !important;
      }
      /* 文章标题 */
      .tit, .title, h1, h2 {
        color: #ff6b35 !important;
        font-size: 18px !important;
        font-weight: bold !important;
        margin: 8px 0 !important;
      }
      /* 正文段落 */
      p, .p, .content, .Content {
        color: #d0d0d0 !important;
        font-size: 14px !important;
        line-height: 1.8 !important;
        margin: 8px 0 !important;
      }
      /* 图片:居中,最大宽度 */
      img {
        max-width: 95% !important;
        height: auto !important;
        display: block !important;
        margin: 8px auto !important;
        border-radius: 4px;
      }
      /* 分页导航:居中显示 */
      .page, .page2, .pagination {
        text-align: center !important;
        margin: 12px 0 !important;
      }
      .page a, .page2 a, .pagination a {
        color: #4ade80 !important;
        padding: 4px 10px !important;
        margin: 0 2px !important;
        border: 1px solid #444 !important;
        border-radius: 3px !important;
        text-decoration: none !important;
      }
      .page a:hover, .page2 a:hover {
        background: rgba(139,0,0,0.5) !important;
      }
      /* 滚动条 */
      ::-webkit-scrollbar { width: 8px; }
      ::-webkit-scrollbar-track { background: rgba(0,0,0,0.3); }
      ::-webkit-scrollbar-thumb { background: rgba(120,40,20,0.7); border-radius: 4px; }
    `;
  }
  apply();
  // SPA/动态加载后重新应用
  if(!window.__d4_quest_observer){
    window.__d4_quest_observer = new MutationObserver(function(){ apply(); });
    window.__d4_quest_observer.observe(document.body, {childList:true, subtree:false});
  }
})();
"""


def _markdown_to_html(md_text):
    """简单的 Markdown → HTML 转换(支持标题/列表/加粗/段落),带暗色主题"""
    import re as _re
    import html as _html

    lines = md_text.split('\n')
    out = []
    in_list = False

    def esc(s):
        return _html.escape(s, quote=False)

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                out.append('</ul>')
                in_list = False
            out.append('')
            continue

        # 标题
        m = _re.match(r'^(#{1,4})\s+(.+)$', stripped)
        if m:
            if in_list:
                out.append('</ul>')
                in_list = False
            level = len(m.group(1))
            out.append(f'<h{level}>{esc(m.group(2))}</h{level}>')
            continue

        # 无序列表
        m = _re.match(r'^[-*]\s+(.+)$', stripped)
        if m:
            if not in_list:
                out.append('<ul>')
                in_list = True
            content = esc(m.group(1))
            # 加粗 **text**
            content = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            out.append(f'<li>{content}</li>')
            continue

        # 段落
        if in_list:
            out.append('</ul>')
            in_list = False
        content = esc(stripped)
        content = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
        out.append(f'<p>{content}</p>')

    if in_list:
        out.append('</ul>')

    body = '\n'.join(out)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{
    background: #1a1a2e;
    color: #e0e0e0;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 14px;
    line-height: 1.7;
    padding: 20px 24px;
    max-width: 720px;
    margin: 0 auto;
  }}
  h2 {{ color: #ff6b35; border-bottom: 2px solid #ff6b35; padding-bottom: 6px; margin-top: 0; }}
  h3 {{ color: #ffa500; margin-top: 18px; }}
  ul {{ padding-left: 20px; }}
  li {{ margin: 4px 0; }}
  strong {{ color: #ffd700; }}
  p {{ margin: 8px 0; }}
  ::-webkit-scrollbar {{ width: 8px; }}
  ::-webkit-scrollbar-track {{ background: rgba(0,0,0,0.3); }}
  ::-webkit-scrollbar-thumb {{ background: rgba(120,40,20,0.7); border-radius: 4px; }}
</style>
</head><body>
{body}
</body></html>"""


class QuestGuideWebView(QWidget):
    """任务图文攻略嵌入式网页组件

    用法:
      wv = QuestGuideWebView(parent)
      wv.load_guide('破碎群峰')      # 按名称加载
      wv.load_url('https://...')    # 按 URL 加载
      wv.search('奶牛关')            # 搜索并加载第一个匹配
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_url = GAMERSKY_D4_HOME
        self._load_ok = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not WEB_AVAILABLE:
            placeholder = QLabel(
                "QtWebEngine 不可用\n"
                "请安装: pip install PyQtWebEngine\n\n"
                "或手动在浏览器中打开:\n"
                f"{GAMERSKY_D4_HOME}"
            )
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #888; font-size: 13px; padding: 40px;")
            layout.addWidget(placeholder)
            self._webview = None
            return

        self._webview = QWebEngineView()
        self._webview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        settings = self._webview.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, False)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, True)

        self._webview.loadFinished.connect(self._on_load_finished)
        self._webview.setStyleSheet("background: #1a1a2e;")

        layout.addWidget(self._webview, 1)

        # 默认加载游民星空暗黑4专区首页
        self._webview.load(QUrl(self._current_url))

    def _on_load_finished(self, ok):
        """页面加载完成后注入 CSS 优化阅读体验(仅对游民星空页面)"""
        if not ok or not WEB_AVAILABLE or self._webview is None:
            self._load_ok = False
            logger.warning(f"攻略页面加载失败: {self._current_url}")
            return

        self._load_ok = True

        # 只对游民星空域名注入 CSS(搜索引擎页面不注入,避免破坏搜索结果)
        url = self._current_url.lower()
        if 'gamersky.com' not in url:
            return

        self._webview.page().runJavaScript(INJECT_CSS)
        # 延迟多次注入,确保动态加载的元素也被处理
        for delay in (600, 1600, 3200):
            QTimer.singleShot(
                delay,
                lambda: self._webview.page().runJavaScript(INJECT_CSS)
                if WEB_AVAILABLE and self._webview else None,
            )

    def load_url(self, url):
        """加载指定 URL 的攻略页面"""
        if not WEB_AVAILABLE or self._webview is None:
            logger.warning("WebEngine 不可用,无法加载攻略")
            return False
        self._current_url = url
        self._load_ok = False
        self._webview.load(QUrl(url))
        logger.info(f"[QuestGuide] 加载攻略: {url}")
        return True

    def load_markdown(self, markdown_text, title=''):
        """直接显示本地 Markdown 攻略(不依赖网络)

        Args:
            markdown_text: Markdown 格式的攻略文本
            title: 页面标题(显示在顶栏)

        Returns:
            bool: 是否成功显示
        """
        if not WEB_AVAILABLE or self._webview is None:
            logger.warning("WebEngine 不可用,无法显示本地攻略")
            return False

        html = _markdown_to_html(markdown_text)
        self._current_url = 'about:blank'
        self._load_ok = False
        self._webview.setHtml(html, QUrl('about:blank'))
        logger.info(f"[QuestGuide] 显示本地 Markdown 攻略: {title} ({len(markdown_text)} 字)")
        return True

    def load_guide(self, name):
        """按攻略名称加载页面

        Args:
            name: 攻略名称(如 '破碎群峰'、'憎恨之王DLC流程'、'奶牛关任务')

        Returns:
            bool: 是否成功加载
        """
        url = get_guide_url(name)
        if url:
            return self.load_url(url)
        logger.warning(f"[QuestGuide] 找不到攻略: {name}")
        return False

    def search(self, keyword):
        """搜索攻略并加载第一个匹配项

        Args:
            keyword: 搜索关键词

        Returns:
            bool: 是否找到并加载
        """
        results = search_guide(keyword)
        if results:
            name, info = results[0]
            logger.info(f"[QuestGuide] 搜索 '{keyword}' → 命中: {name}")
            return self.load_url(info['url'])
        logger.info(f"[QuestGuide] 搜索 '{keyword}' 无结果,加载专区首页")
        return self.load_url(GAMERSKY_D4_HOME)

    def search_online(self, keyword):
        """在线搜索任务攻略并用 LLM 汇总(游民星空攻略库未匹配时使用)

        在后台线程执行 Bing 搜索 + 智谱 GLM 汇总,避免阻塞 UI。
        完成后通过 online_search_finished 信号通知主线程。

        Args:
            keyword: OCR 识别到的任务文字

        Returns:
            bool: 是否成功启动后台搜索
        """
        if not WEB_AVAILABLE or self._webview is None:
            logger.warning("WebEngine 不可用,无法在线搜索")
            return False

        # 避免重复搜索同样的关键词
        if getattr(self, '_online_searching_keyword', None) == keyword:
            logger.info(f"[QuestGuide] 在线搜索进行中,跳过重复: '{keyword}'")
            return False
        self._online_searching_keyword = keyword

        logger.info(f"[QuestGuide] 启动后台在线搜索: '{keyword}'")

        # 后台线程执行搜索+LLM汇总
        import threading

        def _worker():
            try:
                from online_quest_searcher import search_and_summarize
                result = search_and_summarize(keyword)
                if result:
                    logger.info(
                        f"[QuestGuide] 在线搜索完成: {result['title']} -> {result['best_url']}"
                    )
                    # 在主线程加载 URL + 更新 UI
                    QTimer.singleShot(0, lambda: self._apply_online_result(
                        keyword, result
                    ))
                else:
                    logger.warning(f"[QuestGuide] 在线搜索无结果: '{keyword}'")
                    QTimer.singleShot(0, lambda: self._apply_online_failed(keyword))
            except Exception as e:
                logger.error(f"[QuestGuide] 在线搜索异常: {e}", exc_info=True)
                QTimer.singleShot(0, lambda: self._apply_online_failed(keyword))
            finally:
                self._online_searching_keyword = None

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return True

    def _apply_online_result(self, keyword, result):
        """在主线程应用在线搜索结果(加载最佳攻略URL)"""
        if not WEB_AVAILABLE or self._webview is None:
            return
        self.load_url(result['best_url'])
        # 显示 LLM 汇总说明(通过 QObject 属性传递,由 gui.py 读取)
        self._online_summary = result.get('summary', '')
        self._online_title = result.get('title', '')
        # 摘要就绪回调(供 gui.py 语音播报攻略摘要);在主线程调用,安全
        cb = getattr(self, 'on_summary_ready', None)
        if cb and self._online_summary:
            try:
                cb(self._online_title, self._online_summary)
            except Exception as e:
                logger.debug(f"[QuestGuide] on_summary_ready 回调失败: {e}")

    def _apply_online_failed(self, keyword):
        """在线搜索失败时加载 Bing 搜索页兜底"""
        if not WEB_AVAILABLE or self._webview is None:
            return
        search_query = f"暗黑4 {keyword} 攻略"
        encoded = urllib.parse.quote(search_query)
        search_url = f"https://www.bing.com/search?q={encoded}"
        logger.info(f"[QuestGuide] 在线搜索失败,兜底加载 Bing: {search_url}")
        self.load_url(search_url)

    def go_home(self):
        """回到游民星空暗黑4专区首页"""
        self.load_url(GAMERSKY_D4_HOME)

    def go_back(self):
        """后退"""
        if WEB_AVAILABLE and self._webview is not None:
            self._webview.back()

    def go_forward(self):
        """前进"""
        if WEB_AVAILABLE and self._webview is not None:
            self._webview.forward()

    @property
    def is_available(self):
        """WebEngine 是否可用"""
        return WEB_AVAILABLE and self._webview is not None
