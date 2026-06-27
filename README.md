# 🎮 暗黑破坏神4 - 游戏助手

实时游戏辅助工具，基于 Intel Gaming Assistant SDK、屏幕捕获、OCR文字识别、语音交互和网站数据爬虫，为玩家提供智能攻略推荐。

## ✨ 功能特性

### 🧠 Intel Gaming Assistant SDK 集成
- **Vision 场景识别**：基于图像相似度自动识别游戏场景（替代传统OCR）
- **Knowledge/RAG 知识问答**：检索增强生成，智能回答游戏相关问题
- **Memory 记忆存储**：结构化存储游戏进度，语义检索历史记录
- **MMR 多模态检索**：文本+图片混合搜索，更精准的攻略匹配
- **ASR 语音识别**：Paraformer/Whisper 语音转文字（替代 Google/Sphinx）
- **BAR Boss动作识别**：SAM2分割+TAM时序模型，实时识别Boss动作
- **优雅降级**：SDK不可用时自动回退到本地模式，零中断体验

### 🔍 屏幕捕获 + OCR识别
- 实时捕获游戏窗口画面
- 多引擎OCR文字识别（PaddleOCR / EasyOCR / Tesseract）
- 自动识别游戏状态：任务、BOSS、位置、职业
- 图像预处理：暗色背景增强、高对比度模式

### 🎤 语音交互
- **语音输入**：SDK ASR优先 / Google / Sphinx / Whisper 多引擎
- **意图识别**：自动解析7种玩家意图（查BOSS/查装备/查技能/查构筑/查任务/查位置/通用搜索）
- **语音播报**：Edge TTS / pyttsx3 语音回复搜索结果
- **持续监听**：支持唤醒词激活，后台持续监听

### 📊 内容索引 + 智能推荐
- 本地游戏数据库（任务/BOSS/技能/装备）
- 网站数据爬虫（装备/技能/构筑/攻略）
- 关键词模糊匹配 + 相关度排序
- 上下文感知推荐

### 🎨 图形化游戏叠加层
- **技能树可视化**：QPainter绘制的圆形节点+连线，活跃技能发光高亮
- **巅峰盘可视化**：菱形网格节点，稀有节点金色高亮，多盘垂直排列
- **装备布局可视化**：角色轮廓+环绕装备槽位，稀有度边框着色
- 半透明暗黑风格，三档透明度调节
- 快捷键切换面板：Ctrl+Alt+E/S/P（装备/技能/巅峰）

### 🌐 网站数据爬虫
- 基于 Selenium 的动态页面爬取
- 支持爬取：装备列表、技能详情、构筑推荐、攻略详情
- 本地JSON缓存，离线可用

