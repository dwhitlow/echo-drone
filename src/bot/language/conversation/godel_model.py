from typing import Optional

import torch
from transformers import AutoModelForSeq2SeqLM

from bot.language.conversation.data import Message
from bot.language.conversation.model import ConversationModel

DEFAULT_CHAT_HISTORY_LIMIT = 8
DEFAULT_BOT_INSTRUCTIONS=(
  'given a dialog context, you need to respond helpfully, '
  'but your responses can be quick-witted and snarky'
)
DEFAULT_BOT_KNOWLEDGE=''
DEFAULT_GENERATE_ARGS = {
  'min_length': 8,
  'max_length': 40,
  'top_p': 0.9,
  'do_sample': True,
}


class GodelModel(ConversationModel):
  """
  ConversationModel implementation for Microsoft GODEL

  https://huggingface.co/microsoft/GODEL-v1_1-large-seq2seq
  https://huggingface.co/microsoft/GODEL-v1_1-base-seq2seq
  """

  def __init__(
      self,
      model_name: str,
      bot_name: str,
      torch_device_name: Optional[str] = None,
      chat_history_limit: int = DEFAULT_CHAT_HISTORY_LIMIT,
      bot_instructions: str = DEFAULT_BOT_INSTRUCTIONS,
      bot_knowledge: str = DEFAULT_BOT_KNOWLEDGE,
      **generate_kwargs: dict,
  ):
    super().__init__(
      model_name,
      bot_name,
      torch_device_name,
      chat_history_limit,
      **{**DEFAULT_GENERATE_ARGS, **generate_kwargs},
    )

    self.bot_instructions = bot_instructions
    self.bot_knowledge = bot_knowledge

    self._log_init(**{
      'model_name': model_name,
      'bot_name': bot_name,
      'bot_instructions': bot_instructions,
      'bot_knowledge': bot_knowledge,
      'generate_kwargs': generate_kwargs,
    })

  def _auto_model_class(self) -> any:
    return AutoModelForSeq2SeqLM

  def _format_model_input(self, chat_history: list[Message]) -> str:
    instructions = f"Instruction: {self.bot_instructions}"
    dialog = ' EOS '.join([msg.body for msg in chat_history])
    knowledge = f" [KNOWLEDGE] {self.bot_knowledge}" if self.bot_knowledge != '' else ''
    return f"{instructions} [CONTEXT] {dialog}{knowledge}"

  def _format_model_output(self, chat_history: list[Message], response: Message) -> str:
    return response.body

  def _extract_model_response(
    self,
    input_tensor: torch.Tensor,
    output_tensor: torch.Tensor,
  ) -> torch.Tensor:
    return output_tensor

  def _decode_text(self, tensor: torch.Tensor) -> str:
    return self.tokenizer.decode(tensor[0], skip_special_tokens=True)
