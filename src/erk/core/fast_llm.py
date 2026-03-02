"""Fast LLM calls via Anthropic SDK.

For lightweight operations (slug generation) where spawning a full
Claude CLI subprocess is too slow.
"""

import os

from anthropic import Anthropic


def execute_haiku_call(client: Anthropic, prompt: str, *, system_prompt: str) -> str:
    """Execute a single Haiku call. Raises on failure."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def fast_haiku_call(prompt: str, *, system_prompt: str) -> str | None:
    """Call Haiku directly via Anthropic SDK (~200ms vs ~5s subprocess).

    Returns response text, or None if API key unavailable or call fails.

    Args:
        prompt: The user message to send
        system_prompt: System prompt for the model

    Returns:
        Response text string, or None on any failure
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key is None:
        return None

    try:
        client = Anthropic(api_key=api_key)
        return execute_haiku_call(client, prompt, system_prompt=system_prompt)
    except Exception:
        return None
