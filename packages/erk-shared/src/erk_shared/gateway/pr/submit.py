"""Utilities for PR submission.

Utility functions used by the submit pipeline for PR body validation
and divergence error construction.
"""

import re


def has_body_footer(body: str) -> bool:
    """Check if PR body already contains a footer section.

    Checks for the 'erk pr checkout' marker that is included in the
    standard PR footer.

    Args:
        body: The PR body text to check

    Returns:
        True if the body already contains a footer section
    """
    return "erk pr checkout" in body


def has_checkout_footer_for_pr(body: str, pr_number: int) -> bool:
    """Check if PR body contains checkout footer for a specific PR number.

    Used to validate that a PR's body contains the correct checkout command.
    This is more strict than has_body_footer() as it validates the PR number.

    Args:
        body: The PR body text to check
        pr_number: The PR number to validate against

    Returns:
        True if the body contains 'erk pr checkout <pr_number>'
    """
    return bool(re.search(rf"erk pr checkout {pr_number}\b", body))


def has_issue_closing_reference(body: str, issue_number: int, plans_repo: str | None) -> bool:
    """Check if PR body contains a closing reference for a specific issue.

    Checks for patterns like "Closes #123" (same-repo) or "Closes owner/repo#123"
    (cross-repo) that GitHub recognizes as issue closing keywords.

    Args:
        body: The PR body text to check
        issue_number: The issue number to validate against
        plans_repo: Target repo in "owner/repo" format, or None for same repo

    Returns:
        True if the body contains the expected closing reference
    """
    if plans_repo is None:
        # Same-repo: "Closes #123"
        return bool(re.search(rf"Closes\s+#{issue_number}\b", body, re.IGNORECASE))
    # Cross-repo: "Closes owner/repo#123"
    escaped_repo = re.escape(plans_repo)
    return bool(re.search(rf"Closes\s+{escaped_repo}#{issue_number}\b", body, re.IGNORECASE))
