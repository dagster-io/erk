"""Unit tests for shared PR command helpers: recover_plan_header and assemble_pr_body."""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.pr.shared import assemble_pr_body, recover_plan_header
from erk.core.plan_context_provider import PlanContext
from erk_shared.gateway.github.metadata.core import find_metadata_block, render_metadata_block
from erk_shared.gateway.github.metadata.types import MetadataBlock
from erk_shared.gateway.github.types import PRDetails
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from erk_shared.plan_store.planned_pr_lifecycle import build_plan_stage_body
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.time import FakeTime
from tests.fakes.tests.shared_context import context_for_test
from tests.test_utils.plan_helpers import format_plan_header_body_for_test

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pr_with_plan_header(
    *,
    number: int = 100,
    author: str = "alice",
    lifecycle_stage: str | None = None,
) -> PRDetails:
    """Create a PRDetails with a valid plan-header metadata block."""
    metadata_body = format_plan_header_body_for_test(
        created_by=author,
        lifecycle_stage=lifecycle_stage,
    )
    plan_content = "# Plan\n\nDo the thing."
    pr_body = build_plan_stage_body(metadata_body, plan_content, summary=None)
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=f"Plan #{number}",
        body=pr_body,
        state="OPEN",
        is_draft=True,
        base_ref_name="main",
        head_ref_name=f"plan-{number}",
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="owner",
        repo="repo",
        author=author,
        labels=("erk-pr",),
    )


