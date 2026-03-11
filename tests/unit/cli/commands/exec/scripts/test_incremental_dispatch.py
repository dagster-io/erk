"""Unit tests for incremental-dispatch command."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.incremental_dispatch import incremental_dispatch
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.plan_store.planned_pr import GitHubManagedPrBackend
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.graphite import FakeGraphite
from tests.fakes.gateway.time import FakeTime
from tests.fakes.tests.shared_context import context_for_test
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _make_pr(number: int, *, state: str = "OPEN", branch: str = "feature-branch") -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/test-owner/test-repo/pull/{number}",
        title=f"Test PR #{number}",
        body="PR body",
        state=state,
        is_draft=False,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
        labels=["erk-pr"],
    )


def _make_fake_git(repo_root: Path) -> FakeGit:
    """Create a FakeGit with trunk sync requirements satisfied."""
    sha = "abc123"
    return FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "main"},
        branch_heads={"main": sha, "origin/main": sha},
    )


def test_incremental_dispatch_success(tmp_path: Path) -> None:
    """Test successful incremental dispatch."""
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# My Incremental Plan\n\n- Step 1\n- Step 2", encoding="utf-8")

    pr = _make_pr(42, branch="feature/my-feature")
    fake_git = _make_fake_git(tmp_path)
    fake_github = FakeLocalGitHub(pr_details={42: pr})

    runner = CliRunner()
    result = runner.invoke(
        incremental_dispatch,
        ["--plan-file", str(plan_file), "--pr", "42", "--format", "json"],
        obj=ErkContext.for_test(git=fake_git, github=fake_github, repo_root=tmp_path),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output.strip().split("\n")[-1])
    assert output["success"] is True
    assert output["pr_number"] == 42
    assert output["branch_name"] == "feature/my-feature"
    assert "workflow_run_id" in output
    assert "workflow_url" in output

    # Verify impl-context was committed to the branch
    branch_commits = fake_git.commit.branch_commits
    assert len(branch_commits) == 1
    assert branch_commits[0].branch == "feature/my-feature"
    assert ".erk/impl-context/plan.md" in branch_commits[0].files
    assert "My Incremental Plan" in branch_commits[0].files[".erk/impl-context/plan.md"]
    assert ".erk/impl-context/ref.json" in branch_commits[0].files
    assert "Incremental dispatch" in branch_commits[0].message
    assert "My Incremental Plan" in branch_commits[0].message

    # Verify workflow was triggered
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs, _ref = fake_github.triggered_workflows[0]
    assert workflow == "plan-implement.yml"
    assert inputs["pr_number"] == "42"
    assert inputs["branch_name"] == "feature/my-feature"
    assert inputs["plan_backend"] == "planned_pr"


def test_incremental_dispatch_pr_not_found(tmp_path: Path) -> None:
    """Test error when PR does not exist."""
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Plan", encoding="utf-8")

    fake_github = FakeLocalGitHub(pr_details={})

    runner = CliRunner()
    result = runner.invoke(
        incremental_dispatch,
        ["--plan-file", str(plan_file), "--pr", "999", "--format", "json"],
        obj=ErkContext.for_test(github=fake_github, repo_root=tmp_path),
    )

    assert result.exit_code == 1
    output = json.loads(result.output.strip().split("\n")[-1])
    assert output["success"] is False
    assert "not found" in output["error"]


def test_incremental_dispatch_pr_not_open(tmp_path: Path) -> None:
    """Test error when PR is not OPEN."""
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Plan", encoding="utf-8")

    pr = _make_pr(42, state="CLOSED")
    fake_github = FakeLocalGitHub(pr_details={42: pr})

    runner = CliRunner()
    result = runner.invoke(
        incremental_dispatch,
        ["--plan-file", str(plan_file), "--pr", "42", "--format", "json"],
        obj=ErkContext.for_test(github=fake_github, repo_root=tmp_path),
    )

    assert result.exit_code == 1
    output = json.loads(result.output.strip().split("\n")[-1])
    assert output["success"] is False
    assert "CLOSED" in output["error"]


def test_incremental_dispatch_display_format(tmp_path: Path) -> None:
    """Test display output format."""
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Display Plan\n\n- Step 1", encoding="utf-8")

    pr = _make_pr(42, branch="feature/display-test")
    fake_git = _make_fake_git(tmp_path)
    fake_github = FakeLocalGitHub(pr_details={42: pr})

    runner = CliRunner()
    result = runner.invoke(
        incremental_dispatch,
        ["--plan-file", str(plan_file), "--pr", "42", "--format", "display"],
        obj=ErkContext.for_test(git=fake_git, github=fake_github, repo_root=tmp_path),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "Workflow" in result.output


def test_incremental_dispatch_checked_out_branch(tmp_path: Path) -> None:
    """Test dispatch when branch is checked out in a worktree uses reset_hard."""
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Checked Out Plan\n\n- Step 1", encoding="utf-8")

    worktree_path = tmp_path / "worktree"
    pr = _make_pr(42, branch="feature/checked-out")
    remote_sha = "remote123"
    fake_git = FakeGit(
        current_branches={tmp_path: "main", worktree_path: "feature/checked-out"},
        trunk_branches={tmp_path: "main"},
        branch_heads={
            "main": "abc123",
            "origin/main": "abc123",
            "feature/checked-out": "local456",
            "origin/feature/checked-out": remote_sha,
        },
        worktrees={
            tmp_path: [
                WorktreeInfo(path=tmp_path, branch="main", is_root=True),
                WorktreeInfo(path=worktree_path, branch="feature/checked-out"),
            ]
        },
        existing_paths={worktree_path},
    )
    fake_github = FakeLocalGitHub(pr_details={42: pr})
    fake_graphite = FakeGraphite()

    runner = CliRunner()
    ctx = context_for_test(
        git=fake_git, github=fake_github, graphite=fake_graphite, repo_root=tmp_path
    )
    result = runner.invoke(
        incremental_dispatch,
        ["--plan-file", str(plan_file), "--pr", "42", "--format", "json"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output.strip().split("\n")[-1])
    assert output["success"] is True

    # Verify reset_hard was called (not update_local_ref) to keep working tree in sync
    reset_calls = fake_git.branch.reset_hard_calls
    assert len(reset_calls) == 1
    assert reset_calls[0] == (worktree_path, remote_sha)

    # Verify update_local_ref was NOT called for the feature branch
    updated_refs = fake_git.branch.updated_refs
    assert not any(branch == "feature/checked-out" for _, branch, _ in updated_refs)

    # Verify create_branch was NOT called for the feature branch
    created = fake_git.branch.created_branches
    assert all(b[1] != "feature/checked-out" for b in created)

    # Verify retrack_branch() was called with correct arguments
    assert len(fake_graphite.retrack_branch_calls) == 1
    assert fake_graphite.retrack_branch_calls[0] == (tmp_path, "feature/checked-out")

    # Verify files were written to the worktree path
    assert (worktree_path / ".erk/impl-context/plan.md").exists()
    assert (worktree_path / ".erk/impl-context/ref.json").exists()

    # Verify stage_files() was called with the impl-context files
    assert ".erk/impl-context/plan.md" in fake_git.commit.staged_files
    assert ".erk/impl-context/ref.json" in fake_git.commit.staged_files


def test_incremental_dispatch_writes_dispatch_metadata(tmp_path: Path) -> None:
    """Dispatch metadata (run_id, node_id, timestamp) is written to plan-header after dispatch."""
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Metadata Plan\n\n- Step 1", encoding="utf-8")

    branch = "feature/metadata-test"
    plan_header_body = format_plan_header_body_for_test(branch_name=branch)
    pr = PRDetails(
        number=42,
        url="https://github.com/test-owner/test-repo/pull/42",
        title="Test PR #42",
        body=plan_header_body,
        state="OPEN",
        is_draft=True,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
        labels=["erk-pr"],
    )
    fake_git = _make_fake_git(tmp_path)
    prs = {
        branch: PullRequestInfo(
            number=42,
            state="OPEN",
            url=pr.url,
            is_draft=True,
            title=pr.title,
            checks_passing=None,
            owner="test-owner",
            repo="test-repo",
            head_branch=branch,
        ),
    }
    fake_github = FakeLocalGitHub(pr_details={42: pr}, prs=prs)
    plan_store = GitHubManagedPrBackend(fake_github, fake_github.issues, time=FakeTime())

    runner = CliRunner()
    result = runner.invoke(
        incremental_dispatch,
        ["--plan-file", str(plan_file), "--pr", "42", "--format", "json"],
        obj=ErkContext.for_test(
            git=fake_git, github=fake_github, plan_store=plan_store, repo_root=tmp_path
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output.strip().split("\n")[-1])
    assert output["success"] is True

    # Verify dispatch metadata was written to the plan-header
    assert len(fake_github.updated_pr_bodies) >= 1
    _, updated_body = fake_github.updated_pr_bodies[-1]
    assert "last_dispatched_run_id" in updated_body
    assert "last_dispatched_node_id" in updated_body
    assert "last_dispatched_at" in updated_body
