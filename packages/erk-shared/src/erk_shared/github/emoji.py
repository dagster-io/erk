"""GitHub PR and checks status emojis.

This module provides emoji constants and formatting functions for displaying
GitHub PR states, checks status, and merge conflicts in CLI output.
"""

from erk_shared.github.types import PullRequestInfo

# PR state emojis (aligned with erk-statusline conventions)
PR_STATE_EMOJIS = {
    "OPEN": "👀",  # published/open PR
    "DRAFT": "🚧",  # draft PR
    "MERGED": "🎉",  # merged PR
    "CLOSED": "⛔",  # closed PR
}

# Additional status indicators
CONFLICTS_EMOJI = "💥"  # merge conflicts
CHECKS_PENDING_EMOJI = "🔄"  # checks pending or no checks
CHECKS_PASSING_EMOJI = "✅"  # all checks passing
CHECKS_FAILING_EMOJI = "🚫"  # any checks failing


def get_pr_status_emoji(pr: PullRequestInfo) -> str:
    """Get emoji representation of PR status (state + conflicts).

    Returns a combination of state emoji (👀/🚧/🎉/⛔) and optionally
    a conflicts indicator (💥) for open/draft PRs with merge conflicts.

    Args:
        pr: PR information

    Returns:
        Emoji string representing PR status (e.g., "👀" or "👀💥")
    """
    # Draft PRs have state="OPEN" but is_draft=True, so check is_draft first
    if pr.is_draft:
        emoji = PR_STATE_EMOJIS["DRAFT"]
    else:
        emoji = PR_STATE_EMOJIS.get(pr.state, "")

    # Add conflicts indicator for open/draft PRs (draft PRs also have state="OPEN")
    if pr.state == "OPEN" and pr.has_conflicts:
        emoji += CONFLICTS_EMOJI

    return emoji


def get_checks_status_emoji(pr: PullRequestInfo | None) -> str:
    """Get emoji representation of checks status.

    Returns:
        - "-" if no PR provided
        - "🔄" if checks are pending or no checks configured
        - "✅" if all checks are passing
        - "🚫" if any checks are failing

    Args:
        pr: PR information, or None if no PR

    Returns:
        Emoji string representing checks status
    """
    if pr is None:
        return "-"

    if pr.checks_passing is None:
        return CHECKS_PENDING_EMOJI  # Pending or no checks
    if pr.checks_passing:
        return CHECKS_PASSING_EMOJI  # All pass
    return CHECKS_FAILING_EMOJI  # Any failing


def get_issue_state_emoji(state: str) -> str:
    """Get emoji for issue state.

    Args:
        state: Issue state ("OPEN" or "CLOSED")

    Returns:
        🟢 for OPEN, 🔴 for CLOSED
    """
    return "🟢" if state == "OPEN" else "🔴"


def format_checks_cell(pr: PullRequestInfo | None) -> str:
    """Format checks status with emoji and counts.

    Returns:
        - "-" if no PR provided
        - "🔄" if checks are pending or no checks configured
        - "✅ 3/3" if all checks passing (with counts)
        - "🚫 2/5" if any checks failing (with counts)

    Args:
        pr: PR information, or None if no PR

    Returns:
        Formatted string with emoji and optional counts
    """
    if pr is None:
        return "-"

    if pr.checks_passing is None:
        return CHECKS_PENDING_EMOJI  # Pending or no checks

    # Determine emoji
    emoji = CHECKS_PASSING_EMOJI if pr.checks_passing else CHECKS_FAILING_EMOJI

    # Add counts if available
    if pr.checks_counts is not None:
        passing, total = pr.checks_counts
        return f"{emoji} {passing}/{total}"

    return emoji
