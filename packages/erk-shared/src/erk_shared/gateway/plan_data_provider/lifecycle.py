"""Lifecycle stage display computation for plans.

Extracted to a standalone module to avoid circular imports when testing.
The main consumer is RealPlanDataProvider in real.py.
"""

from erk_shared.gateway.github.metadata.schemas import LIFECYCLE_STAGE
from erk_shared.plan_store.conversion import header_str
from erk_shared.plan_store.types import Plan


def resolve_lifecycle_stage(
    plan: Plan,
    *,
    has_workflow_run: bool = False,
    linked_pr_state: str | None = None,
) -> str | None:
    """Resolve the lifecycle stage for a plan.

    Reads lifecycle_stage from plan header fields if present, otherwise infers from
    is_draft and pr_state in plan metadata. When the resolved stage is "planned" and
    has_workflow_run is True, upgrades to "impl".

    Args:
        plan: Plan with header_fields and metadata populated
        has_workflow_run: Whether the plan has an associated workflow run
        linked_pr_state: PR state from linked PR (e.g. "MERGED", "CLOSED", "OPEN").
            Used for issue-backed plans where pr_state is not in plan.metadata.

    Returns:
        Stage string (e.g., "planned", "impl", "merged"), or None if stage
        cannot be determined.
    """
    stage = header_str(plan.header_fields, LIFECYCLE_STAGE)

    # Terminal PR states override header field (header may be stale).
    # Check explicit linked_pr_state first, then fall back to metadata.
    effective_pr_state = linked_pr_state
    if effective_pr_state is None and plan.metadata:
        raw = plan.metadata.get("pr_state")
        if isinstance(raw, str):
            effective_pr_state = raw

    if effective_pr_state == "MERGED":
        stage = "merged"
    elif effective_pr_state == "CLOSED":
        stage = "closed"

    # Fall back to inferring from PR metadata
    if stage is None and plan.metadata:
        is_draft = plan.metadata.get("is_draft")
        pr_state = plan.metadata.get("pr_state")
        if isinstance(is_draft, bool) and isinstance(pr_state, str):
            if is_draft and pr_state == "OPEN":
                stage = "planned"
            elif not is_draft and pr_state == "OPEN":
                stage = "impl"
            elif not is_draft and pr_state == "MERGED":
                stage = "merged"
            elif not is_draft and pr_state == "CLOSED":
                stage = "closed"

    if stage == "planned" and has_workflow_run:
        stage = "impl"

    return stage


def compute_lifecycle_display(
    plan: Plan,
    *,
    has_workflow_run: bool,
    linked_pr_state: str | None = None,
) -> str:
    """Compute lifecycle stage display string for a plan.

    Delegates to resolve_lifecycle_stage for detection, then applies
    color-coded Rich markup for table display.

    Args:
        plan: Plan with header_fields and metadata populated
        has_workflow_run: Whether the plan has an associated workflow run
        linked_pr_state: PR state from linked PR (e.g. "MERGED", "CLOSED", "OPEN").
            Used for issue-backed plans where pr_state is not in plan.metadata.

    Returns:
        Display string (may contain Rich markup for color)
    """
    stage = resolve_lifecycle_stage(
        plan, has_workflow_run=has_workflow_run, linked_pr_state=linked_pr_state
    )

    if stage is None:
        return "-"

    # Color-code by stage
    if stage in ("prompted", "planning"):
        return f"[magenta]{stage}[/magenta]"
    if stage == "planned":
        return f"[dim]{stage}[/dim]"
    if stage in ("impl", "implementing", "implemented"):
        return "[yellow]impl[/yellow]"
    if stage == "merged":
        return f"[green]{stage}[/green]"
    if stage == "closed":
        return f"[dim red]{stage}[/dim red]"
    return stage


def compute_status_indicators(
    lifecycle_display: str,
    *,
    is_draft: bool | None,
    has_conflicts: bool | None,
    review_decision: str | None,
    checks_passing: bool | None,
    has_unresolved_comments: bool | None,
    is_stacked: bool | None = None,
) -> str:
    """Compute status indicator emojis for a lifecycle stage.

    Returns a space-joined string of emoji indicators, or "-" when empty.
    This is the standalone version used to populate the "sts" column.

    Args:
        lifecycle_display: Pre-formatted lifecycle string (may contain Rich markup)
        is_draft: True for draft PR, False for published PR, None if unknown
        has_conflicts: True if PR has merge conflicts, False/None otherwise
        review_decision: "APPROVED", "CHANGES_REQUESTED", "REVIEW_REQUIRED", or None
        checks_passing: True if all CI checks pass, False/None otherwise
        has_unresolved_comments: True if there are unresolved review threads,
            False/None otherwise
        is_stacked: True if PR base branch is not master/main, None if unknown

    Returns:
        Space-joined indicators string (e.g., "🚧 💥"), or "-" when no indicators
    """
    indicators = _build_indicators(
        lifecycle_display,
        is_draft=is_draft,
        has_conflicts=has_conflicts,
        review_decision=review_decision,
        checks_passing=checks_passing,
        has_unresolved_comments=has_unresolved_comments,
        is_stacked=is_stacked,
    )
    if not indicators:
        return "-"
    return " ".join(indicators)


