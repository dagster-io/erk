"""Fast LLM calls via Anthropic SDK.

For lightweight operations (slug generation) where spawning a full
Claude CLI subprocess is too slow.
"""

import logging
import os

from anthropic import Anthropic, APIError
from anthropic.types import TextBlock

from erk_shared.core.llm_caller import LlmCaller, LlmCallFailed, LlmResponse, NoApiKey

logger = logging.getLogger(__name__)


class AnthropicLlmCaller(LlmCaller):
    def call(
        self, prompt: str, *, system_prompt: str, max_tokens: int
    ) -> LlmResponse | NoApiKey | LlmCallFailed:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key is None:
            logger.warning("ANTHROPIC_API_KEY environment variable not set")
            return NoApiKey(message="ANTHROPIC_API_KEY environment variable not set")
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
