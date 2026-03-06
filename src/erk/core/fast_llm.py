"""Fast LLM calls via Anthropic SDK.

For lightweight operations (slug generation) where spawning a full
Claude CLI subprocess is too slow. Falls back to Claude CLI when
ANTHROPIC_API_KEY is unavailable.
"""

import logging
import os
import shutil
import subprocess

from anthropic import Anthropic, APIError
from anthropic.types import TextBlock

from erk_shared.core.llm_caller import LlmCaller, LlmCallFailed, LlmResponse, NoApiKey
from erk_shared.subprocess_utils import build_claude_subprocess_env

logger = logging.getLogger(__name__)


def _call_claude_cli(prompt: str, *, system_prompt: str) -> LlmResponse | NoApiKey | LlmCallFailed:
    """Fall back to Claude CLI when ANTHROPIC_API_KEY is unavailable."""
    if shutil.which("claude") is None:
        return NoApiKey(message="ANTHROPIC_API_KEY not set and claude CLI not available")

    logger.debug("Falling back to Claude CLI for LLM call")
    cmd = [
        "claude",
        "--print",
        "--no-session-persistence",
        "--model",
        "claude-haiku-4-5-20251001",
        "--output-format",
        "text",
        "--system-prompt",
        system_prompt,
        prompt,
    ]
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        env=build_claude_subprocess_env(),
    )
    if result.returncode != 0:
        return LlmCallFailed(message=f"Claude CLI failed: {result.stderr.strip()}")
    return LlmResponse(text=result.stdout.strip())


class AnthropicLlmCaller(LlmCaller):
    def call(
        self, prompt: str, *, system_prompt: str, max_tokens: int
    ) -> LlmResponse | NoApiKey | LlmCallFailed:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key is None:
            logger.warning("ANTHROPIC_API_KEY environment variable not set")
            return _call_claude_cli(prompt, system_prompt=system_prompt)
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
