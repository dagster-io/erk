"""Utilities for PR submission.

Utility functions used by the submit pipeline for PR body validation
and divergence error construction.
"""

import re


def has_body_footer(body: str) -> bool:
    """Check if PR body already contains a footer section.

    Checks for 'erk pr teleport' or 'erk pr checkout' markers
    that are included in the standard PR footer.

    Args:
        body: The PR body text to check

    Returns:
        True if the body already contains a footer section
    """
    return "erk pr teleport" in body or "erk pr checkout" in body


def has_checkout_footer_for_pr(body: str, pr_number: int) -> bool:
    """Check if PR body contains teleport/checkout footer for a specific PR number.

    Accepts both 'erk pr teleport' and 'erk pr checkout' formats.

    Args:
        body: The PR body text to check
        pr_number: The PR number to validate against

    Returns:
        True if the body contains 'erk pr teleport <pr_number>'
            or 'erk pr checkout <pr_number>'
    """
    return bool(re.search(rf"erk pr (teleport|checkout) {pr_number}\b", body))