def _pr_without_plan_header(
    *,
    number: int = 100,
    author: str = "alice",
) -> PRDetails:
    """Create a PRDetails where the plan-header has been destroyed."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=f"Plan #{number}",
        body="Body without plan-header (destroyed by gh pr edit)",
        state="OPEN",
        is_draft=True,
        base_ref_name="main",
        head_ref_name=f"plan-{number}",
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="owner",
        repo="repo",
        author=author,
        labels=("erk-pr",),
        created_at=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
    )


def _backend_from_pr(pr: PRDetails) -> tuple[PlannedPRBackend, FakeLocalGitHub]:
    """Create PlannedPRBackend from a single PRDetails."""
    fake_github = FakeLocalGitHub(pr_details={pr.number: pr})
    backend = PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime())
    return backend, fake_github


# ---------------------------------------------------------------------------
# recover_plan_header tests
# ---------------------------------------------------------------------------


def test_recover_returns_none_for_missing_plan(tmp_path: Path) -> None:
    """Returns None when the plan does not exist in the backend."""
    ctx = context_for_test(cwd=tmp_path)

    result = recover_plan_header(ctx, repo_root=tmp_path, plan_id="999")

    assert result is None


def test_recover_uses_header_fields_when_present(tmp_path: Path) -> None:
    """Returns MetadataBlock from header_fields when plan-header is intact."""
    pr = _pr_with_plan_header(number=100, author="alice", lifecycle_stage="impl")
    backend, _fg = _backend_from_pr(pr)
    ctx = context_for_test(cwd=tmp_path, plan_store=backend)

    result = recover_plan_header(ctx, repo_root=tmp_path, plan_id="100")

    assert result is not None
    assert result.key == "plan-header"
    assert result.data["schema_version"] == "2"
    assert result.data["created_by"] == "alice"
    assert result.data["lifecycle_stage"] == "impl"


def test_recover_constructs_minimal_header_when_destroyed(tmp_path: Path) -> None:
    """Constructs minimal plan-header from PR metadata when header is gone."""
    pr = _pr_without_plan_header(number=100, author="alice")
    backend, _fg = _backend_from_pr(pr)
    ctx = context_for_test(cwd=tmp_path, plan_store=backend)

    result = recover_plan_header(ctx, repo_root=tmp_path, plan_id="100")

    assert result is not None
    assert result.key == "plan-header"
    assert result.data["schema_version"] == "2"
    assert result.data["created_at"] == "2024-06-01T12:00:00+00:00"
    assert result.data["created_by"] == "alice"


def test_recover_uses_unknown_when_author_empty(tmp_path: Path) -> None:
    """Falls back to 'unknown' when PR author is empty string."""
    pr = _pr_without_plan_header(number=100, author="")
    backend, _fg = _backend_from_pr(pr)
    ctx = context_for_test(cwd=tmp_path, plan_store=backend)

    result = recover_plan_header(ctx, repo_root=tmp_path, plan_id="100")

    assert result is not None
    assert result.data["created_by"] == "unknown"


# ---------------------------------------------------------------------------
# assemble_pr_body with recovered_plan_header tests
# ---------------------------------------------------------------------------


def test_existing_header_takes_precedence_over_recovery() -> None:
    """When existing_pr_body has a plan-header, recovered_plan_header is ignored."""
    original_header = MetadataBlock(
        key="plan-header",
        data={
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00+00:00",
            "created_by": "original-user",
        },
    )
    existing_body = "Some content\n\n" + render_metadata_block(original_header)

    recovered = MetadataBlock(
        key="plan-header",
        data={
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00+00:00",
            "created_by": "recovered-user",
        },
    )

    result = assemble_pr_body(
        body="New body",
        plan_context=None,
        pr_number=42,
        header="",
        existing_pr_body=existing_body,
        recovered_plan_header=recovered,
    )

    assert "original-user" in result
    assert "recovered-user" not in result


def test_recovery_used_when_header_missing() -> None:
    """When existing_pr_body lacks plan-header, recovered_plan_header is used."""
    recovered = MetadataBlock(
        key="plan-header",
        data={
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00+00:00",
            "created_by": "recovered-user",
        },
    )

    result = assemble_pr_body(
        body="New body",
        plan_context=None,
        pr_number=42,
        header="",
        existing_pr_body="Body without plan-header",
        recovered_plan_header=recovered,
    )

    block = find_metadata_block(result, "plan-header")
    assert block is not None
    assert block.data["created_by"] == "recovered-user"


def test_no_header_no_recovery_produces_no_plan_header() -> None:
    """When both existing header and recovery are absent, no plan-header in output."""
    result = assemble_pr_body(
        body="New body",
        plan_context=None,
        pr_number=42,
        header="",
        existing_pr_body="Body without plan-header",
        recovered_plan_header=None,
    )

    block = find_metadata_block(result, "plan-header")
    assert block is None


# ---------------------------------------------------------------------------
# Objective link insertion tests
# ---------------------------------------------------------------------------


def _plan_context(*, objective_summary: str | None = None) -> PlanContext:
    """Create a minimal PlanContext for objective link tests."""
    return PlanContext(
        plan_id="100",
        plan_content="# Plan\n\nDo the thing.",
        objective_summary=objective_summary,
    )


def test_objective_link_inserted_before_key_changes() -> None:
    """Objective link appears between summary and Key Changes heading."""
    body = "Summary paragraph.\n\n## Key Changes\n- Item 1"
    plan_context = _plan_context(objective_summary="Objective #9009: Agent-Friendly CLI")

    result = assemble_pr_body(
        body=body,
        plan_context=plan_context,
        pr_number=42,
        header="",
        existing_pr_body="",
        recovered_plan_header=None,
    )

    objective_pos = result.find("**Objective #9009:** Agent-Friendly CLI")
    key_changes_pos = result.find("## Key Changes")
    assert objective_pos != -1, "Objective link not found in output"
    assert key_changes_pos != -1, "Key Changes heading not found in output"
    assert objective_pos < key_changes_pos


def test_objective_link_appended_when_no_key_changes() -> None:
    """Objective link appended after body when Key Changes heading absent."""
    body = "Summary paragraph only."
    plan_context = _plan_context(objective_summary="Objective #9009: Agent-Friendly CLI")

    result = assemble_pr_body(
        body=body,
        plan_context=plan_context,
        pr_number=42,
        header="",
        existing_pr_body="",
        recovered_plan_header=None,
    )

    assert "**Objective #9009:** Agent-Friendly CLI" in result


def test_no_objective_link_when_summary_is_none() -> None:
    """No objective link when objective_summary is None."""
    body = "Summary paragraph.\n\n## Key Changes\n- Item 1"
    plan_context = _plan_context(objective_summary=None)

    result = assemble_pr_body(
        body=body,
        plan_context=plan_context,
        pr_number=42,
        header="",
        existing_pr_body="",
        recovered_plan_header=None,
    )

    assert "**Objective" not in result


def test_no_objective_link_without_plan_context() -> None:
    """No objective link when plan_context is None."""
    body = "Summary paragraph.\n\n## Key Changes\n- Item 1"

    result = assemble_pr_body(
        body=body,
        plan_context=None,
        pr_number=42,
        header="",
        existing_pr_body="",
        recovered_plan_header=None,
    )

    assert "**Objective" not in result
