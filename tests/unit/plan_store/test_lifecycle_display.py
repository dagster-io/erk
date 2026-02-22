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


def test_prompted_stage_returns_magenta_markup() -> None:
    """prompted header field returns magenta markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "prompted"})
    assert compute_lifecycle_display(plan, has_workflow_run=False) == "[magenta]prompted[/magenta]"


def test_planning_stage_returns_magenta_markup() -> None:
    """planning header field returns magenta markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "planning"})
    assert compute_lifecycle_display(plan, has_workflow_run=False) == "[magenta]planning[/magenta]"


def test_planned_stage_returns_dim_markup() -> None:
    """planned header field returns dim markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "planned"})
    assert compute_lifecycle_display(plan, has_workflow_run=False) == "[dim]planned[/dim]"


def test_implementing_stage_returns_yellow_markup() -> None:
    """implementing header field returns yellow markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "implementing"})
    result = compute_lifecycle_display(plan, has_workflow_run=False)
    assert result == "[yellow]impling[/yellow]"


def test_implemented_stage_returns_cyan_markup() -> None:
    """implemented header field returns cyan markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "implemented"})
    assert compute_lifecycle_display(plan, has_workflow_run=False) == "[cyan]impld[/cyan]"


def test_merged_stage_returns_green_markup() -> None:
    """merged header field returns green markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "merged"})
    assert compute_lifecycle_display(plan, has_workflow_run=False) == "[green]merged[/green]"


def test_closed_stage_returns_dim_red_markup() -> None:
    """closed header field returns dim red markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "closed"})
    assert compute_lifecycle_display(plan, has_workflow_run=False) == "[dim red]closed[/dim red]"


# --- No header field, infer from metadata ---


def test_infer_planned_from_draft_open_pr() -> None:
    """Draft + OPEN PR infers planned stage."""
    plan = _make_plan(metadata={"is_draft": True, "pr_state": "OPEN"})
    assert compute_lifecycle_display(plan, has_workflow_run=False) == "[dim]planned[/dim]"


def test_infer_review_from_non_draft_open_pr() -> None:
    """Non-draft + OPEN PR infers implemented stage."""
    plan = _make_plan(metadata={"is_draft": False, "pr_state": "OPEN"})
    assert compute_lifecycle_display(plan, has_workflow_run=False) == "[cyan]impld[/cyan]"


def test_infer_merged_from_merged_pr() -> None:
    """Non-draft + MERGED PR infers merged stage."""
    plan = _make_plan(metadata={"is_draft": False, "pr_state": "MERGED"})
    assert compute_lifecycle_display(plan, has_workflow_run=False) == "[green]merged[/green]"


def test_infer_closed_from_closed_pr() -> None:
    """Non-draft + CLOSED PR infers closed stage."""
    plan = _make_plan(metadata={"is_draft": False, "pr_state": "CLOSED"})
    assert compute_lifecycle_display(plan, has_workflow_run=False) == "[dim red]closed[/dim red]"


# --- No header field, no metadata ---


def test_no_header_no_metadata_returns_dash() -> None:
    """No header field and no metadata returns dash."""
    plan = _make_plan()
    assert compute_lifecycle_display(plan, has_workflow_run=False) == "-"


def test_empty_metadata_returns_dash() -> None:
    """Empty metadata dict returns dash."""
    plan = _make_plan(metadata={})
    assert compute_lifecycle_display(plan, has_workflow_run=False) == "-"


# --- Unknown stage string ---


def test_unknown_stage_returns_stage_without_markup() -> None:
    """Unknown stage string returns stage with no markup."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "custom-stage"})
    assert compute_lifecycle_display(plan, has_workflow_run=False) == "custom-stage"


# --- Header field takes precedence over metadata ---


def test_header_field_takes_precedence_over_metadata() -> None:
    """Header field stage takes precedence over inferred metadata stage."""
    plan = _make_plan(
        header_fields={LIFECYCLE_STAGE: "implementing"},
        metadata={"is_draft": False, "pr_state": "MERGED"},
    )
    result = compute_lifecycle_display(plan, has_workflow_run=False)
    assert result == "[yellow]impling[/yellow]"


