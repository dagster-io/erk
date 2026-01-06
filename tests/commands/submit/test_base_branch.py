"""Tests for custom base branch handling in submit."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import ERK_PLAN_LABEL, submit_cmd
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from tests.commands.submit.conftest import create_plan, make_plan_body


def test_submit_with_custom_base_branch(tmp_path: Path) -> None:
    """Test submit creates PR with custom base branch when --base is specified."""
    plan = create_plan("123", "Implement feature X")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    from tests.test_utils.plan_helpers import create_plan_store_with_plans

    fake_plan_store, fake_github_issues = create_plan_store_with_plans({"123": plan})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
        # Custom feature branch exists on remote
        remote_branches={repo_root: ["origin/feature/parent-branch"]},
    )
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "--base", "feature/parent-branch"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "issue(s) submitted successfully!" in result.output

    # Verify PR was created with custom base branch
    assert len(fake_github.created_prs) == 1
    branch_name, title, body, base, draft = fake_github.created_prs[0]
    assert base == "feature/parent-branch"  # NOT "master"

    # Verify branch was created via git (FakeGit tracks created branches)
    assert len(fake_git.created_branches) == 1
    created_repo, created_branch, created_base = fake_git.created_branches[0]
    assert created_repo == repo_root
    assert created_base == "origin/feature/parent-branch"


def test_submit_with_invalid_base_branch(tmp_path: Path) -> None:
    """Test submit fails early when --base branch doesn't exist on remote (LBYL)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue (we won't get to validation because base branch check fails first)
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body=make_plan_body(),
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
        # "nonexistent-branch" does NOT exist on remote
        remote_branches={repo_root: []},
    )
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "--base", "nonexistent-branch"], obj=ctx)

    # Should fail early with error (LBYL)
    assert result.exit_code == 1
    assert "Error: Base branch 'nonexistent-branch' does not exist on remote" in result.output

    # Verify workflow was NOT triggered (failure happened before workflow dispatch)
    assert len(fake_github.triggered_workflows) == 0


def test_submit_passes_base_branch_in_workflow_inputs(tmp_path: Path) -> None:
    """Test submit passes base_branch in workflow inputs for stacked branch support.

    The base_branch is used by the remote worker to rebase onto the correct parent
    branch (not always trunk) when resolving merge conflicts.
    """
    plan = create_plan("456", "Implement stacked feature")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    from tests.test_utils.plan_helpers import create_plan_store_with_plans

    fake_plan_store, fake_github_issues = create_plan_store_with_plans({"456": plan})
    fake_git = FakeGit(
        current_branches={repo_root: "feature-parent"},
        trunk_branches={repo_root: "master"},
        # Parent branch exists on remote
        remote_branches={repo_root: ["origin/feature-parent"]},
    )
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    # Submit from feature-parent (current branch is used as base by default)
    result = runner.invoke(submit_cmd, ["456"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify workflow was triggered with base_branch in inputs
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    assert workflow == "erk-impl.yml"
    assert inputs["issue_number"] == "456"
    # CRITICAL: base_branch must be passed to workflow for stacked PR support
    assert "base_branch" in inputs
    assert inputs["base_branch"] == "feature-parent"


def test_submit_with_custom_base_passes_in_workflow_inputs(tmp_path: Path) -> None:
    """Test submit with --base passes custom base_branch in workflow inputs."""
    plan = create_plan("789", "Implement child feature")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    from tests.test_utils.plan_helpers import create_plan_store_with_plans

    fake_plan_store, fake_github_issues = create_plan_store_with_plans({"789": plan})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
        # Custom parent branch exists on remote
        remote_branches={repo_root: ["origin/feature-parent"]},
    )
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["789", "--base", "feature-parent"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify workflow was triggered with custom base_branch
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    # CRITICAL: Custom base_branch must be passed for stacked PR rebase support
    assert inputs["base_branch"] == "feature-parent"
