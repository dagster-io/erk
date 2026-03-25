"""Tests for AnthropicApiPromptExecutor."""

from __future__ import annotations

from pathlib import Path

import pytest

from erk.core.anthropic_prompt_executor import AnthropicApiPromptExecutor, _resolve_model


def test_is_available_when_api_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns True when ANTHROPIC_API_KEY is set."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    executor = AnthropicApiPromptExecutor()
    assert executor.is_available() is True


def test_is_available_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns False when ANTHROPIC_API_KEY is not set."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    executor = AnthropicApiPromptExecutor()
    assert executor.is_available() is False


def test_execute_prompt_returns_failure_when_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """execute_prompt returns PromptResult with success=False when API key is missing."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    executor = AnthropicApiPromptExecutor()
    result = executor.execute_prompt(
        "test prompt",
        model="claude-haiku-4-5-20251001",
        tools=None,
        cwd=None,
        system_prompt=None,
        dangerous=False,
    )
    assert result.success is False
    assert result.error is not None


def test_execute_command_streaming_raises() -> None:
    """execute_command_streaming raises NotImplementedError."""
    executor = AnthropicApiPromptExecutor()
    with pytest.raises(NotImplementedError):
        list(
            executor.execute_command_streaming(
                command="/test",
                worktree_path=Path("/tmp"),
                dangerous=False,
                permission_mode="safe",
            )
        )


def test_execute_interactive_raises() -> None:
    """execute_interactive raises NotImplementedError."""
    executor = AnthropicApiPromptExecutor()
    with pytest.raises(NotImplementedError):
        executor.execute_interactive(
            worktree_path=Path("/tmp"),
            dangerous=False,
            command="/test",
            target_subpath=None,
            permission_mode="safe",
        )


def test_resolve_model_expands_shorthand() -> None:
    """Shorthand model names are expanded to full model IDs."""
    assert _resolve_model("haiku") == "claude-haiku-4-5-20251001"
    assert _resolve_model("sonnet") == "claude-sonnet-4-6"
    assert _resolve_model("opus") == "claude-opus-4-6"


def test_resolve_model_passes_through_full_id() -> None:
    """Full model IDs are returned unchanged."""
    assert _resolve_model("claude-haiku-4-5-20251001") == "claude-haiku-4-5-20251001"
    assert _resolve_model("claude-sonnet-4-6") == "claude-sonnet-4-6"


def test_execute_prompt_passthrough_raises() -> None:
    """execute_prompt_passthrough raises NotImplementedError."""
    executor = AnthropicApiPromptExecutor()
    with pytest.raises(NotImplementedError):
        executor.execute_prompt_passthrough(
            "test prompt",
            model="claude-haiku-4-5-20251001",
            tools=None,
            cwd=Path("/tmp"),
            dangerous=False,
        )


def test_prompt_label_returns_anthropic_api() -> None:
    """prompt_label property returns 'Anthropic API'."""
    executor = AnthropicApiPromptExecutor()
    assert executor.prompt_label == "Anthropic API"
