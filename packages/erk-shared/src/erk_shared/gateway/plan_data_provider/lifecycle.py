"""Lifecycle stage display computation for plans.

Extracted to a standalone module to avoid circular imports when testing.
The main consumer is RealPlanDataProvider in real.py.
"""

from erk_shared.gateway.github.metadata.schemas import LIFECYCLE_STAGE
from erk_shared.plan_store.conversion import header_str
from erk_shared.plan_store.types import Plan


def compute_lifecycle_display(plan: Plan) -> str:
    """Compute lifecycle stage display string for a plan.

    Reads lifecycle_stage from plan header fields if present, otherwise
    infers from is_draft and pr_state in plan metadata. Returns a
    color-coded Rich markup string for table display.

    Args:
        plan: Plan with header_fields and metadata populated

    Returns:
        Display string (may contain Rich markup for color)
    """
    # Read from header fields first
    stage = header_str(plan.header_fields, LIFECYCLE_STAGE)

    # Fall back to inferring from PR metadata
    if stage is None and plan.metadata:
        is_draft = plan.metadata.get("is_draft")
        pr_state = plan.metadata.get("pr_state")
        if isinstance(is_draft, bool) and isinstance(pr_state, str):
            if is_draft and pr_state == "OPEN":
                stage = "planned"
            elif not is_draft and pr_state == "OPEN":
                stage = "review"
            elif not is_draft and pr_state == "MERGED":
                stage = "merged"
            elif not is_draft and pr_state == "CLOSED":
                stage = "closed"

    if stage is None:
        return "-"

    # Color-code by stage
    if stage in ("pre-plan", "planning"):
        return f"[magenta]{stage}[/magenta]"
    if stage == "planned":
        return f"[dim]{stage}[/dim]"
    if stage == "implementing":
        return f"[yellow]{stage}[/yellow]"
    if stage == "review":
        return f"[cyan]{stage}[/cyan]"
    if stage == "merged":
        return f"[green]{stage}[/green]"
    if stage == "closed":
        return f"[dim red]{stage}[/dim red]"
    return stage


def format_lifecycle_with_status(
    lifecycle_display: str,
    *,
    has_conflicts: bool | None,
    review_decision: str | None,
) -> str:
    """Append status indicators to a lifecycle stage display string.

    Adds emoji indicators to the stage text when relevant:
    - 💥 for merge conflicts (on implementing and review stages)
    - ✔ for approved PRs (on review stage only)
    - ❌ for changes requested (on review stage only)

    Indicators are inserted inside Rich markup tags so they inherit
    the stage color.

    Args:
        lifecycle_display: Pre-formatted lifecycle string (may contain Rich markup)
        has_conflicts: True if PR has merge conflicts, False/None otherwise
        review_decision: "APPROVED", "CHANGES_REQUESTED", "REVIEW_REQUIRED", or None

    Returns:
        Lifecycle display string with appended indicators
    """
    # Only add indicators for implementing and review stages
    # Detect stage from the display string content
    is_implementing = "implementing" in lifecycle_display
    is_review = "review" in lifecycle_display and "REVIEW" not in lifecycle_display

    if not is_implementing and not is_review:
        return lifecycle_display

    # Build indicator suffix
    indicators: list[str] = []

    if has_conflicts is True:
        indicators.append("💥")

    if is_review:
        if review_decision == "APPROVED":
            indicators.append("✔")
        elif review_decision == "CHANGES_REQUESTED":
            indicators.append("❌")

    if not indicators:
        return lifecycle_display

    suffix = " " + " ".join(indicators)

    # Insert suffix inside Rich markup closing tag so indicators inherit color
    # Pattern: "[color]stage[/color]" -> "[color]stage suffix[/color]"
    closing_idx = lifecycle_display.rfind("[/")
    if closing_idx != -1:
        before = lifecycle_display[:closing_idx]
        after = lifecycle_display[closing_idx:]
        return before + suffix + after

    # No Rich markup - just append
    return lifecycle_display + suffix
