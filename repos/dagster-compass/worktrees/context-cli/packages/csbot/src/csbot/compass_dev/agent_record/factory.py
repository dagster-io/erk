"""Agent factory registry and management."""

from typing import Any

from .anthropic.factory import AnthropicAgentFactory
from .recorder import AgentFactory

# Hardcoded registry of available agent factories
AGENT_FACTORIES: dict[str, type[AgentFactory]] = {
    "anthropic": AnthropicAgentFactory,
    # Future agent types can be added here:
    # "gemini": GeminiAgentFactory,
}


def get_agent_factory(agent_type: str) -> AgentFactory:
    """Get a factory instance for the specified agent type.

    Args:
        agent_type: The agent type identifier

    Returns:
        Factory instance for the agent type

    Raises:
        ValueError: If agent type is not registered
    """
    if agent_type not in AGENT_FACTORIES:
        available = list(AGENT_FACTORIES.keys())
        raise ValueError(f"Unknown agent type: {agent_type}. Available: {available}")

    factory_class = AGENT_FACTORIES[agent_type]
    return factory_class()


def list_available_agents() -> list[str]:
    """Get list of all registered agent types."""
    return list(AGENT_FACTORIES.keys())


def validate_agent_availability(agent_type: str, config: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate that an agent type is available and properly configured.

    Args:
        agent_type: The agent type to validate
        config: Configuration dictionary for the agent

    Returns:
        Tuple of (is_available, error_message)
    """
    try:
        get_agent_factory(agent_type)
        # Basic validation that the factory can be instantiated
        return True, None
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Agent factory error: {e}"
