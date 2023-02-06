import logging
from abc import ABC, abstractmethod
from typing import Optional

import torch
from halo import Halo
from transformers import AutoModelForCausalLM, AutoTokenizer

from bot.common.halo import halo_stream
from bot.common.logging import serialize_dict
from bot.common.perf import log_resource_usage, timed_fn
from bot.language.conversation.data import Message, Speaker

logger = logging.getLogger(__name__)


class ConversationModel(ABC):
  """
  ConversationModel is an abstraction for conversational Hugging Face transformers
  https://huggingface.co/tasks/conversational
  """

  def __init__(
      self,
      model_name: str,
      bot_name: str,
      torch_device_name: Optional[str],
      chat_history_limit: int,
      **generate_kwargs: dict,
  ):
    if torch_device_name is not None:
      self.device = torch.device(torch_device_name)
    else:
      self.device = self.default_device()

    self.__load_model(model_name)

    self.model_name = model_name
    self.bot_name = bot_name
    self.chat_history_limit = chat_history_limit
    self.generate_kwargs = generate_kwargs

    self.chat_history: list[Message] = []

  @timed_fn
  def __load_model(self, model_name: str) -> None:
    with Halo(text='Loading chat model...', spinner='dots', stream=halo_stream()):
      self.tokenizer = AutoTokenizer.from_pretrained(model_name)
      self.model = self._auto_model_class().from_pretrained(model_name)

      # TODO: Parameterize half precision switch
      if self.device.type != 'cpu':
        # Transform model to use a half precision parameter datatype before copying model
        # to target device to save memory at the cost of accuracy
        self.model.half()

      self.model.to(self.device)

  def _log_init(self, **init_args: dict):
    logger.debug(f'Initialized {self.__class__.__name__} with args:\n{serialize_dict(init_args)}')
    log_resource_usage(self.device)

  def _auto_model_class(self) -> any: # Skip return type hint for hidden class _BaseAutoModelClass
    """
    Returns a subclass transformers.models.auto.auto_factory._BaseAutoModelClass
    that will be used by __load_model().
    """
    return AutoModelForCausalLM

  def default_device(self) -> torch.device:
    """Determines the default device that the model should run on"""
    if torch.cuda.is_available():
      return torch.device('cuda')
    elif torch.backends.mps.is_available():
      return torch.device('mps')
    else:
      return torch.device('cpu')

  def converse(self, input_text: str) -> str:
    """
    Submits the chat history and user input to the model and returns its latest response
    """
    self.chat_history.append(Message(Speaker.USER, input_text))
    recent_chat_history = self.chat_history[len(self.chat_history)-self.chat_history_limit:]
    input_tensor = self._encode_text(self._format_model_input(recent_chat_history))

    output_tensor = self._extract_model_response(input_tensor, self._generate(input_tensor))
    output_text = self._transform_output(self._decode_text(output_tensor))
    self.chat_history.append(Message(Speaker.BOT, output_text))

    return output_text

  @timed_fn
  def _generate(self, input_tensor: torch.Tensor) -> torch.Tensor:
    """
    Copies the input tensor to the appropriate device, runs the model
    on the tokenized input, and returns the raw output
    """
    with Halo(text=f"{self.bot_name} is thinking...", spinner='dots', stream=halo_stream()):
      input_tensor = input_tensor.to(self.device)
      return self.model.generate(input_tensor, **self.generate_kwargs)

  @abstractmethod
  def _format_model_input(self, chat_history: list[Message]) -> str:
    """
    Formats the input that will be passed to the model's generate function
    """

  @abstractmethod
  def _format_model_output(self, chat_history: list[Message], response: Message) -> str:
    """
    Formats the expected model output for training purposes, given the chat history
    """

  def _extract_model_response(
    self,
    input_tensor: torch.Tensor,
    output_tensor: torch.Tensor,
  ) -> torch.Tensor:
    """
    Given the model input and output, extracts the latest response
    """
    return output_tensor[:, input_tensor.shape[-1]:][0]

  def _transform_output(self, output_text: str) -> str:
    """
    Apply any necessary model-specific transformations / post-processing on the output
    """
    return output_text

  def _encode_text(self, text: str) -> torch.Tensor:
    """Generate Pytorch tensor from string"""
    return self.tokenizer.encode(text, return_tensors='pt')

  def _decode_text(self, tensor: torch.Tensor) -> str:
    """Generate text from Pytorch tensor"""
    return self.tokenizer.decode(tensor, skip_special_tokens=True)
