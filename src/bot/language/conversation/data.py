# Allows methods to reference their enclosing class in their type hints
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Speaker(StrEnum):
  """Indicates the role of a speaker associated with a Message"""
  USER = 'User'
  BOT = 'Bot'

  def other(self) -> Speaker:
    """Returns the other party in the conversation"""
    if self == Speaker.USER:
      return Speaker.BOT
    else:
      return Speaker.USER


@dataclass
class Message:
  """
  Represents a message in a chat history used by ConversationModel.
  Associates a speaker role with the message body.
  """
  speaker: Speaker
  body: str
