import argparse
import logging
import os
import shutil

from snips_nlu import SnipsNLUEngine
from snips_nlu.dataset import Dataset
from snips_nlu.default_configs import CONFIG_EN

from bot import LOGS_DIR
from bot import logger as root_logger
from bot.common.logging import numbered_file_handler
from bot.common.main import init
from bot.common.perf import log_resource_usage, timed_fn
from bot.language.assistant import ASSISTANT_DATA_DIR, ASSISTANT_MODEL_DIR

logger = logging.getLogger('bot.language.assistant.train')
logger.setLevel(logging.NOTSET) # Override default behavior for root logger


@timed_fn
def train(
    data_dir: str = ASSISTANT_DATA_DIR,
    output_dir: str = ASSISTANT_MODEL_DIR,
) -> None:
  """Trains the snips NLU engine used by assistant.Executor"""
  dataset_paths = []
  for entry in os.listdir(data_dir):
    path = os.path.join(data_dir, entry)
    if not os.path.isfile(path):
      continue
    dataset_paths.append(path)

  dataset = Dataset.from_yaml_files('en', dataset_paths)
  logger.info(
    f'Loaded {len(dataset.intents)} intents and {len(dataset.entities)} entities from {data_dir}')

  engine = SnipsNLUEngine(config=CONFIG_EN, random_state=20230206)
  engine.fit(dataset)

  log_resource_usage()

  os.makedirs(os.path.dirname(output_dir), exist_ok=True)
  shutil.rmtree(output_dir, ignore_errors=True)
  engine.persist(output_dir)


def main():
  # Create a separate log file for each training run
  root_logger.addHandler(numbered_file_handler(os.path.join(LOGS_DIR, 'assistant', 'trainings')))

  logger.info('Training assistant...')

  parser = argparse.ArgumentParser(
    prog = 'drone train_assist'
  )
  parser.add_argument('-d', '--data-dir', default=ASSISTANT_DATA_DIR)
  parser.add_argument('-o', '--output-dir', default=ASSISTANT_MODEL_DIR)
  args = parser.parse_args()

  train(**vars(args))


if __name__ == '__main__':
  init(main)
