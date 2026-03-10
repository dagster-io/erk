"""Pure filtering logic for TUI dashboard."""

from erk.tui.data.types import PrRowData


def filter_plans(plans: list[PrRowData], query: str) -> list[PrRowData]:
    """Filter plans by query matching full title, plan ID, or PR number.

    Case-insensitive substring matching against:
    - Plan full title
    - Plan ID (as string)
    - PR number (as string, if present)

    Args:
        plans: List of plans to filter
        query: Search query string

    Returns:
        Filtered list of plans matching the query.
        Returns all plans if query is empty.
    """
    if not query:
        return plans

    query_lower = query.lower()
    result: list[PrRowData] = []

    for plan in plans:
        # Check full title (case-insensitive)
        if query_lower in plan.full_title.lower():
            result.append(plan)
            continue

        # Check plan ID
        if query_lower in str(plan.pr_number):
            result.append(plan)
            continue

        # Check PR number if present
        if plan.pr_number is not None and query_lower in str(plan.pr_number):
            result.append(plan)
            continue

        # Check author
        if query_lower in plan.author.lower():
            result.append(plan)

    return result
