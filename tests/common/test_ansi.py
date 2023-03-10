from bot.common.ansi import Code, escape
from tests import EchoTestCase


class AnsiTestCase(EchoTestCase):
  def test_format(self) -> None:
    input = 'Test input'
    result = escape(input, Code.GREEN, Code.BOLD, Code.ITALIC)
    self.assertEqual(result, f"\033[32;1;3m{input}\033[0m")
