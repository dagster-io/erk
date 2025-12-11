"""Tests for basic completion functionality and agent lifecycle."""

from unittest.mock import Mock, patch

import pytest
from anthropic.types import Usage

from csbot.agents.messages import AgentTextMessage


class TestCompletion:
    """Test completion functionality."""

    @pytest.mark.asyncio
    async def test_create_completion_simple(self, agent, mock_anthropic_client):
        """Test simple completion creation."""
        # Mock the response
        mock_response = Mock()
        mock_text_block = Mock()
        mock_text_block.text = "Hello! I'm Claude, an AI assistant."
        mock_response.content = [mock_text_block]
        mock_response.usage = Usage(input_tokens=0, output_tokens=0)

        mock_anthropic_client.messages.create.return_value = mock_response

        with patch.object(agent, "client", mock_anthropic_client):
            result = await agent.create_completion(
                model="claude-3-sonnet-20240229",
                system="You are a helpful assistant.",
                messages=[AgentTextMessage(role="user", content="Hello!")],
                max_tokens=1000,
            )

        assert result == "Hello! I'm Claude, an AI assistant."
        mock_anthropic_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_completion_empty_response(self, agent, mock_anthropic_client):
        """Test completion with empty response."""
        mock_response = Mock()
        mock_response.content = []
        mock_response.usage = Usage(input_tokens=0, output_tokens=0)

        mock_anthropic_client.messages.create.return_value = mock_response

        with patch.object(agent, "client", mock_anthropic_client):
            result = await agent.create_completion(
                model="claude-3-sonnet-20240229",
                system="You are a helpful assistant.",
                messages=[AgentTextMessage(role="user", content="Hello!")],
            )

        assert result == ""


class TestAgentLifecycle:
    """Test agent setup and cleanup."""

    @pytest.mark.asyncio
    async def test_close(self, agent, mock_anthropic_client):
        """Test agent cleanup."""
        with patch.object(agent, "client", mock_anthropic_client):
            await agent.close()

        mock_anthropic_client.close.assert_called_once()
