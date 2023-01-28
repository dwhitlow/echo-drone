import logging
import os

from bot.common.logging import file_handler, stream_handler

PROJECT_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

DATA_DIR = os.path.join(PROJECT_ROOT_DIR, 'data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
COOKED_DATA_DIR = os.path.join(DATA_DIR, 'cooked')

MODELS_DIR = os.path.join(PROJECT_ROOT_DIR, 'models')

LOGS_DIR = os.path.join(PROJECT_ROOT_DIR, 'logs')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(stream_handler(log_level=logging.INFO))
