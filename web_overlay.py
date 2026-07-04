#!/usr/bin/env python3

import logging
import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QFrame, QSizePolicy,
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QUrl, pyqtSignal

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False

try:
    from PyQt5.QtWebChannel import QWebChannel
    CHANNEL_AVAILABLE = True
except ImportError:
    CHANNEL_AVAILABLE = False

try:
    from config import OVERLAY_CONFIG
except ImportError:
    OVERLAY_CONFIG = {}

logger = logging.getLogger(__name__)

D4CORE_BASE = 'https://www.d2core.com/d4'

D4CORE_URLS = {
    'planner': f'{D4CORE_BASE}/planner',
    'builds': f'{D4CORE_BASE}/builds',
    'data': f'{D4CORE_BASE}/data',
}

INJECT_CSS = """
(function(){
  var STYLE_ID = '__d4inject_style';
  function apply(){
    var style = document.getElementById(STYLE_ID);
    if(!style){
      style = document.createElement('style');
      style.id = STYLE_ID;
      document.head.appendChild(style);
    }
    style.textContent = `
      /* 隐藏 d2core(uni-app) 左侧导航栏 / 作者侧栏 / 下载弹窗 / 顶栏 */
      .left-window__nav, .sidebar-nav,
      .nav-download__popup, .nav-download,
      .planner-header-aside, .planner-author,
      .uni-app--showtopwindow > .top-window,
      [class*="ad-"], [class*="-ad"], [class*="qrcode"], [class*="QRCode"] {
        display: none !important;
      }
      /* 主内容区:取消左边距,撑满整个宽度 */
      .uni-app--showleftwindow .uni-layout__main,
      .content-layout__shell-wrap,
      .content-layout__shell,
      .content-layout__main,
      .content-layout__header,
      .content-layout__header-inner {
        left: 0 !important; margin-left: 0 !important;
        width: 100% !important; max-width: 100% !important;
        padding-left: 4px !important; padding-right: 4px !important;
      }
      .planner-inner-layout, .planner-inner-layout__body, .planner-body,
      .gear-planner-wrapper, .gear-planner, .planner-header-block,
      .planner-header-main, .planner-variant-bar {
        width: 100% !important; max-width: 100% !important; margin: 0 !important;
      }
      /* 让装备+技能规划器主体更大 */
      .gear-planner--split { transform-origin: top left; }
      body, html { background: #0c0a08 !important; overflow-x: hidden !important; }
      ::-webkit-scrollbar { width: 8px; }
      ::-webkit-scrollbar-track { background: rgba(0,0,0,0.3); }
      ::-webkit-scrollbar-thumb { background: rgba(120,40,20,0.7); border-radius: 4px; }
    `;
  }
  apply();
  // SPA 路由切换/重渲染后重新应用
  if(!window.__d4observer){
    window.__d4observer = new MutationObserver(function(){ apply(); });
    window.__d4observer.observe(document.body, {childList:true, subtree:false});
  }
})();
"""

POPULAR_BUILDS = [
    ('野蛮人 - 溶解旋风', f'{D4CORE_BASE}/planner?bd=1SZ2'),
    ('法师 - 电球', f'{D4CORE_BASE}/planner?bd=1Tok'),
    ('游侠 - 穿透箭', f'{D4CORE_BASE}/planner?bd=1UFG'),
    ('死灵 - 纯招骷髅', f'{D4CORE_BASE}/planner?bd=1T85'),
    ('灵巫 - 妙妙剔骨', f'{D4CORE_BASE}/planner?bd=1STz'),
]


