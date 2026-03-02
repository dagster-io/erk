"""Tests for fast_llm module."""

from dataclasses import dataclass
from unittest.mock import patch

import pytest

from erk.core.fast_llm import LlmCaller, fast_haiku_call


@dataclass(frozen=True)
class FakeLlmCaller(LlmCaller):
    response: str | None

    def call(self, prompt: str, *, system_prompt: str) -> str | None:
        return self.response


def test_fake_returns_configured_response() -> None:
    """FakeLlmCaller returns configured response string."""
    caller = FakeLlmCaller(response="my-slug")
    result = caller.call("generate slug", system_prompt="system")
    assert result == "my-slug"


def test_fake_returns_none_when_configured() -> None:
    """FakeLlmCaller returns None when configured with None."""
    caller = FakeLlmCaller(response=None)
    result = caller.call("generate slug", system_prompt="system")
    assert result is None


def test_fast_haiku_call_returns_none_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns None when ANTHROPIC_API_KEY is not set."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = fast_haiku_call("test", system_prompt="system")
    assert result is None


def test_fast_haiku_call_returns_none_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns None when Anthropic client raises an exception."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with patch("erk.core.fast_llm.Anthropic", side_effect=RuntimeError("boom")):
        result = fast_haiku_call("test", system_prompt="system")
    assert result is None
