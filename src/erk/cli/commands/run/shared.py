"""Shared utilities for run commands."""

import re


def extract_pr_number(display_title: str | None) -> int | None:
    """Extract PR number from display_title containing '#NNN'.

    Handles:
    - "pr-address:#456:abc123" → 456
    - "8559:#460:abc123" → 460
    - "one-shot:#458:abc123" → 458
    - "rebase:#456:abc123" → 456
    - "8559:abc123" (old format, no #) → None
    - "Some title [abc123]" (legacy) → None
    - None or empty → None
    """
    if not display_title:
        return None
    match = re.search(r"#(\d+)", display_title)
    if match is None:
        return None
    return int(match.group(1))


def extract_plan_number(display_title: str | None) -> int | None:
    """Extract plan number from display_title format '123:abc456'.

    Handles:
    - New format: "123:abc456" → 123
    - Old format: "Issue title [abc123]" → None (no colon at start)
    - None or empty → None
    """
    if not display_title or ":" not in display_title:
        return None
    parts = display_title.split(":", 1)
    # Validate that the first part is a number
    first_part = parts[0].strip()
    if not first_part.isdigit():
        return None
    return int(first_part)
