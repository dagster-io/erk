"""Tests for erk objective reconcile command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import context_for_test
from erk_shared.context.types import RepoContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo


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


def test_reconcile_objective_not_found(tmp_path: Path) -> None:
    """Test that reconcile with non-existent issue shows error."""
    # Empty issues - no issue #9999 exists
    issues_ops = FakeGitHubIssues(username="testuser", issues={})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "reconcile", "9999"], obj=ctx)

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "#9999 not found" in result.output


def test_reconcile_objective_not_erk_objective(tmp_path: Path) -> None:
    """Test that reconcile with non-erk-objective issue shows error."""
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
    result = runner.invoke(cli, ["objective", "reconcile", "5934"], obj=ctx)

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "not an erk-objective" in result.output


def test_reconcile_requires_objective_argument(tmp_path: Path) -> None:
    """Test that reconcile without argument shows usage error."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        repo=_create_repo_context(tmp_path),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["objective", "reconcile"], obj=ctx)

    assert result.exit_code == 2
    assert "Missing argument" in result.output or "OBJECTIVE" in result.output
