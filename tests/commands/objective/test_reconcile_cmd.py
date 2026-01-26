"""Tests for erk objective reconcile command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import context_for_test
from erk_shared.context.types import RepoContext
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.prompt_executor.fake import FakePromptExecutor


def _create_issue(
    number: int,
    *,
    labels: list[str],
    title: str | None = None,
    body: str = "Test body",
) -> IssueInfo:
    """Create a test issue with the given labels."""
    return IssueInfo(
        number=number,
        title=title or f"Test Objective #{number}",
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=labels,
        assignees=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        author="testuser",
    )


def _create_repo_context(tmp_path: Path) -> RepoContext:
    """Create a RepoContext for testing."""
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    return RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )


def test_reconcile_dry_run_shows_planned_actions(tmp_path: Path) -> None:
    """Test that reconcile with --dry-run shows planned actions for objectives."""
    issue = _create_issue(
        5934,
        labels=["erk-objective", "auto-advance"],
        title="Test Objective",
        body="Test objective body with roadmap",
    )
    issues_ops = FakeGitHubIssues(username="testuser", issues={5934: issue})
    prompt_executor = FakePromptExecutor(
        output="""NEXT_STEP: yes
STEP_ID: 3.1
DESCRIPTION: Create ReconcileAction type
PHASE: Phase 3: CLI Command
REASON: Previous steps complete"""
    )

    ctx = context_for_test(
        issues=issues_ops,
        prompt_executor=prompt_executor,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "reconcile", "--dry-run"], obj=ctx)

    assert result.exit_code == 0
    assert "Reconciling auto-advance objectives" in result.output
    assert "#5934" in result.output
    assert "Test Objective" in result.output
    assert "create_plan" in result.output
    assert "3.1" in result.output
    assert "Would create 1 plan(s)" in result.output


def test_reconcile_no_auto_advance_objectives(tmp_path: Path) -> None:
    """Test that reconcile handles empty list gracefully."""
    # No objectives with auto-advance label
    issue = _create_issue(
        5934,
        labels=["erk-objective"],  # Missing auto-advance
        title="Regular Objective",
    )
    issues_ops = FakeGitHubIssues(username="testuser", issues={5934: issue})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "reconcile", "--dry-run"], obj=ctx)

    assert result.exit_code == 0
    assert "No auto-advance objectives found" in result.output


def test_reconcile_inference_error(tmp_path: Path) -> None:
    """Test that reconcile handles LLM errors gracefully."""
    issue = _create_issue(
        5934,
        labels=["erk-objective", "auto-advance"],
        title="Test Objective",
    )
    issues_ops = FakeGitHubIssues(username="testuser", issues={5934: issue})
    prompt_executor = FakePromptExecutor(
        should_fail=True,
        error="Rate limited by API",
    )

    ctx = context_for_test(
        issues=issues_ops,
        prompt_executor=prompt_executor,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "reconcile", "--dry-run"], obj=ctx)

    assert result.exit_code == 0
    assert "#5934" in result.output
    assert "error" in result.output
    assert "Rate limited by API" in result.output
    assert "No actions needed" in result.output


def test_reconcile_mixed_results(tmp_path: Path) -> None:
    """Test reconcile with multiple objectives showing different action types."""
    # Create issues dict directly with different objectives
    issue1 = _create_issue(
        5934,
        labels=["erk-objective", "auto-advance"],
        title="Active Objective",
        body="Roadmap with pending steps",
    )
    issue2 = _create_issue(
        5940,
        labels=["erk-objective", "auto-advance"],
        title="Completed Objective",
        body="Roadmap with all steps done",
    )
    issues_ops = FakeGitHubIssues(
        username="testuser",
        issues={5934: issue1, 5940: issue2},
    )

    # First call returns create_plan, second returns none
    # Since FakePromptExecutor only returns one configured output, we need to
    # test with a single objective. Multiple objectives need more sophisticated
    # fake setup. For now, test with single objective.
    prompt_executor = FakePromptExecutor(
        output="""NEXT_STEP: yes
STEP_ID: 2.1
DESCRIPTION: Create type
PHASE: Phase 2
REASON: Phase 1 complete"""
    )

    ctx = context_for_test(
        issues=issues_ops,
        prompt_executor=prompt_executor,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "reconcile", "--dry-run"], obj=ctx)

    assert result.exit_code == 0
    # Both objectives should be listed
    assert "#5934" in result.output
    assert "#5940" in result.output
    # At least some action should be shown
    assert "create_plan" in result.output


OBJECTIVE_WITH_ROADMAP = """# Test Objective

## Goal

Test objective for reconciler.

## Roadmap

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 4.1 | Generate plan content | pending | |
| 4.2 | Create plan issue | pending | |
"""

GENERATED_PLAN_OUTPUT = """# Step 4.1: Generate Plan Content

**Part of Objective #5934, Step 4.1**

## Goal

Generate plan content from objective step.

## Implementation

Do the thing.
"""

UPDATED_ROADMAP_BODY = """# Test Objective

## Goal

Test objective for reconciler.

