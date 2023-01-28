import logging
import os
from io import StringIO

from bot.common.paths import find_latest_numbered_entry


def stream_handler(log_level: int = logging.NOTSET) -> logging.StreamHandler:
  """Builds and returns a configured console log handler"""
  handler = logging.StreamHandler()
  handler.setLevel(log_level)
  # Prepend carriage return to overwrite Halo spinners
  handler.setFormatter(logging.Formatter('\r[%(name)s] %(message)s'))
  handler.addFilter(__console_io_filter)
  return handler


def numbered_file_handler(log_dir: str, log_level: int = logging.NOTSET) -> logging.FileHandler:
  """
  Builds and returns a log handler that writes to a uniquely-numbered file
  in `log_dir`.
  """
  os.makedirs(log_dir, exist_ok=True)
  log_id = find_latest_numbered_entry(log_dir, r'(\d+).log') + 1
  return file_handler(os.path.join(log_dir, f'{log_id}.log'), log_level)


def file_handler(log_file_path: str, log_level: int = logging.NOTSET) -> logging.FileHandler:
  """Builds and returns a configured file log handler"""
  handler = logging.FileHandler(log_file_path)
  handler.setLevel(log_level)
  handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s'))
  return handler


def serialize_dict(d: dict, indent_level: int = 2) -> str:
  """Serializes a dictionary in human-readable format."""
  string_builder = StringIO()
  for k, v in d.items():
    string_builder.write(' ' * indent_level)
    if v and isinstance(v, dict):
      string_builder.write(f'{k}:\n{serialize_dict(v, indent_level + 2)}\n')
    elif v and isinstance(v, list):
      list_indent = ' ' * (indent_level + 2)
      serialized_list = '\n'.join([
        serialize_dict(lv, indent_level + 2) if isinstance(lv, dict) else f'{list_indent}{lv}'
        for lv in v
      ])
      string_builder.write(f'{k}:\n{serialized_list}\n')
    else:
      string_builder.write(f'{k}: {v}\n')
  return string_builder.getvalue().rstrip()


def __console_io_filter(record: logging.LogRecord) -> int:
  """
  Filters out StreamHandler logs from IOHandler
  as they are already printed with custom formatting
  """
  if record.name == 'bot.language.io':
    return 0
  else:
    return 1
