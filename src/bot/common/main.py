import logging
import sys

logger = logging.getLogger(__name__)


def init(main_fn: callable) -> None:
  """Calls an entrypoint function and handles errors"""
  try:
    main_fn()
  except KeyboardInterrupt:
    sys.exit(130)
  except BaseException as ex:
    logger.critical('An uncaught exception occurred', exc_info=True)
    raise ex
