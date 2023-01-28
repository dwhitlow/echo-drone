import logging
from abc import ABC, abstractmethod

from bot.common.ansi import Code, escape

logger = logging.getLogger(__name__)


class IOHandler(ABC):
  """Base class for language package I/O"""

  @abstractmethod
  def receive(self) -> str:
    """Blocks for user input and returns then returns that input"""

  @abstractmethod
  def send(self, text: str) -> None:
    """Outputs the provided text"""


class ConsoleIOHandler(IOHandler):
  """Connects to stdin/stdout"""

  def __init__(self, bot_name: str):
    self.bot_name = bot_name

  def receive(self) -> str:
    text = input(f"{escape('You', Code.BLUE, Code.BOLD)}: ")
    logger.info(f'You: {text}')
    return text

  def send(self, text: str) -> None:
    logger.info(f'{self.bot_name}: {text}')
    print(f"{escape(self.bot_name, Code.GREEN, Code.BOLD)}: {text}")
