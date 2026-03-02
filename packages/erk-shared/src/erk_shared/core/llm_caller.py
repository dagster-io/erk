"""LLM caller ABC and discriminated union result types.

Defines the interface for lightweight LLM calls (e.g., slug generation)
and the non-ideal state types returned when calls fail.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


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
