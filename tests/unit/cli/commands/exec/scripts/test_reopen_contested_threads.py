"""Unit tests for reopen-contested-threads exec command.

Tests the command that detects and reopens "contested" resolved PR review
threads — those resolved by erk:pr-address that have subsequent reviewer
comments pushing back.

Uses FakeLocalGitHub for fast, reliable testing.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.reopen_contested_threads import (
    PR_ADDRESS_MARKER,
    _find_contested_threads,
    _has_marker,
    reopen_contested_threads,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.types import PRDetails, PRReviewComment, PRReviewThread
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub

# ============================================================================
# Test helpers
# ============================================================================


def make_pr_details(pr_number: int, *, branch: str = "feature-branch") -> PRDetails:
    """Create minimal PRDetails for testing."""
    return PRDetails(
        number=pr_number,
        url=f"https://github.com/test-owner/test-repo/pull/{pr_number}",
        title=f"Test PR #{pr_number}",
        body="Test PR body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )


def make_comment(
    comment_id: int,
    body: str,
    *,
    author: str = "reviewer",
    path: str = "src/foo.py",
    line: int | None = 42,
) -> PRReviewComment:
    """Create a PRReviewComment for testing."""
    return PRReviewComment(
        id=comment_id,
        body=body,
        author=author,
        path=path,
        line=line,
        created_at="2024-01-01T10:00:00Z",
    )


def make_thread(
    thread_id: str,
    comments: list[PRReviewComment],
    *,
    is_resolved: bool = True,
    path: str = "src/foo.py",
    line: int | None = 42,
) -> PRReviewThread:
    """Create a PRReviewThread with the given comments."""
    return PRReviewThread(
        id=thread_id,
        path=path,
        line=line,
        is_resolved=is_resolved,
        is_outdated=False,
        comments=tuple(comments),
    )


MARKER_COMMENT_BODY = (
    "Fixed the issue.\n\n"
    "_Addressed via `/erk:pr-address` at 2024-01-01 10:00 UTC_\n"
    f"{PR_ADDRESS_MARKER}"
)


# ============================================================================
# Pure function tests: _has_marker
# ============================================================================


def test_has_marker_with_marker() -> None:
    """_has_marker returns True when PR_ADDRESS_MARKER is in body."""
    assert _has_marker(MARKER_COMMENT_BODY) is True


def test_has_marker_without_marker() -> None:
    """_has_marker returns False when PR_ADDRESS_MARKER is absent."""
    assert _has_marker("This is a regular comment with no marker.") is False


def test_has_marker_empty_string() -> None:
    """_has_marker returns False for empty string."""
    assert _has_marker("") is False


def test_has_marker_partial_match() -> None:
    """_has_marker requires exact marker string."""
    assert _has_marker("<!-- erk:pr-address -->") is False
    assert _has_marker("<!-- erk:pr-address-resolved") is False


# ============================================================================
# Pure function tests: _find_contested_threads
# ============================================================================


def test_find_contested_threads_no_threads() -> None:
    """Empty input returns empty result."""
    result = _find_contested_threads([])
    assert result == []


def test_find_contested_threads_unresolved_threads_untouched() -> None:
    """Unresolved threads are never returned as contested."""
    thread = make_thread(
        "PRRT_1",
        [
            make_comment(1, "Fix this"),
            make_comment(2, MARKER_COMMENT_BODY),
            make_comment(3, "But wait, reconsider"),
        ],
        is_resolved=False,
    )
    result = _find_contested_threads([thread])
    assert result == []


def test_find_contested_threads_no_marker_not_contested() -> None:
    """Resolved thread without marker (manually resolved) is not contested."""
    thread = make_thread(
        "PRRT_1",
        [
            make_comment(1, "Fix this"),
            make_comment(2, "Looks good now"),
        ],
        is_resolved=True,
    )
    result = _find_contested_threads([thread])
    assert result == []


def test_find_contested_threads_attribution_is_last_comment() -> None:
    """Resolved thread where attribution is the last comment is not contested."""
    thread = make_thread(
        "PRRT_1",
        [
            make_comment(1, "Fix this"),
            make_comment(2, MARKER_COMMENT_BODY),
        ],
        is_resolved=True,
    )
    result = _find_contested_threads([thread])
    assert result == []


def test_find_contested_threads_single_contested() -> None:
    """Resolved thread with reviewer comment after attribution marker is contested."""
    thread = make_thread(
        "PRRT_1",
        [
            make_comment(1, "Fix this"),
            make_comment(2, MARKER_COMMENT_BODY),
            make_comment(3, "This doesn't actually fix the issue"),
        ],
        is_resolved=True,
    )
    result = _find_contested_threads([thread])
    assert len(result) == 1
    assert result[0].id == "PRRT_1"


def test_find_contested_threads_uses_last_marker_comment() -> None:
    """When multiple marker comments exist, use the last one to check for pushback."""
    # Thread has two marker comments; reviewer comment is between them (not contested)
    thread = make_thread(
        "PRRT_1",
        [
            make_comment(1, "Fix this"),
            make_comment(2, MARKER_COMMENT_BODY),
            make_comment(3, "Pushback after first resolution"),
            make_comment(4, MARKER_COMMENT_BODY),  # Second resolution
        ],
        is_resolved=True,
    )
    result = _find_contested_threads([thread])
    # Last marker is comment 4 (last), no comments after it
    assert result == []


def test_find_contested_threads_multiple_markers_with_pushback() -> None:
    """When multiple marker comments exist and there is pushback after the last, it's contested."""
    thread = make_thread(
        "PRRT_1",
        [
            make_comment(1, "Fix this"),
            make_comment(2, MARKER_COMMENT_BODY),
            make_comment(3, "Still not right"),
            make_comment(4, MARKER_COMMENT_BODY),  # Second resolution
            make_comment(5, "I still disagree"),  # Pushback after last marker
        ],
        is_resolved=True,
    )
    result = _find_contested_threads([thread])
    assert len(result) == 1
    assert result[0].id == "PRRT_1"


