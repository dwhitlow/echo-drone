import tempfile

from snips_nlu import SnipsNLUEngine

from bot.language.assistant.train import train
from tests import EchoTestCase


class TrainTestCase(EchoTestCase):
  def test_train(self):
    with tempfile.TemporaryDirectory() as output_dir:
      print(output_dir)
      train(output_dir=output_dir)
      SnipsNLUEngine.from_path(output_dir)
