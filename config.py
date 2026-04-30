import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 资源目录
RESOURCES_DIR = os.path.join(BASE_DIR, 'resources')
IMAGES_DIR = os.path.join(RESOURCES_DIR, 'images')
DATA_DIR = os.path.join(RESOURCES_DIR, 'data')

# 屏幕捕获区域配置 (根据游戏窗口大小调整)
SCREEN_REGION = {
    'left': 0,
    'top': 0,
    'width': 1920,
    'height': 1080
}

# 识别配置
CONFIDENCE_THRESHOLD = 0.8
SCAN_INTERVAL = 1.0  # 扫描间隔（秒）

# GUI配置
GUI_WIDTH = 300
GUI_HEIGHT = 500
GUI_ALWAYS_ON_TOP = True

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = os.path.join(BASE_DIR, 'game_assistant.log')

# 确保目录存在
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)