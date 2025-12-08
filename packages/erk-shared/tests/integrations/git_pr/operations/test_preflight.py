"""Unit tests for git-only PR preflight operation.

Tests the preflight phase of the git-only PR workflow, including:
- GitHub authentication checks
- Branch state detection
- Push to remote
- PR creation (or finding existing)
- Diff extraction
"""

from pathlib import Path

from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from erk_shared.integrations.git_pr.fake import FakeGitPrKit
from erk_shared.integrations.git_pr.operations.preflight import execute_preflight
from erk_shared.integrations.git_pr.types import GitPreflightError, GitPreflightResult
from erk_shared.integrations.gt.events import CompletionEvent


def _get_completion_result(
    ops: FakeGitPrKit, cwd: Path, session_id: str
) -> GitPreflightResult | GitPreflightError:
    """Helper to run execute_preflight and return the final result."""
    result = None
    for event in execute_preflight(ops, cwd, session_id):
        if isinstance(event, CompletionEvent):
            result = event.result
    if result is None:
        msg = "execute_preflight did not yield a CompletionEvent"
        raise AssertionError(msg)
    return result


class TestGitPreflightAuthentication:
    """Tests for GitHub authentication checks."""

    def test_fails_when_github_not_authenticated(self, tmp_path: Path) -> None:
        """Preflight should fail early when GitHub CLI is not authenticated."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        fake_git = FakeGit(
            current_branches={repo_root: "feature"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
        )

        fake_github = FakeGitHub(authenticated=False)

        ops = FakeGitPrKit(git=fake_git, github=fake_github)
        result = _get_completion_result(ops, repo_root, session_id="test-session")

        assert isinstance(result, GitPreflightError)
        assert result.success is False
        assert result.error_type == "gh_not_authenticated"
        assert "gh auth login" in result.message


class TestGitPreflightBranchDetection:
    """Tests for branch state detection."""

    def test_fails_when_not_on_branch(self, tmp_path: Path) -> None:
        """Preflight should fail when in detached HEAD state."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # current_branch is None = detached HEAD
        fake_git = FakeGit(
            current_branches={repo_root: None},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
        )

        fake_github = FakeGitHub(authenticated=True)

        ops = FakeGitPrKit(git=fake_git, github=fake_github)
        result = _get_completion_result(ops, repo_root, session_id="test-session")

        assert isinstance(result, GitPreflightError)
        assert result.success is False
        assert result.error_type == "no_branch"
        assert "detached HEAD" in result.message


class TestGitPreflightPRCreation:
    """Tests for PR creation and finding existing PRs."""

    def test_finds_existing_pr(self, tmp_path: Path) -> None:
        """Preflight should find and use existing PR for branch."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        fake_git = FakeGit(
            current_branches={repo_root: "feature"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
            commits_ahead={(repo_root, "main"): 1},
            commit_messages_since={(repo_root, "main"): ["Initial commit"]},
        )

        existing_pr = PRDetails(
            number=42,
            url="https://github.com/test/repo/pull/42",
            title="Feature",
            body="Feature body",
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
            pr_diffs={42: "diff --git a/file.py b/file.py\n-old\n+new"},
        )

        ops = FakeGitPrKit(git=fake_git, github=fake_github)
        result = _get_completion_result(ops, repo_root, session_id="test-session")

        assert isinstance(result, GitPreflightResult)
        assert result.success is True
        assert result.pr_number == 42
        assert result.pr_created is False
        assert result.branch_name == "feature"


class TestGitPreflightCommitMessages:
    """Tests for commit message capture."""

    def test_captures_commit_messages(self, tmp_path: Path) -> None:
        """Preflight should capture commit messages for AI context."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        commit_messages = [
            "Add user authentication\n\nImplemented JWT auth.",
            "Fix login bug\n\nFixed edge case in login.",
        ]

        fake_git = FakeGit(
            current_branches={repo_root: "feature"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
            commits_ahead={(repo_root, "main"): 2},
            commit_messages_since={(repo_root, "main"): commit_messages},
        )

        existing_pr = PRDetails(
            number=99,
            url="https://github.com/test/repo/pull/99",
            title="Feature",
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
                    number=99,
                    state="OPEN",
                    url="https://github.com/test/repo/pull/99",
                    is_draft=False,
                    title="Feature",
                    checks_passing=True,
                    owner="test",
                    repo="repo",
                ),
            },
            pr_details={99: existing_pr},
            pr_diffs={99: "diff"},
        )

        ops = FakeGitPrKit(git=fake_git, github=fake_github)
        result = _get_completion_result(ops, repo_root, session_id="test-session")

        assert isinstance(result, GitPreflightResult)
        assert result.success is True
        assert result.commit_messages is not None
        assert len(result.commit_messages) == 2
        assert "Add user authentication" in result.commit_messages[0]
        assert "Fix login bug" in result.commit_messages[1]
