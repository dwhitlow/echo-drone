import logging
import re
from typing import Optional

from bot.language.conversation.data import Message, Speaker
from bot.language.conversation.model import ConversationModel

logger = logging.getLogger(__name__)

DEFAULT_CHAT_HISTORY_LIMIT = 8
DEFAULT_BOT_PERSONA='This character is quick-witted and snarky, but helpful.'
DEFAULT_GENERATE_ARGS = {
  'max_new_tokens': 40,
}


class PygmalionModel(ConversationModel):
  """
  ConversationModel implementation for PygmalionAI

  https://huggingface.co/PygmalionAI/pygmalion-2.7b
  https://huggingface.co/PygmalionAI/pygmalion-1.3b
  https://huggingface.co/PygmalionAI/pygmalion-350m
  """

  def __init__(
      self,
      model_name: str,
      bot_name: str,
      torch_device_name: Optional[str] = None,
      chat_history_limit: int = DEFAULT_CHAT_HISTORY_LIMIT,
      bot_persona: str = DEFAULT_BOT_PERSONA,
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

    self.bot_persona = bot_persona

    self._log_init(**{
      'model_name': model_name,
      'bot_name': bot_name,
      'bot_persona': bot_persona,
      'generate_kwargs': generate_kwargs,
    })

  def _format_model_input(self, chat_history: list[Message]) -> str:
    prompt_delimiter = '<START>'
    if 'pygmalion-350m' in self.model_name:
      prompt_delimiter = ''
    prompt = f"{self.bot_name}'s Persona: {self.bot_persona}\n{prompt_delimiter}\n"

    chat_history = [
      f"{'You' if msg.speaker == Speaker.USER else self.bot_name}: {msg.body}\n"
      for msg in chat_history
    ]

    return f"{prompt}{''.join(chat_history)}{self.bot_name}: "

  def _format_model_output(self, chat_history: list[Message], response: Message) -> str:
    return re.sub(
      fr"\n{self.bot_name}: $",
      '',
      self._format_model_input(chat_history + [response]))

  def _transform_output(self, output_text: str) -> str:
    stripped_lines = [line.strip() for line in output_text.split("\n") if line.strip() != '']
    transformed_output_text = stripped_lines[0] if stripped_lines else ''
    if transformed_output_text != output_text:
      logger.debug(f"NOTE: the original output was edited:\n{output_text}")
    return transformed_output_text
