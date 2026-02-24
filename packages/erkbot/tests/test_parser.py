import unittest

from erkbot.models import (
    ChatCommand,
    OneShotCommand,
    OneShotMissingMessageCommand,
    PlanListCommand,
    QuoteCommand,
)
from erkbot.parser import parse_erk_command


class TestParseErkCommand(unittest.TestCase):
    def test_parse_plan_list(self) -> None:
        command = parse_erk_command("<@U123> plan list")
        self.assertIsInstance(command, PlanListCommand)

    def test_parse_quote(self) -> None:
        command = parse_erk_command("<@U123> quote")
        self.assertIsInstance(command, QuoteCommand)

    def test_parse_one_shot_message(self) -> None:
        command = parse_erk_command("<@U123> one-shot Review README")
        self.assertIsInstance(command, OneShotCommand)
        assert isinstance(command, OneShotCommand)
        self.assertEqual(command.message, "Review README")

    def test_parse_one_shot_missing_message(self) -> None:
        command = parse_erk_command("<@U123> one-shot")
        self.assertIsInstance(command, OneShotMissingMessageCommand)

    def test_parse_chat_command(self) -> None:
        command = parse_erk_command("<@U123> chat What is Python?")
        self.assertIsInstance(command, ChatCommand)
        self.assertEqual(command.message, "What is Python?")

    def test_parse_chat_no_message(self) -> None:
        command = parse_erk_command("<@U123> chat")
        self.assertIsNone(command)

    def test_parse_unknown(self) -> None:
        self.assertIsNone(parse_erk_command("<@U123> unsupported"))


if __name__ == "__main__":
    unittest.main()
