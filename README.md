# 🎮 暗黑破坏神4 - 游戏助手

实时游戏辅助工具，基于屏幕捕获、OCR文字识别、语音交互和网站数据爬虫，为玩家提供智能攻略推荐。

## ✨ 功能特性

### 🔍 屏幕捕获 + OCR识别
- 实时捕获游戏窗口画面
- 多引擎OCR文字识别（PaddleOCR / EasyOCR / Tesseract）
- 自动识别游戏状态：任务、BOSS、位置、职业
- 图像预处理：暗色背景增强、高对比度模式

### 🎤 语音交互
- **语音输入**：支持 Google / Sphinx / Whisper 引擎识别玩家语音
- **意图识别**：自动解析7种玩家意图（查BOSS/查装备/查技能/查构筑/查任务/查位置/通用搜索）
- **语音播报**：Edge TTS / pyttsx3 语音回复搜索结果
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

### 🖥️ GUI界面
- 暗色主题，可拖拽、置顶、半透明
- 实时显示OCR状态和识别文字
- 语音助手状态面板
- 搜索框 + 语音控制按钮

## 📁 项目结构

```
├── main.py                 # 主入口文件
├── config.py               # 配置文件
├── gui.py                  # GUI界面（PyQt5）
├── realtime_assistant.py   # 实时助手核心
├── game_detector.py        # 游戏状态检测
├── game_data.py            # 本地游戏数据库
├── content_indexer.py      # 内容索引引擎
├── screen_capture.py       # 屏幕捕获模块
├── ocr_recognizer.py       # OCR文字识别模块
├── voice_assistant.py      # 语音交互模块
├── data_spider.py          # 网站数据爬虫
├── push_to_github.py       # GitHub推送脚本
├── requirements.txt        # 依赖列表
├── index.html              # Web界面
├── script.js               # Web交互
├── styles.css              # Web样式
├── test_core.py            # 核心模块单元测试
├── test_api.py             # API可达性测试
├── test_selenium.py        # Selenium爬虫测试
└── resources/              # 资源目录
    ├── images/             # 图像资源
    └── data/               # 数据文件
```

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.9+
- Windows 10/11（屏幕捕获和游戏窗口检测依赖Windows API）
- 麦克风（语音输入功能需要）
- 音频输出设备（语音播报功能需要）
- 网络连接（Google语音识别、Edge TTS、网站爬虫需要）

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