# --- format_lifecycle_with_status tests ---


def test_review_no_indicators() -> None:
    """Review stage with no issues returns unchanged."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        is_draft=None,
        has_conflicts=False,
        review_decision=None,
    )
    assert result == "[cyan]review[/cyan]"


def test_review_with_conflicts() -> None:
    """Review stage with conflicts shows explosion emoji."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        is_draft=None,
        has_conflicts=True,
        review_decision=None,
    )
    assert result == "[cyan]review 💥[/cyan]"


def test_review_approved() -> None:
    """Review stage with approval shows checkmark."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        is_draft=None,
        has_conflicts=False,
        review_decision="APPROVED",
    )
    assert result == "[cyan]review ✔[/cyan]"


def test_review_changes_requested() -> None:
    """Review stage with changes requested shows X."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        is_draft=None,
        has_conflicts=False,
        review_decision="CHANGES_REQUESTED",
    )
    assert result == "[cyan]review ❌[/cyan]"


def test_review_conflicts_and_changes_requested() -> None:
    """Review stage with both conflicts and changes requested shows both."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        is_draft=None,
        has_conflicts=True,
        review_decision="CHANGES_REQUESTED",
    )
    assert result == "[cyan]review 💥 ❌[/cyan]"


def test_review_conflicts_and_approved() -> None:
    """Review stage with conflicts and approval shows both."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        is_draft=None,
        has_conflicts=True,
        review_decision="APPROVED",
    )
    assert result == "[cyan]review 💥 ✔[/cyan]"


def test_implementing_with_conflicts() -> None:
    """Implementing stage with conflicts shows explosion emoji."""
    result = format_lifecycle_with_status(
        "[yellow]impling[/yellow]",
        is_draft=None,
        has_conflicts=True,
        review_decision=None,
    )
    assert result == "[yellow]impling 💥[/yellow]"


def test_implementing_no_conflicts() -> None:
    """Implementing stage without conflicts returns unchanged."""
    result = format_lifecycle_with_status(
        "[yellow]impling[/yellow]",
        is_draft=None,
        has_conflicts=False,
        review_decision=None,
    )
    assert result == "[yellow]impling[/yellow]"


def test_implementing_ignores_review_decision() -> None:
    """Implementing stage does not show review decision indicators."""
    result = format_lifecycle_with_status(
        "[yellow]impling[/yellow]",
        is_draft=None,
        has_conflicts=False,
        review_decision="APPROVED",
    )
    assert result == "[yellow]impling[/yellow]"


def test_planned_stage_no_indicators() -> None:
    """Planned stage never shows indicators regardless of status."""
    result = format_lifecycle_with_status(
        "[dim]planned[/dim]",
        is_draft=None,
        has_conflicts=True,
        review_decision="CHANGES_REQUESTED",
    )
    assert result == "[dim]planned[/dim]"


def test_merged_stage_no_indicators() -> None:
    """Merged stage never shows indicators."""
    result = format_lifecycle_with_status(
        "[green]merged[/green]",
        is_draft=None,
        has_conflicts=True,
        review_decision="APPROVED",
    )
    assert result == "[green]merged[/green]"


def test_dash_stage_no_indicators() -> None:
    """Dash (no stage) never shows indicators."""
    result = format_lifecycle_with_status(
        "-",
        is_draft=None,
        has_conflicts=True,
        review_decision="APPROVED",
    )
    assert result == "-"


def test_review_with_none_conflicts() -> None:
    """Review stage with None conflicts (unknown) shows no conflict indicator."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        is_draft=None,
        has_conflicts=None,
        review_decision="APPROVED",
    )
    assert result == "[cyan]review ✔[/cyan]"


def test_review_required_shows_no_indicator() -> None:
    """REVIEW_REQUIRED does not show any indicator (not actionable)."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        is_draft=None,
        has_conflicts=False,
        review_decision="REVIEW_REQUIRED",
    )
    assert result == "[cyan]review[/cyan]"


