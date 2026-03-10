"""Unit tests for get_plan_info exec command.

Tests backend-aware plan info retrieval using PlannedPRBackend and FakeLocalGitHub.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_plan_info import get_plan_info
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.time import FakeTime
from tests.fakes.tests.shared_context import context_for_test


def _create_backend_with_plan(
    *, title: str = "Test Plan Title", content: str = "# Plan Content"
) -> tuple[PlannedPRBackend, FakeLocalGitHub, str]:
    """Create a PlannedPRBackend with a single plan.

    Returns:
        Tuple of (backend, fake_github, plan_id).
    """
    fake_github = FakeLocalGitHub()
    backend = PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime())

    result = backend.create_plan(
        repo_root=Path("/repo"),
        title=title,
        content=content,
        labels=("erk-plan",),
        metadata={"branch_name": "test-branch-info"},
        summary=None,
    )
    return backend, fake_github, result.pr_id


# ============================================================================
# Success Cases
# ============================================================================


def test_get_plan_info_success() -> None:
    """Test successful plan info retrieval from PlannedPRBackend."""
    backend, fake_github, plan_id = _create_backend_with_plan()
    runner = CliRunner()

    result = runner.invoke(
        get_plan_info,
        [plan_id],
        obj=context_for_test(
            github=fake_github,
            plan_store=backend,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == plan_id
    assert "Test Plan Title" in output["title"]
    assert output["state"] == "OPEN"
    assert "erk-plan" in output["labels"]
    assert isinstance(output["url"], str)
    assert output["backend"] == "github-draft-pr"


def test_get_plan_info_includes_objective_id() -> None:
    """Test that objective_id is included in the response."""
    backend, fake_github, plan_id = _create_backend_with_plan()
    runner = CliRunner()

    result = runner.invoke(
        get_plan_info,
        [plan_id],
        obj=context_for_test(
            github=fake_github,
            plan_store=backend,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert "objective_id" in output


# ============================================================================
# --include-body flag
# ============================================================================


def test_get_plan_info_include_body() -> None:
    """Test that --include-body adds body field to the response."""
    backend, fake_github, plan_id = _create_backend_with_plan()
    runner = CliRunner()

    result = runner.invoke(
        get_plan_info,
        [plan_id, "--include-body"],
        obj=context_for_test(
            github=fake_github,
            plan_store=backend,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "body" in output
    assert isinstance(output["body"], str)


def test_get_plan_info_excludes_body_by_default() -> None:
    """Test that body field is NOT present without --include-body."""
    backend, fake_github, plan_id = _create_backend_with_plan()
    runner = CliRunner()

    result = runner.invoke(
        get_plan_info,
        [plan_id],
        obj=context_for_test(
            github=fake_github,
            plan_store=backend,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "body" not in output


# ============================================================================
# Error Cases
# ============================================================================


def test_get_plan_info_not_found() -> None:
    """Test error when plan doesn't exist."""
    runner = CliRunner()

    result = runner.invoke(
        get_plan_info,
        ["9999"],
        obj=context_for_test(),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "plan_not_found"
    assert "#9999" in output["message"]
