"""Lifecycle stage display computation for plans.

Extracted to a standalone module to avoid circular imports when testing.
The main consumer is RealPlanDataProvider in real.py.
"""

import re

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


# Pattern to match Rich markup: [tag]text[/tag]
_RICH_MARKUP_PATTERN = re.compile(r"^(\[.*?\])(.+?)(\[/.*?\])$")


def enrich_lifecycle_with_status(
    lifecycle_display: str,
    *,
    has_conflicts: bool | None,
    review_decision: str | None,
) -> str:
    """Enrich lifecycle display string with conflict and review indicators.

    Only enriches 'implementing' and 'review' stages. Other stages are
    returned unchanged.

    Args:
        lifecycle_display: The base lifecycle display string (may contain Rich markup)
        has_conflicts: True if PR has merge conflicts, False if clean, None if unknown
        review_decision: GitHub review decision ("APPROVED", "CHANGES_REQUESTED", etc.)

    Returns:
        Enriched display string with emoji indicators appended
    """
    # Build suffix from indicators
    suffix_parts: list[str] = []
    if has_conflicts is True:
        suffix_parts.append("\U0001f4a5")  # 💥
    if review_decision == "APPROVED":
        suffix_parts.append("\u2714")  # ✔
    elif review_decision == "CHANGES_REQUESTED":
        suffix_parts.append("\u274c")  # ❌

    if not suffix_parts:
        return lifecycle_display

    suffix = " " + " ".join(suffix_parts)

    # Check if it's Rich markup
    match = _RICH_MARKUP_PATTERN.match(lifecycle_display)
    if match:
        open_tag, text, close_tag = match.groups()
        # Only enrich implementing and review stages
        if text not in ("implementing", "review"):
            return lifecycle_display
        return f"{open_tag}{text}{suffix}{close_tag}"

    # Bare string: only enrich implementing and review
    if lifecycle_display not in ("implementing", "review"):
        return lifecycle_display
    return f"{lifecycle_display}{suffix}"
