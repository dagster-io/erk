"""Fast LLM calls via Anthropic SDK.

For lightweight operations (slug generation) where spawning a full
Claude CLI subprocess is too slow.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from anthropic import Anthropic


@dataclass(frozen=True)
class LlmResponse:
    text: str


@dataclass(frozen=True)
class NoApiKey:
    message: str

    @property
    def error_type(self) -> str:
        return "no-api-key"


@dataclass(frozen=True)
class LlmCallFailed:
    message: str

    @property
    def error_type(self) -> str:
        return "llm-call-failed"


class LlmCaller(ABC):
    @abstractmethod
    def call(self, prompt: str, *, system_prompt: str) -> LlmResponse | NoApiKey | LlmCallFailed:
        """Execute an LLM call."""
        ...


class AnthropicLlmCaller(LlmCaller):
    def call(self, prompt: str, *, system_prompt: str) -> LlmResponse | NoApiKey | LlmCallFailed:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key is None:
            return NoApiKey(message="ANTHROPIC_API_KEY environment variable not set")
        try:
            client = Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=50,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            return LlmResponse(text=response.content[0].text.strip())
        except Exception as exc:
            return LlmCallFailed(message=str(exc))
