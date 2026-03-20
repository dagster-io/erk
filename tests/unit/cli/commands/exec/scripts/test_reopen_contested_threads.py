"""Unit tests for reopen-contested-threads exec command.

Tests the command that detects and reopens resolved PR review threads
with unaddressed reviewer pushback.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.reopen_contested_threads import (
    _find_contested_threads,
    _has_marker,
    reopen_contested_threads,
)
from erk.cli.commands.exec.scripts.resolve_review_thread import PR_ADDRESS_MARKER
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.types import PRDetails, PRReviewComment, PRReviewThread
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub

# ============================================================================
# Test helpers
# ============================================================================


def make_pr_details(pr_number: int, *, branch: str) -> PRDetails:
    """Create test PRDetails."""
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


def make_comment(body: str, *, comment_id: int = 1) -> PRReviewComment:
    """Create test PRReviewComment."""
    return PRReviewComment(
        id=comment_id,
        body=body,
        author="reviewer",
        path="src/foo.py",
        line=42,
        created_at="2024-01-01T10:00:00Z",
    )


def make_thread(
    thread_id: str,
    comments: tuple[PRReviewComment, ...],
    *,
    is_resolved: bool = True,
    path: str = "src/foo.py",
    line: int | None = 42,
) -> PRReviewThread:
    """Create test PRReviewThread."""
    return PRReviewThread(
        id=thread_id,
        path=path,
        line=line,
        is_resolved=is_resolved,
        is_outdated=False,
        comments=comments,
    )


def make_attribution_comment(*, comment_id: int = 99) -> PRReviewComment:
    """Create a pr-address attribution comment with the HTML marker."""
    body = (
        f"Fixed the issue\n\n_Addressed via `/erk:pr-address` at 2024-01-01 10:00 UTC_"
        f"\n{PR_ADDRESS_MARKER}"
    )
    return make_comment(body, comment_id=comment_id)


# ============================================================================
# Pure function tests: _has_marker
# ============================================================================


def test_has_marker_with_marker() -> None:
    """_has_marker returns True when body contains the HTML marker."""
    body = f"Some comment text\n{PR_ADDRESS_MARKER}"
    assert _has_marker(body) is True


def test_has_marker_without_marker() -> None:
    """_has_marker returns False when body does not contain the marker."""
    body = "Some comment text without marker"
    assert _has_marker(body) is False


def test_has_marker_empty_body() -> None:
    """_has_marker returns False for empty body."""
    assert _has_marker("") is False


def test_has_marker_partial_match() -> None:
    """_has_marker requires the exact marker string."""
    body = "<!-- erk:pr-address -->"
    assert _has_marker(body) is False


def test_has_marker_exact_constant() -> None:
    """_has_marker returns True for the exact PR_ADDRESS_MARKER constant."""
    assert _has_marker(PR_ADDRESS_MARKER) is True


# ============================================================================
# Pure function tests: _find_contested_threads
# ============================================================================


def test_find_contested_threads_empty() -> None:
    """_find_contested_threads returns empty list for no threads."""
    assert _find_contested_threads([]) == []


def test_find_contested_threads_no_resolved() -> None:
    """_find_contested_threads ignores unresolved threads."""
    unresolved_thread = make_thread(
        "PRRT_1",
        (make_attribution_comment(), make_comment("pushback")),
        is_resolved=False,
    )
    assert _find_contested_threads([unresolved_thread]) == []


def test_find_contested_threads_resolved_attribution_as_last() -> None:
    """Thread with attribution as last comment is not contested."""
    reviewer_comment = make_comment("Please fix this", comment_id=1)
    attribution = make_attribution_comment(comment_id=2)
    thread = make_thread("PRRT_1", (reviewer_comment, attribution), is_resolved=True)

    assert _find_contested_threads([thread]) == []


def test_find_contested_threads_with_pushback_after_attribution() -> None:
    """Thread with reviewer comment after attribution is contested."""
    reviewer_comment = make_comment("Please fix this", comment_id=1)
    attribution = make_attribution_comment(comment_id=2)
    pushback = make_comment("This fix is wrong, please redo it", comment_id=3)
    thread = make_thread("PRRT_1", (reviewer_comment, attribution, pushback), is_resolved=True)

    contested = _find_contested_threads([thread])
    assert len(contested) == 1
    assert contested[0].id == "PRRT_1"


def test_find_contested_threads_manually_resolved_ignored() -> None:
    """Manually resolved thread (no marker) is not contested."""
    reviewer_comment = make_comment("Please fix this", comment_id=1)
    developer_reply = make_comment("I fixed it", comment_id=2)
    # No attribution marker - this was manually resolved
    thread = make_thread("PRRT_1", (reviewer_comment, developer_reply), is_resolved=True)

    assert _find_contested_threads([thread]) == []


def test_find_contested_threads_multiple_attributions_uses_last() -> None:
    """When thread has multiple attribution comments, uses the last one."""
    reviewer_comment = make_comment("Issue 1", comment_id=1)
    first_attribution = make_attribution_comment(comment_id=2)
    reviewer_pushback = make_comment("Still not fixed", comment_id=3)
    second_attribution = make_attribution_comment(comment_id=4)
    # Nothing after the last attribution - not contested
    thread = make_thread(
        "PRRT_1",
        (reviewer_comment, first_attribution, reviewer_pushback, second_attribution),
        is_resolved=True,
    )

    assert _find_contested_threads([thread]) == []


def test_find_contested_threads_multiple_attributions_pushback_after_last() -> None:
    """Contested if pushback after last attribution (even with earlier attributions)."""
    reviewer_comment = make_comment("Issue 1", comment_id=1)
    first_attribution = make_attribution_comment(comment_id=2)
    reviewer_pushback_1 = make_comment("Still not fixed", comment_id=3)
    second_attribution = make_attribution_comment(comment_id=4)
    reviewer_pushback_2 = make_comment("Still wrong!", comment_id=5)
    thread = make_thread(
        "PRRT_1",
        (
            reviewer_comment,
            first_attribution,
            reviewer_pushback_1,
            second_attribution,
            reviewer_pushback_2,
        ),
        is_resolved=True,
    )

    contested = _find_contested_threads([thread])
    assert len(contested) == 1
    assert contested[0].id == "PRRT_1"


def test_find_contested_threads_mixed() -> None:
    """Returns only contested threads from a mixed set."""
    # Thread 1: contested
    attribution_1 = make_attribution_comment(comment_id=1)
    pushback_1 = make_comment("Wrong fix", comment_id=2)
    contested_thread = make_thread("PRRT_1", (attribution_1, pushback_1), is_resolved=True)

    # Thread 2: not contested (attribution is last)
    attribution_2 = make_attribution_comment(comment_id=3)
    clean_thread = make_thread("PRRT_2", (attribution_2,), is_resolved=True)

    # Thread 3: manually resolved (no marker)
    manual_comment = make_comment("Manually resolved", comment_id=4)
    manual_thread = make_thread("PRRT_3", (manual_comment,), is_resolved=True)

    # Thread 4: unresolved
    reviewer_comment = make_comment("Please fix", comment_id=5)
    unresolved_thread = make_thread("PRRT_4", (reviewer_comment,), is_resolved=False)

    contested = _find_contested_threads(
        [contested_thread, clean_thread, manual_thread, unresolved_thread]
    )
    assert len(contested) == 1
    assert contested[0].id == "PRRT_1"


# ============================================================================
# CLI command tests
# ============================================================================


def test_reopen_contested_no_contested_threads(tmp_path: Path) -> None:
    """Command returns success with empty contested_threads when none are contested."""
    pr_details = make_pr_details(123, branch="feature/test")
    # Thread resolved by pr-address with attribution as last comment
    attribution = make_attribution_comment()
    resolved_thread = make_thread("PRRT_1", (attribution,), is_resolved=True)

    fake_github = FakeLocalGitHub(
        pr_details={123: pr_details},
        pr_review_threads={123: [resolved_thread]},
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
    assert output["contested_threads"] == []
    assert output["total_resolved_checked"] == 1
    assert output["total_contested"] == 0
    assert output["total_reopened"] == 0
    assert fake_github.unresolved_thread_ids == set()


def test_reopen_contested_single_contested_thread(tmp_path: Path) -> None:
    """Command reopens a single contested thread."""
    pr_details = make_pr_details(456, branch="feature/test")
    attribution = make_attribution_comment(comment_id=1)
    pushback = make_comment("This is still wrong", comment_id=2)
    contested_thread = make_thread(
        "PRRT_1", (attribution, pushback), is_resolved=True, path="src/foo.py", line=42
    )

    fake_github = FakeLocalGitHub(
        pr_details={456: pr_details},
        pr_review_threads={456: [contested_thread]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            reopen_contested_threads,
            ["--pr", "456"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 456
    assert len(output["contested_threads"]) == 1
    assert output["contested_threads"][0]["thread_id"] == "PRRT_1"
    assert output["contested_threads"][0]["path"] == "src/foo.py"
    assert output["contested_threads"][0]["line"] == 42
    assert output["contested_threads"][0]["unresolve_success"] is True
    assert output["total_resolved_checked"] == 1
    assert output["total_contested"] == 1
    assert output["total_reopened"] == 1

    # Verify the thread was actually unresolved in the fake
    assert "PRRT_1" in fake_github.unresolved_thread_ids


def test_reopen_contested_unresolved_thread_appears_unresolved(tmp_path: Path) -> None:
    """After unresolving, subsequent get_pr_review_threads call shows thread as unresolved."""
    pr_details = make_pr_details(789, branch="feature/test")
    attribution = make_attribution_comment(comment_id=1)
    pushback = make_comment("Wrong fix", comment_id=2)
    # Thread starts resolved
    contested_thread = make_thread("PRRT_1", (attribution, pushback), is_resolved=True)

    fake_github = FakeLocalGitHub(
        pr_details={789: pr_details},
        pr_review_threads={789: [contested_thread]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        cwd_path = cwd

        result = runner.invoke(
            reopen_contested_threads,
            ["--pr", "789"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["total_reopened"] == 1

    # Now check that get_pr_review_threads sees it as unresolved (no include_resolved)
    threads = fake_github.get_pr_review_threads(cwd_path, 789, include_resolved=False)
    assert len(threads) == 1
    assert threads[0].id == "PRRT_1"
    assert threads[0].is_resolved is False


def test_reopen_contested_mixed_threads(tmp_path: Path) -> None:
    """Command handles mix of contested, clean-resolved, manually-resolved, and unresolved."""
    pr_details = make_pr_details(100, branch="feature/test")

    # Contested: attribution then pushback
    attribution_1 = make_attribution_comment(comment_id=1)
    pushback_1 = make_comment("Still wrong", comment_id=2)
    contested = make_thread("PRRT_contested", (attribution_1, pushback_1), is_resolved=True)

    # Clean resolved: attribution is last
    attribution_2 = make_attribution_comment(comment_id=3)
    clean_resolved = make_thread("PRRT_clean", (attribution_2,), is_resolved=True)

    # Manually resolved: no attribution marker
    manual_comment = make_comment("Dev resolved manually", comment_id=4)
    manually_resolved = make_thread("PRRT_manual", (manual_comment,), is_resolved=True)

    # Unresolved: open thread
    reviewer_comment = make_comment("Please fix this", comment_id=5)
    unresolved = make_thread("PRRT_open", (reviewer_comment,), is_resolved=False)

    fake_github = FakeLocalGitHub(
        pr_details={100: pr_details},
        pr_review_threads={100: [contested, clean_resolved, manually_resolved, unresolved]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            reopen_contested_threads,
            ["--pr", "100"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["total_resolved_checked"] == 3  # Three resolved threads
    assert output["total_contested"] == 1
    assert output["total_reopened"] == 1
    assert len(output["contested_threads"]) == 1
    assert output["contested_threads"][0]["thread_id"] == "PRRT_contested"

    # Only the contested thread was unresolved
    assert fake_github.unresolved_thread_ids == {"PRRT_contested"}


def test_reopen_contested_unresolve_api_failure_captured_per_thread(tmp_path: Path) -> None:
    """API failure during unresolve is captured per-thread without crashing."""
    pr_details = make_pr_details(200, branch="feature/test")
    attribution = make_attribution_comment(comment_id=1)
    pushback = make_comment("Wrong", comment_id=2)
    contested = make_thread("PRRT_1", (attribution, pushback), is_resolved=True)

    # Configure fake to fail on unresolve
    fake_github = FakeLocalGitHub(
        pr_details={200: pr_details},
        pr_review_threads={200: [contested]},
        unresolve_thread_failures={"PRRT_1"},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            reopen_contested_threads,
            ["--pr", "200"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True  # Command itself succeeded
    assert output["total_contested"] == 1
    assert output["total_reopened"] == 0  # Unresolve failed
    assert output["contested_threads"][0]["unresolve_success"] is False


def test_reopen_contested_no_resolved_threads(tmp_path: Path) -> None:
    """Command handles PR with no resolved threads."""
    pr_details = make_pr_details(300, branch="feature/test")
    open_thread = make_thread("PRRT_1", (make_comment("Fix this"),), is_resolved=False)

    fake_github = FakeLocalGitHub(
        pr_details={300: pr_details},
        pr_review_threads={300: [open_thread]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            reopen_contested_threads,
            ["--pr", "300"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["total_resolved_checked"] == 0
    assert output["total_contested"] == 0
    assert output["total_reopened"] == 0


def test_reopen_contested_no_threads_at_all(tmp_path: Path) -> None:
    """Command handles PR with no threads at all."""
    pr_details = make_pr_details(400, branch="feature/test")

    fake_github = FakeLocalGitHub(
        pr_details={400: pr_details},
        pr_review_threads={400: []},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            reopen_contested_threads,
            ["--pr", "400"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["total_resolved_checked"] == 0
    assert output["total_contested"] == 0


# ============================================================================
# Fake behavior tests
# ============================================================================


def test_fake_unresolve_tracks_thread_ids(tmp_path: Path) -> None:
    """FakeLocalGitHub.unresolve_review_thread tracks unresolved thread IDs."""
    fake_github = FakeLocalGitHub()

    result = fake_github.unresolve_review_thread(tmp_path, "PRRT_abc")
    assert result is True
    assert "PRRT_abc" in fake_github.unresolved_thread_ids


def test_fake_unresolve_failure(tmp_path: Path) -> None:
    """FakeLocalGitHub.unresolve_review_thread returns False for configured failures."""
    fake_github = FakeLocalGitHub(unresolve_thread_failures={"PRRT_fail"})

    result = fake_github.unresolve_review_thread(tmp_path, "PRRT_fail")
    assert result is False
    assert "PRRT_fail" not in fake_github.unresolved_thread_ids


def test_fake_unresolved_thread_not_in_resolved_ids(tmp_path: Path) -> None:
    """Unresolved thread IDs don't overlap with resolved IDs."""
    fake_github = FakeLocalGitHub()

    fake_github.resolve_review_thread(tmp_path, "PRRT_1")
    fake_github.unresolve_review_thread(tmp_path, "PRRT_1")

    assert "PRRT_1" in fake_github.resolved_thread_ids
    assert "PRRT_1" in fake_github.unresolved_thread_ids
