"""Tests for backend validation in RealAgentLauncher."""

import dataclasses

import pytest

from erk_shared.context.types import InteractiveAgentConfig
from erk_shared.gateway.agent_launcher.real import RealAgentLauncher


def test_launch_rejects_non_claude_backend() -> None:
    """RealAgentLauncher raises RuntimeError for unsupported backends."""
    config = dataclasses.replace(InteractiveAgentConfig.default(), backend="codex")
    launcher = RealAgentLauncher()

    with pytest.raises(RuntimeError, match="Unsupported agent backend"):
        launcher.launch_interactive(config, command="")
