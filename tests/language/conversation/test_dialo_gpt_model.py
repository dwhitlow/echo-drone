from bot.language.conversation.dialo_gpt_model import DialoGPTModel
from tests import EchoTestCase


class DialoGPTModelTestCase(EchoTestCase):
  def test_converse(self) -> None:
    model = DialoGPTModel('microsoft/DialoGPT-small', 'Bot')

    output = model.converse('Hello!')
    self.assertEqual(output, 'Hi!')