> **注意**：使用 Tesseract OCR 需要额外安装 [Tesseract-OCR](https://github.com/UB-Mannheim/tesseract/wiki) 软件，并确保 `tesseract` 命令在系统 PATH 中。

### 3. 启动应用

```bash
# GUI模式（默认，推荐）
python main.py

# 带网站数据的GUI模式（首次运行会爬取数据，需要几分钟）
python main.py --web

# 禁用语音（不需要麦克风时）
python main.py --no-voice

# 禁用OCR（调试/测试用）
python main.py --no-ocr
```

### 4. 命令行参数

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

---

## 📖 详细使用指南

### 模式一：GUI模式（推荐）

这是最常用的模式，提供完整的图形界面。

```bash
python main.py
```

启动后会在屏幕右侧出现一个半透明的暗色面板：

#### 界面布局

```
┌──────────────────────────┐
│  🔍 暗黑4助手            │  ← 标题栏（可拖拽）
├──────────────────────────┤
│  [搜索框___________] [🔍]│  ← 手动搜索
├──────────────────────────┤
│  📷 OCR状态              │
│  引擎: PaddleOCR         │
│  识别: 暗黑破坏神...      │
├──────────────────────────┤
│  🎤 语音助手             │
│  识别: Google             │
│  播报: Edge TTS           │
│  最近查询: --             │
│  回复: --                 │
├──────────────────────────┤
│  📋 当前任务              │
│  📍 当前位置              │
│  👹 BOSS信息              │
│  ⚔️ 职业推荐              │
├──────────────────────────┤
│  💡 智能推荐              │
│  [推荐内容区域]           │
├──────────────────────────┤
│ [🎤 语音输入] [🔊 朗读] [⏹]│  ← 语音控制按钮
└──────────────────────────┘
```

#### 使用步骤

1. **启动游戏**：先启动暗黑破坏神4，进入游戏画面
2. **启动助手**：运行 `python main.py`，助手窗口会出现在屏幕右侧
3. **自动识别**：助手每隔2秒自动截屏，通过OCR识别游戏画面中的文字
4. **查看推荐**：识别到任务/BOSS/位置等信息后，自动在面板中显示攻略推荐

#### 搜索功能

- 在搜索框中输入关键词（如"骷髅王"、"暗金装备"），点击🔍按钮搜索
- 搜索结果会显示在"智能推荐"区域，包含匹配度和分类信息

#### 语音功能

1. 点击 **🎤 语音输入** 按钮开始监听（按钮变红表示正在监听）
2. 对着麦克风说话，例如："屠夫怎么打"
3. 助手自动识别语音 → 解析意图 → 搜索数据库 → 语音播报回复
4. 结果同时显示在面板的"最近查询"和"回复"区域
5. 点击 **🔊 朗读结果** 可以重新朗读当前推荐内容
6. 点击 **⏹ 停止朗读** 可以中断正在播放的语音

---

### 模式二：CLI命令行模式

适合不需要GUI的场景，或在没有显示器的服务器上运行。

```bash
python main.py --cli
```

#### 交互命令

启动后进入交互循环，支持以下命令：

| 按键 | 功能 | 说明 |
|------|------|------|
| 回车 | 继续分析 | 再次截屏分析游戏状态 |
| `s` | 搜索 | 输入关键词搜索数据库 |
| `v` | 语音输入 | 开始一次语音识别 |
| `u` | 更新数据 | 从网站爬取最新数据 |
| `q` | 退出 | 退出程序 |

#### 搜索示例

```
按回车继续 (q=退出, s=搜索, v=语音, u=更新数据): s
搜索关键词: 暗黑破坏神
意图: general_search
回复: 任务：杀死暗黑破坏神，地点：混沌要塞。进入混沌要塞，击败暗黑破坏神
```

---

### 模式三：语音交互模式

纯语音交互，不需要键盘输入，适合游戏中双手操作的场景。

```bash
python main.py --cli --voice
```

启动后助手持续监听麦克风，识别到语音后自动处理并播报：

```
语音交互模式 - 请说话...
识别: 屠夫怎么打
意图: boss_info | 关键词: 屠夫
回复: 关于屠夫的攻略：屠夫是第一章的BOSS...
  [bosses] 85% - 屠夫
```

---

### 语音意图识别详解

助手能自动理解你的语音意图，以下是支持的7种意图及对应说法：

| 意图 | 说法示例 | 搜索范围 | 助手回复示例 |
|------|---------|---------|-------------|
| BOSS攻略 | "屠夫怎么打"、"骷髅王攻略"、"查BOSS屠夫" | bosses | "关于屠夫的攻略：..." |
| 装备搜索 | "查暗金装备推荐"、"传奇武器在哪"、"最好的护甲" | equipment | "找到以下装备：..." |
| 技能查询 | "野蛮人怎么加点"、"法师技能推荐"、"死灵法师天赋" | skills | "野蛮人推荐加点：..." |
| 构筑推荐 | "法师最强构筑"、"游侠BD推荐"、"德鲁伊流派" | build_details | "推荐构筑：..." |
| 任务指引 | "任务怎么做"、"暗黑破坏神任务攻略"、"主线攻略" | quests | "任务指引：..." |
| 位置查询 | "破碎群峰在哪"、"怎么去凯吉斯坦" | quests | "位置信息：..." |
| 通用搜索 | "帮我查骷髅王"、"暗黑破坏神是什么" | 全部分类 | "搜索结果：..." |

#### 职业关键词

语音中提到以下职业名会自动提取，并缩小搜索范围：

| 职业 | 关键词 |
|------|--------|
| 野蛮人 | 野蛮人、barbarian |
| 法师 | 法师、魔法师、sorcerer |
| 游侠 | 游侠、rogue |
| 德鲁伊 | 德鲁伊、druid |
| 死灵法师 | 死灵法师、necromancer |

---

### 网站数据爬虫

使用 `--web` 参数启用网站数据爬取，获取更丰富的攻略数据：

```bash
python main.py --web
```

#### 爬取内容

| 数据类型 | 说明 | 存储位置 |
|---------|------|---------|
| 装备数据 | 暗金/传奇/套装装备列表 | `resources/data/equipment.json` |
| 技能数据 | 各职业技能详情 | `resources/data/skills_web.json` |
| 构筑数据 | 玩家构筑/BD推荐 | `resources/data/build_details.json` |
| 攻略数据 | 攻略详情页内容 | `resources/data/guides.json` |

> **注意**：首次使用 `--web` 会启动浏览器爬取数据，需要几分钟。爬取完成后数据会缓存到本地JSON文件，之后即使离线也能使用。

---

### OCR识别详解

助手通过OCR识别游戏画面中的文字，自动判断当前游戏状态。

#### 识别区域

助手会分析屏幕的不同区域：

| 区域 | 屏幕位置 | 识别内容 |
|------|---------|---------|
| 任务区 | 左上角 | 当前任务名称和描述 |
| 位置区 | 左下角 | 当前所在地图/区域 |
| BOSS区 | 中上方 | BOSS名称和血条 |
| 技能栏 | 下方中间 | 当前装备的技能 |
| 物品提示 | 右侧中间 | 鼠标悬停的物品信息 |
| 聊天区 | 左侧中间 | 聊天内容 |
| 小地图 | 右上角 | 地图信息 |

#### OCR引擎选择

```bash
# 使用PaddleOCR（推荐，中文识别效果最好）
python main.py --ocr=paddleocr

# 使用EasyOCR（离线，效果中等）
python main.py --ocr=easyocr

# 使用Tesseract（最快，中文效果较弱）
python main.py --ocr=tesseract

# 不指定则自动选择（按 PaddleOCR → EasyOCR → Tesseract 降级）
python main.py
```

---

### 配置文件

编辑 `config.py` 可以自定义助手行为：

```python
# 屏幕捕获区域（根据你的显示器分辨率调整）
SCREEN_REGION = {
    'left': 0, 'top': 0,
    'width': 1920, 'height': 1080
}

# OCR配置
OCR_CONFIG = {
    'engine': 'auto',        # auto/paddleocr/easyocr/tesseract
    'lang': 'ch',            # 语言：ch(中文)/en(英文)
    'preprocess': 'auto',    # 图像预处理：auto/none/enhance/high_contrast
    'cache_ttl': 2.0,        # OCR结果缓存时间（秒）
    'min_text_length': 2,    # 最小文字长度
}

# 语音配置
VOICE_CONFIG = {
    'stt_engine': 'google',              # 语音识别引擎：google/sphinx/whisper
    'tts_engine': 'auto',                # 语音播报引擎：auto/edge_tts/pyttsx3
    'language': 'zh-CN',                 # 语言
    'tts_voice': 'zh-CN-XiaoxiaoNeural', # Edge TTS语音（仅edge_tts生效）
    'tts_rate': 180,                     # 播报语速
    'wake_word': '小助手',               # 唤醒词
    'listen_timeout': 5,                 # 监听超时（秒）
    'phrase_time_limit': 10,             # 单次语音最大时长（秒）
}

# GUI配置
GUI_WIDTH = 340               # 窗口宽度
GUI_HEIGHT = 700              # 窗口高度
GUI_ALWAYS_ON_TOP = True      # 窗口置顶
```

#### 常用配置调整

**调整屏幕区域**（如果你的显示器不是1920x1080）：
```python
SCREEN_REGION = {
    'left': 0, 'top': 0,
    'width': 2560, 'height': 1440  # 2K显示器
}
```

**更换语音**（Edge TTS支持多种中文语音）：
```python
VOICE_CONFIG = {
    'tts_voice': 'zh-CN-YunxiNeural',   # 男声-云希
    # 'tts_voice': 'zh-CN-XiaoyiNeural', # 女声-晓伊
    # 'tts_voice': 'zh-CN-YunjianNeural',# 男声-云健
}
```

**调整OCR扫描间隔**：
```python
SCAN_INTERVAL = 1.0   # 更快扫描（默认2.0秒）
```

---

### 运行测试

项目包含完整的单元测试：

```bash
# 运行全部测试
python -m pytest test_core.py test_api.py test_selenium.py -v

# 仅运行核心模块测试（不需要网络和浏览器）
python -m pytest test_core.py -v

# 仅运行API测试（需要网络）
python -m pytest test_api.py -v

# 仅运行Selenium测试（需要Chrome浏览器）
python -m pytest test_selenium.py -v
```

#### 测试覆盖

| 测试文件 | 测试内容 | 用例数 |
|---------|---------|--------|
| test_core.py | GameDatabase / ContentIndexer / IntentRecognizer / VoiceAssistant | 37 |
| test_api.py | CDN可达性 / 主站访问 / JS路径解析 | 6 |
| test_selenium.py | 页面加载 / 链接存在 / 物品元素 | 3 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────┐
│                   GUI / CLI                      │
├─────────┬──────────┬──────────┬─────────────────┤
│屏幕捕获  │ OCR识别   │ 语音交互  │   网站爬虫      │
│Screen   │ PaddleOCR│ VoiceInput│  DataSpider    │
│Capture  │ EasyOCR  │ VoiceOutput│  Selenium     │
│         │ Tesseract│ IntentRec │               │
├─────────┴──────────┴──────────┴─────────────────┤
│              内容索引引擎 ContentIndexer           │
├────────────────────┬────────────────────────────┤
│   本地数据库        │      网站缓存数据            │
│   GameDatabase     │      Web Data (JSON)       │
└────────────────────┴────────────────────────────┘
```

### 数据流

**OCR模式：**
```
屏幕捕获 → OCR文字识别 → 内容索引匹配 → 智能推荐 → 屏幕提示
```

**语音模式：**
```
语音输入 → 意图识别 → 数据库搜索 → 语音播报 + 屏幕提示
```

## 🔧 引擎配置

### OCR引擎（自动降级）

| 引擎 | 类型 | 中文效果 | 速度 | 安装大小 |
|------|------|---------|------|---------|
| PaddleOCR | 在线/离线 | ⭐⭐⭐ | 中 | ~200MB |
| EasyOCR | 离线 | ⭐⭐ | 慢 | ~500MB |
| Tesseract | 离线 | ⭐ | 快 | ~50MB |

### 语音识别引擎

| 引擎 | 类型 | 中文效果 | 延迟 | 备注 |
|------|------|---------|------|------|
| Google | 在线 | ⭐⭐⭐ | 低 | 推荐，需网络 |
| Sphinx | 离线 | ⭐ | 低 | 中文支持弱 |
| Whisper | 离线 | ⭐⭐⭐ | 高 | 高精度，需GPU |

### 语音播报引擎

| 引擎 | 类型 | 音质 | 延迟 | 备注 |
|------|------|------|------|------|
| Edge TTS | 在线 | ⭐⭐⭐ | 低 | 推荐，微软神经网络语音 |
| pyttsx3 | 离线 | ⭐ | 极低 | 机器音，无需网络 |

## 📦 依赖说明

| 库 | 用途 | 必需 |
|----|------|------|
| PyQt5 | GUI界面 | 是 |
| mss | 屏幕捕获 | 是 |
| opencv-python | 图像处理 | 是 |
| numpy | 数值计算 | 是 |
| Pillow | 图像处理 | 是 |
| requests | HTTP请求 | 是 |
| beautifulsoup4 | HTML解析 | 是 |
| paddleocr / paddlepaddle | OCR识别（推荐） | 否 |
| easyocr | OCR识别（备选） | 否 |
| pytesseract | OCR识别（备选） | 否 |
| SpeechRecognition | 语音输入 | 否 |
| edge-tts | 语音播报（推荐） | 否 |
| pyttsx3 | 语音播报（备选） | 否 |
| pygame | 音频播放 | 否 |
| openai-whisper | 离线高精度语音识别 | 否 |
| selenium | 网站爬虫 | 否 |
| webdriver-manager | 浏览器驱动管理 | 否 |

## ❓ 常见问题

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

### Q: 语音播报没有声音？
A:
1. 推荐使用 Edge TTS：`pip install edge-tts`
2. 确认系统音量未静音
3. 如果 Edge TTS 不可用，安装 pyttsx3：`pip install pyttsx3`

### Q: `--web` 爬虫启动后没有反应？
A:
1. 首次爬取需要几分钟，请耐心等待
2. 确保已安装 Chrome 浏览器
3. 安装依赖：`pip install selenium webdriver-manager`

### Q: OCR识别结果不准确？
A:
1. 确保游戏画面清晰，不要被其他窗口遮挡
2. 尝试切换OCR引擎：`--ocr=paddleocr`
3. 调整 `config.py` 中的 `SCREEN_REGION` 匹配你的分辨率

## 📄 License

MIT License
