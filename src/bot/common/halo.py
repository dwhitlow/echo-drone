import io
import os
import sys


def halo_stream() -> io.TextIOBase | io.TextIOWrapper:
  """
  Determines the correct write stream to use for Halo spinners based on
  the HALO_STREAM env var. Defaults to stdout.
  """
  stream_name = os.getenv('HALO_STREAM')
  if stream_name == 'stdout' or stream_name == '' or stream_name is None:
    return sys.stdout
  if stream_name == 'stderr':
    return sys.stderr
  if stream_name == '/dev/null':
    return open(os.devnull, 'w', encoding='utf8')
  raise ValueError(f'Unrecognized Halo stream name: {stream_name}')