def test_find_contested_threads_mixed_manually_and_pr_address_resolved() -> None:
    """Only pr-address resolved threads with pushback are contested; manually resolved ignored."""
    manual_thread = make_thread(
        "PRRT_manual",
        [make_comment(1, "Fix this"), make_comment(2, "Reviewer pushback")],
        is_resolved=True,
    )
    contested_thread = make_thread(
        "PRRT_addressed",
        [
            make_comment(3, "Fix this"),
            make_comment(4, MARKER_COMMENT_BODY),
            make_comment(5, "Still wrong"),
        ],
        is_resolved=True,
    )
    result = _find_contested_threads([manual_thread, contested_thread])
    assert len(result) == 1
    assert result[0].id == "PRRT_addressed"


# ============================================================================
# Command integration tests
# ============================================================================


def test_reopen_contested_threads_no_contested(tmp_path: Path) -> None:
    """Command returns success with zero contested when no threads qualify."""
    pr_details = make_pr_details(123)
    thread = make_thread(
        "PRRT_1",
        [make_comment(1, "Fix this"), make_comment(2, MARKER_COMMENT_BODY)],
        is_resolved=True,
    )
    fake_github = FakeLocalGitHub(
        pr_details={123: pr_details},
        pr_review_threads={123: [thread]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            reopen_contested_threads,
            ["--pr", "123"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 123
    assert output["total_contested"] == 0
    assert output["total_reopened"] == 0
    assert output["contested_threads"] == []
    # No unresolution should have happened
    assert fake_github.unresolved_thread_ids == set()


def test_reopen_contested_threads_single_contested(tmp_path: Path) -> None:
    """Command unresolves a single contested thread and reports it."""
    pr_details = make_pr_details(123)
    thread = make_thread(
        "PRRT_1",
        [
            make_comment(1, "Fix this"),
            make_comment(2, MARKER_COMMENT_BODY),
            make_comment(3, "I still disagree"),
        ],
        is_resolved=True,
    )
    fake_github = FakeLocalGitHub(
        pr_details={123: pr_details},
        pr_review_threads={123: [thread]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            reopen_contested_threads,
            ["--pr", "123"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 123
    assert output["total_resolved_checked"] == 1
    assert output["total_contested"] == 1
    assert output["total_reopened"] == 1
    assert len(output["contested_threads"]) == 1
    assert output["contested_threads"][0]["thread_id"] == "PRRT_1"
    assert output["contested_threads"][0]["unresolve_success"] is True
    # Verify unresolution was tracked
    assert "PRRT_1" in fake_github.unresolved_thread_ids


def test_reopen_contested_threads_mixed_threads(tmp_path: Path) -> None:
    """Command handles mix of unresolved, manually resolved, and contested threads."""
    pr_details = make_pr_details(123)
    unresolved = make_thread(
        "PRRT_unresolved",
        [make_comment(1, "Fix this")],
        is_resolved=False,
    )
    manual_resolved = make_thread(
        "PRRT_manual",
        [make_comment(2, "Fix this"), make_comment(3, "OK thanks")],
        is_resolved=True,
    )
    contested = make_thread(
        "PRRT_contested",
        [
            make_comment(4, "Fix this"),
            make_comment(5, MARKER_COMMENT_BODY),
            make_comment(6, "Still wrong"),
        ],
        is_resolved=True,
    )
    no_pushback = make_thread(
        "PRRT_clean",
        [make_comment(7, "Fix this"), make_comment(8, MARKER_COMMENT_BODY)],
        is_resolved=True,
    )

    fake_github = FakeLocalGitHub(
        pr_details={123: pr_details},
        pr_review_threads={123: [unresolved, manual_resolved, contested, no_pushback]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            reopen_contested_threads,
            ["--pr", "123"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["total_resolved_checked"] == 3  # manual, contested, clean
    assert output["total_contested"] == 1
    assert output["total_reopened"] == 1
    assert output["contested_threads"][0]["thread_id"] == "PRRT_contested"
    assert fake_github.unresolved_thread_ids == {"PRRT_contested"}


def test_reopen_contested_threads_api_failure_per_thread(tmp_path: Path) -> None:
    """API failure during unresolve is captured per-thread, not fatal."""
    pr_details = make_pr_details(123)
    thread = make_thread(
        "PRRT_fail",
        [
            make_comment(1, "Fix this"),
            make_comment(2, MARKER_COMMENT_BODY),
            make_comment(3, "Pushback"),
        ],
        is_resolved=True,
    )
    fake_github = FakeLocalGitHub(
        pr_details={123: pr_details},
        pr_review_threads={123: [thread]},
        unresolve_thread_failures={"PRRT_fail"},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            reopen_contested_threads,
            ["--pr", "123"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["total_contested"] == 1
    assert output["total_reopened"] == 0  # Failed
    assert output["contested_threads"][0]["unresolve_success"] is False
    assert fake_github.unresolved_thread_ids == set()
