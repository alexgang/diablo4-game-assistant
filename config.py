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
    'engine': 'auto',
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

GUI_WIDTH = 340
GUI_HEIGHT = 600
GUI_ALWAYS_ON_TOP = True

LOG_LEVEL = 'INFO'
LOG_FILE = os.path.join(BASE_DIR, 'game_assistant.log')

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
