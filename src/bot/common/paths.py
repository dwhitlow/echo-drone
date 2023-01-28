import os
import re


def find_latest_numbered_entry(search_dir: str, pattern: re.Pattern[str]) -> int:
  """
  Finds all entries in a directory `dir` that match a `pattern` with an
  int capture group at index 1 (ex: r'(\d+).log'). Returns the highest integer
  matched. If no matches were found, returns -1

  This function is used to manage strictly increasing series of files/directories
  for things like run logs, trained model saves, etc.

  Will return IndexError if pattern does not include at least one capture group,
  and ValueError if the string matched by group(1) cannot be parsed as an int.
  """
  id_number = -1

  for entry in os.listdir(search_dir):
    match = re.match(pattern, entry)
    if match:
      id_number = max(id_number, int(match.group(1)))

  return id_number
