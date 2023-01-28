import re
from typing import Optional

from bot.language.conversation.data import Message
from bot.language.conversation.model import ConversationModel

DEFAULT_CHAT_HISTORY_LIMIT = 8
DEFAULT_GENERATE_ARGS = {
  'max_new_tokens': 40,
}


class DialoGPTModel(ConversationModel):
  """
  ConversationModel implementation for Microsoft DialoGPT

  https://huggingface.co/microsoft/DialoGPT-medium
  https://huggingface.co/microsoft/DialoGPT-large
  https://huggingface.co/microsoft/DialoGPT-small
  """

  def __init__(
      self,
      model_name: str,
      bot_name: str,
      torch_device_name: Optional[str] = None,
      chat_history_limit: int = DEFAULT_CHAT_HISTORY_LIMIT,
      **generate_kwargs: dict,
  ):
    super().__init__(
      model_name,
      bot_name,
      torch_device_name,
      chat_history_limit,
      **{**DEFAULT_GENERATE_ARGS, **generate_kwargs},
    )

    if 'pad_token_id' not in self.generate_kwargs:
      self.generate_kwargs['pad_token_id'] = self.tokenizer.eos_token_id

    self._log_init(**{
      'model_name': model_name,
      'bot_name': bot_name,
      'generate_kwargs': generate_kwargs,
    })

  def _format_model_input(self, chat_history: list[Message]) -> str:
    return ''.join([msg.body + self.tokenizer.eos_token for msg in chat_history])

  def _format_model_output(self, chat_history: list[Message], response: Message) -> str:
    return re.sub(
      fr"{self.tokenizer.eos_token}$",
      '',
      self._format_model_input(chat_history + [response]))
