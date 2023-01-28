import unittest

from bot.language.conversation.pygmalion_model import PygmalionModel


class PygmalionModelTestCase(unittest.TestCase):
  def test_converse(self) -> None:
    model = PygmalionModel(
      'PygmalionAI/pygmalion-1.3b',
      'Jarvis',
      bot_persona = 'This character is quick-witted and snarky, but sanguine. While they are quick to tease others, this belies a caring and helpful nature.',
    )

    output = model.converse('Hello, how are you doing today?')
    output = output.strip('"')
    self.assertEqual(output, "I'm doing great today! I've been doing a lot of work though, and you?")