# 职业 → 推荐构筑列表（按推荐优先级排序）
# 第一个为默认推荐（最高优先级），当识别到职业后会自动加载
# 构筑名只保留流派名（不带赛季后缀），避免赛季过期后标签误导
CLASS_RECOMMENDED_BUILDS = {
    'barbarian': [
        ('溶解旋风', f'{D4CORE_BASE}/planner?bd=1SZ2'),
        ('双重尘魔', f'{D4CORE_BASE}/planner?bd=1SaX'),
        ('先祖之锤', f'{D4CORE_BASE}/planner?bd=1SbP'),
    ],
    'sorcerer': [
        ('电球', f'{D4CORE_BASE}/planner?bd=1Tok'),
        ('冰法', f'{D4CORE_BASE}/planner?bd=1ToE'),
        ('燃烧', f'{D4CORE_BASE}/planner?bd=1Too'),
    ],
    'rogue': [
        ('箭雨冰穿', f'{D4CORE_BASE}/planner?bd=1UPR'),
        ('毒灌刃舞', f'{D4CORE_BASE}/planner?bd=1T4s'),
    ],
    'necromancer': [
        ('纯招骷髅', f'{D4CORE_BASE}/planner?bd=1T85'),
        ('骨矛', f'{D4CORE_BASE}/planner?bd=1T8N'),
        ('血雾', f'{D4CORE_BASE}/planner?bd=1T8P'),
    ],
    'spiritborn': [
        ('灵巫 - 千喉', f'{D4CORE_BASE}/planner?bd=1STz'),
        ('灵巫 - 虎掌', f'{D4CORE_BASE}/planner?bd=1STh'),
        ('灵巫 - 鹰爪', f'{D4CORE_BASE}/planner?bd=1STj'),
    ],
    'druid': [
        ('伙伴流', f'{D4CORE_BASE}/planner?bd=1SDb'),
        ('风暴德', f'{D4CORE_BASE}/planner?bd=1SDs'),
        ('狼人', f'{D4CORE_BASE}/planner?bd=1SDw'),
    ],
    # 资料片新职业(圣骑士/术师): d2core 暂无固定 bd 码,用构筑列表页,页面内按职业筛选
    'paladin': [
        ('圣骑士构筑列表', f'{D4CORE_BASE}/d4/builds'),
    ],
    'warlock': [
        ('术师构筑列表', f'{D4CORE_BASE}/d4/builds'),
    ],
}


# 职业中文名 → key
CLASS_NAME_TO_KEY = {
    '野蛮人': 'barbarian',
    'barbarian': 'barbarian',
    '巫师': 'sorcerer',
    '法师': 'sorcerer',
    'sorcerer': 'sorcerer',
    '游侠': 'rogue',
    'rogue': 'rogue',
    '死灵法师': 'necromancer',
    '死灵': 'necromancer',
    'necromancer': 'necromancer',
    '灵巫': 'spiritborn',
    'spiritborn': 'spiritborn',
    '德鲁伊': 'druid',
    'druid': 'druid',
    '圣骑士': 'paladin',
    'paladin': 'paladin',
    '术师': 'warlock',   # 资料片新职业(勿与"术士/巫师"混淆)
    'warlock': 'warlock',
}


