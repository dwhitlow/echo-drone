from enum import StrEnum

ESCAPE = "\033[{}m"


class Code(StrEnum):
  """ANSI escape code values that are used with `escape` to format text"""
  RESET = '0'
  BOLD = '1'
  FAINT = '2'
  ITALIC = '3'
  UNDERLINE = '4'
  BLINK = '5'
  INVERSE = '7'
  HIDDEN = '8'
  STRIKETHROUGH = '9'

  BLACK = '30'
  RED = '31'
  GREEN = '32'
  YELLOW = '33'
  BLUE = '34'
  MAGENTA = '35'
  CYAN = '36'
  WHITE = '37'
  DEFAULT_COLOR = '39'

  BLACK_BG = '40'
  RED_BG = '41'
  GREEN_BG = '42'
  YELLOW_BG = '43'
  BLUE_BG = '44'
  MAGENTA_BG = '45'
  CYAN_BG = '46'
  WHITE_BG = '47'
  DEFAULT_BG = '49'


def escape(text: str, *modes: Code) -> str:
  """
  Returns a string beginning with the specified ANSI escape codes and ending with a reset code
  """
  return f"{ESCAPE.format(';'.join(modes))}{text}{ESCAPE.format(Code.RESET)}"