def test_plain_text_stage_appends_suffix() -> None:
    """Plain text stage (no Rich markup) appends suffix directly."""
    result = format_lifecycle_with_status(
        "review",
        is_draft=None,
        has_conflicts=True,
        review_decision="APPROVED",
    )
    assert result == "review 💥 ✔"


# --- is_draft prefix tests ---


def test_planned_draft_shows_construction_emoji() -> None:
    """Planned stage with draft PR shows construction emoji prefix."""
    result = format_lifecycle_with_status(
        "[dim]planned[/dim]",
        is_draft=True,
        has_conflicts=None,
        review_decision=None,
    )
    assert result == "[dim]planned 🚧[/dim]"


def test_planned_published_shows_eyes_emoji() -> None:
    """Planned stage with published PR shows eyes emoji prefix."""
    result = format_lifecycle_with_status(
        "[dim]planned[/dim]",
        is_draft=False,
        has_conflicts=None,
        review_decision=None,
    )
    assert result == "[dim]planned 👀[/dim]"


def test_implementing_draft_shows_construction_emoji() -> None:
    """Implementing stage with draft PR shows construction emoji prefix."""
    result = format_lifecycle_with_status(
        "[yellow]impling[/yellow]",
        is_draft=True,
        has_conflicts=None,
        review_decision=None,
    )
    assert result == "[yellow]impling 🚧[/yellow]"


def test_implementing_published_shows_eyes_emoji() -> None:
    """Implementing stage with published PR shows eyes emoji prefix."""
    result = format_lifecycle_with_status(
        "[yellow]impling[/yellow]",
        is_draft=False,
        has_conflicts=None,
        review_decision=None,
    )
    assert result == "[yellow]impling 👀[/yellow]"


def test_review_published_shows_eyes_emoji() -> None:
    """Review stage with published PR shows eyes emoji prefix."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        is_draft=False,
        has_conflicts=False,
        review_decision=None,
    )
    assert result == "[cyan]review 👀[/cyan]"


def test_review_published_with_conflicts_shows_both() -> None:
    """Review stage with published PR and conflicts shows prefix and suffix."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        is_draft=False,
        has_conflicts=True,
        review_decision=None,
    )
    assert result == "[cyan]review 👀 💥[/cyan]"


def test_review_published_with_approved_shows_both() -> None:
    """Review stage with published PR and approval shows prefix and suffix."""
    result = format_lifecycle_with_status(
        "[cyan]review[/cyan]",
        is_draft=False,
        has_conflicts=False,
        review_decision="APPROVED",
    )
    assert result == "[cyan]review 👀 ✔[/cyan]"


def test_merged_draft_false_no_prefix() -> None:
    """Merged stage does not show draft/published prefix."""
    result = format_lifecycle_with_status(
        "[green]merged[/green]",
        is_draft=False,
        has_conflicts=None,
        review_decision=None,
    )
    assert result == "[green]merged[/green]"


def test_closed_draft_false_no_prefix() -> None:
    """Closed stage does not show draft/published prefix."""
    result = format_lifecycle_with_status(
        "[dim red]closed[/dim red]",
        is_draft=False,
        has_conflicts=None,
        review_decision=None,
    )
    assert result == "[dim red]closed[/dim red]"


def test_plain_text_stage_with_draft_prefix() -> None:
    """Plain text stage (no Rich markup) prepends draft prefix."""
    result = format_lifecycle_with_status(
        "review",
        is_draft=False,
        has_conflicts=False,
        review_decision=None,
    )
    assert result == "review 👀"


def test_implementing_draft_with_conflicts_shows_both() -> None:
    """Implementing draft with conflicts shows prefix and suffix."""
    result = format_lifecycle_with_status(
        "[yellow]impling[/yellow]",
        is_draft=True,
        has_conflicts=True,
        review_decision=None,
    )
    assert result == "[yellow]impling 🚧 💥[/yellow]"


# --- Ready-to-merge (rocket) indicator tests ---


