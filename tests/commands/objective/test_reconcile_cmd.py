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


def test_reconcile_without_dry_run_shows_error() -> None:
    """Test that running without --dry-run shows not implemented message."""
    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "reconcile"])

    assert result.exit_code == 1
    assert "Live execution not yet implemented" in result.output
    assert "--dry-run" in result.output


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


def test_reconcile_with_objective_option(tmp_path: Path) -> None:
    """Test that --objective targets a specific objective without requiring auto-advance."""
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
    result = runner.invoke(
        cli, ["objective", "reconcile", "--dry-run", "--objective", "5934"], obj=ctx
    )

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
    result = runner.invoke(
        cli, ["objective", "reconcile", "--dry-run", "--objective", "9999"], obj=ctx
    )

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
    result = runner.invoke(
        cli, ["objective", "reconcile", "--dry-run", "--objective", "5934"], obj=ctx
    )

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "not an erk-objective" in result.output