### 🔮 d2core 构筑自动加载（核心特性）
- **嵌入式网页展示**：在主窗口内嵌 QWebEngineView，直接加载 [d2core.com](https://www.d2core.com) 的在线构筑页面，无需切换浏览器
- **自动职业识别**：综合三种策略自动识别当前角色职业
  - 职业图标模板匹配（多区域裁剪 + ORB 特征匹配）
  - OCR 关键词识别（中英文职业名 + 角色名映射）
  - 主属性识别（力量/智力/敏捷/意志 数值最大者）
- **自动加载构筑**：识别到职业后自动加载 d2core 上对应的 S13 季节构筑
- **场景驱动网页内 Tab 切换**：5 秒一次 Vision 场景识别，自动驱动网页内部 tab 跟随游戏画面
  - 游戏在装备界面 → 网页切到「总览」
  - 游戏在技能树界面 → 网页切到「技能」
  - 游戏在巅峰界面 → 网页切到「巅峰」
- **JS 注入切换**：通过注入 JS 点击 `.planner-module-tab` 实现网页内部 tab 无刷新切换

### 🖥️ GUI界面（无边框置顶窗口）
- **无边框置顶**：`FramelessWindowHint | WindowStaysOnTopHint`，半透明暗色主题
- **header 拖动手柄**：点击窗口顶部 header 任意位置即可拖动窗口（QLabel 对鼠标事件透明，关闭按钮仍可点击）
- **菜单栏集成**：所有功能按钮隐藏到顶部菜单栏（场景 / 控制 / 语音 / 叠加层 / 伤害 / 搜索），最大化网页展示区域
- **隐藏 Tab 栏**：界面不再显示战斗/装备/技能/巅峰/地图 tab，由场景识别自动切换
- SDK连接状态、OCR 引擎、语音引擎、场景信息实时显示在 header
- 搜索通过菜单触发弹窗输入

## 📁 项目结构

```
├── main.py                 # 主入口文件（含 WebEngine 数据目录沙箱重定向）
├── config.py               # 配置文件（含SDK配置）
├── sdk_client.py           # Intel Gaming Assistant SDK客户端
├── gui.py                  # GUI界面（无边框置顶窗口 + 菜单栏 + 嵌入式网页）
├── web_overlay.py          # 嵌入式 QWebEngineView（加载 d2core 构筑网页 + JS 注入切换 tab）
├── scene_classifier.py     # 场景分类器（SceneCategory: 战斗/装备/技能/巅峰/地图）
├── class_icon_detector.py  # 职业图标检测（多区域裁剪 + ORB 模板匹配）
├── class_recommender.py    # 职业推荐器（OCR关键词 + 角色名 + 主属性识别）
├── builds_config.py        # d2core S13 季节构筑截图配置
├── graphical_overlay.py    # 图形化游戏叠加层
├── overlay.py              # 文本叠加层（降级备选）
├── realtime_assistant.py   # 实时助手核心
├── game_detector.py        # 游戏状态检测（SDK优先+本地降级）
├── game_data.py            # 本地游戏数据库（D4数据）
├── content_indexer.py      # 内容索引引擎
├── screen_capture.py       # 屏幕捕获模块
├── ocr_recognizer.py       # OCR文字识别模块
├── voice_assistant.py      # 语音交互模块（SDK ASR优先）
├── damage_analyzer.py      # 伤害分析模块（SDK BAR集成）
├── hotkey_manager.py       # 全局快捷键管理
├── data_spider.py          # 网站数据爬虫
├── requirements.txt        # 依赖列表
└── resources/              # 资源目录
    ├── images/             # 图像资源
    └── data/               # 数据文件
```

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- Windows 10/11（屏幕捕获和游戏窗口检测依赖Windows API）
- Intel Gaming Assistant ToolServer（可选，启用SDK功能）
- 麦克风（语音输入功能需要）
- 音频输出设备（语音播报功能需要）
- 网络连接（SDK服务、Google语音识别、Edge TTS、网站爬虫需要）

### 2. 安装依赖

```bash
# 克隆项目
git clone https://github.com/alexgang/diablo4-game-assistant.git
cd diablo4-game-assistant

# 安装全部依赖（推荐）
pip install -r requirements.txt
```

如果全部安装遇到问题，可以按需安装：

```bash
# 最小依赖（仅GUI + 本地数据库 + 搜索）
pip install PyQt5 mss opencv-python numpy Pillow requests beautifulsoup4

# 加上OCR功能
pip install paddleocr paddlepaddle
# 或者
pip install easyocr
# 或者
pip install pytesseract    # 还需安装 Tesseract-OCR 软件

# 加上语音功能
pip install SpeechRecognition pyttsx3 edge-tts pygame
# 可选：高精度离线语音识别（需要较大磁盘空间和GPU）
pip install openai-whisper

# 加上网站爬虫
pip install selenium webdriver-manager
```

### 3. 启动 Intel Gaming Assistant SDK（可选）

如需使用SDK增强功能（Vision场景识别、Knowledge知识问答、ASR语音识别、BAR Boss识别等）：

```bash
# 启动 GameAssistantToolServer
# 默认运行在 http://127.0.0.1:9190
GameAssistantToolServer.exe
```

> **注意**：SDK为可选功能。未启动SDK时，程序自动使用本地模式运行，所有功能不受影响。

### 4. 启动应用

```bash
# GUI模式（默认，推荐）
python main.py

# 指定SDK服务器地址
python main.py --sdk-url=http://10.239.140.191:9190

# 带网站数据的GUI模式（首次运行会爬取数据，需要几分钟）
python main.py --web

# 禁用语音（不需要麦克风时）
python main.py --no-voice

# 禁用OCR（调试/测试用）
python main.py --no-ocr
```

### 5. 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--web` | 启用网站数据爬虫 | `python main.py --web` |
| `--cli` | 命令行模式 | `python main.py --cli` |
| `--voice` | 语音交互模式（配合 --cli） | `python main.py --cli --voice` |
| `--no-ocr` | 禁用OCR | `python main.py --no-ocr` |
| `--no-voice` | 禁用语音 | `python main.py --no-voice` |
| `--ocr=ENGINE` | 指定OCR引擎 | `python main.py --ocr=paddleocr` |
| `--stt=ENGINE` | 指定语音识别引擎 | `python main.py --stt=google` |
| `--tts=ENGINE` | 指定语音播报引擎 | `python main.py --tts=edge_tts` |
| `--sdk-url=URL` | 指定SDK服务器地址 | `python main.py --sdk-url=http://localhost:9190` |

---

## 🧠 SDK 服务详解

### 服务架构

```
┌─────────────────────────────────────────────────────────┐
│                    GameAssistantToolServer               │
│                  http://127.0.0.1:9190                    │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│  Vision  │Knowledge │  Memory  │   MMR    │    ASR      │
│ 场景识别  │ RAG问答   │ 记忆存储  │ 多模态检索 │  语音识别   │
├──────────┴──────────┴──────────┴──────────┴─────────────┤
│                        BAR                               │
│                   Boss动作识别                             │
└─────────────────────────────────────────────────────────┘
```

### 服务与功能映射

| SDK服务 | 替代的本地模块 | 增强能力 |
|---------|-------------|---------|
| Vision | OCR场景检测 | 图像相似度识别，比OCR更精准 |
| Knowledge/RAG | ContentIndexer | LLM生成式回答，而非关键词匹配 |
| Memory | 无（新增） | 游戏进度存储与语义检索 |
| MMR | ContentIndexer搜索 | 文本+图片混合搜索 |
| ASR | Google/Sphinx/Whisper | Paraformer中文优化，支持热词 |
| BAR | 简单BOSS名检测 | SAM2分割+TAM时序，实时Boss动作识别 |

### SDK配置

编辑 `config.py` 中的 `SDK_CONFIG`：

```python
SDK_CONFIG = {
    'server_url': 'http://127.0.0.1:9190',  # SDK服务器地址
    'instance_id': 'd4_assistant',            # 实例ID
    'vision': {
        'enabled': True,
        'mode': 'accurate',       # accurate(3D场景) / basic(2D/过场)
        'threshold': -1,          # -1=自动阈值
        'topk': 3,                # 返回前3个匹配场景
    },
    'knowledge': {
        'enabled': True,
        'knowledge_id': 'd4_guide',  # 知识库ID
    },
    'asr': {
        'enabled': True,
        'hotwords': '暗黑破坏神 莉莉丝 野蛮人 法师 游侠 死灵法师 德鲁伊',
    },
    'bar': {
        'enabled': True,
        'k_actions': 3,           # 识别前3个动作
    },
}
```

---

## 🎨 图形化叠加层

游戏叠加层提供三种可视化面板，在游戏中直接显示加点建议和出装建议：

### 技能树面板
- 圆形节点表示技能，活跃技能发光高亮
- 分类标题：核心/防御/终极/被动
- 点数显示在节点内部
- 职业色填充（野蛮人红/法师蓝/游侠绿/死灵法师紫/德鲁伊橙）

### 巅峰盘面板
- 菱形网格节点（8×6）
- 稀有节点金色高亮，中心节点职业色
- 多个巅峰盘垂直排列

### 装备布局面板
- 角色轮廓居中
- 装备槽位按身体部位排列（头盔/胸甲/手套/裤子/靴子/武器/护符/戒指）
- 稀有度边框着色（暗金橙/传奇棕/套装绿）
- 空槽虚线框显示

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+Alt+O | 切换叠加层显示 |
| Ctrl+Alt+E | 显示装备面板 |
| Ctrl+Alt+S | 显示技能面板 |
| Ctrl+Alt+P | 显示巅峰面板 |
| Ctrl+Alt+V | 切换语音输入 |
| Ctrl+Alt+H | 隐藏/显示主窗口 |
| Ctrl+Alt+R | 刷新分析 |
| Ctrl+Alt+D | 切换伤害监控 |

---

## 📖 详细使用指南

### 模式一：GUI模式（推荐）

```bash
python main.py
```

启动后会在屏幕上出现一个半透明、无边框、置顶的暗色面板，包含：
- **顶部 header**：标题、OCR 引擎、语音引擎、SDK 状态、当前场景信息、关闭按钮（**点击 header 任意位置可拖动窗口**）
- **菜单栏**：场景 / 控制 / 语音 / 叠加层 / 伤害 / 搜索（所有功能按钮隐藏在此）
- **主区域**：嵌入式 QWebEngineView 加载 d2core 构筑网页，根据场景识别自动切换网页内部 tab
- **自动流程**：识别到职业后自动加载对应构筑 → 5 秒一次场景识别 → 自动切换网页 tab（装备→总览 / 技能树→技能 / 巅峰→巅峰）

> **提示**：若启动后窗口无法拖动，请尝试点击窗口顶部 header 区域（标题文字、引擎状态等标签处均可）。

### 模式二：CLI命令行模式

```bash
python main.py --cli
```

| 按键 | 功能 |
|------|------|
| 回车 | 继续分析 |
| `s` | 搜索 |
| `v` | 语音输入 |
| `u` | 更新数据 |
| `q` | 退出 |

### 语音意图识别

| 意图 | 说法示例 | 搜索范围 |
|------|---------|---------|
| 技能查询 | "游侠升级攻略"、"法师技能加点" | skills, build_details |
| 构筑推荐 | "野蛮人开荒流派"、"法师最强BD" | build_details, web_skills |
| BOSS攻略 | "怎么打莉莉丝"、"阿沙文弱点" | bosses |
| 装备搜索 | "暗金装备推荐"、"传奇武器在哪" | equipment, items |
| 任务指引 | "任务怎么做"、"主线攻略" | quests, guides |
| 位置查询 | "斯科斯格伦在哪"、"怎么去凯吉斯坦" | quests, guides |
| 通用搜索 | "帮我查骷髅王"、"暗黑破坏神是什么" | 全部分类 |

---

## 🏗️ 系统架构

```
┌───────────────────────────────────────────────────────────┐
│                      GUI / CLI                             │
├──────────┬──────────┬──────────┬──────────┬───────────────┤
│  Vision  │Knowledge │   ASR    │   BAR    │   本地降级      │
│ 场景识别  │ RAG问答   │ 语音识别  │Boss识别  │ OCR+Indexer   │
├──────────┴──────────┴──────────┴──────────┴───────────────┤
│              Intel Gaming Assistant SDK                    │
│            (GameAssistantToolServer :9190)                 │
├───────────────────────────────────────────────────────────┤
│     屏幕捕获  │  语音交互  │  网站爬虫  │  图形化叠加层      │
├────────────────────┬──────────────────────────────────────┤
│   本地数据库        │      网站缓存数据                      │
│   GameDatabase     │      Web Data (JSON)                 │
└────────────────────┴──────────────────────────────────────┘
```

### 数据流

**SDK模式：**
```
屏幕捕获 → Vision场景识别 → Knowledge RAG问答 → 智能推荐 → 图形化叠加层
```

**本地降级模式：**
```
屏幕捕获 → OCR文字识别 → 内容索引匹配 → 智能推荐 → 图形化叠加层
```

**语音模式：**
```
语音输入 → SDK ASR/Google识别 → 意图识别 → 搜索 → 语音播报 + 叠加层
```

---

## ❓ 常见问题

### Q: 启动后显示"SDK服务器不可用"？
A: 这是正常的，SDK为可选功能。如需启用：
1. 启动 `GameAssistantToolServer.exe`（默认端口9190）
2. 或指定远程服务器：`python main.py --sdk-url=http://远程地址:9190`
3. 未启动SDK时程序自动使用本地模式，功能不受影响

### Q: 启动后OCR状态显示"不可用"？
A: 需要安装OCR引擎，推荐安装 PaddleOCR：
```bash
pip install paddleocr paddlepaddle
```

### Q: 语音输入按钮显示"麦克风不可用"？
A:
1. 确认麦克风已连接并在系统设置中启用
2. 安装语音依赖：`pip install SpeechRecognition`
3. Windows可能需要允许Python访问麦克风

### Q: 叠加层遮挡游戏画面？
A: 点击叠加层顶部的👁按钮可切换透明度（0.85 → 0.5 → 0.2），或按—按钮最小化内容区

### Q: OCR识别结果不准确？
A:
1. 启用SDK Vision服务可获得更精准的场景识别
2. 尝试切换OCR引擎：`--ocr=paddleocr`
3. 调整 `config.py` 中的 `SCREEN_REGION` 匹配你的分辨率

## 🙏 致谢与参考

本项目基于以下优秀的开源项目与技术构建：

- **Intel AI Gaming Assistant Library** — 本项目核心依赖的 Intel Gaming Assistant SDK（Vision 场景识别 / Knowledge RAG 问答 / ASR 语音识别 / BAR Boss 动作识别）即来自此开源项目。
  - 仓库地址：https://github.com/GameTechDev/IntelAIGamingAssistantLibrary
- [d2core.com](https://www.d2core.com) — 暗黑破坏神 IV 构筑（Build）数据来源
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) — GUI 框架与 QtWebEngine
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) / [OpenVINO](https://github.com/openvinotoolkit/openvino) — OCR 文字识别
- [Edge-TTS](https://github.com/rany2/edge-tts) — 语音播报

> 如果 Intel Gaming Assistant SDK 帮助到了你，欢迎前往 [IntelAIGamingAssistantLibrary](https://github.com/GameTechDev/IntelAIGamingAssistantLibrary) 给项目点个 ⭐。

---

## 📄 License

MIT License
