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
- **OpenVINO OCR**（基于 PaddleOCR 模型）为主引擎，支持 CPU/GPU/NPU 设备配置
- 多引擎回退：OpenVINO → EasyOCR → Tesseract
- 自动识别游戏状态：任务、BOSS、位置、职业
- 图像预处理：暗色背景增强、高对比度模式
- **QuestOCR**：从画面右侧任务面板裁剪文字（原始分辨率，避免缩放模糊），自动匹配攻略库

### 🎤 语音交互
- **语音输入**：SDK ASR优先（Paraformer 中文优化，首次调用自动启用） / Google / Sphinx / Whisper 多引擎
- **意图识别**：自动解析7种玩家意图（查BOSS/查装备/查技能/查构筑/查任务/查位置/通用搜索）
- **语音播报**：Edge TTS（最优，低延迟） / MeloTTS / pyttsx3 语音回复搜索结果
- **持续监听**：支持唤醒词激活，后台持续监听

### 📊 内容索引 + 智能推荐
- 本地游戏数据库（任务/BOSS/技能/装备）
- 网站数据爬虫（装备/技能/构筑/攻略）
- 关键词模糊匹配 + 相关度排序
- 上下文感知推荐

### 🌐 网站数据爬虫
- 基于 Selenium 的动态页面爬取
- 支持爬取：装备列表、技能详情、构筑推荐、攻略详情
- 本地JSON缓存，离线可用

