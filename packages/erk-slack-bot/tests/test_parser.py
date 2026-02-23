import unittest

from erk_slack_bot.models import (
    OneShotCommand,
    OneShotMissingMessageCommand,
    PlanListCommand,
    QuoteCommand,
)
from erk_slack_bot.parser import parse_erk_command


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

    def test_parse_unknown(self) -> None:
        self.assertIsNone(parse_erk_command("<@U123> unsupported"))


if __name__ == "__main__":
    unittest.main()
