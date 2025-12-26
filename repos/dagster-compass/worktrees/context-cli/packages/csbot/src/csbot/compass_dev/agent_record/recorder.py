"""Base classes for agent recording infrastructure."""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

from csbot.agents.messages import AgentMessage
from csbot.agents.protocol import AsyncAgent


def get_scenario_subdirectory(scenario_name: str) -> str:
    """Determine the subdirectory for a scenario based on its name.

    Args:
        scenario_name: Name of the scenario being recorded

    Returns:
        Subdirectory name for organizing recordings
    """
    scenario_lower = scenario_name.lower()

    if "tool" in scenario_lower:
        return "tool_calling"
    elif "error" in scenario_lower or "fail" in scenario_lower:
        return "error_cases"
    elif "edge" in scenario_lower or "empty" in scenario_lower or "unicode" in scenario_lower:
        return "edge_cases"
    else:
        return "text_responses"


class AsyncAgentRecorder(ABC):
    """Abstract base class for recording agent responses."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or Path(__file__).parent / "recordings"

    def get_output_path(self, scenario_name: str, filename: str) -> Path:
        """Get the full output path for a recording file.

        Args:
            scenario_name: Name of the scenario being recorded
            filename: Name of the output file

        Returns:
            Full path where the recording should be saved
        """
        subdirectory = get_scenario_subdirectory(scenario_name)
        output_path = self.output_dir / subdirectory / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    @abstractmethod
    async def record_scenario(
        self,
        scenario_name: str,
        system: str,
        messages: list[AgentMessage],
        model: str = "default",
        tools: Mapping[str, Callable[..., Awaitable[Any]]] | None = None,
        max_tokens: int = 1000,
        save_as: str | None = None,
    ) -> Any:
        """Record a specific scenario with agent-specific event capture.

        Args:
            scenario_name: Name of the scenario being recorded
            system: System prompt for the scenario
            messages: Input messages for the scenario
            model: Model to use for generation
            tools: Optional tools available to the model
            max_tokens: Maximum tokens to generate
            save_as: Optional custom filename

        Returns:
            Structured recording data and metadata
        """
        ...

    @abstractmethod
    def get_agent_type(self) -> str:
        """Get the agent type identifier."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources."""
        ...


class AgentConfig:
    """Configuration for creating agent instances."""

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        client_options: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        self.api_key = api_key
        self.model = model
        self.client_options = client_options or {}
        self.extra_params = kwargs


class RecorderConfig:
    """Configuration for creating recorder instances."""

    def __init__(
        self,
        api_key: str,
        output_dir: Path | None = None,
        **kwargs: Any,
    ):
        self.api_key = api_key
        self.output_dir = output_dir
        self.extra_params = kwargs


class AgentFactory(ABC):
    """Abstract factory for creating agents and recorders."""

    @abstractmethod
    def create_agent(self, config: AgentConfig) -> AsyncAgent:
        """Create an agent instance."""
        ...

    @abstractmethod
    def create_recorder(self, config: RecorderConfig) -> AsyncAgentRecorder:
        """Create a recorder instance."""
        ...

    @abstractmethod
    def get_supported_models(self) -> list[str]:
        """Get list of supported model names."""
        ...

    @abstractmethod
    def get_agent_type(self) -> str:
        """Get the agent type identifier."""
        ...
