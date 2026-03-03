"""Tests for fast_llm module."""

import pytest

from erk.core.fast_llm import AnthropicLlmCaller
from erk_shared.core.fakes import FakeLlmCaller
from erk_shared.core.llm_caller import LlmCallFailed, LlmResponse, NoApiKey


def test_fake_returns_configured_response() -> None:
    """FakeLlmCaller returns configured LlmResponse."""
    caller = FakeLlmCaller(response=LlmResponse(text="my-slug"))
    result = caller.call("generate slug", system_prompt="system")
    assert isinstance(result, LlmResponse)
    assert result.text == "my-slug"


def test_fake_returns_no_api_key() -> None:
    """FakeLlmCaller returns NoApiKey when configured."""
    caller = FakeLlmCaller(response=NoApiKey(message="no key"))
    result = caller.call("generate slug", system_prompt="system")
    assert isinstance(result, NoApiKey)
    assert result.message == "no key"
    assert result.error_type == "no-api-key"


def test_fake_returns_llm_call_failed() -> None:
    """FakeLlmCaller returns LlmCallFailed when configured."""
    caller = FakeLlmCaller(response=LlmCallFailed(message="timeout"))
    result = caller.call("generate slug", system_prompt="system")
    assert isinstance(result, LlmCallFailed)
    assert result.message == "timeout"
    assert result.error_type == "llm-call-failed"


def test_fake_is_configured_default_true() -> None:
    """FakeLlmCaller.is_configured() returns True by default."""
    caller = FakeLlmCaller(response=LlmResponse(text="slug"))
    assert caller.is_configured() is True


def test_fake_is_configured_can_be_false() -> None:
    """FakeLlmCaller.is_configured() returns False when configured=False."""
    caller = FakeLlmCaller(response=LlmResponse(text="slug"), configured=False)
    assert caller.is_configured() is False


def test_fake_accepts_max_tokens_parameter() -> None:
    """FakeLlmCaller accepts max_tokens parameter (ignored)."""
    caller = FakeLlmCaller(response=LlmResponse(text="result"))
    result = caller.call("prompt", system_prompt="system", max_tokens=4096)
    assert isinstance(result, LlmResponse)
    assert result.text == "result"


def test_anthropic_llm_caller_returns_no_api_key_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns NoApiKey when ANTHROPIC_API_KEY is not set."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = AnthropicLlmCaller().call("test", system_prompt="system")
    assert isinstance(result, NoApiKey)


def test_anthropic_llm_caller_is_configured_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AnthropicLlmCaller.is_configured() returns False without API key."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert AnthropicLlmCaller().is_configured() is False


def test_anthropic_llm_caller_is_configured_with_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AnthropicLlmCaller.is_configured() returns True with API key set."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    assert AnthropicLlmCaller().is_configured() is True
