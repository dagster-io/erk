"""Unit tests for push-and-create-pr exec script."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.push_and_create_pr import push_and_create_pr
from erk.core.context import context_for_test
from erk_shared.gateway.git.abc import BranchDivergence
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails


def _pr_details(
    *,
    number: int = 42,
    branch: str = "feature",
    base: str = "main",
    body: str = "",
) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title="Test PR",
        body=body,
        state="OPEN",
        base_ref_name=base,
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )


def test_success_json_output(tmp_path: Path) -> None:
    """Successful run outputs JSON with success=True and pr info."""
    pr = _pr_details(number=42, branch="feature")
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
        commits_ahead={(tmp_path, "main"): 1},
        branch_divergence={
            (tmp_path, "feature", "origin"): BranchDivergence(
                is_diverged=False,
                ahead=1,
                behind=0,
            )
        },
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    ctx = context_for_test(git=fake_git, github=fake_github, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(push_and_create_pr, [], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["branch"] == "feature"
    assert output["pr"]["number"] == 42
    assert output["pr"]["url"] == "https://github.com/owner/repo/pull/42"


def test_error_json_output_on_no_branch(tmp_path: Path) -> None:
    """Detached HEAD outputs JSON with success=False and error info."""
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: None},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(push_and_create_pr, [], obj=ctx)

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"]["error_type"] == "no_branch"
    assert output["error"]["phase"] == "prepare"


def test_force_flag_propagation(tmp_path: Path) -> None:
    """--force flag is passed through to the pipeline."""
    pr = _pr_details(number=42, branch="feature")
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
        commits_ahead={(tmp_path, "main"): 3},
        branch_divergence={
            (tmp_path, "feature", "origin"): BranchDivergence(
                is_diverged=True,
                ahead=3,
                behind=2,
            )
        },
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    ctx = context_for_test(git=fake_git, github=fake_github, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(push_and_create_pr, ["--force"], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr"]["number"] == 42


def test_no_graphite_flag(tmp_path: Path) -> None:
    """--no-graphite skips Graphite in favor of git + gh."""
    pr = _pr_details(number=42, branch="feature")
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
        commits_ahead={(tmp_path, "main"): 1},
        branch_divergence={
            (tmp_path, "feature", "origin"): BranchDivergence(
                is_diverged=False,
                ahead=1,
                behind=0,
            )
        },
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    ctx = context_for_test(git=fake_git, github=fake_github, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(push_and_create_pr, ["--no-graphite"], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["graphite_url"] is None


def test_no_commits_returns_error(tmp_path: Path) -> None:
    """Zero commits ahead of parent => exit code 1 with error JSON."""
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
        commits_ahead={(tmp_path, "main"): 0},
        branch_divergence={
            (tmp_path, "feature", "origin"): BranchDivergence(
                is_diverged=False,
                ahead=0,
                behind=0,
            )
        },
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(push_and_create_pr, [], obj=ctx)

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"]["error_type"] == "no_commits"
