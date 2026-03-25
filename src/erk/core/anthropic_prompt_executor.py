"""Anthropic API prompt execution implementation.

This module provides the AnthropicApiPromptExecutor that calls the
Anthropic SDK directly, bypassing the CLI subprocess overhead. Used
for lightweight operations (slug generation, commit messages) where
low latency matters.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from anthropic import Anthropic, APIError
from anthropic.types import TextBlock

from erk_shared.core.prompt_executor import (
    ExecutorEvent,
    PromptExecutor,
    PromptResult,
)

if TYPE_CHECKING:
    from erk_shared.context.types import PermissionMode

logger = logging.getLogger(__name__)

_MODEL_ALIASES: dict[str, str] = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
}


def _resolve_model(model: str) -> str:
    return _MODEL_ALIASES.get(model, model)


class AnthropicApiPromptExecutor(PromptExecutor):
    """PromptExecutor backed by the Anthropic SDK (no CLI subprocess)."""

    @property
    def prompt_label(self) -> str:
        return "Anthropic API"

    def is_available(self) -> bool:
        """Check if ANTHROPIC_API_KEY is set."""
        return os.environ.get("ANTHROPIC_API_KEY") is not None

    def execute_prompt(
        self,
        prompt: str,
        *,
        model: str,
        tools: list[str] | None,
        cwd: Path | None,
        system_prompt: str | None,
        dangerous: bool,
    ) -> PromptResult:
        """Execute a single prompt via the Anthropic SDK.

        Args:
            prompt: The prompt text.
            model: Model name (e.g., "claude-haiku-4-5-20251001").
            tools: Ignored (not applicable to SDK calls).
            cwd: Ignored (not applicable to SDK calls).
            system_prompt: Optional system prompt.
            dangerous: Ignored (not applicable to SDK calls).

        Returns:
            PromptResult with success status and output text.
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key is None:
            return PromptResult(
                success=False,
                output="",
                error="ANTHROPIC_API_KEY not set",
            )

        kwargs: dict[str, Any] = {
            "model": _resolve_model(model),
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt is not None:
            kwargs["system"] = system_prompt

        try:
            client = Anthropic(api_key=api_key)
            response = client.messages.create(**kwargs)
        except APIError as exc:
            logger.warning("Anthropic API call failed: %s", exc)
            return PromptResult(
                success=False,
                output="",
                error=str(exc),
            )

        content_block = response.content[0]
        if not isinstance(content_block, TextBlock):
            return PromptResult(
                success=False,
                output="",
                error="Unexpected response type from Anthropic API",
            )

        return PromptResult(
            success=True,
            output=content_block.text.strip(),
            error=None,
        )

    def execute_command_streaming(
        self,
        *,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
        debug: bool = False,
        model: str | None = None,
        permission_mode: PermissionMode,
        allow_dangerous: bool = False,
    ) -> Iterator[ExecutorEvent]:
        """Not supported for API executor."""
        raise NotImplementedError("AnthropicApiPromptExecutor does not support streaming commands")

    def execute_interactive(
        self,
        *,
        worktree_path: Path,
        dangerous: bool,
        command: str,
        target_subpath: Path | None,
        model: str | None = None,
        permission_mode: PermissionMode,
    ) -> None:
        """Not supported for API executor."""
        raise NotImplementedError("AnthropicApiPromptExecutor does not support interactive mode")

    def execute_prompt_passthrough(
        self,
        prompt: str,
        *,
        model: str,
        tools: list[str] | None,
        cwd: Path,
        dangerous: bool,
    ) -> int:
        """Not supported for API executor."""
        raise NotImplementedError("AnthropicApiPromptExecutor does not support passthrough mode")
