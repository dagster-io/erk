"""Shared formatting functions for CI check run display."""

from erk_shared.gateway.github.ci_summary_parsing import match_summary_to_check
from erk_shared.gateway.github.types import PRCheckRun


def format_check_line(check: PRCheckRun) -> str:
    """Format a single check run as a markdown list item.

    Args:
        check: The check run to format

    Returns:
        Markdown list item string
    """
    conclusion_str = check.conclusion or "in progress"
    if check.detail_url is not None:
        return f"- **{check.name}** — {conclusion_str} ([details]({check.detail_url}))"
    return f"- **{check.name}** — {conclusion_str}"


def format_summary_blockquote(
    check_name: str,
    *,
    summaries: dict[str, str],
    summary_keys: set[str],
) -> list[str]:
    """Render a check's summary as blockquote lines.

    Args:
        check_name: The check run name (may have "ci / " prefix)
        summaries: Mapping of check name to summary text
        summary_keys: Pre-computed set of summary keys for matching

    Returns:
        List of blockquote lines, or empty list if no match
    """
    matched_key = match_summary_to_check(check_name, summary_keys)
    if matched_key is None:
        return []
    return [f"  > {line}" for line in summaries[matched_key].splitlines()]


def format_check_runs(
    check_runs: list[PRCheckRun],
    *,
    summaries: dict[str, str] | None,
) -> str:
    """Format failing check runs as markdown for display.

    When summaries are available, renders each as a blockquote under the
    check name for quick triage.

    Args:
        check_runs: List of failing PRCheckRun objects
        summaries: Optional mapping of check name to summary text

    Returns:
        Markdown-formatted string with check run details
    """
    if not check_runs:
        return "*No failing checks*"

    summary_keys = set(summaries.keys()) if summaries else set()

    parts: list[str] = []
    for check in check_runs:
        parts.append(format_check_line(check))
        if summaries and summary_keys:
            parts.extend(
                format_summary_blockquote(
                    check.name,
                    summaries=summaries,
                    summary_keys=summary_keys,
                )
            )

    return "\n".join(parts)