def format_lifecycle_with_status(
    lifecycle_display: str,
    *,
    is_draft: bool | None,
    has_conflicts: bool | None,
    review_decision: str | None,
    checks_passing: bool | None,
    has_unresolved_comments: bool | None,
    is_stacked: bool | None = None,
) -> str:
    """Add draft/published prefix and status suffix to a lifecycle stage display.

    Adds emoji indicators to the stage text when relevant:
    - 🥞 prefix for stacked PRs (base branch != master/main)
    - 🚧/👀 suffix for draft/published state (on planned, impl, review)
    - 💥 suffix for merge conflicts (on impl and review stages)
    - ✔ suffix for approved PRs (on review stage only)
    - ❌ suffix for changes requested (on review stage only)
    - 🚀 suffix for impl PRs that are ready to merge (checks pass, no
      unresolved comments, no conflicts)

    Indicators are inserted inside Rich markup tags so they inherit
    the stage color.

    Args:
        lifecycle_display: Pre-formatted lifecycle string (may contain Rich markup)
        is_draft: True for draft PR, False for published PR, None if unknown
        has_conflicts: True if PR has merge conflicts, False/None otherwise
        review_decision: "APPROVED", "CHANGES_REQUESTED", "REVIEW_REQUIRED", or None
        checks_passing: True if all CI checks pass, False/None otherwise
        has_unresolved_comments: True if there are unresolved review threads,
            False/None otherwise
        is_stacked: True if PR base branch is not master/main, None if unknown

    Returns:
        Lifecycle display string with prefix/suffix indicators
    """
    indicators = _build_indicators(
        lifecycle_display,
        is_draft=is_draft,
        has_conflicts=has_conflicts,
        review_decision=review_decision,
        checks_passing=checks_passing,
        has_unresolved_comments=has_unresolved_comments,
        is_stacked=is_stacked,
    )

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


def _build_indicators(
    lifecycle_display: str,
    *,
    is_draft: bool | None,
    has_conflicts: bool | None,
    review_decision: str | None,
    checks_passing: bool | None,
    has_unresolved_comments: bool | None,
    is_stacked: bool | None = None,
) -> list[str]:
    """Build list of emoji indicators for a lifecycle stage.

    Shared logic used by both compute_status_indicators() and
    format_lifecycle_with_status().

    Args:
        lifecycle_display: Pre-formatted lifecycle string (may contain Rich markup)
        is_draft: True for draft PR, False for published PR, None if unknown
        has_conflicts: True if PR has merge conflicts, False/None otherwise
        review_decision: "APPROVED", "CHANGES_REQUESTED", "REVIEW_REQUIRED", or None
        checks_passing: True if all CI checks pass, False/None otherwise
        has_unresolved_comments: True if there are unresolved review threads,
            False/None otherwise
        is_stacked: True if PR base branch is not master/main, None if unknown

    Returns:
        List of emoji indicator strings
    """
    # Detect stage from the display string content
    is_planned = "planned" in lifecycle_display
    is_impl = "impl" in lifecycle_display  # matches "impl", "implementing", "implemented"
    is_review = "review" in lifecycle_display and "REVIEW" not in lifecycle_display
    is_active_stage = is_planned or is_impl or is_review

    # Build indicator suffix — all emojis go on the right for consistency
    indicators: list[str] = []

    # Stacked PR indicator — first, before all other indicators
    if is_stacked is True:
        indicators.append("🥞")

    # Draft/published indicator for active stages
    if is_active_stage and is_draft is not None:
        indicators.append("🚧" if is_draft else "👀")

    # Conflict/review indicators for impl and review stages
    if is_impl or is_review:
        if has_conflicts is True:
            indicators.append("💥")

        if is_review:
            if review_decision == "APPROVED":
                indicators.append("✔")
            elif review_decision == "CHANGES_REQUESTED":
                indicators.append("❌")

    # Ready-to-land indicator for impl stage:
    # shown only when checks pass, no unresolved comments, and no blocking indicators
    # (🥞, 👀, and ✔ are informational and should not block 🚀)
    _non_blocking = {"🥞", "👀", "✔"}
    has_blocking_indicators = any(i not in _non_blocking for i in indicators)
    if is_impl and not has_blocking_indicators:
        if checks_passing is True and has_unresolved_comments is not True:
            indicators.append("🚀")

    return indicators
