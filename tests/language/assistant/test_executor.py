from bot.language.assistant.executor import Executor
from bot.language.assistant.intents import IntentHandler
from tests import EchoTestCase


class ExecutorTestCase(EchoTestCase):
  def setUp(self):
    self.executor = Executor(intent_handlers=[ExampleHandler()])

  def test_converse(self):
    result = self.executor.converse("Will it rain in San Francisco on February 11, 2023?")
    self.assertEqual(result, 'query_weather;San Francisco;2023-02-11 00:00:00 -08:00;precipitation')


class ExampleHandler(IntentHandler):
  def can_handle(self, intent: dict) -> bool:
    return self._find_intent_name(intent) == 'query_weather'

  def handle(self, intent: dict) -> str:
    return f"{self._find_intent_name(intent)};{self._find_named_slot_value(intent, 'city', '')};{self._find_named_slot_value(intent, 'time', '')};{self._find_named_slot_value(intent, 'attribute', '')}"
