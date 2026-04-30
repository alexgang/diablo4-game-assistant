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
└── resources/              # 资源目录
    ├── images/             # 图像资源
    └── data/               # 数据文件
```

## 🚀 快速开始

### 安装依赖

```bash
# 基础依赖
pip install -r requirements.txt

# 仅安装语音依赖
pip install SpeechRecognition pyttsx3 edge-tts pygame

# 仅安装OCR依赖
pip install paddleocr paddlepaddle
```

### 启动

```bash
# GUI模式（默认）
python main.py

# 启用网站数据
python main.py --web

# 命令行模式
python main.py --cli

# 语音交互模式
python main.py --cli --voice
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--web` | 启用网站数据爬虫 |
| `--cli` | 命令行模式 |
| `--voice` | 语音交互模式（需配合 --cli） |
| `--no-ocr` | 禁用OCR（使用模拟模式） |
| `--no-voice` | 禁用语音功能 |
| `--ocr=ENGINE` | 指定OCR引擎（paddleocr/easyocr/tesseract） |
| `--stt=ENGINE` | 指定语音识别引擎（google/sphinx/whisper） |
| `--tts=ENGINE` | 指定语音播报引擎（edge_tts/pyttsx3） |

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

## 🎤 语音意图识别

支持7种玩家意图自动识别：

| 意图 | 示例语音 | 搜索范围 |
|------|---------|---------|
| BOSS攻略 | "屠夫怎么打" | bosses |
| 装备搜索 | "查暗金装备推荐" | equipment |
| 技能查询 | "野蛮人怎么加点" | skills |
| 构筑推荐 | "法师最强构筑" | build_details |
| 任务指引 | "任务怎么做" | quests |
| 位置查询 | "破碎群峰在哪" | quests |
| 通用搜索 | "帮我查骷髅王" | 全部分类 |

## 🔧 引擎配置

### OCR引擎（自动降级）

| 引擎 | 类型 | 中文效果 | 速度 |
|------|------|---------|------|
| PaddleOCR | 在线/离线 | ⭐⭐⭐ | 中 |
| EasyOCR | 离线 | ⭐⭐ | 慢 |
| Tesseract | 离线 | ⭐ | 快 |

### 语音识别引擎

| 引擎 | 类型 | 中文效果 | 备注 |
|------|------|---------|------|
| Google | 在线 | ⭐⭐⭐ | 推荐，需网络 |
| Sphinx | 离线 | ⭐ | 中文支持弱 |
| Whisper | 离线 | ⭐⭐⭐ | 高精度，需GPU |

### 语音播报引擎

| 引擎 | 类型 | 音质 | 备注 |
|------|------|------|------|
| Edge TTS | 在线 | ⭐⭐⭐ | 推荐，微软神经网络语音 |
| pyttsx3 | 离线 | ⭐ | 机器音 |

## 📦 依赖说明

| 库 | 用途 |
|----|------|
| PyQt5 | GUI界面 |
| mss | 屏幕捕获 |
| opencv-python | 图像处理 |
| paddleocr / easyocr / pytesseract | OCR识别 |
| SpeechRecognition | 语音输入 |
| edge-tts / pyttsx3 | 语音播报 |
| pygame | 音频播放 |
| selenium | 网站爬虫 |
| beautifulsoup4 | HTML解析 |
| requests | HTTP请求 |

## 📄 License

MIT License
