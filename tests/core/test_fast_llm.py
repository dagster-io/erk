"""Tests for fast_llm module."""

from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from erk.core.fast_llm import AnthropicLlmCaller
from erk_shared.core.fakes import FakeLlmCaller
from erk_shared.core.llm_caller import LlmCallFailed, LlmResponse, NoApiKey


def test_fake_returns_configured_response() -> None:
    """FakeLlmCaller returns configured LlmResponse."""
    caller = FakeLlmCaller(response=LlmResponse(text="my-slug"))
    result = caller.call("generate slug", system_prompt="system", max_tokens=50)
    assert isinstance(result, LlmResponse)
    assert result.text == "my-slug"


def test_fake_returns_no_api_key() -> None:
    """FakeLlmCaller returns NoApiKey when configured."""
    caller = FakeLlmCaller(response=NoApiKey(message="no key"))
    result = caller.call("generate slug", system_prompt="system", max_tokens=50)
    assert isinstance(result, NoApiKey)
    assert result.message == "no key"
    assert result.error_type == "no-api-key"


def test_fake_returns_llm_call_failed() -> None:
    """FakeLlmCaller returns LlmCallFailed when configured."""
    caller = FakeLlmCaller(response=LlmCallFailed(message="timeout"))
    result = caller.call("generate slug", system_prompt="system", max_tokens=50)
    assert isinstance(result, LlmCallFailed)
    assert result.message == "timeout"
    assert result.error_type == "llm-call-failed"


def test_anthropic_llm_caller_returns_no_api_key_when_no_key_and_no_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns NoApiKey when ANTHROPIC_API_KEY is not set and claude CLI is unavailable."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("erk.core.fast_llm.shutil.which", return_value=None):
        result = AnthropicLlmCaller().call("test", system_prompt="system", max_tokens=50)
    assert isinstance(result, NoApiKey)


def test_anthropic_llm_caller_falls_back_to_claude_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falls back to Claude CLI when ANTHROPIC_API_KEY is not set but CLI is available."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fake_result = CompletedProcess(args=[], returncode=0, stdout="my-slug\n", stderr="")
    with (
        patch("erk.core.fast_llm.shutil.which", return_value="/usr/bin/claude"),
        patch("erk.core.fast_llm.subprocess.run", return_value=fake_result) as mock_run,
    ):
        result = AnthropicLlmCaller().call(
            "test prompt", system_prompt="system prompt", max_tokens=50
        )
    assert isinstance(result, LlmResponse)
    assert result.text == "my-slug"
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "claude"
    assert "--print" in cmd
    assert "--no-session-persistence" in cmd
    assert "test prompt" in cmd


def test_anthropic_llm_caller_cli_fallback_returns_failed_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns LlmCallFailed when Claude CLI fallback fails."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fake_result = CompletedProcess(args=[], returncode=1, stdout="", stderr="some error\n")
    with (
        patch("erk.core.fast_llm.shutil.which", return_value="/usr/bin/claude"),
        patch("erk.core.fast_llm.subprocess.run", return_value=fake_result),
    ):
        result = AnthropicLlmCaller().call("test", system_prompt="system", max_tokens=50)
    assert isinstance(result, LlmCallFailed)
    assert "some error" in result.message
