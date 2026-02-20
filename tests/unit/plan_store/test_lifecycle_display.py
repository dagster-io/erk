"""Tests for lifecycle display functions."""

from datetime import UTC, datetime

from erk_shared.gateway.github.metadata.schemas import LIFECYCLE_STAGE
from erk_shared.gateway.plan_data_provider.lifecycle import (
    compute_lifecycle_display,
    format_lifecycle_with_status,
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


# --- format_lifecycle_with_status tests ---


def test_no_indicators_returns_original() -> None:
    """No conflicts or review decision returns original display string."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        has_conflicts=None,
        review_decision=None,
    )
    assert result == "[cyan]review[/cyan]"


def test_no_indicators_when_false_conflicts() -> None:
    """has_conflicts=False does not add indicator."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        has_conflicts=False,
        review_decision=None,
    )
    assert result == "[cyan]review[/cyan]"


def test_conflicts_indicator_with_rich_markup() -> None:
    """Conflicts indicator inserted inside Rich markup closing tag."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        has_conflicts=True,
        review_decision=None,
    )
    assert result == "[cyan]review 💥[/cyan]"


def test_approved_indicator_with_rich_markup() -> None:
    """Approved indicator inserted inside Rich markup closing tag."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        has_conflicts=None,
        review_decision="APPROVED",
    )
    assert result == "[cyan]review ✔[/cyan]"


def test_changes_requested_indicator() -> None:
    """Changes requested indicator inserted inside Rich markup closing tag."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        has_conflicts=None,
        review_decision="CHANGES_REQUESTED",
    )
    assert result == "[cyan]review ❌[/cyan]"


def test_conflicts_and_changes_requested() -> None:
    """Both conflicts and changes requested shown together."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        has_conflicts=True,
        review_decision="CHANGES_REQUESTED",
    )
    assert result == "[cyan]review 💥 ❌[/cyan]"


def test_conflicts_and_approved() -> None:
    """Both conflicts and approved shown together."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        has_conflicts=True,
        review_decision="APPROVED",
    )
    assert result == "[cyan]review 💥 ✔[/cyan]"


def test_implementing_with_conflicts() -> None:
    """Implementing stage with conflicts shows indicator."""
    result = format_lifecycle_with_status(
        "[yellow]implementing[/yellow]",
        has_conflicts=True,
        review_decision=None,
    )
    assert result == "[yellow]implementing 💥[/yellow]"


def test_plain_text_without_markup() -> None:
    """Plain text without Rich markup appends indicators."""
    result = format_lifecycle_with_status(
        "custom-stage",
        has_conflicts=True,
        review_decision=None,
    )
    assert result == "custom-stage 💥"


def test_dash_with_no_indicators() -> None:
    """Dash display with no indicators unchanged."""
    result = format_lifecycle_with_status(
        "-",
        has_conflicts=None,
        review_decision=None,
    )
    assert result == "-"


def test_review_required_not_shown() -> None:
    """REVIEW_REQUIRED does not add an indicator (not actionable)."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        has_conflicts=None,
        review_decision="REVIEW_REQUIRED",
    )
    assert result == "[cyan]review[/cyan]"


def test_dim_red_markup_with_conflicts() -> None:
    """Indicators work with dim red markup (nested tags)."""
    result = format_lifecycle_with_status(
        "[dim red]closed[/dim red]",
        has_conflicts=True,
        review_decision=None,
    )
    assert result == "[dim red]closed 💥[/dim red]"
