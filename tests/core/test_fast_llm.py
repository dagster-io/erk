"""Tests for fast_llm module."""

from dataclasses import dataclass

import pytest

from erk.core.fast_llm import execute_haiku_call, fast_haiku_call


@dataclass(frozen=True)
class FakeTextBlock:
    text: str


@dataclass(frozen=True)
class FakeMessage:
    content: tuple[FakeTextBlock, ...]


@dataclass(frozen=True)
class FakeMessages:
    response_text: str

    def create(self, **kwargs: object) -> FakeMessage:
        return FakeMessage(content=(FakeTextBlock(text=self.response_text),))


@dataclass(frozen=True)
class FakeAnthropicClient:
    response_text: str

    @property
    def messages(self) -> FakeMessages:
        return FakeMessages(response_text=self.response_text)


class CapturingMessages:
    """Messages endpoint that captures call kwargs."""

    def __init__(self) -> None:
        self.captured_kwargs: dict[str, object] = {}

    def create(self, **kwargs: object) -> FakeMessage:
        self.captured_kwargs = kwargs
        return FakeMessage(content=(FakeTextBlock(text="result"),))


class CapturingClient:
    """Client that captures call kwargs for assertion."""

    def __init__(self) -> None:
        self._messages = CapturingMessages()

    @property
    def messages(self) -> CapturingMessages:
        return self._messages


class ErrorMessages:
    """Messages endpoint that raises on create."""

    def create(self, **kwargs: object) -> FakeMessage:
        raise RuntimeError("API error")


class ErrorClient:
    """Client whose messages.create always raises."""

    @property
    def messages(self) -> ErrorMessages:
        return ErrorMessages()


def test_fast_haiku_call_returns_none_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns None when ANTHROPIC_API_KEY is not set."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = fast_haiku_call("test", system_prompt="system")
    assert result is None


def test_execute_haiku_call_returns_stripped_text() -> None:
    """Strips whitespace from response text."""
    client = FakeAnthropicClient(response_text="  hello-world  ")
    result = execute_haiku_call(client, "test", system_prompt="system")  # type: ignore[arg-type]
    assert result == "hello-world"


def test_execute_haiku_call_passes_correct_params() -> None:
    """Passes model, system prompt, and messages to the SDK."""
    client = CapturingClient()
    execute_haiku_call(client, "my prompt", system_prompt="my system")  # type: ignore[arg-type]

    kwargs = client.messages.captured_kwargs
    assert kwargs["model"] == "claude-haiku-4-5-20251001"
    assert kwargs["max_tokens"] == 50
    assert kwargs["system"] == "my system"
    assert kwargs["messages"] == [{"role": "user", "content": "my prompt"}]


def test_execute_haiku_call_raises_on_api_error() -> None:
    """Propagates exception from client, which fast_haiku_call catches."""
    client = ErrorClient()
    with pytest.raises(RuntimeError, match="API error"):
        execute_haiku_call(client, "test", system_prompt="system")  # type: ignore[arg-type]
