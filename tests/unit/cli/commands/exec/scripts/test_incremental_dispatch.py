"""Unit tests for incremental-dispatch command."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.incremental_dispatch import incremental_dispatch
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails


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
    fake_github = FakeGitHub(pr_details={42: pr})

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

    # Verify workflow was triggered
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs, _ref = fake_github.triggered_workflows[0]
    assert workflow == "plan-implement.yml"
    assert inputs["plan_id"] == "42"
    assert inputs["branch_name"] == "feature/my-feature"
    assert inputs["plan_backend"] == "planned_pr"


def test_incremental_dispatch_pr_not_found(tmp_path: Path) -> None:
    """Test error when PR does not exist."""
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Plan", encoding="utf-8")

    fake_github = FakeGitHub(pr_details={})

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
    fake_github = FakeGitHub(pr_details={42: pr})

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
    fake_github = FakeGitHub(pr_details={42: pr})

    runner = CliRunner()
    result = runner.invoke(
        incremental_dispatch,
        ["--plan-file", str(plan_file), "--pr", "42", "--format", "display"],
        obj=ErkContext.for_test(git=fake_git, github=fake_github, repo_root=tmp_path),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "Workflow" in result.output