class WebOverlay(QWidget):

    closed = pyqtSignal()
    visibility_changed = pyqtSignal(bool)

    def __init__(self, parent=None, opacity=None, embedded=False):
        super().__init__(parent)
        self._cfg = OVERLAY_CONFIG
        self.opacity = opacity if opacity is not None else self._cfg.get('opacity', 0.95)
        self._dragging = False
        self._drag_pos = None
        self._current_url = D4CORE_URLS['planner']
        self._embedded = embedded
        self._load_ok = False               # 网页是否加载完成(供自动切tab判断)
        self._pending_inner_tab = None       # 加载中收到的待切内部tab

        if not embedded:
            # 独立浮窗模式
            self.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint |
                Qt.Tool
            )
            self.setAttribute(Qt.WA_TranslucentBackground, False)
            self.setAttribute(Qt.WA_ShowWithoutActivating)
            self.setFocusPolicy(Qt.NoFocus)
        # embedded 模式:作为普通子部件,不设窗口标志/焦点策略,网页可正常交互

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        container = QWidget()
        container.setObjectName("webOverlayContainer")
        container.setStyleSheet(
            "#webOverlayContainer {"
            "  background: rgba(18, 12, 8, 245);"
            "  border: 2px solid rgba(120, 40, 20, 180);"
            "  border-radius: 4px;"
            "}"
        )
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(4, 4, 4, 4)
        container_layout.setSpacing(2)

        self._build_toolbar(container_layout)
        self._build_webview(container_layout)

        main_layout.addWidget(container)
        self.resize(960, 1080)
        self.setMinimumSize(600, 700)
        self.setWindowOpacity(self.opacity)

    def _build_toolbar(self, parent_layout):
        toolbar = QWidget()
        toolbar.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 rgba(25,12,8,240), stop:1 rgba(15,8,12,240));"
            "border-radius: 3px;"
        )
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(6, 3, 6, 3)
        tb_layout.setSpacing(4)

        title = QLabel("暗黑核")
        title.setFont(QFont('Georgia', 11, QFont.Bold))
        title.setStyleSheet("color: #ff6b35; background: transparent;")
        tb_layout.addWidget(title)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("输入暗黑核构筑链接或搜索...")
        self._url_input.setStyleSheet(
            "QLineEdit {"
            "  background: rgba(0,0,0,0.4); color: #ddd;"
            "  border: 1px solid rgba(68,68,68,0.5);"
            "  border-radius: 3px; padding: 3px 8px; font-size: 11px;"
            "}"
            "QLineEdit:focus { border-color: rgba(200,80,20,0.8); }"
        )
        self._url_input.returnPressed.connect(self._navigate_to_input)
        tb_layout.addWidget(self._url_input, 1)

        go_btn = QPushButton("▶")
        go_btn.setFixedSize(26, 22)
        go_btn.setStyleSheet(
            "QPushButton { color: #4ade80; background: rgba(0,60,0,150);"
            "  border: 1px solid rgba(0,100,0,100); border-radius: 3px; font-size: 12px; }"
            "QPushButton:hover { background: rgba(0,80,0,200); }"
        )
        go_btn.clicked.connect(self._navigate_to_input)
        tb_layout.addWidget(go_btn)

        self._build_combo = QComboBox()
        self._build_combo.setFixedWidth(140)
        self._build_combo.setStyleSheet(
            "QComboBox {"
            "  background: rgba(20,15,18,180); color: #ccc;"
            "  border: 1px solid rgba(80,50,40,100); border-radius: 3px;"
            "  padding: 2px 6px; font-size: 10px;"
            "}"
            "QComboBox::drop-down { border: none; width: 16px; }"
            "QComboBox QAbstractItemView {"
            "  background: rgba(20,15,18,240); color: #ccc;"
            "  selection-background-color: rgba(120,30,10,200);"
            "  border: 1px solid rgba(80,50,40,100);"
            "}"
        )
        for name, url in POPULAR_BUILDS:
            self._build_combo.addItem(name, url)
        self._build_combo.currentIndexChanged.connect(self._on_build_selected)
        tb_layout.addWidget(self._build_combo)

        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background-color: rgba(80,50,30,100);")
        tb_layout.addWidget(sep)

        back_btn = QPushButton("◀")
        back_btn.setFixedSize(24, 22)
        back_btn.setStyleSheet(
            "QPushButton { color: #aaa; background: transparent; border: none; font-size: 13px; }"
            "QPushButton:hover { color: #ffd700; }"
        )
        back_btn.clicked.connect(self._go_back)
        tb_layout.addWidget(back_btn)

        fwd_btn = QPushButton("▶")
        fwd_btn.setFixedSize(24, 22)
        fwd_btn.setStyleSheet(
            "QPushButton { color: #aaa; background: transparent; border: none; font-size: 13px; }"
            "QPushButton:hover { color: #ffd700; }"
        )
        fwd_btn.clicked.connect(self._go_forward)
        tb_layout.addWidget(fwd_btn)

        home_btn = QPushButton("🏠")
        home_btn.setFixedSize(24, 22)
        home_btn.setStyleSheet(
            "QPushButton { color: #aaa; background: transparent; border: none; font-size: 12px; }"
            "QPushButton:hover { color: #ffd700; }"
        )
        home_btn.clicked.connect(self._go_home)
        tb_layout.addWidget(home_btn)

        builds_btn = QPushButton("📋")
        builds_btn.setFixedSize(24, 22)
        builds_btn.setStyleSheet(
            "QPushButton { color: #aaa; background: transparent; border: none; font-size: 12px; }"
            "QPushButton:hover { color: #ffd700; }"
        )
        builds_btn.clicked.connect(self._go_builds)
        tb_layout.addWidget(builds_btn)

        opacity_btn = QPushButton("👁")
        opacity_btn.setFixedSize(24, 22)
        opacity_btn.setStyleSheet(
            "QPushButton { color: #aaa; background: transparent; border: none; font-size: 12px; }"
            "QPushButton:hover { color: #ff6b35; }"
        )
        opacity_btn.clicked.connect(self.toggle_opacity)
        tb_layout.addWidget(opacity_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 22)
        close_btn.setStyleSheet(
            "QPushButton { color: #ff6b35; background: transparent; border: none; font-size: 13px; }"
            "QPushButton:hover { color: #ff4444; }"
        )
        close_btn.clicked.connect(self._on_close)
        tb_layout.addWidget(close_btn)

        parent_layout.addWidget(toolbar)

        sep_line = QFrame()
        sep_line.setFixedHeight(1)
        sep_line.setStyleSheet("background-color: rgba(120,40,20,100);")
        parent_layout.addWidget(sep_line)

    def _build_webview(self, parent_layout):
        if not WEB_AVAILABLE:
            no_web = QLabel(
                "QtWebEngine 不可用\n"
                "请安装: pip install PyQtWebEngine\n\n"
                "或者手动在浏览器中打开:\n"
                f"{D4CORE_URLS['planner']}"
            )
            no_web.setAlignment(Qt.AlignCenter)
            no_web.setStyleSheet("color: #888; font-size: 13px; padding: 40px;")
            parent_layout.addWidget(no_web)
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

        self._webview.urlChanged.connect(self._on_url_changed)
        self._webview.loadFinished.connect(self._on_load_finished)

        self._webview.setStyleSheet("background: #0c0a08;")

        parent_layout.addWidget(self._webview, 1)

        self._webview.load(QUrl(self._current_url))

    def _navigate_to_input(self):
        text = self._url_input.text().strip()
        if not text:
            return

        if text.startswith('http'):
            url = text
        elif 'd2core.com' in text:
            url = text if text.startswith('http') else f'https://{text}'
        else:
            url = f'{D4CORE_BASE}/planner?bd={text}'

        self.load_url(url)

    def _on_build_selected(self, index):
        if index < 0:
            return
        url = self._build_combo.itemData(index)
        if url:
            self.load_url(url)

    def _on_url_changed(self, url):
        self._current_url = url.toString()
        if 'd2core.com' in self._current_url:
            self._url_input.setText(self._current_url)

    def _on_load_finished(self, ok):
        if ok and WEB_AVAILABLE:
            self._load_ok = True
            # SPA 异步渲染:首次+多次延迟注入,确保导航/侧栏元素出现后被隐藏
            from PyQt5.QtCore import QTimer
            self._webview.page().runJavaScript(INJECT_CSS)
            for delay in (600, 1600, 3200):
                QTimer.singleShot(
                    delay,
                    lambda: self._webview.page().runJavaScript(INJECT_CSS)
                    if WEB_AVAILABLE else None,
                )
            # 网页加载中曾收到切tab请求 -> 现在补切
            if self._pending_inner_tab:
                which = self._pending_inner_tab
                self._pending_inner_tab = None
                QTimer.singleShot(800, lambda: self.switch_inner_tab(which))
        else:
            self._load_ok = False

    def switch_inner_tab(self, which):
        """切换 d2core 网页内部的 tab。which ∈ {'skill','peak','overview'}
        游戏画面切到技能树/巅峰界面时调用,让网页自动跟随。"""
        if not WEB_AVAILABLE or self._webview is None:
            return
        label = {'skill': '技能', 'peak': '巅峰', 'overview': '总览'}.get(which)
        if not label:
            return
        # 网页还没加载完 -> 记下来,loadFinished 后补切
        if not self._load_ok:
            self._pending_inner_tab = which
            return
        js = """
        (function(){
          var tabs = document.querySelectorAll('.planner-module-tab');
          for (var i=0;i<tabs.length;i++){
            var t = tabs[i].textContent || '';
            if (t.indexOf('%s') !== -1){ tabs[i].click(); return true; }
          }
          return false;
        })();
        """ % label
        self._webview.page().runJavaScript(js)
        # SPA 元素可能延迟,400ms 后兜底再点一次
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(400, lambda: self._webview.page().runJavaScript(js)
                          if WEB_AVAILABLE and self._webview else None)

    def _go_back(self):
        if WEB_AVAILABLE:
            self._webview.back()

    def _go_forward(self):
        if WEB_AVAILABLE:
            self._webview.forward()

    def _go_home(self):
        self.load_url(D4CORE_URLS['planner'])

    def _go_builds(self):
        self.load_url(D4CORE_URLS['builds'])

    def load_url(self, url):
        if not WEB_AVAILABLE:
            return
        self._current_url = url
        self._load_ok = False            # 换页 -> 重新等加载完成
        if hasattr(self, '_url_input') and self._url_input is not None:
            self._url_input.setText(url)
        self._webview.load(QUrl(url))

    def load_build(self, bd_id):
        self.load_url(f'{D4CORE_BASE}/planner?bd={bd_id}')

    def load_class_recommendation(self, class_type, bd_index: int = 0) -> bool:
        """
        根据职业自动加载对应的推荐构筑

        Args:
            class_type: 职业标识，可以是 D4Class 枚举、字符串 key、'barbarian'、中文名等
            bd_index: 该职业第几个推荐（默认 0 = 最高优先级）

        Returns:
            bool: 是否成功加载
        """
        # 归一化职业 key
        key = None
        if class_type is None:
            return False
        if hasattr(class_type, 'value'):
            key = class_type.value  # D4Class 枚举
        elif isinstance(class_type, str):
            key = class_type.lower().strip()
            # 查中文名映射
            if key not in CLASS_RECOMMENDED_BUILDS:
                key = CLASS_NAME_TO_KEY.get(class_type, key)
        if not key:
            return False
        if key not in CLASS_RECOMMENDED_BUILDS:
            logger.debug(f"无 {key} 职业的推荐构筑列表")
            return False

        builds = CLASS_RECOMMENDED_BUILDS[key]
        if bd_index < 0 or bd_index >= len(builds):
            bd_index = 0
        name, url = builds[bd_index]

        # 同步更新下拉框（让用户也能看到当前选的是什么）
        for i in range(self._build_combo.count()):
            item_url = self._build_combo.itemData(i)
            if item_url == url:
                self._build_combo.blockSignals(True)
                self._build_combo.setCurrentIndex(i)
                self._build_combo.blockSignals(False)
                break

        logger.info(
            f"[WebOverlay] 自动加载职业推荐: {key} → {name} ({url})"
        )
        self.load_url(url)
        return True

    def refresh_builds_for_class(self, class_type) -> None:
        """
        根据职业刷新下拉框内容（点击"装备/技能/巅峰"Tab 时自动调用）

        Args:
            class_type: 职业标识
        """
        key = None
        if hasattr(class_type, 'value'):
            key = class_type.value
        elif isinstance(class_type, str):
            key = class_type.lower().strip()
            if key not in CLASS_RECOMMENDED_BUILDS:
                key = CLASS_NAME_TO_KEY.get(class_type, key)

        self._build_combo.blockSignals(True)
        self._build_combo.clear()
        if key and key in CLASS_RECOMMENDED_BUILDS:
            for name, url in CLASS_RECOMMENDED_BUILDS[key]:
                self._build_combo.addItem(name, url)
        else:
            for name, url in POPULAR_BUILDS:
                self._build_combo.addItem(name, url)
        self._build_combo.setCurrentIndex(0)
        self._build_combo.blockSignals(False)
        # 自动加载第一个推荐构筑(否则只填了下拉框不显示网页)
        if self._build_combo.count() > 0:
            first_url = self._build_combo.itemData(0)
            if first_url:
                self.load_url(first_url)

    def toggle_opacity(self):
        if self.opacity > 0.7:
            self.opacity = 0.5
        elif self.opacity > 0.3:
            self.opacity = 0.2
        else:
            self.opacity = 0.85
        self.setWindowOpacity(self.opacity)

    def show_at_game_position(self, screen_width=1920, screen_height=1080):
        cfg = OVERLAY_CONFIG
        position = cfg.get('position', 'right')

        # 用实际主屏尺寸(默认值在高分屏会算偏)
        try:
            from PyQt5.QtWidgets import QApplication
            scr = QApplication.primaryScreen().geometry()
            screen_width, screen_height = scr.width(), scr.height()
        except Exception:
            pass

        w = self.width()
        h = self.height()

        if position == 'right':
            x = screen_width - w - 10
            y = max(0, (screen_height - h) // 2)
        elif position == 'left':
            x = 10
            y = max(0, (screen_height - h) // 2)
        elif position == 'top-right':
            x = screen_width - w - 10
            y = 10
        elif position == 'top-left':
            x = 10
            y = 10
        else:
            x = screen_width - w - 10
            y = max(0, (screen_height - h) // 2)

        self.move(x, y)
        self.show()
        self.raise_()              # 提到最前(避免被游戏窗口盖住)
        self.activateWindow()

    def _on_close(self):
        self.hide()
        self.closed.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