## Roadmap

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 4.1 | Generate plan content | pending | plan #6001 |
| 4.2 | Create plan issue | pending | |
"""

INFERENCE_OUTPUT = """NEXT_STEP: yes
STEP_ID: 4.1
DESCRIPTION: Generate plan content
PHASE: Phase 4
REASON: No previous steps"""


def test_reconcile_live_creates_plan_and_updates_roadmap(tmp_path: Path) -> None:
    """Test that live reconcile creates plan issue and updates objective roadmap."""
    issue = _create_issue(
        5934,
        labels=["erk-objective", "auto-advance"],
        title="Test Objective",
        body=OBJECTIVE_WITH_ROADMAP,
    )
    issues_ops = FakeGitHubIssues(
        username="testuser",
        issues={5934: issue},
        labels={"erk-plan"},  # Pre-create label
        next_issue_number=6001,
    )

    # FakePromptExecutor returns different outputs for sequential calls:
    # First call: determine_action (step inference)
    # Second call: execute_action -> generate_plan_for_step (plan generation)
    # Third call: execute_action -> update_roadmap_with_plan (roadmap update)
    prompt_executor = FakePromptExecutor(
        outputs=[INFERENCE_OUTPUT, GENERATED_PLAN_OUTPUT, UPDATED_ROADMAP_BODY]
    )

    ctx = context_for_test(
        issues=issues_ops,
        prompt_executor=prompt_executor,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "reconcile"], obj=ctx)

    assert result.exit_code == 0
    assert "#5934" in result.output
    assert "create_plan" in result.output
    assert "Created" in result.output
    assert "#6001" in result.output

    # Verify plan issue was created
    assert len(issues_ops.created_issues) == 1

    # Verify objective roadmap was updated with plan reference
    objective_updates = [body for num, body in issues_ops.updated_bodies if num == 5934]
    assert len(objective_updates) == 1
    assert "plan #6001" in objective_updates[0]


def test_reconcile_live_no_actions_when_all_complete(tmp_path: Path) -> None:
    """Test that live reconcile handles no actions gracefully."""
    issue = _create_issue(
        5934,
        labels=["erk-objective", "auto-advance"],
        title="Test Objective",
        body="Completed objective",
    )
    issues_ops = FakeGitHubIssues(username="testuser", issues={5934: issue})

    prompt_executor = FakePromptExecutor(
        output="""NEXT_STEP: no
STEP_ID: none
DESCRIPTION: none
PHASE: none
REASON: All steps complete"""
    )

    ctx = context_for_test(
        issues=issues_ops,
        prompt_executor=prompt_executor,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "reconcile"], obj=ctx)

    assert result.exit_code == 0
    assert "No actions needed" in result.output
    # No plan issues should have been created
    assert len(issues_ops.created_issues) == 0


def test_reconcile_live_reports_errors(tmp_path: Path) -> None:
    """Test that live reconcile reports errors with non-zero exit code."""
    issue = _create_issue(
        5934,
        labels=["erk-objective", "auto-advance"],
        title="Test Objective",
        body="Test body",
    )
    issues_ops = FakeGitHubIssues(username="testuser", issues={5934: issue})

    prompt_executor = FakePromptExecutor(
        should_fail=True,
        error="Rate limited by API",
    )

    ctx = context_for_test(
        issues=issues_ops,
        prompt_executor=prompt_executor,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "reconcile"], obj=ctx)

    assert result.exit_code == 1
    assert "error" in result.output
    assert "Rate limited by API" in result.output
    assert "error(s) occurred" in result.output


def test_reconcile_alias_rec_works(tmp_path: Path) -> None:
    """Test that 'rec' alias works for reconcile command."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "rec", "--dry-run"], obj=ctx)

    assert result.exit_code == 0
    assert "No auto-advance objectives found" in result.output


def test_reconcile_with_objective_argument(tmp_path: Path) -> None:
    """Test that positional argument targets a specific objective without requiring auto-advance."""
    # Objective without auto-advance label (would normally be skipped)
    issue = _create_issue(
        5934,
        labels=["erk-objective"],  # No auto-advance, but should still work with --objective
        title="Specific Objective",
        body="Test objective body",
    )
    issues_ops = FakeGitHubIssues(username="testuser", issues={5934: issue})
    prompt_executor = FakePromptExecutor(
        output="""NEXT_STEP: yes
STEP_ID: 2.1
DESCRIPTION: Create type
PHASE: Phase 2
REASON: Phase 1 complete"""
    )

    ctx = context_for_test(
        issues=issues_ops,
        prompt_executor=prompt_executor,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "reconcile", "5934", "--dry-run"], obj=ctx)

    assert result.exit_code == 0
    assert "Analyzing objective #5934" in result.output
    assert "#5934" in result.output
    assert "Specific Objective" in result.output
    assert "create_plan" in result.output


def test_reconcile_objective_not_found(tmp_path: Path) -> None:
    """Test that --objective with non-existent issue shows error."""
    # Empty issues - no issue #9999 exists
    issues_ops = FakeGitHubIssues(username="testuser", issues={})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "reconcile", "9999", "--dry-run"], obj=ctx)

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "#9999 not found" in result.output


def test_reconcile_objective_not_erk_objective(tmp_path: Path) -> None:
    """Test that --objective with non-erk-objective issue shows error."""
    # Issue exists but lacks erk-objective label
    issue = _create_issue(
        5934,
        labels=["bug"],  # Not an erk-objective
        title="Regular Bug Issue",
    )
    issues_ops = FakeGitHubIssues(username="testuser", issues={5934: issue})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "reconcile", "5934", "--dry-run"], obj=ctx)

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "not an erk-objective" in result.output
