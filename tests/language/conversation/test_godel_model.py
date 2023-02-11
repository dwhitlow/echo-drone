import torch

from bot.language.conversation.godel_model import GodelModel
from tests import EchoTestCase


class GodelModelTestCase(EchoTestCase):
  def test_converse(self) -> None:
    torch.manual_seed(0)

    model = GodelModel(
      'microsoft/GODEL-v1_1-base-seq2seq',
      'Bot',
      bot_instructions = 'given a dialog context, you need to respond helpfully',
    )

    output = model.converse('Hello!')
    self.assertEqual(output, 'i like to make friends with my friends')
