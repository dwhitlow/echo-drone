import logging
import time

import psutil
import torch

logger = logging.getLogger(__name__)


__BYTE_CONVERSION_FACTOR = 1024
__CONVERSION_THRESHOLD_FACTOR = 10

# Consume meaningless 0.0 value that occurs on first call
try:
  psutil.Process().cpu_percent()
except (psutil.AccessDenied, psutil.NoSuchProcess) as init_ex:
  logger.warning(f"Couldn't get process info for perf logging: {init_ex}")


def timed_fn(fn: callable) -> callable:
  """Decorator that will log the execution time of decorated functions in seconds"""
  def wrapped_fn(*args, **kwargs):
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    end = time.perf_counter()
    logger.debug(f"Function {fn.__name__!r} executed in {end-start:.04f} seconds")
    return result

  return wrapped_fn


def log_resource_usage(torch_device: torch.device) -> None:
  """Logs memory used by this process. Does not include child processes."""
  try:
    proc = psutil.Process()
    mem_info = proc.memory_full_info()
    virtual_mem = psutil.virtual_memory()

    logger.debug(f'CPU: {proc.cpu_percent():.01f} % / {psutil.cpu_count()} cores')

    used_mem = __bytes_human_readable(mem_info.rss)
    available_mem = __bytes_human_readable(virtual_mem.active)
    total_mem = __bytes_human_readable(virtual_mem.total)
    logger.debug(f'Memory: {used_mem} used / {available_mem} available / {total_mem} total')

    used_swap = __bytes_human_readable(mem_info.swap)
    total_swap = __bytes_human_readable(psutil.swap_memory().total)
    logger.debug(f'Swap: {used_swap} used / {total_swap} total')

  except (psutil.AccessDenied, psutil.NoSuchProcess) as ex:
    logger.warning(f"Couldn't get process info for perf logging: {ex}")

  if torch_device.type == 'cuda' and torch.cuda.is_available():
    logger.debug(f'GPU utilization: {torch.cuda.utilization(torch_device)}%')

    alloc_gpu_mem = __bytes_human_readable(torch.cuda.memory_allocated(torch_device))
    res_gpu_mem = __bytes_human_readable(torch.cuda.memory_reserved(torch_device))
    total_gpu_mem = __bytes_human_readable(
      torch.cuda.get_device_properties(torch_device).total_memory)
    logger.debug(
      f'GPU memory: {alloc_gpu_mem} used / '
      f'{res_gpu_mem} reserved / '
      f'{total_gpu_mem} total'
    )


def __bytes_human_readable(num_bytes: int) -> str:
  units = ['TiB', 'GiB', 'MiB', 'KiB', 'bytes']
  unit_factor = __BYTE_CONVERSION_FACTOR ** (len(units) - 1)
  for unit in units:
    if num_bytes >= unit_factor * __CONVERSION_THRESHOLD_FACTOR:
      return f'{round(num_bytes / unit_factor):,} {unit}'
    unit_factor /= __BYTE_CONVERSION_FACTOR
  return f'{num_bytes:,} bytes'
