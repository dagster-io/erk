import re

from erkbot.models import (
    Command,
    OneShotCommand,
    OneShotMissingMessageCommand,
    PlanListCommand,
    QuoteCommand,
)


def strip_mentions(text: str) -> str:
    return re.sub(r"<@[^>]+>", " ", text).strip()


def parse_erk_command(text: str) -> Command | None:
    message = strip_mentions(text)
    if not message:
        return None

    normalized = " ".join(message.split())
    lowered = normalized.lower()

    if lowered == "plan list":
        return PlanListCommand()
    if lowered == "quote":
        return QuoteCommand()

    one_shot_match = re.match(r"(?i)^one[- ]shot\b", normalized)
    if not one_shot_match:
        return None

    one_shot_message = normalized[one_shot_match.end() :].strip()
    if not one_shot_message:
        return OneShotMissingMessageCommand()
    return OneShotCommand(message=one_shot_message)
