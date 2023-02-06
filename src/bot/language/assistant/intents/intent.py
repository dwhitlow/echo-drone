from abc import ABC, abstractmethod
from typing import Optional


class IntentHandler(ABC):
  """Base class for intent handlers. Provides convenience methods for extracting data
  from snips-nlu intent dictionaries returned by the parser"""
  @abstractmethod
  def can_handle(self, intent: dict) -> bool:
    """Returns true if this class can handle the specified intent."""

  @abstractmethod
  def handle(self, intent: dict) -> str:
    """Handles a parsed intent and returns a text response to either summarize
    how the response was handled or answer the query represented by the intent.
    
    Raises ValueError if this IntentHandler class can't handle the specified intent."""

  def _find_intent_name(self, intent: dict) -> str:
    return intent['intent']['intentName']

  def _find_named_slot_value(
      self, intent: dict, name: str, default_value: Optional[str] = None) -> Optional[str]:
    for slot in intent['slots']:
      if slot['slotName'] == name:
        match slot['value'].get('kind', None):
          case 'TimeInterval':
            return slot['value']['from']
          case _:
            return slot['value']['value']
    return default_value
