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
    """Enrich lifecycle display string with PR status indicators.

    Appends emoji indicators to the lifecycle stage text when relevant:
    - 💥 for merge conflicts (implementing, review stages)
    - ✔ for approved (review stage)
    - ❌ for changes requested (review stage)

    Indicators are inserted inside Rich markup tags so they inherit color.

    Args:
        lifecycle_display: Pre-computed lifecycle display string from
            compute_lifecycle_display() (may contain Rich markup)
        has_conflicts: True if PR has merge conflicts
        review_decision: PR review decision ("APPROVED", "CHANGES_REQUESTED",
            "REVIEW_REQUIRED", or None)

    Returns:
        Enriched display string with status indicators appended
    """
    # Build the suffix from relevant indicators
    indicators: list[str] = []

    if has_conflicts is True:
        indicators.append("💥")

    if review_decision == "APPROVED":
        indicators.append("✔")
    elif review_decision == "CHANGES_REQUESTED":
        indicators.append("❌")

    if not indicators:
        return lifecycle_display

    suffix = " " + " ".join(indicators)

    # Insert suffix inside Rich markup closing tag if present
    # Rich markup format: [color]text[/color]
    # We want: [color]text 💥[/color]
    close_tag_start = lifecycle_display.rfind("[/")
    if close_tag_start != -1:
        return lifecycle_display[:close_tag_start] + suffix + lifecycle_display[close_tag_start:]

    # No Rich markup — just append
    return lifecycle_display + suffix
