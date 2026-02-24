"""Tests for submit command validation."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import ERK_PLAN_LABEL, submit_cmd
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from tests.commands.submit.conftest import make_plan_body


def test_submit_missing_erk_plan_label(tmp_path: Path) -> None:
    """Test submit rejects PR without erk-plan label."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create PR WITHOUT erk-plan label
    from erk_shared.gateway.github.types import PRDetails

    pr = PRDetails(
        number=123,
        url="https://github.com/test-owner/test-repo/pull/123",
        title="Regular PR",
        body="Not a plan PR",
        state="OPEN",
        is_draft=True,
        base_ref_name="main",
        head_ref_name="plnd/123-regular-pr",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
        labels=("bug",),  # Missing erk-plan label
    )

    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
    )
    fake_github = FakeGitHub(pr_details={123: pr})

    # Need plan_store for the new backend
    from tests.commands.submit.conftest import create_plan, make_plan_body
    from tests.test_utils.plan_helpers import create_plan_store

    plan = create_plan("123", "Regular PR", body=make_plan_body(), labels=["bug"])
    fake_plan_store, _ = create_plan_store({"123": plan}, backend="planned_pr")

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
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 1
    assert "does not have erk-plan label" in result.output
    assert "Cannot submit non-plan PRs" in result.output

    # Verify workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0


def test_submit_closed_pr(tmp_path: Path) -> None:
    """Test submit rejects closed PRs."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create CLOSED PR with erk-plan label
    from erk_shared.gateway.github.types import PRDetails

    pr = PRDetails(
        number=123,
        url="https://github.com/test-owner/test-repo/pull/123",
        title="Implement feature X",
        body=make_plan_body(),
        state="CLOSED",
        is_draft=True,
        base_ref_name="main",
        head_ref_name="plnd/123-implement-feature-x",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
        labels=(ERK_PLAN_LABEL,),
    )

    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
    )
    fake_github = FakeGitHub(pr_details={123: pr})

    # Need plan_store for the new backend
    from tests.commands.submit.conftest import create_plan
    from tests.test_utils.plan_helpers import create_plan_store

    plan = create_plan("123", "Implement feature X", body=make_plan_body())
    fake_plan_store, _ = create_plan_store({"123": plan}, backend="planned_pr")

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
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 1
    assert "is CLOSED" in result.output
    assert "Cannot submit closed PRs" in result.output

    # Verify workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0


def test_submit_pr_not_found(tmp_path: Path) -> None:
    """Test submit handles missing PR gracefully."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Empty pr_details dict - PR 999 doesn't exist
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
    )
    fake_github = FakeGitHub(pr_details={})  # Empty - no PRs

    # Need plan_store for the new backend
    from tests.test_utils.plan_helpers import create_plan_store

    fake_plan_store, _ = create_plan_store({}, backend="planned_pr")

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
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["999"], obj=ctx)

    # Should fail with PR not found error
    assert result.exit_code == 1
    assert "PR #999 not found" in result.output


def test_submit_requires_gh_authentication(tmp_path: Path) -> None:
    """Test submit fails early if gh CLI is not authenticated (LBYL)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create valid PR with erk-plan label
    from erk_shared.gateway.github.types import PRDetails

    pr = PRDetails(
        number=123,
        url="https://github.com/test-owner/test-repo/pull/123",
        title="Implement feature X",
        body=make_plan_body(),
        state="OPEN",
        is_draft=True,
        base_ref_name="main",
        head_ref_name="plnd/123-implement-feature-x",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
        labels=(ERK_PLAN_LABEL,),
    )

    fake_git = FakeGit()
    # Configure FakeGitHub to simulate unauthenticated state
    fake_github = FakeGitHub(authenticated=False, pr_details={123: pr})

    # Need plan_store for the new backend
    from tests.commands.submit.conftest import create_plan
    from tests.test_utils.plan_helpers import create_plan_store

    plan = create_plan("123", "Implement feature X", body=make_plan_body())
    fake_plan_store, _ = create_plan_store({"123": plan}, backend="planned_pr")

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
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    # Should fail early with authentication error (LBYL)
    assert result.exit_code == 1
    assert "Error: GitHub CLI (gh) is not authenticated" in result.output
    assert "gh auth login" in result.output

    # Verify workflow was NOT triggered (failure happened before workflow dispatch)
    assert len(fake_github.triggered_workflows) == 0
