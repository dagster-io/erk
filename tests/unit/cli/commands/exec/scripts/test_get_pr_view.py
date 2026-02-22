"""Unit tests for get-pr-view command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_pr_view import get_pr_view
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails


def _make_pr_details(
    *,
    number: int,
    head_ref_name: str,
    title: str = "Test PR",
    body: str = "Test body",
    state: str = "OPEN",
    is_draft: bool = False,
    base_ref_name: str = "master",
    labels: tuple[str, ...] = (),
    author: str = "testuser",
) -> PRDetails:
    """Create a test PRDetails with sensible defaults."""
    now = datetime.now(UTC)
    return PRDetails(
        number=number,
        url=f"https://github.com/test/repo/pull/{number}",
        title=title,
        body=body,
        state=state,
        is_draft=is_draft,
        base_ref_name=base_ref_name,
        head_ref_name=head_ref_name,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test",
        repo="repo",
        labels=labels,
        created_at=now,
        updated_at=now,
        author=author,
    )


def test_get_pr_view_by_number() -> None:
    """Test direct PR number lookup returns all expected fields."""
    pr = _make_pr_details(number=123, head_ref_name="feature-branch", title="My PR", body="PR body")
    fake_gh = FakeGitHub(pr_details={123: pr})
    runner = CliRunner()

    result = runner.invoke(
        get_pr_view,
        ["123"],
        obj=ErkContext.for_test(github=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["number"] == 123
    assert output["title"] == "My PR"
    assert output["body"] == "PR body"
    assert output["url"] == "https://github.com/test/repo/pull/123"
    assert output["state"] == "OPEN"
    assert output["is_draft"] is False
    assert output["head_ref_name"] == "feature-branch"
    assert output["base_ref_name"] == "master"
    assert output["author"] == "testuser"
    assert output["mergeable"] == "MERGEABLE"
    assert output["merge_state_status"] == "CLEAN"
    assert output["is_cross_repository"] is False
    assert "created_at" in output
    assert "updated_at" in output


def test_get_pr_view_not_found() -> None:
    """Test PR number that doesn't exist returns error."""
    fake_gh = FakeGitHub()
    runner = CliRunner()

    result = runner.invoke(
        get_pr_view,
        ["999"],
        obj=ErkContext.for_test(github=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "not found" in output["error"].lower()


def test_get_pr_view_auto_detect_from_branch() -> None:
    """Test auto-detection of current branch to find PR."""
    cwd = Path("/fake/worktree")
    pr = _make_pr_details(number=42, head_ref_name="my-feature")
    fake_gh = FakeGitHub(prs_by_branch={"my-feature": pr})
    fake_git = FakeGit(current_branches={cwd: "my-feature"})
    runner = CliRunner()

    result = runner.invoke(
        get_pr_view,
        [],
        obj=ErkContext.for_test(github=fake_gh, git=fake_git, cwd=cwd),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["number"] == 42
    assert output["head_ref_name"] == "my-feature"


def test_get_pr_view_auto_detect_no_pr() -> None:
    """Test auto-detection when current branch has no PR."""
    cwd = Path("/fake/worktree")
    fake_gh = FakeGitHub()
    fake_git = FakeGit(current_branches={cwd: "no-pr-branch"})
    runner = CliRunner()

    result = runner.invoke(
        get_pr_view,
        [],
        obj=ErkContext.for_test(github=fake_gh, git=fake_git, cwd=cwd),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "not found" in output["error"].lower()


def test_get_pr_view_by_branch_flag() -> None:
    """Test explicit --branch flag lookup."""
    pr = _make_pr_details(number=77, head_ref_name="feature-x")
    fake_gh = FakeGitHub(prs_by_branch={"feature-x": pr})
    runner = CliRunner()

    result = runner.invoke(
        get_pr_view,
        ["--branch", "feature-x"],
        obj=ErkContext.for_test(github=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["number"] == 77
    assert output["head_ref_name"] == "feature-x"


def test_get_pr_view_labels() -> None:
    """Test that labels are returned as a flat array."""
    pr = _make_pr_details(
        number=55,
        head_ref_name="labeled-branch",
        labels=("erk-plan", "erk-plan-review", "bug"),
    )
    fake_gh = FakeGitHub(pr_details={55: pr})
    runner = CliRunner()

    result = runner.invoke(
        get_pr_view,
        ["55"],
        obj=ErkContext.for_test(github=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["labels"] == ["erk-plan", "erk-plan-review", "bug"]
