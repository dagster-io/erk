"""Tests for FallbackPromptExecutor."""

from __future__ import annotations

from pathlib import Path

from erk.core.fallback_prompt_executor import FallbackPromptExecutor
from tests.fakes.prompt_executor import FakePromptExecutor


def _make_executor(
    *,
    api_available: bool = True,
    cli_available: bool = True,
) -> tuple[FallbackPromptExecutor, FakePromptExecutor, FakePromptExecutor]:
    api = FakePromptExecutor(available=api_available)
    cli = FakePromptExecutor(available=cli_available)
    fallback = FallbackPromptExecutor(api_executor=api, cli_executor=cli)
    return fallback, api, cli


def test_is_available_when_api_available() -> None:
    """is_available returns True when api_executor is available."""
    fallback, _, _ = _make_executor(api_available=True, cli_available=False)
    assert fallback.is_available() is True


def test_is_available_when_cli_available() -> None:
    """is_available returns True when cli_executor is available."""
    fallback, _, _ = _make_executor(api_available=False, cli_available=True)
    assert fallback.is_available() is True


def test_is_available_when_neither() -> None:
    """is_available returns False when neither executor is available."""
    fallback, _, _ = _make_executor(api_available=False, cli_available=False)
    assert fallback.is_available() is False


def test_execute_prompt_uses_api_when_available() -> None:
    """execute_prompt calls api_executor when it is available."""
    fallback, api, cli = _make_executor(api_available=True, cli_available=True)
    fallback.execute_prompt(
        "hello",
        model="claude-haiku-4-5-20251001",
        tools=None,
        cwd=None,
        system_prompt=None,
        dangerous=False,
    )
    assert len(api.prompt_calls) == 1
    assert len(cli.prompt_calls) == 0


def test_execute_prompt_falls_back_to_cli() -> None:
    """execute_prompt calls cli_executor when api_executor is unavailable."""
    fallback, api, cli = _make_executor(api_available=False, cli_available=True)
    fallback.execute_prompt(
        "hello",
        model="claude-haiku-4-5-20251001",
        tools=None,
        cwd=None,
        system_prompt=None,
        dangerous=False,
    )
    assert len(api.prompt_calls) == 0
    assert len(cli.prompt_calls) == 1


def test_streaming_delegates_to_cli() -> None:
    """execute_command_streaming always delegates to cli_executor."""
    fallback, api, cli = _make_executor(api_available=True, cli_available=True)
    list(
        fallback.execute_command_streaming(
            command="/test",
            worktree_path=Path("/tmp"),
            dangerous=False,
            permission_mode="safe",
        )
    )
    assert len(cli.executed_commands) == 1
    assert len(api.executed_commands) == 0


def test_interactive_delegates_to_cli() -> None:
    """execute_interactive always delegates to cli_executor."""
    fallback, api, cli = _make_executor(api_available=True, cli_available=True)
    fallback.execute_interactive(
        worktree_path=Path("/tmp"),
        dangerous=False,
        command="/test",
        target_subpath=None,
        permission_mode="safe",
    )
    assert len(cli.interactive_calls) == 1
    assert len(api.interactive_calls) == 0


def test_passthrough_delegates_to_cli() -> None:
    """execute_prompt_passthrough always delegates to cli_executor."""
    fallback, api, cli = _make_executor(api_available=True, cli_available=True)
    fallback.execute_prompt_passthrough(
        "hello",
        model="claude-haiku-4-5-20251001",
        tools=None,
        cwd=Path("/tmp"),
        dangerous=False,
    )
    assert len(cli.passthrough_calls) == 1
    assert len(api.passthrough_calls) == 0


def test_prompt_label_returns_api_label_when_available() -> None:
    """prompt_label returns api_executor's label when API is available."""
    fallback, api, cli = _make_executor(api_available=True, cli_available=True)
    assert fallback.prompt_label == api.prompt_label


def test_prompt_label_returns_cli_label_when_api_unavailable() -> None:
    """prompt_label returns cli_executor's label when API is unavailable."""
    fallback, api, cli = _make_executor(api_available=False, cli_available=True)
    assert fallback.prompt_label == cli.prompt_label
