"""Shared fixtures and utilities for AnthropicAgent tests."""

from unittest.mock import AsyncMock

import pytest

from csbot.agents.anthropic.anthropic_agent import AnthropicAgent
from csbot.agents.messages import (
    AgentModelSpecificMessage,
    AgentTextMessage,
)


@pytest.fixture
def agent():
    """Create an AnthropicAgent instance for testing."""
    return AnthropicAgent.from_api_key("test-api-key")


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    return AsyncMock()


@pytest.fixture
def sample_messages():
    """Sample messages for testing."""
    return [
        AgentTextMessage(role="user", content="Hello, how are you?"),
        AgentModelSpecificMessage(role="assistant", content="I'm doing well, thank you!"),
    ]
