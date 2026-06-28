# 本次改动说明(2026-06-28)

本次提交包含多个功能模块的更新,主要是 BOSS 战辅导系统、职业识别、语音助手、LLM 集成等。以下是详细改动说明,供后续维护参考。

## 一、新增文件

### 1. `boss_detector.py` — BOSS 战斗检测模块
- **功能**:检测游戏画面中的 BOSS 血条和名字,触发 BOSS 战斗状态
- **核心类**:
  - `BossDetector`:BOSS 血条检测(基于红色像素 HSV 分析 + 形态学特征)
  - `BossNameDetector`:BOSS 名字 OCR 识别(血条上方区域)
  - `BossSkillDetector`:BOSS 技能前摇检测(画面中央高亮度像素占比)
- **触发机制**:
  - 主触发:血条检测(连续2帧红色像素 >5%,长宽比 ≥5:1,位置稳定性检查)
  - 补充触发:OCR 识别 BOSS 名字(8秒节流,容错匹配别名)
- **数据外置**:`boss_data.json` 存储 BOSS 弱点/抗性/攻略,`_HARDCODED_BOSS_DB` 作为回退
- **热重载**:`refresh_boss_db()` 支持运行时刷新 BOSS 数据
- **关键参数**:
  - 血条检测区域:`x=0.30, y=0.20, w=0.40, h=0.05`(屏幕顶部偏下20%)
  - 名字检测区域:`y=0.02`(血条上方)
  - 技能前摇:V≥200 高亮度像素面积 >5%,冷却8秒
  - `ACTIVATE_FRAMES=2`, `DEACTIVATE_FRAMES=3`(快速触发,防误触)

### 2. `build_skill_icon_index.py` — 技能图标 Vision 索引构建工具
- **功能**:将5个职业(野蛮人/游侠/巫师/德鲁伊/死灵)的125个技能池图标添加到 SDK Vision 索引
- **用法**:
  ```bash
  python build_skill_icon_index.py          # 添加图标并构建索引
  python build_skill_icon_index.py --test   # 测试匹配
  ```
- **索引结构**:每个职业25个图标作为一个 scene(`skill_icon_barbarian` 等)
- **图标来源**:`class_icon_templates/pool/<职业>/r*_c*.png`(100x100 像素)

### 3. `capture_class_templates.py` — 职业模板采集工具
- **功能**:交互式采集职业图标和技能栏模板
- **用法**:运行后按提示操作,支持自动截图和剪贴板导入

### 4. `generate_boss_audio.py` — BOSS 攻略音频生成工具
- **功能**:为每个 BOSS 预生成 intro/phase1-4/outro 音频,实现低延迟播报
- **输出**:`resources/audio/<boss_id>_*.mp3`
- **通用音频**:`_common_boss_start.mp3`(血条触发时立即播放), `_common_boss_end.mp3`

## 二、修改文件

### 1. `class_icon_detector.py` — 职业识别模块(重大重构)
- **核心改动**:职业识别方案从"技能池整图匹配"改为"Vision API 图标逐个匹配"
- **新增函数**:
  - `split_skill_bar_icons()`:将技能栏水平等分为6个图标
  - `detect_via_skill_bar_icons()`:Vision API 图标匹配主方案
  - `CLASS_FROM_SKILL_ICON_SCENE_ID`:skill_icon_* 场景映射
- **修改函数**:
  - `crop_skill_bar()`:裁剪区域从 `x=13-43%, y=50-97%` 改为 `x=30-70%, y=85-97%`(只含底部6个技能图标,所有界面通用)
- **识别流程**(`detect_via_skill_bar`):
  1. Vision API 图标匹配(主方案,所有界面通用)
  2. 技能池整图匹配(回退,仅技能界面打开时有效)
  3. Vision 整栏查询(辅助)
- **Vision 图标匹配算法**(`detect_via_skill_bar_icons`):
  - 分割6个图标,跳过纯色空槽(std <5)
  - 每个图标缩放到 100x100(与数据库图标尺寸一致)
  - 查询 Vision API(topk=10, threshold=0, threshold_2=0, basic模式优先)
  - 只看 `skill_icon_*` 结果,取 top1 投票
  - 投票阈值 0.60(低于此分数不投票)
  - 最佳职业 hits ≥2 且多于第二名时返回;单图标命中且分数 ≥0.75 也接受

### 2. `gui.py` — 主界面(大量改动)
- **BOSS 检测集成**:
  - 独立 BOSS 检测 QTimer(1.5秒间隔,降低延迟)
  - `_boss_quick_check()`:轻量级血条检测
  - 血条触发时立即播放通用提示音(0延迟),名字识别后播放 BOSS intro
  - 阶段切换播放对应 phase 音频,死亡播放 outro
- **BOSS 攻略菜单**:新增"刷新 BOSS 数据"和"导出 BOSS 数据模板"
- **攻略优先级**:本地 Markdown(boss_data.json guide)→TTS 播报;游民星空→网页;在线搜索→网页
- **TTS 播报**:`_markdown_to_plain_text()` 转纯文本,英文术语本地化(Phase 1→第1阶段,AOE→范围攻击),截断800字
- **小图标/主窗口联动**:
  - `_user_pinned` 标志:用户手工点击小图标唤醒主界面时不自动隐藏
  - 最小化按钮:点击返回小图标状态
  - 未识别场景连续3次(约15秒)才隐藏窗口