def test_implemented_checks_passing_no_comments_shows_rocket() -> None:
    """Implemented with passing checks and no unresolved comments shows rocket."""
    result = format_lifecycle_with_status(
        "[cyan]impld[/cyan]",
        is_draft=None,
        has_conflicts=False,
        review_decision=None,
        checks_passing=True,
        has_unresolved_comments=False,
    )
    assert result == "[cyan]impld 🚀[/cyan]"


def test_implemented_checks_failing_no_rocket() -> None:
    """Implemented with failing checks does not show rocket."""
    result = format_lifecycle_with_status(
        "[cyan]impld[/cyan]",
        is_draft=None,
        has_conflicts=False,
        review_decision=None,
        checks_passing=False,
        has_unresolved_comments=False,
    )
    assert result == "[cyan]impld[/cyan]"


def test_implemented_checks_none_no_rocket() -> None:
    """Implemented with unknown checks does not show rocket."""
    result = format_lifecycle_with_status(
        "[cyan]impld[/cyan]",
        is_draft=None,
        has_conflicts=False,
        review_decision=None,
        checks_passing=None,
        has_unresolved_comments=False,
    )
    assert result == "[cyan]impld[/cyan]"


def test_implemented_unresolved_comments_no_rocket() -> None:
    """Implemented with unresolved comments does not show rocket."""
    result = format_lifecycle_with_status(
        "[cyan]impld[/cyan]",
        is_draft=None,
        has_conflicts=False,
        review_decision=None,
        checks_passing=True,
        has_unresolved_comments=True,
    )
    assert result == "[cyan]impld[/cyan]"


def test_implemented_conflicts_no_rocket() -> None:
    """Implemented with conflicts shows conflict emoji, not rocket."""
    result = format_lifecycle_with_status(
        "[cyan]impld[/cyan]",
        is_draft=None,
        has_conflicts=True,
        review_decision=None,
        checks_passing=True,
        has_unresolved_comments=False,
    )
    assert result == "[cyan]impld 💥[/cyan]"


def test_implementing_checks_passing_no_rocket() -> None:
    """Implementing stage does not show rocket even with passing checks."""
    result = format_lifecycle_with_status(
        "[yellow]impling[/yellow]",
        is_draft=None,
        has_conflicts=False,
        review_decision=None,
        checks_passing=True,
        has_unresolved_comments=False,
    )
    assert result == "[yellow]impling[/yellow]"


# --- Workflow run inference tests ---


def test_planned_with_workflow_run_upgrades_to_implementing() -> None:
    """Header "planned" with workflow run upgrades to implementing."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "planned"})
    assert compute_lifecycle_display(plan, has_workflow_run=True) == "[yellow]impling[/yellow]"


def test_planned_without_workflow_run_stays_planned() -> None:
    """Header "planned" without workflow run stays planned."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "planned"})
    assert compute_lifecycle_display(plan, has_workflow_run=False) == "[dim]planned[/dim]"


def test_inferred_planned_with_workflow_run_upgrades_to_implementing() -> None:
    """Draft + OPEN (inferred planned) with workflow run upgrades to implementing."""
    plan = _make_plan(metadata={"is_draft": True, "pr_state": "OPEN"})
    assert compute_lifecycle_display(plan, has_workflow_run=True) == "[yellow]impling[/yellow]"


def test_implementing_with_workflow_run_stays_implementing() -> None:
    """Already implementing with workflow run stays implementing (no double-upgrade)."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "implementing"})
    assert compute_lifecycle_display(plan, has_workflow_run=True) == "[yellow]impling[/yellow]"


def test_implemented_with_workflow_run_stays_implemented() -> None:
    """Past implementing stage with workflow run does not downgrade."""
    plan = _make_plan(header_fields={LIFECYCLE_STAGE: "implemented"})
    assert compute_lifecycle_display(plan, has_workflow_run=True) == "[cyan]impld[/cyan]"


def test_no_stage_with_workflow_run_returns_dash() -> None:
    """No stage resolved with workflow run still returns dash."""
    plan = _make_plan()
    assert compute_lifecycle_display(plan, has_workflow_run=True) == "-"
