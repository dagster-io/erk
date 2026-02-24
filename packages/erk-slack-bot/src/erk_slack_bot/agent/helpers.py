from collections.abc import AsyncIterator

from erk_slack_bot.agent.events import AgentEvent, AgentResult, TextDelta


async def accumulate_text(*, events: AsyncIterator[AgentEvent]) -> str:
    parts: list[str] = []
    async for event in events:
        if isinstance(event, TextDelta):
            parts.append(event.text)
    return "".join(parts)


async def collect_events(*, events: AsyncIterator[AgentEvent]) -> list[AgentEvent]:
    result: list[AgentEvent] = []
    async for event in events:
        result.append(event)
    return result


def extract_result(*, events: list[AgentEvent]) -> AgentResult | None:
    for event in reversed(events):
        if isinstance(event, AgentResult):
            return event
    return None
