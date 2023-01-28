import unittest

from bot.language.conversation.dialo_gpt_model import DialoGPTModel


class DialoGPTModelTestCase(unittest.TestCase):
  def test_converse(self) -> None:
    model = DialoGPTModel('microsoft/DialoGPT-small', 'Bot')

    output = model.converse('Hello!')
    self.assertEqual(output, 'Hi!')
