"""Unit tests for set-local-review-marker exec command.

Tests PR body marker setting for local review skip in CI.
Uses FakeGitHub and FakeGit for fast, reliable testing.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.set_local_review_marker import (
    _append_marker,
    _strip_existing_marker,
    set_local_review_marker,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo


def _make_pr_details(
    *,
    number: int,
    head_ref_name: str,
    body: str,
) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/test-owner/test-repo/pull/{number}",
        title=f"PR #{number}",
        body=body,
        state="OPEN",
        is_draft=False,
        base_ref_name="master",
        head_ref_name=head_ref_name,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )


def _make_pr_info(
    *,
    number: int,
    head_branch: str,
) -> PullRequestInfo:
    return PullRequestInfo(
        number=number,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/pull/{number}",
        is_draft=False,
        title=f"PR #{number}",
        checks_passing=True,
        owner="test-owner",
        repo="test-repo",
        head_branch=head_branch,
    )


# ============================================================================
# Helper Function Tests
# ============================================================================


def test_strip_existing_marker_removes_marker() -> None:
    """Test that existing marker is stripped from body."""
    sha = "abc123def456789012345678901234567890abcd"
    body = f"PR description\n<!-- erk:local-review-passed:{sha} -->\n"
    result = _strip_existing_marker(body)
    assert "erk:local-review-passed" not in result
    assert "PR description" in result


def test_strip_existing_marker_no_marker() -> None:
    """Test that body without marker is unchanged."""
    body = "PR description\nSome content"
    result = _strip_existing_marker(body)
    assert result == body


def test_append_marker_adds_to_end() -> None:
    """Test that marker is appended to body."""
    body = "PR description"
    sha = "abc123def456789012345678901234567890abcd"
    result = _append_marker(body, sha)
    assert result.endswith(f"<!-- erk:local-review-passed:{sha} -->\n")
    assert result.startswith("PR description\n")


def test_append_marker_replaces_existing() -> None:
    """Test that old marker is replaced with new one."""
    old_sha = "0000000000000000000000000000000000000000"
    new_sha = "abc123def456789012345678901234567890abcd"
    body = f"PR description\n<!-- erk:local-review-passed:{old_sha} -->\n"
    result = _append_marker(body, new_sha)
    assert old_sha not in result
    assert f"<!-- erk:local-review-passed:{new_sha} -->" in result


def test_append_marker_preserves_body_content() -> None:
    """Test that body content is preserved when appending marker."""
    body = "## Summary\n\nThis PR does things.\n\n## Test Plan\n\n- [x] Tests pass"
    sha = "abc123def456789012345678901234567890abcd"
    result = _append_marker(body, sha)
    assert "## Summary" in result
    assert "## Test Plan" in result
    assert result.endswith(f"<!-- erk:local-review-passed:{sha} -->\n")


# ============================================================================
# Happy Path
# ============================================================================


def test_happy_path_sets_marker(tmp_path: Path) -> None:
    """Test successful marker setting on PR."""
    branch = "feature-branch"
    sha = "abc123def456789012345678901234567890abcd"
    pr_body = "Original PR body"
    fake_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(
        issues_gateway=fake_issues,
        prs={branch: _make_pr_info(number=42, head_branch=branch)},
        pr_details={42: _make_pr_details(number=42, head_ref_name=branch, body=pr_body)},
    )
    fake_git = FakeGit(
        current_branches={tmp_path: branch},
        branch_heads={branch: sha},
    )
    runner = CliRunner()

    result = runner.invoke(
        set_local_review_marker,
        [],
        obj=ErkContext.for_test(
            github=fake_gh,
            github_issues=fake_issues,
            git=fake_git,
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 42
    assert output["sha"] == sha

    # Verify PR body was updated with marker
    assert len(fake_gh.updated_pr_bodies) == 1
    updated_pr_number, updated_body = fake_gh.updated_pr_bodies[0]
    assert updated_pr_number == 42
    assert f"<!-- erk:local-review-passed:{sha} -->" in updated_body
    assert "Original PR body" in updated_body


# ============================================================================
# No PR for Branch
# ============================================================================


def test_no_pr_for_branch(tmp_path: Path) -> None:
    """Test graceful handling when no PR exists for branch."""
    branch = "feature-branch"
    sha = "abc123def456789012345678901234567890abcd"
    fake_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(issues_gateway=fake_issues, prs={}, pr_details={})
    fake_git = FakeGit(
        current_branches={tmp_path: branch},
        branch_heads={branch: sha},
    )
    runner = CliRunner()

    result = runner.invoke(
        set_local_review_marker,
        [],
        obj=ErkContext.for_test(
            github=fake_gh,
            github_issues=fake_issues,
            git=fake_git,
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["reason"] == "no_pr"
    assert len(fake_gh.updated_pr_bodies) == 0


# ============================================================================
# Existing Marker Replaced
# ============================================================================


def test_existing_marker_replaced(tmp_path: Path) -> None:
    """Test that old marker is stripped and new one appended."""
    branch = "feature-branch"
    old_sha = "0000000000000000000000000000000000000000"
    new_sha = "abc123def456789012345678901234567890abcd"
    pr_body = f"PR description\n<!-- erk:local-review-passed:{old_sha} -->\n"
    fake_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(
        issues_gateway=fake_issues,
        prs={branch: _make_pr_info(number=42, head_branch=branch)},
        pr_details={42: _make_pr_details(number=42, head_ref_name=branch, body=pr_body)},
    )
    fake_git = FakeGit(
        current_branches={tmp_path: branch},
        branch_heads={branch: new_sha},
    )
    runner = CliRunner()

    result = runner.invoke(
        set_local_review_marker,
        [],
        obj=ErkContext.for_test(
            github=fake_gh,
            github_issues=fake_issues,
            git=fake_git,
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify old marker is gone and new one is present
    _, updated_body = fake_gh.updated_pr_bodies[0]
    assert old_sha not in updated_body
    assert f"<!-- erk:local-review-passed:{new_sha} -->" in updated_body
    assert "PR description" in updated_body


# ============================================================================
# PR Body with Footer
# ============================================================================


def test_pr_body_with_footer(tmp_path: Path) -> None:
    """Test that marker is appended correctly when PR has footer content."""
    branch = "feature-branch"
    sha = "abc123def456789012345678901234567890abcd"
    pr_body = "## Summary\n\nChanges.\n\n---\nCloses #123\n\nCo-Authored-By: Test <test@test.com>"
    fake_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(
        issues_gateway=fake_issues,
        prs={branch: _make_pr_info(number=42, head_branch=branch)},
        pr_details={42: _make_pr_details(number=42, head_ref_name=branch, body=pr_body)},
    )
    fake_git = FakeGit(
        current_branches={tmp_path: branch},
        branch_heads={branch: sha},
    )
    runner = CliRunner()

    result = runner.invoke(
        set_local_review_marker,
        [],
        obj=ErkContext.for_test(
            github=fake_gh,
            github_issues=fake_issues,
            git=fake_git,
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify footer content is preserved
    _, updated_body = fake_gh.updated_pr_bodies[0]
    assert "Closes #123" in updated_body
    assert "Co-Authored-By" in updated_body
    assert f"<!-- erk:local-review-passed:{sha} -->" in updated_body


# ============================================================================
# Detached HEAD
# ============================================================================


def test_detached_head(tmp_path: Path) -> None:
    """Test graceful handling when in detached HEAD state."""
    fake_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(issues_gateway=fake_issues)
    fake_git = FakeGit(current_branches={tmp_path: None})
    runner = CliRunner()

    result = runner.invoke(
        set_local_review_marker,
        [],
        obj=ErkContext.for_test(
            github=fake_gh,
            github_issues=fake_issues,
            git=fake_git,
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["reason"] == "detached_head"
