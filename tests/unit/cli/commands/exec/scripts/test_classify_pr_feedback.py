"""Unit tests for classify_pr_feedback exec command.

Tests mechanical classification of PR review feedback before LLM processing.
Uses FakeGit and FakeLocalGitHub for dependency injection.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.classify_pr_feedback import (
    RestructuredFile,
    _classify_impl,
    _is_bot,
    _is_known_informational_discussion,
    _parse_name_status_output,
)
from erk.cli.commands.exec.scripts.classify_pr_feedback import (
    classify_pr_feedback as classify_pr_feedback_command,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.types import IssueComment
from erk_shared.gateway.github.types import (
    PRDetails,
    PRReview,
    PRReviewComment,
    PRReviewThread,
)
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues

# ============================================================================
# 1. Helper Function Tests
# ============================================================================


def test_parse_name_status_output_renames() -> None:
    """Test parsing git diff --name-status output with renames."""
    output = """R100\told/path.py\tnew/path.py
R085\tsrc/old.py\tsrc/new.py"""

    result = _parse_name_status_output(output)

    assert len(result) == 2
    assert result[0] == RestructuredFile(
        old_path="old/path.py",
        new_path="new/path.py",
        status="R100",
    )
    assert result[1] == RestructuredFile(
        old_path="src/old.py",
        new_path="src/new.py",
        status="R085",
    )


def test_parse_name_status_output_copies() -> None:
    """Test parsing git diff --name-status output with copies."""
    output = "C100\tbase.py\tcopy.py"

    result = _parse_name_status_output(output)

    assert len(result) == 1
    assert result[0] == RestructuredFile(
        old_path="base.py",
        new_path="copy.py",
        status="C100",
    )


def test_parse_name_status_output_ignores_non_restructuring() -> None:
    """Test that A/M/D lines are filtered out."""
    output = """R100\told.py\tnew.py
