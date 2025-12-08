"""Unit tests for git-only PR finalize operation.

Tests the finalize phase of the git-only PR workflow, including:
- PR metadata updates
- Footer generation
- Temp file cleanup
"""

import json
from pathlib import Path

from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from erk_shared.integrations.git_pr.fake import FakeGitPrKit
from erk_shared.integrations.git_pr.operations.finalize import execute_finalize
from erk_shared.integrations.git_pr.types import GitFinalizeError, GitFinalizeResult
from erk_shared.integrations.gt.events import CompletionEvent


def _get_completion_result(
    ops: FakeGitPrKit,
    cwd: Path,
    pr_number: int,
    pr_title: str,
    pr_body: str | None = None,
    pr_body_file: Path | None = None,
    diff_file: str | None = None,
) -> GitFinalizeResult | GitFinalizeError:
    """Helper to run execute_finalize and return the final result."""
    result = None
    for event in execute_finalize(ops, cwd, pr_number, pr_title, pr_body, pr_body_file, diff_file):
        if isinstance(event, CompletionEvent):
            result = event.result
    if result is None:
        msg = "execute_finalize did not yield a CompletionEvent"
        raise AssertionError(msg)
    return result


class TestGitFinalizeUpdatesPRMetadata:
    """Tests for PR metadata updates."""

    def test_updates_pr_title_and_body(self, tmp_path: Path) -> None:
        """Finalize should update PR title and body."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        fake_git = FakeGit(
            current_branches={repo_root: "feature"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
        )

        existing_pr = PRDetails(
            number=42,
            url="https://github.com/test/repo/pull/42",
            title="Old Title",
            body="Old body",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="test",
            repo="repo",
        )

        fake_github = FakeGitHub(
            authenticated=True,
            prs={
                "feature": PullRequestInfo(
                    number=42,
                    state="OPEN",
                    url="https://github.com/test/repo/pull/42",
                    is_draft=False,
                    title="Feature",
                    checks_passing=True,
                    owner="test",
                    repo="repo",
                ),
            },
            pr_details={42: existing_pr},
        )

        ops = FakeGitPrKit(git=fake_git, github=fake_github)
        result = _get_completion_result(
            ops,
            repo_root,
            pr_number=42,
            pr_title="New Title",
            pr_body="New body content",
        )

        assert isinstance(result, GitFinalizeResult)
        assert result.success is True
        assert result.pr_number == 42
        assert result.pr_title == "New Title"

        # Verify the GitHub API was called with updated values
        assert len(fake_github.updated_pr_titles) == 1
        assert fake_github.updated_pr_titles[0] == (42, "New Title")
        assert len(fake_github.updated_pr_bodies) == 1
        # Body should include the checkout footer
        assert "erk pr checkout 42" in fake_github.updated_pr_bodies[0][1]

    def test_reads_body_from_file(self, tmp_path: Path) -> None:
        """Finalize should read PR body from file when --pr-body-file is provided."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Create a body file
        body_file = tmp_path / "body.txt"
        body_file.write_text("Body from file", encoding="utf-8")

        fake_git = FakeGit(
            current_branches={repo_root: "feature"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
        )

        existing_pr = PRDetails(
            number=42,
            url="https://github.com/test/repo/pull/42",
            title="Title",
            body="",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="test",
            repo="repo",
        )

        fake_github = FakeGitHub(
            authenticated=True,
            prs={
                "feature": PullRequestInfo(
                    number=42,
                    state="OPEN",
                    url="https://github.com/test/repo/pull/42",
                    is_draft=False,
                    title="Feature",
                    checks_passing=True,
                    owner="test",
                    repo="repo",
                ),
            },
            pr_details={42: existing_pr},
        )

        ops = FakeGitPrKit(git=fake_git, github=fake_github)
        result = _get_completion_result(
            ops,
            repo_root,
            pr_number=42,
            pr_title="Title",
            pr_body_file=body_file,
        )

        assert isinstance(result, GitFinalizeResult)
        assert result.success is True
        # Body should contain content from file plus footer
        assert "Body from file" in fake_github.updated_pr_bodies[0][1]


class TestGitFinalizeIncludesIssueClosing:
    """Tests for issue closing references in PR body."""

    def test_includes_closing_reference_when_issue_exists(self, tmp_path: Path) -> None:
        """Finalize should include 'Closes #N' when .impl/issue.json exists."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Create .impl/issue.json with issue reference (requires all fields)
        impl_dir = repo_root / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_data = {
            "issue_number": 123,
            "issue_url": "https://github.com/test/repo/issues/123",
            "created_at": "2025-01-01T00:00:00Z",
            "synced_at": "2025-01-01T00:00:00Z",
        }
        issue_json.write_text(json.dumps(issue_data), encoding="utf-8")

        fake_git = FakeGit(
            current_branches={repo_root: "feature"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
        )

        existing_pr = PRDetails(
            number=42,
            url="https://github.com/test/repo/pull/42",
            title="Title",
            body="",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="test",
            repo="repo",
        )

        fake_github = FakeGitHub(
            authenticated=True,
            prs={
                "feature": PullRequestInfo(
                    number=42,
                    state="OPEN",
                    url="https://github.com/test/repo/pull/42",
                    is_draft=False,
                    title="Feature",
                    checks_passing=True,
                    owner="test",
                    repo="repo",
                ),
            },
            pr_details={42: existing_pr},
        )

        ops = FakeGitPrKit(git=fake_git, github=fake_github)
        result = _get_completion_result(
            ops,
            repo_root,
            pr_number=42,
            pr_title="Title",
            pr_body="Feature body",
        )

        assert isinstance(result, GitFinalizeResult)
        assert result.success is True
        assert result.issue_number == 123
        # Body should include closing reference
        assert "Closes #123" in fake_github.updated_pr_bodies[0][1]


class TestGitFinalizeCleanup:
    """Tests for temp file cleanup."""

    def test_cleans_up_diff_file(self, tmp_path: Path) -> None:
        """Finalize should clean up temp diff file when provided."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Create a temp diff file
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("diff content", encoding="utf-8")

        fake_git = FakeGit(
            current_branches={repo_root: "feature"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
        )

        existing_pr = PRDetails(
            number=42,
            url="https://github.com/test/repo/pull/42",
            title="Title",
            body="",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="test",
            repo="repo",
        )

        fake_github = FakeGitHub(
            authenticated=True,
            prs={
                "feature": PullRequestInfo(
                    number=42,
                    state="OPEN",
                    url="https://github.com/test/repo/pull/42",
                    is_draft=False,
                    title="Feature",
                    checks_passing=True,
                    owner="test",
                    repo="repo",
                ),
            },
            pr_details={42: existing_pr},
        )

        ops = FakeGitPrKit(git=fake_git, github=fake_github)
        result = _get_completion_result(
            ops,
            repo_root,
            pr_number=42,
            pr_title="Title",
            pr_body="Body",
            diff_file=str(diff_file),
        )

        assert isinstance(result, GitFinalizeResult)
        assert result.success is True
        # Diff file should be deleted
        assert not diff_file.exists()
