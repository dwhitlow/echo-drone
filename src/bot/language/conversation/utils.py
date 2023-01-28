import argparse
import logging
import sys

from transformers import AutoModel, AutoTokenizer

from bot.language.conversation.dialo_gpt_model import DialoGPTModel
from bot.language.conversation.godel_model import GodelModel
from bot.language.conversation.model import ConversationModel
from bot.language.conversation.pygmalion_model import PygmalionModel

logger = logging.getLogger('bot.language.conversation.utils')
logger.setLevel(logging.NOTSET) # Override default behavior for root logger


def load_model(model_name: str, bot_name: str, **model_kwargs: dict) -> ConversationModel:
  """Loads the appropriate ConversationModel subclass based on the name"""
  model_classification_name = model_name.replace('--', '/')
  if not model_name.startswith('/'):
    model_classification_name = f"/{model_classification_name}"

  if '/microsoft/DialoGPT-' in model_classification_name:
    return DialoGPTModel(model_name, bot_name, **model_kwargs)
  if '/microsoft/GODEL-v1_1-' in model_classification_name:
    return GodelModel(model_name, bot_name, **model_kwargs)
  if '/PygmalionAI/pygmalion-' in model_classification_name:
    return PygmalionModel(model_name, bot_name, **model_kwargs)

  raise ValueError(f"No ConversationModel class found for {model_name}")


def download_models(models: list[str]) -> None:
  """
  Downloads transformer models if they are not already cached.

  The current version of the transformers library does not provide a mechanism
  to download models without loading them, so each provided model will be loaded
  into memory and then deleted.

  TODO: Submit transformers feature request and PR to
    decompose model downloading from loading
  """
  for model_name in models:
    logger.info(f"Downloading model {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)

    # Free objects
    del tokenizer
    del model


def main():
  parser = argparse.ArgumentParser(
    prog = 'drone download_chat_models',
  )
  parser.add_argument('-m', '--model-name', action='append', required=True)
  args = parser.parse_args()

  download_models(args.model_name)


if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    sys.exit(130)
