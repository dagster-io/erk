"""Tests for fast_llm module."""

import pytest

from erk.core.fast_llm import AnthropicLlmCaller
from erk_shared.core.fakes import FakeLlmCaller, FakePromptExecutor
from erk_shared.core.llm_caller import LlmCallFailed, LlmResponse, NoApiKey
from erk_shared.core.prompt_executor import PromptResult


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


def test_anthropic_llm_caller_returns_no_api_key_when_no_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns NoApiKey when ANTHROPIC_API_KEY is not set and no executor provided."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = AnthropicLlmCaller().call("test", system_prompt="system", max_tokens=50)
    assert isinstance(result, NoApiKey)


def test_anthropic_llm_caller_returns_no_api_key_when_cli_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns NoApiKey when ANTHROPIC_API_KEY is not set and CLI is unavailable."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    executor = FakePromptExecutor(is_available=False)
    caller = AnthropicLlmCaller(prompt_executor=executor)
    result = caller.call("test", system_prompt="system", max_tokens=50)
    assert isinstance(result, NoApiKey)


def test_anthropic_llm_caller_falls_back_to_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falls back to Claude CLI when ANTHROPIC_API_KEY is not set but CLI is available."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    executor = FakePromptExecutor(
        prompt_results=[PromptResult(success=True, output="my-slug", error=None)]
    )
    caller = AnthropicLlmCaller(prompt_executor=executor)
    result = caller.call("test prompt", system_prompt="system prompt", max_tokens=50)
    assert isinstance(result, LlmResponse)
    assert result.text == "my-slug"
    assert len(executor.prompt_calls) == 1
    assert executor.prompt_calls[0].prompt == "test prompt"
    assert executor.prompt_calls[0].system_prompt == "system prompt"


def test_anthropic_llm_caller_cli_fallback_returns_failed_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns LlmCallFailed when Claude CLI fallback fails."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    executor = FakePromptExecutor(
        prompt_results=[PromptResult(success=False, output="", error="some error")]
    )
    caller = AnthropicLlmCaller(prompt_executor=executor)
    result = caller.call("test", system_prompt="system", max_tokens=50)
    assert isinstance(result, LlmCallFailed)
    assert "some error" in result.message
