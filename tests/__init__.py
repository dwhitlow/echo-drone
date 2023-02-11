import logging
import os
import sys
import unittest
import warnings

from bot import logger as root_logger


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
    warnings.filterwarnings('ignore', category=DeprecationWarning)

    # Disable Halo spinners
    os.environ['HALO_STREAM'] = '/dev/null'
