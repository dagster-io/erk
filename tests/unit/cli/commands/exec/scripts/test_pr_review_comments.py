"""Unit tests for PR review comment kit CLI commands.

Tests get-pr-review-comments and resolve-review-thread commands.
Uses FakeGitHub for fast, reliable testing.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_pr_review_comments import (
    get_pr_review_comments,
)
from erk.cli.commands.exec.scripts.resolve_review_thread import (
    resolve_review_thread,
)
from erk_shared.context import ErkContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PRReviewComment, PRReviewThread


def make_thread(
    thread_id: str,
    path: str,
    line: int | None,
    comment_body: str,
    is_resolved: bool = False,
    is_outdated: bool = False,
) -> PRReviewThread:
    """Create test PRReviewThread with a single comment."""
    comment = PRReviewComment(
        id=1,
        body=comment_body,
        author="reviewer",
        path=path,
        line=line,
        created_at="2024-01-01T10:00:00Z",
    )
    return PRReviewThread(
        id=thread_id,
        path=path,
        line=line,
        is_resolved=is_resolved,
        is_outdated=is_outdated,
        comments=(comment,),
    )


def make_pr_details(pr_number: int, branch: str = "feature-branch") -> PRDetails:
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


# ============================================================================
# get-pr-review-comments Success Cases
# ============================================================================


def test_get_pr_review_comments_with_pr_number(tmp_path: Path) -> None:
    """Test get-pr-review-comments with explicit PR number."""
    thread = make_thread("PRRT_1", "src/foo.py", 42, "Fix this code")
    pr_details = make_pr_details(123)

    fake_github = FakeGitHub(
        pr_details={123: pr_details},
        pr_review_threads={123: [thread]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_review_comments,
            ["--pr", "123"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 123
    assert len(output["threads"]) == 1
    assert output["threads"][0]["path"] == "src/foo.py"
    assert output["threads"][0]["line"] == 42
    assert output["threads"][0]["comments"][0]["body"] == "Fix this code"


def test_get_pr_review_comments_filters_resolved_by_default(tmp_path: Path) -> None:
    """Test that resolved threads are excluded by default."""
    unresolved = make_thread("PRRT_1", "src/foo.py", 10, "Unresolved", is_resolved=False)
    resolved = make_thread("PRRT_2", "src/bar.py", 20, "Resolved", is_resolved=True)
    pr_details = make_pr_details(123)

    fake_github = FakeGitHub(
        pr_details={123: pr_details},
        pr_review_threads={123: [unresolved, resolved]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_review_comments,
            ["--pr", "123"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert len(output["threads"]) == 1
    assert output["threads"][0]["id"] == "PRRT_1"


def test_get_pr_review_comments_include_resolved_flag(tmp_path: Path) -> None:
    """Test --include-resolved flag includes resolved threads."""
    unresolved = make_thread("PRRT_1", "src/foo.py", 10, "Unresolved", is_resolved=False)
    resolved = make_thread("PRRT_2", "src/bar.py", 20, "Resolved", is_resolved=True)
    pr_details = make_pr_details(123)

    fake_github = FakeGitHub(
        pr_details={123: pr_details},
        pr_review_threads={123: [unresolved, resolved]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_review_comments,
            ["--pr", "123", "--include-resolved"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert len(output["threads"]) == 2


def test_get_pr_review_comments_no_threads(tmp_path: Path) -> None:
    """Test get-pr-review-comments returns empty list when no threads."""
    pr_details = make_pr_details(123)

    fake_github = FakeGitHub(
        pr_details={123: pr_details},
        pr_review_threads={123: []},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_review_comments,
            ["--pr", "123"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["threads"] == []


# ============================================================================
# get-pr-review-comments Error Cases
# ============================================================================


def test_get_pr_review_comments_pr_not_found(tmp_path: Path) -> None:
    """Test error when PR doesn't exist."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_review_comments,
            ["--pr", "999"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0  # Graceful degradation
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "pr-not-found"


# ============================================================================
# resolve-review-thread Success Cases
# ============================================================================


def test_resolve_review_thread_success(tmp_path: Path) -> None:
    """Test successfully resolving a review thread."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_thread,
            ["--thread-id", "PRRT_abc123"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["thread_id"] == "PRRT_abc123"

    # Verify the thread was tracked as resolved in the fake
    assert "PRRT_abc123" in fake_github.resolved_thread_ids


def test_resolve_review_thread_multiple(tmp_path: Path) -> None:
    """Test resolving multiple threads tracks all of them."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        # Resolve first thread
        runner.invoke(
            resolve_review_thread,
            ["--thread-id", "PRRT_1"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

        # Resolve second thread
        runner.invoke(
            resolve_review_thread,
            ["--thread-id", "PRRT_2"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    # Both should be tracked
    assert "PRRT_1" in fake_github.resolved_thread_ids
    assert "PRRT_2" in fake_github.resolved_thread_ids


# ============================================================================
# resolve-review-thread CLI Argument Tests
# ============================================================================


def test_resolve_review_thread_missing_thread_id(tmp_path: Path) -> None:
    """Test error when thread-id is missing."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_thread,
            [],  # Missing --thread-id
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    # Click should return error for missing required option
    assert result.exit_code != 0
    assert "thread-id" in result.output.lower()


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_get_pr_review_comments_json_structure(tmp_path: Path) -> None:
    """Test JSON output structure for get-pr-review-comments."""
    thread = make_thread("PRRT_1", "src/foo.py", 42, "Fix this", is_outdated=True)
    pr_details = make_pr_details(123)

    fake_github = FakeGitHub(
        pr_details={123: pr_details},
        pr_review_threads={123: [thread]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_review_comments,
            ["--pr", "123"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify top-level structure
    assert "success" in output
    assert "pr_number" in output
    assert "pr_url" in output
    assert "pr_title" in output
    assert "threads" in output

    # Verify thread structure
    thread_data = output["threads"][0]
    assert "id" in thread_data
    assert "path" in thread_data
    assert "line" in thread_data
    assert "is_outdated" in thread_data
    assert "comments" in thread_data

    # Verify comment structure
    comment_data = thread_data["comments"][0]
    assert "author" in comment_data
    assert "body" in comment_data
    assert "created_at" in comment_data


def test_resolve_review_thread_json_structure_success(tmp_path: Path) -> None:
    """Test JSON output structure for resolve-review-thread success."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_thread,
            ["--thread-id", "PRRT_test"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify success structure
    assert output["success"] is True
    assert output["thread_id"] == "PRRT_test"


# ============================================================================
# resolve-review-thread --comment Flag Tests
# ============================================================================


def test_resolve_review_thread_with_comment(tmp_path: Path) -> None:
    """Test resolving a review thread with a comment."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_thread,
            ["--thread-id", "PRRT_abc123", "--comment", "Resolved via automation"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["thread_id"] == "PRRT_abc123"
    assert output["comment_added"] is True

    # Verify both reply and resolution were tracked
    assert len(fake_github.thread_replies) == 1
    thread_id, comment_body = fake_github.thread_replies[0]
    assert thread_id == "PRRT_abc123"
    assert comment_body.startswith("Resolved via automation\n\n")
    assert "_Addressed via `/erk:pr-address` at" in comment_body
    assert "PRRT_abc123" in fake_github.resolved_thread_ids


def test_resolve_review_thread_without_comment(tmp_path: Path) -> None:
    """Test resolving a review thread without a comment."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_thread,
            ["--thread-id", "PRRT_abc123"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["comment_added"] is False

    # Verify no reply was added, but resolution still happened
    assert len(fake_github.thread_replies) == 0
    assert "PRRT_abc123" in fake_github.resolved_thread_ids


def test_resolve_review_thread_json_structure_with_comment(tmp_path: Path) -> None:
    """Test JSON output structure includes comment_added field."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_thread,
            ["--thread-id", "PRRT_test", "--comment", "Test comment"],
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify success structure includes comment_added
    assert output["success"] is True
    assert output["thread_id"] == "PRRT_test"
    assert "comment_added" in output
    assert output["comment_added"] is True
