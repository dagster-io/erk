"""Fast LLM calls via Anthropic SDK.

For lightweight operations (slug generation) where spawning a full
Claude CLI subprocess is too slow. Falls back to Claude CLI via
PromptExecutor when ANTHROPIC_API_KEY is unavailable.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from anthropic import Anthropic, APIError
from anthropic.types import TextBlock

from erk_shared.core.llm_caller import LlmCaller, LlmCallFailed, LlmResponse, NoApiKey

if TYPE_CHECKING:
    from erk_shared.core.prompt_executor import PromptExecutor

logger = logging.getLogger(__name__)


class AnthropicLlmCaller(LlmCaller):
    def __init__(self, *, prompt_executor: PromptExecutor | None = None) -> None:
        self._prompt_executor = prompt_executor

    def call(
        self, prompt: str, *, system_prompt: str, max_tokens: int
    ) -> LlmResponse | NoApiKey | LlmCallFailed:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key is None:
            logger.warning("ANTHROPIC_API_KEY environment variable not set")
            return self._call_via_cli(prompt, system_prompt=system_prompt)
        try:
            client = Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            content_block = response.content[0]
            if not isinstance(content_block, TextBlock):
                return LlmCallFailed(message="Unexpected response type from LLM")
            return LlmResponse(text=content_block.text.strip())
        except APIError as exc:
            logger.warning("LLM call failed: %s", exc)
            return LlmCallFailed(message=str(exc))

    def _call_via_cli(
        self, prompt: str, *, system_prompt: str
    ) -> LlmResponse | NoApiKey | LlmCallFailed:
        """Fall back to Claude CLI via PromptExecutor when ANTHROPIC_API_KEY is unavailable."""
        if self._prompt_executor is None or not self._prompt_executor.is_available():
            return NoApiKey(message="ANTHROPIC_API_KEY not set and claude CLI not available")

        logger.debug("Falling back to Claude CLI for LLM call")
        result = self._prompt_executor.execute_prompt(
            prompt,
            model="claude-haiku-4-5-20251001",
            tools=None,
            cwd=None,
            system_prompt=system_prompt,
            dangerous=False,
        )
        if not result.success:
            return LlmCallFailed(message=f"Claude CLI failed: {result.error}")
        return LlmResponse(text=result.output)
