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
                stage = "implemented"
            elif not is_draft and pr_state == "MERGED":
                stage = "merged"
            elif not is_draft and pr_state == "CLOSED":
                stage = "closed"

    if stage is None:
        return "-"

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
