"""Utility functions for PR handling."""

from erk_shared.gateway.github.types import PullRequestInfo


def select_display_pr(
    prs: list[PullRequestInfo],
    *,
    exclude_pr_numbers: set[int] | None,
) -> PullRequestInfo | None:
    """Select PR to display: prefer open, then merged, then closed.

    Excludes PRs matching exclude_pr_numbers (e.g., plan review PRs) so
    the implementation PR is preferred.  Falls back to unfiltered selection
    if excluding leaves no candidates.

    Args:
        prs: List of PRs sorted by created_at descending (most recent first)
        exclude_pr_numbers: PR numbers to exclude from selection (e.g., review PRs)

    Returns:
        PR to display, or None if no PRs
    """
    candidates = prs
    if exclude_pr_numbers is not None:
        filtered = [pr for pr in prs if pr.number not in exclude_pr_numbers]
        if filtered:
            candidates = filtered

    # Check for open PRs (published or draft)
    open_prs = [pr for pr in candidates if pr.state in ("OPEN", "DRAFT")]
    if open_prs:
        return open_prs[0]  # Most recent open

    # Fallback to merged PRs
    merged_prs = [pr for pr in candidates if pr.state == "MERGED"]
    if merged_prs:
        return merged_prs[0]  # Most recent merged

    # Fallback to closed PRs
    closed_prs = [pr for pr in candidates if pr.state == "CLOSED"]
    if closed_prs:
        return closed_prs[0]  # Most recent closed

    return None