### 3. `config.py` — 配置
- **LLM**:默认 `gas`(游戏助手服务端 LLM, Qwen3-4B iGPU),`zhipu` 作为回退
- **LLM 超时**:30秒
- **OCR**:`engine='easyocr'`(识别准确率0.92,耗时0.92秒)
- **ASR**:SDK_CONFIG['asr'] 配置服务端 ASR,热词包含 D4 BOSS 和职业名

### 4. `online_quest_searcher.py` — 在线攻略搜索
- **LLM 集成**:
  - `_build_llm_prompt()`:通用 prompt 构建
  - `_parse_llm_response()`:JSON 解析
  - `_call_gas_llm()`:调用游戏助手服务端 LLM
  - `_call_zhipu_llm()`:智谱 GLM 回退
  - `search_and_summarize()`:根据 provider 分发,自动回退

### 5. `voice_assistant.py` — 语音助手
- **ASR 替换为服务端 ASR**:
  - `recognize_from_file()`:优先服务端 ASR(直接传文件路径),本地引擎回退
  - `available` 属性:服务端 ASR 可用时强制 `available=True`, `engine_name='sdk'`
  - 录音使用独立 `_energy_threshold`/`_pause_threshold`,防止 recognizer 为 None 时崩溃
  - 麦克风初始化:即使 speech_recognition 不可用但服务端 ASR 可用时也初始化

### 6. `main.py` — 入口
- 读取 `OCR_CONFIG['engine']` 配置,确保 easyocr 生效

### 7. `quest_guide_webview.py` — 任务攻略 webview
- 新增/调整任务攻略网页加载逻辑

### 8. `README.md` — 文档
- 更新 Roadmap,标记14个任务为已完成

### 9. `.gitignore`
- 新增:`boss_data.json`, `resources/audio/`, `3/`, `trae-contest-post.md`, `_analyze_*`

## 三、关键设计决策

### 1. 职业识别为何改用 Vision API 图标匹配?
- **旧方案问题**:技能池整图匹配只在打开技能界面(S键)时有效,战斗/城镇/地图等场景无法识别
- **新方案优势**:技能栏在所有游戏界面都可见,无需打开技能界面
- **技术难点**:技能池图标(灰度/未学习)与技能栏图标(彩色/已装备)渲染差异大
- **解决方案**:
  - 查询图标缩放到 100x100(与数据库一致)
  - 降低阈值(threshold=0)获取候选结果
  - top1 投票(避免某职业因图标多而过度匹配)
  - 投票阈值 0.60 过滤低置信度匹配

### 2. BOSS 播报如何降低延迟?
- **旧方案问题**:OCR 名字识别耗时3-5秒,角色死亡后才开始播报
- **新方案时序**:
  1. 血条检测触发(0延迟)→ 立即播放通用提示音"BOSS战开始,注意躲避技能"
  2. 名字识别(3-5秒)→ 播放 BOSS intro 音频
  3. 阶段切换 → 播放对应 phase 音频
  4. BOSS 死亡 → 播放 outro 音频
- **关键改动**:`ACTIVATE_FRAMES` 从3降到2,独立 BOSS 检测 QTimer(1.5秒间隔)

### 3. 为何用服务端 LLM/ASR 替换 GLM/本地 ASR?
- **LLM**:游戏助手服务端 Qwen3-4B(iGPU 推理)正确返回 JSON,50字内汇总攻略,无需 API Key
- **ASR**:服务端 Qwen ASR(iGPU)准确率 >95%,支持热词(D4 BOSS/职业名),延迟低

## 四、已知问题与后续优化方向

### 职业识别
- 当前测试在战斗场景(std>40)下能正确识别
- 装备/技能界面下技能栏可能被遮挡,分数偏低(<0.60)会正确返回"未识别"
- **优化方向**:增加更多职业技能图标到索引;尝试灰度查询;考虑用 mcp_MiniMax.understand_image 直接识别

### BOSS 检测
- 当前对小怪误触发已修复(形态学特征收紧 + 位置稳定性检查)
- **优化方向**:增加更多 BOSS 数据到 boss_data.json;优化 OCR 别名匹配

## 五、运行说明

1. **启动 SDK 服务器**(游戏助手服务端)
2. **构建 Vision 索引**:`python build_skill_icon_index.py`
3. **生成 BOSS 音频**:`python generate_boss_audio.py`
4. **启动主程序**:`python main.py`(在外部终端运行,不要在 TRAE 内运行)

### 调试日志关键行
- 职业识别:
  - `技能栏图标匹配: bar=..., 6个图标每个约...`
  - `图标0: sorcerer(0.862) sorcerer(0.861) barbarian(0.767)`
  - `技能栏图标投票(top1): barbarian hits=4 avg=0.767`
- BOSS 检测:
  - `[BOSS] 检测: frame=..., 红色像素=..., active=...`
  - `[TTS] 播报 BOSS 攻略: <BOSS名> (NNN 字)`
