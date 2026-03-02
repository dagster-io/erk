"""Fast LLM calls via Anthropic SDK.

For lightweight operations (slug generation) where spawning a full
Claude CLI subprocess is too slow.
"""

import os


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
        # Inline: anthropic may not be installed in all environments (e.g. CI)
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception:
        return None
