"""Unit tests for get-pr-feedback combined command.

Tests the combined PR feedback command that fetches both review threads
and discussion comments in a single call.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_pr_feedback import get_pr_feedback
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment
from erk_shared.gateway.github.types import PRDetails, PRReviewComment, PRReviewThread


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


def make_thread(
    thread_id: str,
    path: str,
    line: int | None,
    comment_body: str,
    *,
    is_resolved: bool,
    is_outdated: bool,
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


def make_issue_comment(
    comment_id: int,
    body: str,
    *,
    author: str,
    pr_number: int,
) -> IssueComment:
    """Create test IssueComment."""
    return IssueComment(
        body=body,
        url=f"https://github.com/test-owner/test-repo/pull/{pr_number}#issuecomment-{comment_id}",
        id=comment_id,
        author=author,
    )


# ============================================================================
# Success Cases
# ============================================================================


def test_get_pr_feedback_with_pr_number(tmp_path: Path) -> None:
    """Test combined feedback with explicit PR number."""
    thread = make_thread(
        "PRRT_1", "src/foo.py", 42, "Fix this code", is_resolved=False, is_outdated=False
    )
    pr_details = make_pr_details(123)
    comments = [make_issue_comment(100, "Please update docs", author="reviewer1", pr_number=123)]

    fake_github_issues = FakeGitHubIssues(comments_with_urls={123: comments})
    fake_github = FakeGitHub(
        issues_gateway=fake_github_issues,
        pr_details={123: pr_details},
        pr_review_threads={123: [thread]},
    )
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_feedback,
            ["--pr", "123"],
            obj=ErkContext.for_test(
                github=fake_github,
                git=FakeGit(),
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 123
    assert output["pr_title"] == "Test PR #123"
    assert len(output["review_threads"]) == 1
    assert output["review_threads"][0]["path"] == "src/foo.py"
    assert output["review_threads"][0]["comments"][0]["body"] == "Fix this code"
    assert len(output["discussion_comments"]) == 1
    assert output["discussion_comments"][0]["body"] == "Please update docs"
    assert output["discussion_comments"][0]["author"] == "reviewer1"


def test_get_pr_feedback_auto_detect_branch(tmp_path: Path) -> None:
    """Test auto-detection of current branch to find PR."""
    cwd = Path("/fake/worktree")
    pr_details = make_pr_details(42, branch="my-feature")
    thread = make_thread(
        "PRRT_1", "src/main.py", 10, "Add tests", is_resolved=False, is_outdated=False
    )
    comments = [make_issue_comment(200, "Looks good", author="reviewer", pr_number=42)]

    fake_github_issues = FakeGitHubIssues(comments_with_urls={42: comments})
    fake_github = FakeGitHub(
        issues_gateway=fake_github_issues,
        prs_by_branch={"my-feature": pr_details},
        pr_review_threads={42: [thread]},
    )
    fake_git = FakeGit(current_branches={cwd: "my-feature"})
    runner = CliRunner()

    result = runner.invoke(
        get_pr_feedback,
        [],
        obj=ErkContext.for_test(
            github=fake_github,
            git=fake_git,
            repo_root=cwd,
            cwd=cwd,
        ),
    )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 42
    assert len(output["review_threads"]) == 1
    assert len(output["discussion_comments"]) == 1


def test_get_pr_feedback_no_comments(tmp_path: Path) -> None:
    """Test with PR that has no comments or threads."""
    pr_details = make_pr_details(123)

    fake_github_issues = FakeGitHubIssues(comments_with_urls={123: []})
    fake_github = FakeGitHub(
        issues_gateway=fake_github_issues,
        pr_details={123: pr_details},
        pr_review_threads={123: []},
    )
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_feedback,
            ["--pr", "123"],
            obj=ErkContext.for_test(
                github=fake_github,
                git=FakeGit(),
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["review_threads"] == []
    assert output["discussion_comments"] == []


def test_get_pr_feedback_include_resolved(tmp_path: Path) -> None:
    """Test --include-resolved flag includes resolved threads."""
    unresolved = make_thread(
        "PRRT_1", "src/foo.py", 10, "Unresolved", is_resolved=False, is_outdated=False
    )
    resolved = make_thread(
        "PRRT_2", "src/bar.py", 20, "Resolved", is_resolved=True, is_outdated=False
    )
    pr_details = make_pr_details(123)

    fake_github_issues = FakeGitHubIssues(comments_with_urls={123: []})
    fake_github = FakeGitHub(
        issues_gateway=fake_github_issues,
        pr_details={123: pr_details},
        pr_review_threads={123: [unresolved, resolved]},
    )
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_feedback,
            ["--pr", "123", "--include-resolved"],
            obj=ErkContext.for_test(
                github=fake_github,
                git=FakeGit(),
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert len(output["review_threads"]) == 2


def test_get_pr_feedback_filters_resolved_by_default(tmp_path: Path) -> None:
    """Test that resolved threads are excluded by default."""
    unresolved = make_thread(
        "PRRT_1", "src/foo.py", 10, "Unresolved", is_resolved=False, is_outdated=False
    )
    resolved = make_thread(
        "PRRT_2", "src/bar.py", 20, "Resolved", is_resolved=True, is_outdated=False
    )
    pr_details = make_pr_details(123)

    fake_github_issues = FakeGitHubIssues(comments_with_urls={123: []})
    fake_github = FakeGitHub(
        issues_gateway=fake_github_issues,
        pr_details={123: pr_details},
        pr_review_threads={123: [unresolved, resolved]},
    )
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_feedback,
            ["--pr", "123"],
            obj=ErkContext.for_test(
                github=fake_github,
                git=FakeGit(),
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert len(output["review_threads"]) == 1
    assert output["review_threads"][0]["id"] == "PRRT_1"


def test_get_pr_feedback_filters_null_thread_ids(tmp_path: Path) -> None:
    """Test threads with null/empty IDs are filtered out."""
    valid_thread = make_thread(
        "PRRT_valid", "src/foo.py", 10, "Valid comment", is_resolved=False, is_outdated=False
    )
    invalid_thread = PRReviewThread(
        id="",
        path="src/bar.py",
        line=20,
        is_resolved=False,
        is_outdated=False,
        comments=(
            PRReviewComment(
                id=1,
                body="Invalid comment",
                author="reviewer",
                path="src/bar.py",
                line=20,
                created_at="2024-01-01T10:00:00Z",
            ),
        ),
    )
    pr_details = make_pr_details(123)

    fake_github_issues = FakeGitHubIssues(comments_with_urls={123: []})
    fake_github = FakeGitHub(
        issues_gateway=fake_github_issues,
        pr_details={123: pr_details},
        pr_review_threads={123: [valid_thread, invalid_thread]},
    )
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_feedback,
            ["--pr", "123"],
            obj=ErkContext.for_test(
                github=fake_github,
                git=FakeGit(),
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert len(output["review_threads"]) == 1
    assert output["review_threads"][0]["id"] == "PRRT_valid"


# ============================================================================
# Error Cases
# ============================================================================


def test_get_pr_feedback_pr_not_found(tmp_path: Path) -> None:
    """Test error when PR doesn't exist."""
    fake_github_issues = FakeGitHubIssues()
    fake_github = FakeGitHub(issues_gateway=fake_github_issues)
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_feedback,
            ["--pr", "999"],
            obj=ErkContext.for_test(
                github=fake_github,
                git=FakeGit(),
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0  # Graceful degradation
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "pr-not-found"


def test_get_pr_feedback_no_branch_detected(tmp_path: Path) -> None:
    """Test error when no branch can be detected and no --pr specified."""
    fake_github_issues = FakeGitHubIssues()
    fake_github = FakeGitHub(issues_gateway=fake_github_issues)
    fake_git = FakeGit()  # No current branch configured
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_feedback,
            [],
            obj=ErkContext.for_test(
                github=fake_github,
                git=fake_git,
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0  # Graceful degradation
    output = json.loads(result.output)
    assert output["success"] is False


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_get_pr_feedback_json_structure(tmp_path: Path) -> None:
    """Test JSON output contains all expected keys."""
    thread = make_thread(
        "PRRT_1", "src/foo.py", 42, "Fix this", is_resolved=False, is_outdated=True
    )
    pr_details = make_pr_details(123)
    comments = [make_issue_comment(100, "Discussion comment", author="reviewer", pr_number=123)]

    fake_github_issues = FakeGitHubIssues(comments_with_urls={123: comments})
    fake_github = FakeGitHub(
        issues_gateway=fake_github_issues,
        pr_details={123: pr_details},
        pr_review_threads={123: [thread]},
    )
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_feedback,
            ["--pr", "123"],
            obj=ErkContext.for_test(
                github=fake_github,
                git=FakeGit(),
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify top-level structure
    assert "success" in output
    assert "pr_number" in output
    assert "pr_url" in output
    assert "pr_title" in output
    assert "review_threads" in output
    assert "discussion_comments" in output

    # Verify review thread structure
    thread_data = output["review_threads"][0]
    assert "id" in thread_data
    assert "path" in thread_data
    assert "line" in thread_data
    assert "is_outdated" in thread_data
    assert "comments" in thread_data

    # Verify review comment structure
    comment_data = thread_data["comments"][0]
    assert "author" in comment_data
    assert "body" in comment_data
    assert "created_at" in comment_data

    # Verify discussion comment structure
    disc_data = output["discussion_comments"][0]
    assert "id" in disc_data
    assert "author" in disc_data
    assert "body" in disc_data
    assert "url" in disc_data
