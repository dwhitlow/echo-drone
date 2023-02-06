import logging
import os

from bot.common.logging import stream_handler

PROJECT_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT_DIR, 'data')
MODELS_DIR = os.path.join(PROJECT_ROOT_DIR, 'models')
LOGS_DIR = os.path.join(PROJECT_ROOT_DIR, 'logs')

SECRETS_PATH = os.path.join(PROJECT_ROOT_DIR, 'secrets.json')

DEFAULT_BOT_NAME = 'Echo'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(stream_handler(log_level=logging.INFO))