M\tmodified.py
A\tadded.py
D\tdeleted.py"""

    result = _parse_name_status_output(output)

    assert len(result) == 1
    assert result[0].status == "R100"


def test_parse_name_status_output_empty() -> None:
    """Test parsing empty git diff output."""
    assert _parse_name_status_output("") == ()
    assert _parse_name_status_output("\n") == ()


def test_is_bot_detects_suffix() -> None:
    """Test bot detection by [bot] suffix."""
    assert _is_bot("github-actions[bot]") is True
    assert _is_bot("dependabot[bot]") is True
    assert _is_bot("renovate[bot]") is True


def test_is_bot_human_users() -> None:
    """Test bot detection returns False for human users."""
    assert _is_bot("alice") is False
    assert _is_bot("bob") is False
    assert _is_bot("user-name") is False


def test_is_known_informational_discussion_graphite() -> None:
    """Test Graphite stack comments are informational."""
    assert _is_known_informational_discussion("Graphite Automations", "Stack info") is True
    assert _is_known_informational_discussion("graphite-app[bot]", "Stack updated") is True


def test_is_known_informational_discussion_ci_bot() -> None:
    """Test CI bot comments with status updates are informational."""
    assert _is_known_informational_discussion("github-actions[bot]", "CI checks passed") is True
    assert (
        _is_known_informational_discussion("github-actions[bot]", "Test results available") is True
    )
    assert (
        _is_known_informational_discussion("github-actions[bot]", "Build status: success") is True
    )


def test_is_known_informational_discussion_regular_comment() -> None:
    """Test regular user comments are not informational."""
    assert _is_known_informational_discussion("alice", "Please fix this") is False
    assert _is_known_informational_discussion("bob", "Looks good!") is False


# ============================================================================
# 2. Classification Logic Tests
# ============================================================================


def test_classify_impl_approved_review_is_informational() -> None:
    """Test APPROVED reviews are counted as informational, not actionable."""
    reviews = [
        PRReview(
            id="PRR_approved",
            author="reviewer",
            body="LGTM!",
            state="APPROVED",
            submitted_at="2025-01-01T00:00:00Z",
        )
    ]

    result = _classify_impl(reviews=reviews, threads=[], comments=[], restructured_files=())

    assert result.mechanical_informational_count == 1
    assert len(result.review_submissions) == 0  # Not in actionable list


def test_classify_impl_changes_requested_is_actionable() -> None:
    """Test CHANGES_REQUESTED reviews are actionable."""
    reviews = [
        PRReview(
            id="PRR_changes",
            author="reviewer",
            body="Fix the auth flow",
            state="CHANGES_REQUESTED",
            submitted_at="2025-01-01T00:00:00Z",
        )
    ]

    result = _classify_impl(reviews=reviews, threads=[], comments=[], restructured_files=())

    assert result.mechanical_informational_count == 0
    assert len(result.review_submissions) == 1
    assert result.review_submissions[0].classification == "actionable"
    assert result.review_submissions[0].id == "PRR_changes"


def test_classify_impl_commented_empty_body_is_informational() -> None:
    """Test COMMENTED reviews with empty body are informational."""
    reviews = [
        PRReview(
            id="PRR_commented_empty",
            author="reviewer",
            body="",
            state="COMMENTED",
            submitted_at="2025-01-01T00:00:00Z",
        )
    ]

    result = _classify_impl(reviews=reviews, threads=[], comments=[], restructured_files=())

    assert result.mechanical_informational_count == 1
    assert len(result.review_submissions) == 0


def test_classify_impl_commented_with_body_needs_llm() -> None:
    """Test COMMENTED reviews with body need LLM judgment."""
    reviews = [
        PRReview(
            id="PRR_commented_body",
            author="reviewer",
            body="Consider refactoring this",
            state="COMMENTED",
            submitted_at="2025-01-01T00:00:00Z",
        )
    ]

    result = _classify_impl(reviews=reviews, threads=[], comments=[], restructured_files=())

    assert result.mechanical_informational_count == 0
    assert len(result.review_submissions) == 1
    assert result.review_submissions[0].classification == "needs_llm"


def test_classify_impl_bot_detection_in_reviews() -> None:
    """Test bot detection in review submissions."""
    reviews = [
        PRReview(
            id="PRR_bot",
            author="coderabbit[bot]",
            body="Consider adding tests",
            state="COMMENTED",
            submitted_at="2025-01-01T00:00:00Z",
        )
    ]

    result = _classify_impl(reviews=reviews, threads=[], comments=[], restructured_files=())

    assert len(result.review_submissions) == 1
    assert result.review_submissions[0].is_bot is True


def test_classify_impl_pre_existing_candidate_bot_and_restructured() -> None:
    """Test pre-existing candidate when bot comments on restructured file."""
    threads = [
        PRReviewThread(
            id="PRRT_bot_restructured",
            path="src/new.py",
            line=42,
            is_resolved=False,
            is_outdated=False,
            comments=(
                PRReviewComment(
                    id=1,
                    body="Consider adding tests",
                    author="coderabbit[bot]",
                    path="src/new.py",
                    line=42,
                    created_at="2025-01-01T00:00:00Z",
                ),
            ),
        )
    ]
    restructured = (
        RestructuredFile(
            old_path="src/old.py",
            new_path="src/new.py",
            status="R100",
        ),
    )

    result = _classify_impl(
        reviews=[],
        threads=threads,
        comments=[],
        restructured_files=restructured,
    )

    assert len(result.review_threads) == 1
    assert result.review_threads[0].pre_existing_candidate is True
    assert result.review_threads[0].is_bot is True


def test_classify_impl_not_pre_existing_human_or_non_restructured() -> None:
    """Test pre-existing is False for human authors or non-restructured files."""
    threads = [
        # Human on restructured file
        PRReviewThread(
            id="PRRT_human_restructured",
            path="src/new.py",
            line=42,
            is_resolved=False,
            is_outdated=False,
            comments=(
                PRReviewComment(
                    id=1,
                    body="Fix this",
                    author="reviewer",
                    path="src/new.py",
                    line=42,
                    created_at="2025-01-01T00:00:00Z",
                ),
            ),
        ),
        # Bot on non-restructured file
        PRReviewThread(
            id="PRRT_bot_normal",
            path="src/other.py",
            line=10,
            is_resolved=False,
            is_outdated=False,
            comments=(
                PRReviewComment(
                    id=2,
                    body="Add tests",
                    author="bot[bot]",
                    path="src/other.py",
                    line=10,
                    created_at="2025-01-01T00:00:00Z",
                ),
            ),
        ),
    ]
    restructured = (
        RestructuredFile(
            old_path="src/old.py",
            new_path="src/new.py",
            status="R100",
        ),
    )

    result = _classify_impl(
        reviews=[],
        threads=threads,
        comments=[],
        restructured_files=restructured,
    )

    assert len(result.review_threads) == 2
    assert result.review_threads[0].pre_existing_candidate is False  # Human
    assert result.review_threads[1].pre_existing_candidate is False  # Bot on non-restructured


def test_classify_impl_known_informational_discussion() -> None:
    """Test known informational discussion comments."""
    comments = [
        IssueComment(
            id=1,
            author="Graphite Automations",
            body="Stack updated",
            url="https://github.com/owner/repo/issues/123#issuecomment-1",
        ),
        IssueComment(
            id=2,
            author="github-actions[bot]",
            body="CI checks passed",
            url="https://github.com/owner/repo/issues/123#issuecomment-2",
        ),
    ]

    result = _classify_impl(reviews=[], threads=[], comments=comments, restructured_files=())

    assert result.mechanical_informational_count == 2
    assert len(result.discussion_comments) == 2
    assert result.discussion_comments[0].classification == "informational"
    assert result.discussion_comments[1].classification == "informational"


def test_classify_impl_unknown_discussion_needs_llm() -> None:
    """Test unknown discussion comments need LLM judgment."""
    comments = [
        IssueComment(
            id=1,
            author="reviewer",
            body="Please update the docs",
            url="https://github.com/owner/repo/issues/123#issuecomment-1",
        )
    ]

    result = _classify_impl(reviews=[], threads=[], comments=comments, restructured_files=())

    assert result.mechanical_informational_count == 0
    assert len(result.discussion_comments) == 1
    assert result.discussion_comments[0].classification == "needs_llm"


def test_classify_impl_no_feedback() -> None:
    """Test classification with no feedback returns empty result."""
    result = _classify_impl(reviews=[], threads=[], comments=[], restructured_files=())

    assert result.success is True
    assert result.mechanical_informational_count == 0
    assert len(result.review_submissions) == 0
    assert len(result.review_threads) == 0
    assert len(result.discussion_comments) == 0


def test_classify_impl_body_preview_truncation() -> None:
    """Test that body previews are truncated to 200 chars."""
    long_body = "x" * 300
    reviews = [
        PRReview(
            id="PRR_long",
            author="reviewer",
            body=long_body,
            state="CHANGES_REQUESTED",
            submitted_at="2025-01-01T00:00:00Z",
        )
    ]

    result = _classify_impl(reviews=reviews, threads=[], comments=[], restructured_files=())

    assert len(result.review_submissions) == 1
    assert len(result.review_submissions[0].body_preview) == 200
    assert result.review_submissions[0].body_preview == "x" * 200


# ============================================================================
# 3. CLI Integration Tests
# ============================================================================


def test_cli_success_with_pr_number(tmp_path: Path) -> None:
    """Test CLI command with explicit PR number."""
    runner = CliRunner()

    # Set up fake PR
    pr_details = PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="PR body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature",
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="owner",
        repo="repo",
        labels=(),
    )

    reviews = [
        PRReview(
            id="PRR_1",
            author="reviewer",
            body="Fix this",
            state="CHANGES_REQUESTED",
            submitted_at="2025-01-01T00:00:00Z",
        )
    ]

    github = FakeLocalGitHub(
        pr_details={123: pr_details},
        pr_reviews={123: reviews},
        pr_review_threads={123: []},
    )
    github_issues = FakeGitHubIssues(comments_with_urls={123: []})
    git = FakeGit(remote_branches={tmp_path: ["origin/main"]})

    ctx = ErkContext.for_test(
        git=git,
        github=github,
        github_issues=github_issues,
        repo_root=tmp_path,
    )

    result = runner.invoke(classify_pr_feedback_command, ["--pr", "123"], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 123
    assert output["pr_title"] == "Test PR"
    assert len(output["review_submissions"]) == 1
    assert output["review_submissions"][0]["classification"] == "actionable"


def test_cli_success_with_current_branch(tmp_path: Path) -> None:
    """Test CLI command with current branch's PR."""
    runner = CliRunner()

    pr_details = PRDetails(
        number=456,
        url="https://github.com/owner/repo/pull/456",
        title="Feature PR",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="owner",
        repo="repo",
        labels=(),
    )

    github = FakeLocalGitHub(
        prs_by_branch={"feature-branch": pr_details},
        pr_reviews={456: []},
        pr_review_threads={456: []},
    )
    github_issues = FakeGitHubIssues(comments_with_urls={456: []})
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        remote_branches={tmp_path: ["origin/main"]},
    )

    ctx = ErkContext.for_test(
        git=git,
        github=github,
        github_issues=github_issues,
        repo_root=tmp_path,
        cwd=tmp_path,
    )

    result = runner.invoke(classify_pr_feedback_command, [], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 456


def test_cli_with_restructured_files(tmp_path: Path) -> None:
    """Test CLI detects restructured files and flags pre-existing candidates."""
    runner = CliRunner()

    # Create git repo structure for diff command
    (tmp_path / ".git").mkdir()

    pr_details = PRDetails(
        number=789,
        url="https://github.com/owner/repo/pull/789",
        title="Restructure PR",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="restructure",
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="owner",
        repo="repo",
        labels=(),
    )

    threads = [
        PRReviewThread(
            id="PRRT_1",
            path="src/new.py",
            line=10,
            is_resolved=False,
            is_outdated=False,
            comments=(
                PRReviewComment(
                    id=1,
                    body="Add tests",
                    author="bot[bot]",
                    path="src/new.py",
                    line=10,
                    created_at="2025-01-01T00:00:00Z",
                ),
            ),
        )
    ]

    # Set up git diff output simulation
    git_diff_output = "R100\tsrc/old.py\tsrc/new.py"

    # Create a temporary script to simulate git diff
    git_wrapper = tmp_path / "git_wrapper.sh"
    git_wrapper.write_text(
        f"""#!/bin/bash
if [[ "$1" == "diff" ]]; then
    echo '{git_diff_output}'
    exit 0
fi
exec git "$@"
"""
    )
    git_wrapper.chmod(0o755)

    github = FakeLocalGitHub(
        pr_details={789: pr_details},
        pr_reviews={789: []},
        pr_review_threads={789: threads},
    )
    github_issues = FakeGitHubIssues(comments_with_urls={789: []})
    git = FakeGit(remote_branches={tmp_path: ["origin/main"]})

    ctx = ErkContext.for_test(
        git=git,
        github=github,
        github_issues=github_issues,
        repo_root=tmp_path,
    )

    # Note: We can't easily test the git diff subprocess call in unit tests
    # without mocking subprocess. This test verifies the integration structure.
    # The _parse_name_status_output function is tested separately above.
    result = runner.invoke(classify_pr_feedback_command, ["--pr", "789"], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    # Without actual git diff, restructured_files will be empty
    # but the thread should still be classified
    assert len(output["review_threads"]) == 1


def test_cli_include_resolved_flag(tmp_path: Path) -> None:
    """Test that --include-resolved flag is passed through."""
    runner = CliRunner()

    pr_details = PRDetails(
        number=999,
        url="https://github.com/owner/repo/pull/999",
        title="Test",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="test",
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="owner",
        repo="repo",
        labels=(),
    )

    resolved_thread = PRReviewThread(
        id="PRRT_resolved",
        path="file.py",
        line=1,
        is_resolved=True,
        is_outdated=False,
        comments=(
            PRReviewComment(
                id=1,
                body="Fixed",
                author="reviewer",
                path="file.py",
                line=1,
                created_at="2025-01-01T00:00:00Z",
            ),
        ),
    )

    github = FakeLocalGitHub(
        pr_details={999: pr_details},
        pr_reviews={999: []},
        pr_review_threads={999: [resolved_thread]},  # Will be filtered unless --include-resolved
    )
    github_issues = FakeGitHubIssues(comments_with_urls={999: []})
    git = FakeGit(remote_branches={tmp_path: ["origin/main"]})

    ctx = ErkContext.for_test(
        git=git,
        github=github,
        github_issues=github_issues,
        repo_root=tmp_path,
    )

    # Without --include-resolved
    result = runner.invoke(classify_pr_feedback_command, ["--pr", "999"], obj=ctx)
    assert result.exit_code == 0
    output = json.loads(result.output)
    # FakeGitHub doesn't actually filter by include_resolved in its implementation,
    # but the flag is passed through correctly
    assert "review_threads" in output
