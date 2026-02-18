"""Pure sorting logic for TUI dashboard."""

from datetime import datetime

from erk.tui.data.types import PlanRowData
from erk.tui.sorting.types import BranchActivity, SortKey


def sort_plans(
    plans: list[PlanRowData],
    sort_key: SortKey,
    activity_by_plan: dict[int, BranchActivity] | None = None,
) -> list[PlanRowData]:
    """Sort plans by the given key.

    Args:
        plans: List of plans to sort
        sort_key: Which field to sort by
        activity_by_plan: Mapping of plan ID to branch activity data.
            Required when sort_key is BRANCH_ACTIVITY.

    Returns:
        Sorted list of plans. Original list is not modified.
    """
    if sort_key == SortKey.PLAN_ID:
        # Sort by plan ID descending (newest first)
        return sorted(plans, key=lambda p: p.plan_id, reverse=True)

    if sort_key == SortKey.BRANCH_ACTIVITY:
        # Sort by most recent commit on branch
        # Plans with recent activity first, no activity at end
        activity_map = activity_by_plan or {}

        def get_activity_key(plan: PlanRowData) -> tuple[bool, datetime]:
            """Return sort key tuple: (has_activity, timestamp).

            Returns tuple where:
            - has_activity: True if there's branch activity (so it sorts first)
            - timestamp: The activity timestamp (or min datetime for no activity)
            """
            activity = activity_map.get(plan.plan_id)
            if activity is None or activity.last_commit_at is None:
                # No activity - sort to end with very old date
                return (False, datetime.min)
            return (True, activity.last_commit_at)

        # Sort: has_activity=True first, then by timestamp descending (newest first)
        return sorted(
            plans,
            key=get_activity_key,
            reverse=True,
        )

    # Default fallback: return as-is
    return list(plans)
