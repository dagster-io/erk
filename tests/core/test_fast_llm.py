"""Tests for fast_llm module."""

from dataclasses import dataclass

import pytest

from erk.core.fast_llm import (
    AnthropicLlmCaller,
    LlmCaller,
    LlmCallFailed,
    LlmResponse,
    NoApiKey,
)


@dataclass(frozen=True)
class FakeLlmCaller(LlmCaller):
    response: LlmResponse | NoApiKey | LlmCallFailed

    def call(self, prompt: str, *, system_prompt: str) -> LlmResponse | NoApiKey | LlmCallFailed:
        return self.response


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


def test_anthropic_llm_caller_returns_no_api_key_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns NoApiKey when ANTHROPIC_API_KEY is not set."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = AnthropicLlmCaller().call("test", system_prompt="system")
    assert isinstance(result, NoApiKey)
