import os

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
    'engine': 'openvino_cpp',
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
    'tts_engine': 'melotts',
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
        'hotwords': '暗黑破坏神 都瑞尔 墨菲斯托 巴尔 安达利尔 野蛮人 法师 死灵法师 德鲁伊 圣骑士 游侠',
    },
    'bar': {
        'enabled': True,
        'boss_id': '',
        'k_actions': 3,
    },
}

LOG_LEVEL = 'INFO'
LOG_FILE = os.path.join(BASE_DIR, 'game_assistant.log')

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
