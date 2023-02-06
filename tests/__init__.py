import logging
import os
import sys
import unittest
import warnings

from vcr.record_mode import RecordMode

from bot import logger as root_logger

# See README.md and https://vcrpy.readthedocs.io/en/latest/usage.html#record-modes
VCR_RECORD_MODE = RecordMode(os.getenv('VCR_RECORD_MODE', 'none'))


class EchoTestCase(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    # Remove all handlers
    for name in logging.root.manager.loggerDict:
      logger = logging.getLogger(name)
      for handler in logger.handlers:
        logger.removeHandler(handler)

    # Send all root logger logs to stdout
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)

    # Disable deprecation warnings
    warnings.filterwarnings('ignore', category=DeprecationWarning) # triggered by halo
    warnings.filterwarnings('ignore', category=ResourceWarning) # triggered by spotify.py

    # Disable Halo spinners
    os.environ['HALO_STREAM'] = '/dev/null'
