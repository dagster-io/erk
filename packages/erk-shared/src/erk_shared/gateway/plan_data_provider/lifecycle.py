"""Lifecycle stage display computation for plans.

Extracted to a standalone module to avoid circular imports when testing.
The main consumer is RealPlanDataProvider in real.py.
"""

from erk_shared.gateway.github.metadata.schemas import LIFECYCLE_STAGE
from erk_shared.plan_store.conversion import header_str
from erk_shared.plan_store.types import Plan


def compute_lifecycle_display(plan: Plan, *, has_workflow_run: bool) -> str:
    """Compute lifecycle stage display string for a plan.

    Reads lifecycle_stage from plan header fields if present, otherwise
    infers from is_draft and pr_state in plan metadata. Returns a
    color-coded Rich markup string for table display.

    When the resolved stage is "planned" and a workflow run exists,
    upgrades to "implementing" since the plan is actively being worked on.

    Args:
        plan: Plan with header_fields and metadata populated
        has_workflow_run: Whether the plan has an associated workflow run

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
                stage = "implemented"
            elif not is_draft and pr_state == "MERGED":
                stage = "merged"
            elif not is_draft and pr_state == "CLOSED":
                stage = "closed"

    if stage is None:
        return "-"

    # Upgrade "planned" to "implementing" when a workflow run exists
    if stage == "planned" and has_workflow_run:
        stage = "implementing"

    # Color-code by stage
    if stage in ("prompted", "planning"):
        return f"[magenta]{stage}[/magenta]"
    if stage == "planned":
        return f"[dim]{stage}[/dim]"
    if stage == "implementing":
        return f"[yellow]{stage}[/yellow]"
    if stage == "implemented":
        return f"[cyan]{stage}[/cyan]"
    if stage == "merged":
        return f"[green]{stage}[/green]"
    if stage == "closed":
        return f"[dim red]{stage}[/dim red]"
    return stage


def format_lifecycle_with_status(
    lifecycle_display: str,
    *,
    is_draft: bool | None,
    has_conflicts: bool | None,
    review_decision: str | None,
) -> str:
    """Add status indicator prefixes to a lifecycle stage display.

    Adds emoji indicators as prefixes to the stage text when relevant:
    - 🚧/👀 prefix for draft/published state (on planned, implementing, implemented, review)
    - 💥 prefix for merge conflicts (on planned, implementing, implemented, review)
    - ✔ prefix for approved PRs (on review stage only)
    - ❌ prefix for changes requested (on review stage only)

    All indicators are placed before the stage text so they survive
    column truncation in the TUI table (stage column is 9 chars wide).

    Indicators are inserted inside Rich markup tags so they inherit
    the stage color.

    Args:
        lifecycle_display: Pre-formatted lifecycle string (may contain Rich markup)
        is_draft: True for draft PR, False for published PR, None if unknown
        has_conflicts: True if PR has merge conflicts, False/None otherwise
        review_decision: "APPROVED", "CHANGES_REQUESTED", "REVIEW_REQUIRED", or None

    Returns:
        Lifecycle display string with prefix indicators
    """
    # Detect stage from the display string content
    is_implementing = "implementing" in lifecycle_display
    is_implemented = "implemented" in lifecycle_display and not is_implementing
    is_planned = "planned" in lifecycle_display
    is_review = "review" in lifecycle_display and "REVIEW" not in lifecycle_display
    is_active_stage = is_planned or is_implementing or is_implemented or is_review

    if not is_active_stage:
        return lifecycle_display

    # Build ordered prefix parts: draft/published → conflict → review decision
    parts: list[str] = []

    if is_draft is not None:
        parts.append("🚧" if is_draft else "👀")

    if has_conflicts is True:
        parts.append("💥")

    if is_review:
        if review_decision == "APPROVED":
            parts.append("✔")
        elif review_decision == "CHANGES_REQUESTED":
            parts.append("❌")

    if not parts:
        return lifecycle_display

    prefix = " ".join(parts) + " "

    # Parse Rich markup to extract opening tag and stage text
    if lifecycle_display.startswith("["):
        opening_end = lifecycle_display.find("]")
        if opening_end != -1:
            opening_tag = lifecycle_display[: opening_end + 1]
            rest = lifecycle_display[opening_end + 1 :]
            # rest is "stage_text[/color]"
            closing_idx = rest.rfind("[/")
            if closing_idx != -1:
                stage_text = rest[:closing_idx]
                closing_tag = rest[closing_idx:]
                return opening_tag + prefix + stage_text + closing_tag
            return opening_tag + prefix + rest
        return prefix + lifecycle_display

    # No Rich markup - just prepend
    return prefix + lifecycle_display
