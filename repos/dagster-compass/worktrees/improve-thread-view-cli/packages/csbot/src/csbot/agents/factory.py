"""Agent factory functions and managed context managers."""

import asyncio
import os
from contextlib import contextmanager
from typing import TYPE_CHECKING

from csbot.agents.anthropic import AnthropicAgent
from csbot.agents.protocol import AsyncAgent
from csbot.utils.check_async_context import ensure_not_in_async_context

if TYPE_CHECKING:
    from csbot.slackbot.slackbot_core import AIConfig


def create_anthropic_agent(
    api_key: str | None = None, model: str = "claude-sonnet-4-20250514"
) -> AsyncAgent:
    """Create an Anthropic agent instance.

    Args:
        api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
        model: Model name to use (default: claude-sonnet-4-20250514)

    Returns:
        Configured AnthropicAgent instance

    Raises:
        ValueError: If api_key is not provided and ANTHROPIC_API_KEY env var is missing
    """
    if api_key is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

    return AnthropicAgent.from_api_key(api_key, model=model)


def create_agent_from_config(ai_config: "AIConfig") -> AsyncAgent:
    """Create an agent from an AIConfig object.

    Args:
        ai_config: Configuration object containing provider, API key, and model

    Returns:
        Configured agent instance for the specified provider

    Raises:
        ValueError: If provider is not recognized
    """
    if ai_config.provider == "anthropic":
        return create_anthropic_agent(
            api_key=ai_config.api_key.get_secret_value(), model=ai_config.model
        )
    elif ai_config.provider == "bedrock":
        return AnthropicAgent.from_bedrock(
            aws_access_key=ai_config.aws_access_key,
            aws_secret_key=ai_config.aws_secret_key.get_secret_value()
            if ai_config.aws_secret_key
            else None,
            aws_region=ai_config.aws_region,
            inference_profile_arn=ai_config.inference_profile_arn,
        )
    else:
        raise ValueError(f"Unknown AI provider: {ai_config.provider}")


@contextmanager
def managed_anthropic_agent(api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
    """Context manager for Anthropic agent lifecycle in SYNC contexts only.

    Args:
        api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
        model: Model name to use (default: claude-sonnet-4-20250514)

    Raises:
        ValueError: If api_key is not provided and ANTHROPIC_API_KEY env var is missing
        RuntimeError: If called from within an async context
    """
    ensure_not_in_async_context()

    agent = create_anthropic_agent(api_key, model=model)
    try:
        yield agent
    finally:
        asyncio.run(agent.close())
