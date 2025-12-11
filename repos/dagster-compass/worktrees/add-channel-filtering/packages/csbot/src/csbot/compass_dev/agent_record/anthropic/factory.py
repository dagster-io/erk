"""Anthropic agent factory implementation."""

from anthropic import AsyncAnthropic

from csbot.agents.anthropic.anthropic_agent import DEFAULT_ANTHROPIC_RETRIES, AnthropicAgent
from csbot.agents.protocol import AsyncAgent
from csbot.compass_dev.agent_record.anthropic.recorder import AnthropicRecorder
from csbot.compass_dev.agent_record.recorder import (
    AgentConfig,
    AgentFactory,
    AsyncAgentRecorder,
    RecorderConfig,
)


class AnthropicAgentFactory(AgentFactory):
    """Factory for creating Anthropic agents and recorders."""

    def create_agent(self, config: AgentConfig) -> AsyncAgent:
        """Create an Anthropic agent instance."""
        client = AsyncAnthropic(
            api_key=config.api_key, max_retries=DEFAULT_ANTHROPIC_RETRIES, **config.client_options
        )
        return AnthropicAgent(client)

    def create_recorder(self, config: RecorderConfig) -> AsyncAgentRecorder:
        """Create an Anthropic recorder instance."""
        return AnthropicRecorder(api_key=config.api_key, output_dir=config.output_dir)

    def get_supported_models(self) -> list[str]:
        """Get list of supported Anthropic model names."""
        return [
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]

    def get_agent_type(self) -> str:
        """Get the agent type identifier."""
        return "anthropic"
