"""JSON extraction from LLM text output.

LLMs sometimes wrap their JSON in markdown fences or add trailing commentary.
This module provides robust extraction using json.JSONDecoder.raw_decode()
which parses the first valid JSON object from arbitrary surrounding text.
"""

from __future__ import annotations

import json


def extract_json_dict(text: str) -> dict | None:
    """Extract the first JSON dict from LLM text output.

    Uses json.JSONDecoder.raw_decode() to parse the first JSON object,
    ignoring markdown fences, preamble text, and trailing commentary.

    Returns None for empty text, no '{' found, parse errors, or non-dict results.

    This is an error boundary: json parsing can fail on malformed LLM output,
    so catching ValueError here is appropriate (third-party API compatibility).
    """
    if not text:
        return None

    brace_pos = text.find("{")
    if brace_pos == -1:
        return None

    decoder = json.JSONDecoder()
    try:
        parsed, _end = decoder.raw_decode(text, brace_pos)
    except (ValueError, TypeError):
        return None

    if not isinstance(parsed, dict):
        return None

    return parsed