### 🔮 d2core 构筑自动加载（核心特性）
- **嵌入式网页展示**：在主窗口内嵌 QWebEngineView，直接加载 [d2core.com](https://www.d2core.com) 的在线构筑页面，无需切换浏览器
- **自动职业识别**：四级策略自动识别当前角色职业
  - 策略1：右上角职业图标 Vision/模板匹配（装备/巅峰界面）
  - 策略1.5：**技能栏图标识别**（所有界面可见，战斗/城镇/地图通用，程序自动采集模板）
  - 策略2：右侧面板主属性 OCR（力量/智力/敏捷/意志 数值最大者）
  - 策略3：OCR 关键词识别（中英文职业名 + 角色名映射）
- **自动加载构筑**：识别到职业后自动加载 d2core 上对应的 S13 季节构筑
- **场景驱动网页内 Tab 切换**：5 秒一次 Vision 场景识别，自动驱动网页内部 tab 跟随游戏画面
  - 游戏在装备界面 → 网页切到「总览」
  - 游戏在技能树界面 → 网页切到「技能」
  - 游戏在巅峰界面 → 网页切到「巅峰」
- **JS 注入切换**：通过注入 JS 点击 `.planner-module-tab` 实现网页内部 tab 无刷新切换

### 📖 任务图文攻略自动加载（核心特性）
- **嵌入式游民星空攻略**：在主窗口内嵌 QWebEngineView 加载 [gamersky.com](https://www.gamersky.com) 攻略页面，注入 CSS 优化阅读体验（隐藏广告/侧栏/评论）
- **QuestOCR 自动匹配**：每 10 秒从游戏右侧任务面板 OCR 识别任务名，自动匹配攻略库并加载对应 URL
  - 支线任务（按区域：破碎群峰/索格伦/干燥平原/凯基斯坦/哈维泽/三神教）
  - 主线/DLC 流程攻略
  - 新手指南、赛季攻略
- **在线搜索兜底**：攻略库未匹配时，后台线程执行 Bing 搜索 + 智谱 GLM 汇总，主线程加载最佳 URL（约 4 秒，不阻塞 UI）
- **三色状态提示**：攻略库匹配（绿色）/ 搜索中（橙色）/ LLM 汇总完成（蓝色）

### 🎨 图形化叠加层（降级备选）
> 当 d2core 网页不可用时，提供本地 QPainter 绘制的可视化面板作为备选方案。
- 技能树/巅峰盘/装备布局三种可视化面板
- 半透明暗黑风格，快捷键切换：Ctrl+Alt+E/S/P（装备/技能/巅峰）
- 默认使用嵌入式网页方案，此模块仅在网页加载失败时启用

### 🖥️ GUI界面（无边框置顶窗口）
- **无边框置顶**：`FramelessWindowHint | WindowStaysOnTopHint`，半透明暗色主题
- **header 拖动手柄**：点击窗口顶部 header 任意位置即可拖动窗口（QLabel 对鼠标事件透明，关闭按钮仍可点击）
- **菜单栏集成**：所有功能按钮隐藏到顶部菜单栏（场景 / 控制 / 语音 / 叠加层 / 伤害 / 搜索 / 攻略），最大化网页展示区域
  - 「攻略」菜单：支线任务（按区域）/ 主线DLC / 新手指南 / 赛季攻略 / 搜索攻略 / 前进后退
- **隐藏 Tab 栏**：界面不再显示战斗/装备/技能/巅峰/地图/攻略 tab 栏，由场景识别自动切换；默认显示攻略 Tab
- SDK连接状态、OCR 引擎、语音引擎、场景信息实时显示在 header
- 搜索通过菜单触发弹窗输入

## 📁 项目结构

```
├── 启动助手.bat            # 一键启动脚本（双击即可，自动拉起SDK服务器+主程序）
├── main.py                 # 主入口文件（含 WebEngine 数据目录沙箱重定向 + SDK自动拉起）
├── config.py               # 配置文件（含SDK/OCR/LLM配置，自动加载 .env）
├── sdk_client.py           # Intel Gaming Assistant SDK客户端
├── gui.py                  # GUI界面（无边框置顶窗口 + 菜单栏 + 嵌入式网页 + QuestOCR）
├── web_overlay.py          # 嵌入式 QWebEngineView（加载 d2core 构筑网页 + JS 注入切换 tab）
├── quest_guide_webview.py  # 嵌入式游民星空攻略网页（CSS注入优化阅读体验）
├── quest_guide_config.py   # 任务攻略配置（游民星空 URL 索引 + 关键词匹配）
├── online_quest_searcher.py# 在线搜索兜底（Bing搜索 + 智谱GLM汇总）
├── scene_classifier.py     # 场景分类器（SceneCategory: 战斗/装备/技能/巅峰/地图）
├── class_icon_detector.py  # 职业识别（右上角图标 + 技能栏识别 + 模板自动采集）
├── class_recommender.py    # 职业推荐器（OCR关键词 + 角色名 + 主属性识别）
├── builds_config.py        # d2core S13 季节构筑截图配置
├── graphical_overlay.py    # 图形化叠加层（降级备选，网页不可用时启用）
├── overlay.py              # 文本叠加层（降级备选）
├── realtime_assistant.py   # 实时助手核心
├── game_detector.py        # 游戏状态检测（SDK优先+本地降级）
├── game_data.py            # 本地游戏数据库（D4数据）
├── content_indexer.py      # 内容索引引擎
├── screen_capture.py       # 屏幕捕获模块
├── ocr_recognizer.py       # OCR文字识别模块（多引擎封装）
├── openvino_inference.py   # OpenVINO推理引擎（支持CPU/GPU/NPU设备配置）
├── voice_assistant.py      # 语音交互模块（SDK ASR优先 + Edge TTS）
├── damage_analyzer.py      # 伤害分析模块（SDK BAR集成）
├── hotkey_manager.py       # 全局快捷键管理
├── data_spider.py          # 网站数据爬虫
├── build_vision_index.py   # Vision索引构建脚本（场景识别用）
├── requirements.txt        # 依赖列表
├── .env                    # 环境变量（API Key，不入版本库）
└── resources/              # 资源目录
    ├── images/             # 图像资源
    └── data/               # 数据文件
```

---

## 🚀 快速开始

### 🎯 一键启动（推荐游戏玩家）

双击项目根目录下的 **`启动助手.bat`** 即可，无需打开命令行、无需记忆任何参数。

启动脚本会自动完成：
1. 检测并启动 SDK 服务器（如未运行，自动后台拉起）
2. 等待 SDK 就绪（最多 40 秒，模型加载需要时间）
3. 启动游戏助手主程序

> 关闭启动窗口不会关闭游戏助手，如需退出请关闭主程序窗口。
> 如 SDK 服务器不在本机，主程序会自动降级为本地模式，功能不受影响。

### 1. 环境要求

- Python 3.10+
- Windows 10/11（屏幕捕获和游戏窗口检测依赖Windows API）
- Intel Gaming Assistant ToolServer（可选，SDK功能需要，已内置在项目中）
- 麦克风（语音输入功能需要）
- 音频输出设备（语音播报功能需要）
- 网络连接（SDK服务、Google语音识别、Edge TTS、网站爬虫需要）

### 2. 安装依赖

首次使用需安装依赖：

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

### 3. 配置 API Key（可选，在线搜索攻略用）

在项目根目录创建 `.env` 文件（已加入 .gitignore 不会提交）：

```
ZHIPU_API_KEY=你的智谱API Key
```

未配置时，任务攻略的在线搜索兜底功能不可用，但攻略库匹配仍正常工作。

### 4. 命令行启动（开发者可选）

```bash
# GUI模式（默认，推荐）—— 等同于双击 启动助手.bat
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
        'hotwords': '暗黑破坏神 都瑞尔 墨菲斯托 巴尔 安达利尔 野蛮人 法师 死灵法师 德鲁伊 圣骑士 游侠',
    },
    'bar': {
        'enabled': True,
        'k_actions': 3,           # 识别前3个动作
    },
}
```

### LLM 配置（在线搜索攻略汇总用）

编辑 `config.py` 中的 `LLM_CONFIG`，或在 `.env` 文件中设置 `ZHIPU_API_KEY`：

```python
LLM_CONFIG = {
    'provider': 'zhipu',
    'api_key': os.environ.get('ZHIPU_API_KEY', ''),  # 从 .env 读取
    'model': 'glm-4-flash',
    'base_url': 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    'timeout': 15,
    'max_search_results': 8,
}
```

### OCR 设备配置

`config.py` 中的 `OCR_CONFIG['device']` 控制 OpenVINO 推理设备：

| 值 | 说明 |
|----|------|
| `'AUTO'` | 自动选择最优设备（推荐，默认值） |
| `'CPU'` | CPU 推理（小模型最稳定，11ms） |
| `'GPU'` | GPU 推理（首次编译慢约 8s，小模型加速有限） |
| `'NPU'` | NPU 推理（不兼容 PaddleOCR，仅适合大模型） |

> **实测结论**：PaddleOCR 的 det/rec/cls 模型因动态 shape 和算子限制不兼容 NPU；CPU 对小模型最快最稳定，因此默认 `'AUTO'`。

---

## ⌨️ 快捷键

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
- **菜单栏**：场景 / 控制 / 语音 / 叠加层 / 伤害 / 搜索 / 攻略（所有功能按钮隐藏在此）
- **主区域**：默认显示攻略 Tab，内嵌 QWebEngineView 加载游民星空攻略页面；识别到职业后自动切换到 d2core 构筑网页
- **自动流程**：
  - 职业识别：右上角图标 → 技能栏识别 → 主属性 OCR → 关键词匹配（四级策略）
  - 构筑加载：识别到职业后自动加载 d2core 对应构筑，5 秒一次场景识别驱动网页 tab 切换
  - 任务攻略：每 10 秒 QuestOCR 识别右侧任务面板，自动匹配攻略库；未匹配时 Bing + GLM 在线汇总

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
│  屏幕捕获 │ 语音交互 │ 网站爬虫 │ 嵌入式网页(d2core+游民星空) │
├────────────────────┬──────────────────────────────────────┤
│   本地数据库        │      网站缓存数据                      │
│   GameDatabase     │      Web Data (JSON)                 │
└────────────────────┴──────────────────────────────────────┘
```

### 数据流

**职业识别 + 构筑加载：**
```
屏幕捕获 → 右上角图标/技能栏识别/主属性OCR/关键词匹配 → 自动加载 d2core 构筑网页
```

**任务攻略自动加载：**
```
屏幕捕获 → QuestOCR识别任务面板 → 攻略库匹配 → 加载游民星空URL
                                  └未匹配→ Bing搜索+GLM汇总 → 加载最佳URL
```

**语音模式：**
```
语音输入 → SDK ASR/Google识别 → 意图识别 → 搜索 → 语音播报
```

---

## ❓ 常见问题

### Q: 启动后显示"SDK服务器不可用"？
A: 双击 `启动助手.bat` 时会自动启动 SDK 服务器。若仍不可用：
1. 确认 `GamingAssistant Package` 目录存在且包含 `GameAssistantToolServer.exe`
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

## 🗺️ 开发路线图（Roadmap）

以下为正在规划/开发中的功能，欢迎在 Issues 中提出建议。

### 🐉 BOSS 战对战辅导

实时识别 BOSS 战斗状态，提供弱点属性、克制词条与技能预警，帮助玩家高效击杀 BOSS。

| 优先级 | 功能 | 说明 |
|--------|------|------|
| 🔴 高 | BOSS 血条检测 | 识别画面顶部 BOSS 血条位置与血量百分比，作为 BOSS 战触发条件 |
| 🔴 高 | BOSS 技能前摇识别 | 检测 BOSS 施法动作/技能特效，提取关键帧用于技能预警 |
| 🔴 高 | BOSS 阶段切换检测 | 通过血量阈值（75%/50%/25%）或场景变化识别 BOSS 战斗阶段 |
| 🔴 高 | 危险技能预警 UI | 检测到技能前摇时，在助手界面顶部弹出红色预警提示（技能名 + 应对策略） |
| 🟡 中 | BOSS 弱点属性库 | 建立 BOSS 抗性/易伤元素数据库（物理/火焰/冰霜/闪电/毒素/暗影/神圣） |
| 🟡 中 | 推荐克制词条 | 根据 BOSS 弱点属性，推荐对应元素伤害词条、易伤 buff、装备调整建议 |
| 🟡 中 | BOSS 攻略实时加载 | 识别到 BOSS 后，自动加载该 BOSS 的图文攻略（d2core/游民星空）到攻略 Tab |
| 🟢 低 | 炼狱大军赛季改版同步 | 攻略数据源对接游民星空/Maxroll，赛季更新时自动刷新 BOSS 攻略 |

### 🎤 智能语音交互（唤醒 + 意图识别 + TTS 播报）

以唤醒词激活的持续语音交互作为统一入口，串联 BOSS 攻略、装备查询、构筑加载等所有功能模块。

| 优先级 | 功能 | 说明 |
|--------|------|------|
| 🔴 高 | 语音唤醒词激活 | 默认唤醒词 `diablo`，持续后台监听，检测到唤醒词后激活语音交互模式 |
| 🔴 高 | 7 种玩家意图识别 | 查BOSS / 查装备 / 查技能 / 查构筑 / 查任务 / 查位置 / 通用搜索，关键词 + LLM 分类玩家语音指令 |
| 🔴 高 | MeloTTS 多语种语音播报 | 支持中英文混读，无云端依赖，本地推理生成语音回复 |
| 🟡 中 | 语音交互流程编排 | 唤醒词激活 → 录音 → ASR 转文字 → 意图识别 → 执行对应查询 → TTS 播报结果 |
| 🟡 中 | 唤醒词误触抑制 | 环境噪声过滤、置信度阈值、冷却时间（避免频繁误激活） |
| 🟡 中 | 意图-功能路由 | 查BOSS→BOSS攻略、查装备→装备库、查技能→技能树、查构筑→d2core、查任务→QuestOCR、查位置→地图、通用→Bing搜索 |

> **模块协同**：语音"查BOSS"意图会触发 BOSS 战辅导模块，"查任务"会触发 QuestOCR，"查构筑"会加载 d2core。语音交互将作为统一入口串联起所有功能模块。

---

## 📄 License

MIT License
