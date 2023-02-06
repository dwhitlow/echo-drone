import argparse
import json
import logging
import os
from typing import Optional

from bot import DEFAULT_BOT_NAME, LOGS_DIR
from bot import logger as root_logger
from bot.common.logging import numbered_file_handler
from bot.common.main import init
from bot.language.assistant.executor import Executor
from bot.language.conversation.utils import load_model
from bot.language.io import ConsoleIOHandler, IOHandler

DEFAULT_MODEL_NAME = 'microsoft/GODEL-v1_1-large-seq2seq'

logger = logging.getLogger('bot.language.processor')
logger.setLevel(logging.NOTSET) # Override default behavior for root logger


class LanguageProcessor:
  """
  Primary class for the natural language understanding/processing package.

  It connects I/O sources to machine learning models to process and respond to
  statements, commands, and questions from users.
  """

  def __init__(
      self,
      io_handler: IOHandler = None,
      bot_name: str = DEFAULT_BOT_NAME,
      assistant_model_kwargs: Optional[dict] = None,
      conversation_model_name = DEFAULT_MODEL_NAME,
      conversation_model_kwargs: Optional[dict] = None,
  ):
    if io_handler is None:
      self.io_handler = ConsoleIOHandler(bot_name)
    else:
      self.io_handler = io_handler

    self.assistant_model = Executor(bot_name=bot_name, **(assistant_model_kwargs or {}))

    self.conversation_model = load_model(
      conversation_model_name,
      bot_name,
      **(conversation_model_kwargs or {}),
    )

    logger.debug(f'Initialized LanguageProcessor with {self.io_handler.__class__.__name__}')

  def start(self) -> None:
    """Starts a conversation that will continue until the process is terminated."""
    while True:
      self.converse()

  def converse(self) -> None:
    """
    Conducts a single round of conversation between the conversation model and the IO handler
    """
    input_text = self.io_handler.receive()
    output_text = self.assistant_model.converse(input_text)
    output_text = output_text or self.conversation_model.converse(input_text)
    self.io_handler.send(output_text)


def main():
  # Create a separate log file for each chatbot run
  root_logger.addHandler(numbered_file_handler(os.path.join(LOGS_DIR, 'conversation', 'chats')))

  logger.info('Initializing chatbot...')

  parser = argparse.ArgumentParser(
    prog = 'drone chat',
  )
  parser.add_argument('--io', default=None, choices=['console'])
  parser.add_argument('-b', '--bot-name', default=DEFAULT_BOT_NAME)
  parser.add_argument(
    '--assistant-model-args', dest='assistant_model_kwargs', type=json.loads, default={})
  parser.add_argument('-c', '--conversation-model-name', default=DEFAULT_MODEL_NAME)
  parser.add_argument(
    '--conversation-model-args', dest='conversation_model_kwargs', type=json.loads, default={})
  args = vars(parser.parse_args())

  io_handler = None
  match args.pop('io'):
    case 'console':
      io_handler = ConsoleIOHandler(args['bot_name'])

  processor = LanguageProcessor(
    io_handler = io_handler,
    **args,
  )
  processor.start()


if __name__ == '__main__':
  init(main)
