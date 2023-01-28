import os
import tempfile
import unittest

from bot.common.paths import find_latest_numbered_entry


class PathsTestCase(unittest.TestCase):
  def setUp(self) -> None:
    self.dir = tempfile.mkdtemp('drone-test-paths-')

    for fn in ['0.log', '1.log', '3.log', 'README.txt', 'chat-0.log']:
      with open(os.path.join(self.dir, fn), 'w') as f:
        pass

  def test_find_latest_numbered_entry(self) -> None:
    id = find_latest_numbered_entry(self.dir, r'^chat-(\d+).log$')
    self.assertEqual(id, 0)

  def test_find_latest_numbered_entry_no_matches(self) -> None:
    id = find_latest_numbered_entry(self.dir, r'^(\d+).txt$')
    self.assertEqual(id, -1)

  def test_find_latest_numbered_entry_gap(self) -> None:
    id = find_latest_numbered_entry(self.dir, r'^(\d+).log$')
    self.assertEqual(id, 3)
