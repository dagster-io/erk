"""Fast LLM calls via Anthropic SDK.

For lightweight operations (slug generation) where spawning a full
Claude CLI subprocess is too slow.
"""

import logging
import os

from anthropic import Anthropic, APIError

from erk_shared.core.llm_caller import LlmCaller, LlmCallFailed, LlmResponse, NoApiKey

logger = logging.getLogger(__name__)


class AnthropicLlmCaller(LlmCaller):
    def call(self, prompt: str, *, system_prompt: str) -> LlmResponse | NoApiKey | LlmCallFailed:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key is None:
            logger.warning("ANTHROPIC_API_KEY environment variable not set")
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
        except APIError as exc:
            logger.warning("LLM call failed: %s", exc)
            return LlmCallFailed(message=str(exc))
