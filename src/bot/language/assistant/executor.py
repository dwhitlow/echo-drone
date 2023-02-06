import logging
from typing import Optional

import requests
from halo import Halo
from snips_nlu import SnipsNLUEngine

from bot import DEFAULT_BOT_NAME
from bot.common.halo import halo_stream
from bot.common.logging import serialize_dict, serialize_http_error
from bot.common.perf import log_resource_usage, timed_fn
from bot.language.assistant import ASSISTANT_MODEL_DIR
from bot.language.assistant.intents import ALL_HANDLERS, IntentHandler

DEFAULT_CONFIDENCE_THRESHOLD = 0.33

logger = logging.getLogger(__name__)


class Executor:
  """Primary class for the AI assistant.
  
  Uses snips-nlu to parse text into intents (queries or commands),
  which are then passed to the appropriate IntentHandler implementation
  to execute that query/command."""

  def __init__(
      self,
      bot_name: str = DEFAULT_BOT_NAME,
      model_dir: str = ASSISTANT_MODEL_DIR,
      confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
      intent_handlers: list[IntentHandler] = None
  ):
    self.bot_name = bot_name
    self.engine = self.__init_engine(model_dir)
    self.confidence_threshold = confidence_threshold

    self.__init_handlers(intent_handlers)

    log_resource_usage()

  @timed_fn
  def __init_engine(self, model_dir: str) -> SnipsNLUEngine:
    with Halo(text='Loading assistant NLU engine...', spinner='dots', stream=halo_stream()):
      return SnipsNLUEngine.from_path(model_dir)

  @timed_fn
  def __init_handlers(self, intent_handlers: list[IntentHandler]) -> None:
    with Halo(
        text='Initializing assistant intent handlers...', spinner='dots', stream=halo_stream()):
      if intent_handlers is None:
        self.intent_handlers = []
        for handler_type in ALL_HANDLERS:
          try:
            self.intent_handlers.append(handler_type())
          except RuntimeError:
            logger.exception(f"Couldn't initialize handler type {handler_type.__name__!s}")
      else:
        self.intent_handlers = intent_handlers

  @timed_fn
  def converse(self, input_text: str) -> Optional[str]:
    """Parses a text input as an intent, handles that command/query,
    and returns a text response indicating how the input was handled."""
    with Halo(text=f'{self.bot_name} is working...', spinner='dots', stream=halo_stream()):
      intent = self._parse(input_text)

      try:
        logger.debug(f'Parsed assistant intent:\n{serialize_dict(intent)}')

        if intent['intent']['probability'] < self.confidence_threshold:
          logger.debug('Intent was ignored due to low confidence')
          return None

        for handler in self.intent_handlers:
          if handler.can_handle(intent):
            return handler.handle(intent)

        logger.debug("Couldn't find a handler for the intent")
        return None

      except requests.HTTPError as ex:
        logger.exception(
          f'An error occurred while processing the intent\n{serialize_http_error(ex)}')
        return "Sorry, but I'm having trouble connecting to the Internet to handle that for you."
      except requests.ConnectionError:
        logger.exception('An error occurred while processing the intent')
        return "Sorry, but I'm having trouble connecting to the Internet to handle that for you."
      except RuntimeError:
        logger.exception('An error occurred while processing the intent')
        return 'Sorry, but a problem occurred while I was looking into that for you.'

  @timed_fn
  def _parse(self, input_text: str) -> dict:
    return self.engine.parse(input_text)
