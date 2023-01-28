import logging
import os

logging.disable(logging.CRITICAL + 1)

os.environ['HALO_STREAM'] = '/dev/null'
