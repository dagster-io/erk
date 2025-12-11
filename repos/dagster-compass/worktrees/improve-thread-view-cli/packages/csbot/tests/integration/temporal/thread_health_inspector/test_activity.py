"""Tests for thread health inspector Temporal activity."""

import json
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, cast

import pytest
from temporalio.testing import ActivityEnvironment

from csbot.agents.messages import AgentMessage, AgentModelSpecificMessage, AgentTextMessage
from csbot.agents.protocol import AsyncAgent
from csbot.temporal.thread_health_inspector.activity import (
    ThreadHealthInspectorActivity,
    ThreadHealthInspectorInput,
    ThreadHealthInspectorSuccess,
    ThreadHealthScore,
)

if TYPE_CHECKING:
    from csbot.slackbot.storage.interface import SlackbotStorage


class FakeAsyncAgent(AsyncAgent):
    """Fake AsyncAgent for testing that returns predefined scores."""

    def __init__(self, model: str = "test-model"):
        self._model = model
        self.create_completion_calls = []

    @property
    def model(self) -> str:
        return self._model

    async def stream_messages_with_tools(
        self,
        model: str,
        system: str,
        messages: list[AgentMessage],
        tools: dict[str, Callable[..., Awaitable[Any]]],
        max_tokens: int,
        on_history_added: Callable[[AgentMessage], Awaitable[None]] | None = None,
        on_token_usage: Callable[[int, dict[str, Any]], Awaitable[None]] | None = None,
    ):
        if False:
            yield

        raise NotImplementedError("Not needed for this test")

    async def create_completion(
        self, model: str, system: str, messages: list[AgentMessage], max_tokens: int = 4000
    ) -> str:
        self.create_completion_calls.append(
            {"model": model, "system": system, "messages": messages, "max_tokens": max_tokens}
        )
        # Return a predefined JSON response
        return json.dumps(
            {
                "accuracy": 8,
                "responsiveness": 7,
                "helpfulness": 9,
                "reasoning": "Test evaluation: Bot performed well overall",
                "failure_occurred": False,
            }
        )

    async def create_completion_with_tokens(
        self, model: str, system: str, messages: list[AgentMessage], max_tokens: int = 4000
    ) -> tuple[str, int]:
        """Return completion with token count."""
        text = await self.create_completion(model, system, messages, max_tokens)
        return text, 150  # Fake token count

    async def close(self) -> None:
        pass


class FakeSlackbotInstanceStorage:  # Not inheriting from SlackbotInstanceStorage to avoid all abstract methods
    """Fake instance storage for testing."""

    def __init__(self, bot_id: str, events: list[AgentMessage]):
        self.bot_id = bot_id
        self.events = events
        self.kv_data: dict[tuple[str, str], str] = {}

    @property
    def sql_conn_factory(self):
        raise NotImplementedError("Not needed for this test")

    async def get(self, family: str, key: str) -> str | None:
        # Return cached events for slack_thread_events family
        if family == "slack_thread_events":
            return json.dumps(
                [{"role": event.role, "content": event.content} for event in self.events]
            )
        return self.kv_data.get((family, key))

    async def set(
        self, family: str, key: str, value: str, expiry_seconds: int | None = None
    ) -> None:
        self.kv_data[(family, key)] = value

    async def exists(self, family: str, key: str) -> bool:
        return (family, key) in self.kv_data

    async def get_and_set(
        self, family: str, key: str, value_factory, expiry_seconds: int | None = None
    ) -> None:
        raise NotImplementedError("Not needed for this test")

    async def delete(self, family: str, key: str) -> None:
        self.kv_data.pop((family, key), None)

    def for_instance(self, bot_id: str):
        return self


class FakeSlackbotStorage:  # Not inheriting from SlackbotStorage to avoid all abstract methods
    """Fake storage for testing."""

    def __init__(self, instance_storage: FakeSlackbotInstanceStorage):
        self.instance_storage = instance_storage

    def for_instance(self, bot_id: str):
        return self.instance_storage


@pytest.mark.asyncio
async def test_thread_health_inspector_activity_happy_path():
    """Test thread health inspector activity with a simple conversation."""
    # Create fake events for a thread
    events: list[AgentMessage] = [
        AgentModelSpecificMessage(role="user", content="What is our total revenue?"),
        AgentModelSpecificMessage(
            role="assistant",
            content=[
                {"type": "text", "text": "Let me check that for you."},
                {
                    "type": "tool_use",
                    "name": "run_sql_query",
                    "input": {"query": "SELECT SUM(revenue) FROM sales"},
                },
            ],
        ),
        AgentModelSpecificMessage(
            role="user",
            content=[
                {
                    "type": "tool_result",
                    "tool_use_id": "123",
                    "content": "Total revenue: $1,000,000",
                }
            ],
        ),
        AgentModelSpecificMessage(role="assistant", content="Your total revenue is $1,000,000."),
    ]

    # Create fake storage with events
    instance_storage = FakeSlackbotInstanceStorage(
        bot_id="TEST-team-channel-governance", events=events
    )
    fake_storage = FakeSlackbotStorage(instance_storage)

    # Create fake agent
    fake_agent = FakeAsyncAgent()

    # Create activity
    activity = ThreadHealthInspectorActivity(
        slackbot_storage=cast("SlackbotStorage", fake_storage),
        agent=fake_agent,
        honeycomb_config=None,
    )

    # Create input
    activity_input = ThreadHealthInspectorInput(
        governance_bot_id="TEST-team-channel-governance",
        channel_id="C01234567",
        thread_ts="1234567890.123456",
    )

    # Run activity in test environment
    env = ActivityEnvironment()
    result = await env.run(activity.inspect_thread_health, activity_input)

    assert isinstance(result, ThreadHealthInspectorSuccess)

    # Verify result
    assert result.event_count == 4
    assert result.tokens_consumed == 150
    assert isinstance(result.score, ThreadHealthScore)
    assert result.score.accuracy == 8
    assert result.score.responsiveness == 7
    assert result.score.helpfulness == 9
    assert result.score.reasoning == "Test evaluation: Bot performed well overall"

    # Verify agent was called
    assert len(fake_agent.create_completion_calls) == 1
    call = fake_agent.create_completion_calls[0]
    assert "evaluating a conversation" in call["system"].lower()
    assert len(call["messages"]) == 1
    assert isinstance(call["messages"][0], AgentTextMessage)
    assert "TRANSCRIPT" in call["messages"][0].content
