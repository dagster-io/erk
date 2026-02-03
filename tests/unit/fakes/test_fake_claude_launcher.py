"""Tests for FakeClaudeLauncher implementation."""

import pytest

from erk_shared.context.types import InteractiveClaudeConfig
from erk_shared.gateway.claude_launcher.fake import ClaudeLaunchCall, FakeClaudeLauncher


class TestFakeClaudeLauncherLaunchInteractive:
    """Tests for FakeClaudeLauncher launch_interactive tracking functionality."""

    def test_launch_tracks_calls(self) -> None:
        """launch_interactive() calls are tracked in launch_calls property."""
        launcher = FakeClaudeLauncher()
        config1 = InteractiveClaudeConfig.default()
        config2 = InteractiveClaudeConfig(
            model="claude-opus-4-5",
            verbose=False,
            permission_mode="plan",
            dangerous=False,
            allow_dangerous=True,
        )

        with pytest.raises(SystemExit):
            launcher.launch_interactive(config1, command="/erk:plan-implement")

        with pytest.raises(SystemExit):
            launcher.launch_interactive(config2, command="/erk:replan 123")

        assert len(launcher.launch_calls) == 2
        assert launcher.launch_calls[0] == ClaudeLaunchCall(
            config=config1, command="/erk:plan-implement"
        )
        assert launcher.launch_calls[1] == ClaudeLaunchCall(
            config=config2, command="/erk:replan 123"
        )

    def test_last_call_returns_most_recent(self) -> None:
        """last_call returns most recent launch call."""
        launcher = FakeClaudeLauncher()
        config1 = InteractiveClaudeConfig.default()
        config2 = InteractiveClaudeConfig.default()

        with pytest.raises(SystemExit):
            launcher.launch_interactive(config1, command="first")

        with pytest.raises(SystemExit):
            launcher.launch_interactive(config2, command="second")

        assert launcher.last_call == ClaudeLaunchCall(config=config2, command="second")

    def test_last_call_returns_none_when_empty(self) -> None:
        """last_call returns None when no launch calls made."""
        launcher = FakeClaudeLauncher()

        assert launcher.last_call is None

    def test_launch_calls_empty_initially(self) -> None:
        """launch_calls is empty list initially."""
        launcher = FakeClaudeLauncher()

        assert launcher.launch_calls == []

    def test_launch_sets_launch_called_flag(self) -> None:
        """launch_interactive() sets launch_called flag."""
        launcher = FakeClaudeLauncher()
        config = InteractiveClaudeConfig.default()

        with pytest.raises(SystemExit):
            launcher.launch_interactive(config, command="test")

        assert launcher.launch_called is True

    def test_launch_raises_system_exit(self) -> None:
        """launch_interactive() raises SystemExit to simulate process replacement."""
        launcher = FakeClaudeLauncher()
        config = InteractiveClaudeConfig.default()

        with pytest.raises(SystemExit) as exc_info:
            launcher.launch_interactive(config, command="test")

        assert exc_info.value.code == 0

    def test_launch_called_initially_false(self) -> None:
        """launch_called is False initially."""
        launcher = FakeClaudeLauncher()

        assert launcher.launch_called is False


class TestFakeClaudeLauncherLaunchError:
    """Tests for FakeClaudeLauncher launch_error configuration."""

    def test_launch_error_raises_runtime_error(self) -> None:
        """launch_interactive() raises RuntimeError when launch_error is set."""
        launcher = FakeClaudeLauncher(launch_error="Claude CLI not found")
        config = InteractiveClaudeConfig.default()

        with pytest.raises(RuntimeError, match="Claude CLI not found"):
            launcher.launch_interactive(config, command="test")

    def test_launch_error_does_not_track_call(self) -> None:
        """launch_interactive() does not track the call when launch_error is set."""
        launcher = FakeClaudeLauncher(launch_error="test error")
        config = InteractiveClaudeConfig.default()

        with pytest.raises(RuntimeError):
            launcher.launch_interactive(config, command="test")

        assert launcher.launch_called is False
        assert launcher.launch_calls == []


class TestFakeClaudeLauncherDefensiveCopying:
    """Tests for FakeClaudeLauncher defensive copying behavior."""

    def test_launch_calls_returns_copy_of_list(self) -> None:
        """launch_calls returns a copy to prevent external mutation."""
        launcher = FakeClaudeLauncher()
        config = InteractiveClaudeConfig.default()

        with pytest.raises(SystemExit):
            launcher.launch_interactive(config, command="test")

        # Modify the returned list
        returned_list = launcher.launch_calls
        returned_list.append(ClaudeLaunchCall(config=config, command="mutated"))

        # Original should be unchanged
        assert len(launcher.launch_calls) == 1
        assert launcher.launch_calls[0].command == "test"


class TestClaudeLaunchCall:
    """Tests for ClaudeLaunchCall frozen dataclass."""

    def test_frozen_dataclass_immutable(self) -> None:
        """ClaudeLaunchCall is immutable."""
        config = InteractiveClaudeConfig.default()
        call = ClaudeLaunchCall(config=config, command="test")

        with pytest.raises(AttributeError):
            call.command = "modified"  # type: ignore

    def test_equality_based_on_values(self) -> None:
        """Two ClaudeLaunchCall instances with same values are equal."""
        config = InteractiveClaudeConfig.default()
        call1 = ClaudeLaunchCall(config=config, command="test")
        call2 = ClaudeLaunchCall(config=config, command="test")

        assert call1 == call2

    def test_config_field_stores_config(self) -> None:
        """config field stores the InteractiveClaudeConfig."""
        config = InteractiveClaudeConfig(
            model="claude-opus-4-5",
            verbose=True,
            permission_mode="plan",
            dangerous=False,
            allow_dangerous=True,
        )
        call = ClaudeLaunchCall(config=config, command="test")

        assert call.config == config
        assert call.config.model == "claude-opus-4-5"
        assert call.config.permission_mode == "plan"
        assert call.config.allow_dangerous is True

    def test_command_field_stores_command(self) -> None:
        """command field stores the slash command string."""
        config = InteractiveClaudeConfig.default()
        call = ClaudeLaunchCall(config=config, command="/erk:plan-implement 123")

        assert call.command == "/erk:plan-implement 123"
