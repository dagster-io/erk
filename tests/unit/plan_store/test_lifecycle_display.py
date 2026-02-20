"""Tests for lifecycle display computation and enrichment functions."""

from datetime import UTC, datetime

from erk_shared.gateway.github.metadata.schemas import LIFECYCLE_STAGE
from erk_shared.gateway.plan_data_provider.lifecycle import (
    compute_lifecycle_display,
    enrich_lifecycle_with_status,
)
from erk_shared.plan_store.types import Plan, PlanState


def _make_plan(
    *,
    header_fields: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> Plan:
    """Create a Plan for testing with minimal required fields."""
    return Plan(
        plan_identifier="42",
        title="Test plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/test/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        updated_at=datetime(2024, 1, 16, 12, 0, tzinfo=UTC),
        metadata=metadata if metadata is not None else {},
        objective_id=None,
        header_fields=header_fields if header_fields is not None else {},
    )


# --- Header field present: each stage maps to correct color markup ---


def test_pre_plan_stage_returns_magenta_markup() -> None:
    """pre-plan header field returns magenta markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "pre-plan"})
    assert compute_lifecycle_display(plan) == "[magenta]pre-plan[/magenta]"


def test_planning_stage_returns_magenta_markup() -> None:
    """planning header field returns magenta markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "planning"})
    assert compute_lifecycle_display(plan) == "[magenta]planning[/magenta]"


def test_planned_stage_returns_dim_markup() -> None:
    """planned header field returns dim markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "planned"})
    assert compute_lifecycle_display(plan) == "[dim]planned[/dim]"


def test_implementing_stage_returns_yellow_markup() -> None:
    """implementing header field returns yellow markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "implementing"})
    assert compute_lifecycle_display(plan) == "[yellow]implementing[/yellow]"


def test_review_stage_returns_cyan_markup() -> None:
    """review header field returns cyan markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "review"})
    assert compute_lifecycle_display(plan) == "[cyan]review[/cyan]"


def test_merged_stage_returns_green_markup() -> None:
    """merged header field returns green markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "merged"})
    assert compute_lifecycle_display(plan) == "[green]merged[/green]"


def test_closed_stage_returns_dim_red_markup() -> None:
    """closed header field returns dim red markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "closed"})
    assert compute_lifecycle_display(plan) == "[dim red]closed[/dim red]"


# --- No header field, infer from metadata ---


def test_infer_planned_from_draft_open_pr() -> None:
    """Draft + OPEN PR infers planned stage."""
    plan = _make_plan(metadata={"is_draft": True, "pr_state": "OPEN"})
    assert compute_lifecycle_display(plan) == "[dim]planned[/dim]"


def test_infer_review_from_non_draft_open_pr() -> None:
    """Non-draft + OPEN PR infers review stage."""
    plan = _make_plan(metadata={"is_draft": False, "pr_state": "OPEN"})
    assert compute_lifecycle_display(plan) == "[cyan]review[/cyan]"


def test_infer_merged_from_merged_pr() -> None:
    """Non-draft + MERGED PR infers merged stage."""
    plan = _make_plan(metadata={"is_draft": False, "pr_state": "MERGED"})
    assert compute_lifecycle_display(plan) == "[green]merged[/green]"


def test_infer_closed_from_closed_pr() -> None:
    """Non-draft + CLOSED PR infers closed stage."""
    plan = _make_plan(metadata={"is_draft": False, "pr_state": "CLOSED"})
    assert compute_lifecycle_display(plan) == "[dim red]closed[/dim red]"


# --- No header field, no metadata ---


def test_no_header_no_metadata_returns_dash() -> None:
    """No header field and no metadata returns dash."""
    plan = _make_plan()
    assert compute_lifecycle_display(plan) == "-"


def test_empty_metadata_returns_dash() -> None:
    """Empty metadata dict returns dash."""
    plan = _make_plan(metadata={})
    assert compute_lifecycle_display(plan) == "-"


# --- Unknown stage string ---


def test_unknown_stage_returns_stage_without_markup() -> None:
    """Unknown stage string returns stage with no markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "custom-stage"})
    assert compute_lifecycle_display(plan) == "custom-stage"


