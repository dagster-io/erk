"""Parse CI failure summaries from workflow job logs.

Summaries are wrapped in well-known markers:

    === ERK-CI-SUMMARY:check-name ===
    {2-5 bullet point summary}
    === /ERK-CI-SUMMARY:check-name ===

The ci-summarize CI job generates these markers. Tools parse them
to display concise failure explanations alongside check run details.
"""

import re

_SUMMARY_PATTERN = re.compile(
    r"=== ERK-CI-SUMMARY:(.+?) ===\n(.*?)=== /ERK-CI-SUMMARY:\1 ===",
    re.DOTALL,
)


def parse_ci_summaries(log_text: str) -> dict[str, str]:
    """Extract CI failure summaries from log text.

    Parses the well-known marker format and returns a mapping
    of check name to summary text.

    Args:
        log_text: Raw log text from the ci-summarize job

    Returns:
        Mapping of check name to summary text (stripped of leading/trailing whitespace)
    """
    results: dict[str, str] = {}
    for match in _SUMMARY_PATTERN.finditer(log_text):
        check_name = match.group(1).strip()
        summary = match.group(2).strip()
        if check_name:
            results[check_name] = summary
    return results


def match_summary_to_check(check_name: str, summary_keys: set[str]) -> str | None:
    """Match a check run name to a summary key.

    GitHub prepends "ci / " to job names in statusCheckRollup
    (e.g., "ci / unit-tests (3.12)"). This function handles that prefix
    and tries exact match first, then stripped match.

    Args:
        check_name: The check run name from GitHub (may have "ci / " prefix)
        summary_keys: Set of summary keys from parse_ci_summaries()

    Returns:
        The matching summary key, or None if no match found
    """
    # Exact match
    if check_name in summary_keys:
        return check_name

    # Strip "ci / " prefix that GitHub adds
    stripped = check_name
    if " / " in check_name:
        stripped = check_name.split(" / ", 1)[1]

    if stripped in summary_keys:
        return stripped

    return None
