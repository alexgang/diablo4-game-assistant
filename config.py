import os

# 自动加载 .env 文件(包含 API Key 等敏感信息,不入版本库)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RESOURCES_DIR = os.path.join(BASE_DIR, 'resources')
IMAGES_DIR = os.path.join(RESOURCES_DIR, 'images')
DATA_DIR = os.path.join(RESOURCES_DIR, 'data')
CACHE_DIR = os.path.join(BASE_DIR, 'cache')

SCREEN_REGION = {
    'left': 0,
    'top': 0,
    'width': 1920,
    'height': 1080
}

CONFIDENCE_THRESHOLD = 0.8
SCAN_INTERVAL = 2.0

OCR_CONFIG = {
    # OCR 引擎: 'easyocr'(默认,中文识别准确率最高) / 'tesseract'(备选,需额外安装软件)
    # 实测 easyocr 对游戏暗色界面文字识别效果最好,喂原始彩色图即可。
    'engine': 'easyocr',
    'lang': 'ch',
    'preprocess': 'auto',
    'cache_ttl': 2.0,
    'min_text_length': 2,
}

D4_REGIONS = {
    'quest_area': {'x_ratio': 0.0, 'y_ratio': 0.0, 'w_ratio': 0.25, 'h_ratio': 0.1},
    'location_area': {'x_ratio': 0.0, 'y_ratio': 0.9, 'w_ratio': 0.15, 'h_ratio': 0.05},
    'boss_area': {'x_ratio': 0.25, 'y_ratio': 0.15, 'w_ratio': 0.5, 'h_ratio': 0.08},
    'skill_bar': {'x_ratio': 0.3, 'y_ratio': 0.85, 'w_ratio': 0.4, 'h_ratio': 0.12},
    'item_tooltip': {'x_ratio': 0.5, 'y_ratio': 0.1, 'w_ratio': 0.25, 'h_ratio': 0.5},
    'chat_area': {'x_ratio': 0.0, 'y_ratio': 0.5, 'w_ratio': 0.25, 'h_ratio': 0.4},
    'minimap': {'x_ratio': 0.85, 'y_ratio': 0.0, 'w_ratio': 0.15, 'h_ratio': 0.15},
}

VOICE_CONFIG = {
    'stt_engine': 'google',
    # TTS 引擎: edge_tts(微软在线,音质好,需联网) / pyttsx3(系统离线,回退)
    'tts_engine': 'edge_tts',
    'language': 'zh-CN',
    'tts_voice': 'zh-CN-XiaoxiaoNeural',
    'tts_rate': 180,
    'wake_word': '小助手',
    'listen_timeout': 5,
    'phrase_time_limit': 10,
}

GUI_WIDTH = 340
GUI_HEIGHT = 700
GUI_ALWAYS_ON_TOP = True

OVERLAY_CONFIG = {
    'enabled': True,
    'opacity': 0.85,
    'width': 320,
    'height': 480,
    'position': 'right',
    'auto_show': False,
    'default_tab': 0,
    'click_through': False,
    'font_size': 9,
    'show_rarity_colors': True,
    'show_slot_icons': True,
}

HOTKEY_CONFIG = {
    'enabled': True,
    'bindings': {
        'voice_toggle': 'ctrl+alt+v',
        'overlay_toggle': 'ctrl+alt+o',
        'overlay_equip': 'ctrl+alt+e',
        'overlay_skill': 'ctrl+alt+s',
        'overlay_paragon': 'ctrl+alt+p',
        'overlay_merc': 'ctrl+alt+m',
        'window_toggle': 'ctrl+alt+h',
        'refresh': 'ctrl+alt+r',
        'damage_toggle': 'ctrl+alt+d',
    },
}

DAMAGE_CONFIG = {
    'enabled': True,
    'monitor_interval': 1.0,
    'min_damage_number': 10,
    'dps_window_seconds': 60,
    'auto_start': False,
    'ocr_region': 'chat_area',
}

SDK_SERVER_PATH = os.path.join(
    BASE_DIR, 'GamingAssistant Package', '游戏助手服务端', '游戏助手服务端',
    'apps', 'GameAssistantToolServer.exe'
)
SDK_SERVER_WORK_DIR = os.path.dirname(SDK_SERVER_PATH)

SDK_CONFIG = {
    'server_url': os.environ.get('GAS_SERVER_URL', 'http://127.0.0.1:9190'),
    'instance_id': 'd4_assistant',
    'vision': {
        'enabled': True,
        'mode': 'accurate',
        'threshold': -1,
        'threshold_2': -1,
        'topk': 3,
    },
    'knowledge': {
        'enabled': True,
        'knowledge_id': 'd4_guide',
    },
    'memory': {
        'enabled': True,
    },
    'mmr': {
        'enabled': True,
        'topk': 5,
        'threshold': 0.3,
    },
    'asr': {
        'enabled': True,
        'hotwords': '暗黑破坏神 都瑞尔 墨菲斯托 巴尔 安达利尔 野蛮人 法师 死灵法师 德鲁伊 灵巫 游侠',
    },
    'bar': {
        'enabled': True,
        'boss_id': '',
        'k_actions': 3,
    },
}

LOG_LEVEL = 'INFO'
LOG_FILE = os.path.join(BASE_DIR, 'game_assistant.log')

# LLM 配置(用于在线搜索攻略汇总)
# provider:
#   'gas'   - 使用游戏助手服务端内置 LLM(Qwen3,通过 Knowledge query 接口,无需 API Key)
#   'zhipu' - 使用智谱 GLM(需要 API Key,作为回退)
LLM_CONFIG = {
    'provider': 'gas',
    # 智谱 GLM 回退配置(provider='zhipu' 时使用)
    'api_key': os.environ.get('ZHIPU_API_KEY', ''),
    'model': 'glm-4-flash',
    'base_url': 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    'timeout': 30,
    'max_search_results': 8,
}

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