# --- Header field takes precedence over metadata ---


def test_header_field_takes_precedence_over_metadata() -> None:
    """Header field stage takes precedence over inferred metadata stage."""
    plan = _make_plan(
        header_fields={LIFECYCLE_STAGE: "implementing"},
        metadata={"is_draft": False, "pr_state": "MERGED"},
    )
    assert compute_lifecycle_display(plan) == "[yellow]implementing[/yellow]"


# --- enrich_lifecycle_with_status tests ---


def test_enrich_review_with_conflicts() -> None:
    """Review stage with conflicts shows 💥."""
    result = enrich_lifecycle_with_status(
        "[cyan]review[/cyan]", has_conflicts=True, review_decision=None
    )
    assert result == "[cyan]review \U0001f4a5[/cyan]"


def test_enrich_review_with_approved() -> None:
    """Review stage with approved shows ✔."""
    result = enrich_lifecycle_with_status(
        "[cyan]review[/cyan]", has_conflicts=False, review_decision="APPROVED"
    )
    assert result == "[cyan]review \u2714[/cyan]"


def test_enrich_review_with_changes_requested() -> None:
    """Review stage with changes requested shows ❌."""
    result = enrich_lifecycle_with_status(
        "[cyan]review[/cyan]", has_conflicts=False, review_decision="CHANGES_REQUESTED"
    )
    assert result == "[cyan]review \u274c[/cyan]"


def test_enrich_review_with_conflicts_and_changes_requested() -> None:
    """Review stage with conflicts AND changes requested shows both."""
    result = enrich_lifecycle_with_status(
        "[cyan]review[/cyan]", has_conflicts=True, review_decision="CHANGES_REQUESTED"
    )
    assert result == "[cyan]review \U0001f4a5 \u274c[/cyan]"


def test_enrich_implementing_with_conflicts() -> None:
    """Implementing stage with conflicts shows 💥."""
    result = enrich_lifecycle_with_status(
        "[yellow]implementing[/yellow]", has_conflicts=True, review_decision=None
    )
    assert result == "[yellow]implementing \U0001f4a5[/yellow]"


def test_enrich_planned_stage_unchanged() -> None:
    """Planned stage is not enriched even with conflicts."""
    result = enrich_lifecycle_with_status(
        "[dim]planned[/dim]", has_conflicts=True, review_decision=None
    )
    assert result == "[dim]planned[/dim]"


def test_enrich_merged_stage_unchanged() -> None:
    """Merged stage is not enriched."""
    result = enrich_lifecycle_with_status(
        "[green]merged[/green]", has_conflicts=False, review_decision="APPROVED"
    )
    assert result == "[green]merged[/green]"


def test_enrich_no_indicators_unchanged() -> None:
    """No indicators returns unchanged display."""
    result = enrich_lifecycle_with_status(
        "[cyan]review[/cyan]", has_conflicts=False, review_decision=None
    )
    assert result == "[cyan]review[/cyan]"


def test_enrich_bare_string_review() -> None:
    """Bare string (no markup) review stage appends directly."""
    result = enrich_lifecycle_with_status("review", has_conflicts=True, review_decision=None)
    assert result == "review \U0001f4a5"


def test_enrich_bare_string_non_enrichable_unchanged() -> None:
    """Bare string of non-enrichable stage is unchanged."""
    result = enrich_lifecycle_with_status("planned", has_conflicts=True, review_decision=None)
    assert result == "planned"


def test_enrich_has_conflicts_none_no_change() -> None:
    """has_conflicts=None does not add indicator."""
    result = enrich_lifecycle_with_status(
        "[cyan]review[/cyan]", has_conflicts=None, review_decision=None
    )
    assert result == "[cyan]review[/cyan]"


def test_enrich_review_required_no_indicator() -> None:
    """REVIEW_REQUIRED does not add an indicator."""
    result = enrich_lifecycle_with_status(
        "[cyan]review[/cyan]", has_conflicts=False, review_decision="REVIEW_REQUIRED"
    )
    assert result == "[cyan]review[/cyan]"
