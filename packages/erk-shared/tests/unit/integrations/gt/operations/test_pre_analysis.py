"""Unit tests for pre_analysis operation.

Tests the pre-analysis phase of the submit-branch workflow, including
detection of merged parent branches.
"""

from pathlib import Path

from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata
from erk_shared.integrations.gt.events import CompletionEvent
from erk_shared.integrations.gt.operations.pre_analysis import execute_pre_analysis
from erk_shared.integrations.gt.types import PreAnalysisError, PreAnalysisResult
from erk_shared.integrations.time.abc import Time
from erk_shared.integrations.time.fake import FakeTime


class FakeGtKit:
    """Fake GtKit for testing pre_analysis."""

    def __init__(self, git: FakeGit, github: FakeGitHub, graphite: FakeGraphite) -> None:
        self._git = git
        self._github = github
        self._graphite = graphite
        self._time = FakeTime()

    @property
    def git(self) -> FakeGit:
        return self._git

    @property
    def github(self) -> FakeGitHub:
        return self._github

    @property
    def graphite(self) -> FakeGraphite:
        return self._graphite

    @property
    def time(self) -> Time:
        return self._time


def _get_completion_result(ops: FakeGtKit, cwd: Path) -> PreAnalysisResult | PreAnalysisError:
    """Helper to run execute_pre_analysis and return the final result."""
    result = None
    for event in execute_pre_analysis(ops, cwd):
        if isinstance(event, CompletionEvent):
            result = event.result
    if result is None:
        msg = "execute_pre_analysis did not yield a CompletionEvent"
        raise AssertionError(msg)
    return result


class TestPreAnalysisDetectsMergedParent:
    """Tests for detecting merged parent branches."""

    def test_detects_merged_parent_branch(self, tmp_path: Path) -> None:
        """Pre-analysis should fail early if parent branch PR is merged."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Setup: Current branch "feature-child" has parent "feature-parent"
        # Parent branch has a MERGED PR
        fake_git = FakeGit(
            current_branches={repo_root: "feature-child"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
            commits_ahead={(repo_root, "feature-parent"): 1},
        )

        fake_graphite = FakeGraphite(
            branches={
                "feature-child": BranchMetadata(
                    name="feature-child",
                    parent="feature-parent",
                    children=[],
                    is_trunk=False,
                    commit_sha="abc123",
                ),
                "feature-parent": BranchMetadata(
                    name="feature-parent",
                    parent="main",
                    children=["feature-child"],
                    is_trunk=False,
                    commit_sha="def456",
                ),
            },
        )

        # Parent branch has a MERGED PR
        parent_pr = PRDetails(
            number=42,
            url="https://github.com/test/repo/pull/42",
            title="Feature parent",
            body="Parent PR body",
            state="MERGED",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature-parent",
            is_cross_repository=False,
            mergeable="UNKNOWN",
            merge_state_status="UNKNOWN",
            owner="test",
            repo="repo",
        )

        fake_github = FakeGitHub(
            prs={
                "feature-parent": PullRequestInfo(
                    number=42,
                    state="MERGED",
                    url="https://github.com/test/repo/pull/42",
                    is_draft=False,
                    title="Feature parent",
                    checks_passing=True,
                    owner="test",
                    repo="repo",
                ),
            },
            pr_details={42: parent_pr},
        )

        ops = FakeGtKit(fake_git, fake_github, fake_graphite)
        result = _get_completion_result(ops, repo_root)

        # Should fail with parent_merged error
        assert isinstance(result, PreAnalysisError)
        assert result.success is False
        assert result.error_type == "parent_merged"
        assert "feature-parent" in result.message
        assert "gt sync" in result.message
        assert result.details["parent_branch"] == "feature-parent"
        assert result.details["pr_number"] == "42"

    def test_allows_submission_when_parent_not_merged(self, tmp_path: Path) -> None:
        """Pre-analysis should succeed when parent branch PR is still open."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Setup: Current branch "feature-child" has parent "feature-parent"
        # Parent branch has an OPEN PR
        fake_git = FakeGit(
            current_branches={repo_root: "feature-child"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
            commits_ahead={(repo_root, "feature-parent"): 1},
        )

        fake_graphite = FakeGraphite(
            branches={
                "feature-child": BranchMetadata(
                    name="feature-child",
                    parent="feature-parent",
                    children=[],
                    is_trunk=False,
                    commit_sha="abc123",
                ),
                "feature-parent": BranchMetadata(
                    name="feature-parent",
                    parent="main",
                    children=["feature-child"],
                    is_trunk=False,
                    commit_sha="def456",
                ),
            },
        )

        # Parent branch has an OPEN PR
        parent_pr = PRDetails(
            number=42,
            url="https://github.com/test/repo/pull/42",
            title="Feature parent",
            body="Parent PR body",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature-parent",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="test",
            repo="repo",
        )

        # Child branch also needs a PR for the merge conflict check
        child_pr = PRDetails(
            number=43,
            url="https://github.com/test/repo/pull/43",
            title="Feature child",
            body="Child PR body",
            state="OPEN",
            is_draft=False,
            base_ref_name="feature-parent",
            head_ref_name="feature-child",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="test",
            repo="repo",
        )

        fake_github = FakeGitHub(
            prs={
                "feature-parent": PullRequestInfo(
                    number=42,
                    state="OPEN",
                    url="https://github.com/test/repo/pull/42",
                    is_draft=False,
                    title="Feature parent",
                    checks_passing=True,
                    owner="test",
                    repo="repo",
                ),
                "feature-child": PullRequestInfo(
                    number=43,
                    state="OPEN",
                    url="https://github.com/test/repo/pull/43",
                    is_draft=False,
                    title="Feature child",
                    checks_passing=True,
                    owner="test",
                    repo="repo",
                ),
            },
            pr_details={42: parent_pr, 43: child_pr},
        )

        ops = FakeGtKit(fake_git, fake_github, fake_graphite)
        result = _get_completion_result(ops, repo_root)

        # Should succeed
        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.branch_name == "feature-child"
        assert result.parent_branch == "feature-parent"

    def test_skips_check_when_parent_is_trunk(self, tmp_path: Path) -> None:
        """Pre-analysis should skip merged parent check when parent is trunk."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Setup: Current branch "feature" has parent "main" (trunk)
        fake_git = FakeGit(
            current_branches={repo_root: "feature"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
            commits_ahead={(repo_root, "main"): 1},
        )

        fake_graphite = FakeGraphite(
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="abc123",
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha="def456",
                ),
            },
        )

        fake_github = FakeGitHub()

        ops = FakeGtKit(fake_git, fake_github, fake_graphite)
        result = _get_completion_result(ops, repo_root)

        # Should succeed - no merged parent check for trunk parent
        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.branch_name == "feature"
        assert result.parent_branch == "main"

    def test_allows_submission_when_parent_has_no_pr(self, tmp_path: Path) -> None:
        """Pre-analysis should succeed when parent branch has no PR."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Setup: Current branch "feature-child" has parent "feature-parent"
        # Parent branch has NO PR
        fake_git = FakeGit(
            current_branches={repo_root: "feature-child"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
            commits_ahead={(repo_root, "feature-parent"): 1},
        )

        fake_graphite = FakeGraphite(
            branches={
                "feature-child": BranchMetadata(
                    name="feature-child",
                    parent="feature-parent",
                    children=[],
                    is_trunk=False,
                    commit_sha="abc123",
                ),
                "feature-parent": BranchMetadata(
                    name="feature-parent",
                    parent="main",
                    children=["feature-child"],
                    is_trunk=False,
                    commit_sha="def456",
                ),
            },
        )

        # No PR for parent branch
        fake_github = FakeGitHub()

        ops = FakeGtKit(fake_git, fake_github, fake_graphite)
        result = _get_completion_result(ops, repo_root)

        # Should succeed - no merged parent if no PR exists
        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.branch_name == "feature-child"
        assert result.parent_branch == "feature-parent"


class TestPreAnalysisCapturesCommitMessages:
    """Tests for commit message capture in pre-analysis."""

    def test_captures_commit_messages_before_squash(self, tmp_path: Path) -> None:
        """Pre-analysis should capture commit messages before squashing."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        commit_messages = [
            "First commit\n\nAdded initial feature.",
            "Second commit\n\nFixed bug in feature.",
        ]

        fake_git = FakeGit(
            current_branches={repo_root: "feature"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
            commits_ahead={(repo_root, "main"): 2},
            commit_messages_since={(repo_root, "main"): commit_messages},
        )

        fake_graphite = FakeGraphite(
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="abc123",
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha="def456",
                ),
            },
        )

        fake_github = FakeGitHub()

        ops = FakeGtKit(fake_git, fake_github, fake_graphite)
        result = _get_completion_result(ops, repo_root)

        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.commit_messages is not None
        assert len(result.commit_messages) == 2
        assert "First commit" in result.commit_messages[0]
        assert "Second commit" in result.commit_messages[1]

    def test_handles_no_commit_messages(self, tmp_path: Path) -> None:
        """Pre-analysis should handle case where no commit messages returned."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        fake_git = FakeGit(
            current_branches={repo_root: "feature"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
            commits_ahead={(repo_root, "main"): 1},
            # No commit_messages_since configured - will return empty list
        )

        fake_graphite = FakeGraphite(
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="abc123",
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha="def456",
                ),
            },
        )

        fake_github = FakeGitHub()

        ops = FakeGtKit(fake_git, fake_github, fake_graphite)
        result = _get_completion_result(ops, repo_root)

        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        # Empty list should be converted to None
        assert result.commit_messages is None


class TestPreAnalysisIssueLinking:
    """Tests for issue linking during pre-analysis."""

    def test_amends_commit_with_closes_tag_when_issue_reference_exists(
        self, tmp_path: Path
    ) -> None:
        """Pre-analysis should amend commit message with Closes #N when issue.json exists."""
        import json

        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Create .impl/issue.json
        impl_dir = repo_root / ".impl"
        impl_dir.mkdir()
        issue_data = {
            "issue_number": 123,
            "issue_url": "https://github.com/test/repo/issues/123",
            "created_at": "2024-01-01T00:00:00Z",
            "synced_at": "2024-01-01T00:00:00Z",
        }
        (impl_dir / "issue.json").write_text(json.dumps(issue_data), encoding="utf-8")

        fake_git = FakeGit(
            current_branches={repo_root: "feature"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
            commits_ahead={(repo_root, "main"): 1},
            head_commit_messages_full={repo_root: "Implement feature\n\nAdded the feature."},
        )

        fake_graphite = FakeGraphite(
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="abc123",
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha="def456",
                ),
            },
        )

        fake_github = FakeGitHub()

        ops = FakeGtKit(fake_git, fake_github, fake_graphite)
        result = _get_completion_result(ops, repo_root)

        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.issue_number == 123

        # Check that amend_commit was called with the Closes tag
        assert len(fake_git.commits) == 1
        _cwd, message, _files = fake_git.commits[0]
        assert "Closes #123" in message
        assert "Implement feature" in message

    def test_does_not_duplicate_closes_tag_if_already_present(self, tmp_path: Path) -> None:
        """Pre-analysis should not add duplicate Closes #N if already in commit message."""
        import json

        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Create .impl/issue.json
        impl_dir = repo_root / ".impl"
        impl_dir.mkdir()
        issue_data = {
            "issue_number": 123,
            "issue_url": "https://github.com/test/repo/issues/123",
            "created_at": "2024-01-01T00:00:00Z",
            "synced_at": "2024-01-01T00:00:00Z",
        }
        (impl_dir / "issue.json").write_text(json.dumps(issue_data), encoding="utf-8")

        # Commit message already has Closes #123
        fake_git = FakeGit(
            current_branches={repo_root: "feature"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
            commits_ahead={(repo_root, "main"): 1},
            head_commit_messages_full={
                repo_root: "Implement feature\n\nAdded the feature.\n\nCloses #123"
            },
        )

        fake_graphite = FakeGraphite(
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="abc123",
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha="def456",
                ),
            },
        )

        fake_github = FakeGitHub()

        ops = FakeGtKit(fake_git, fake_github, fake_graphite)
        result = _get_completion_result(ops, repo_root)

        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.issue_number == 123

        # amend_commit should NOT have been called since tag already exists
        # (FakeGit.commits would be empty if no commit/amend was made)
        assert len(fake_git.commits) == 0

    def test_skips_issue_linking_when_no_issue_reference(self, tmp_path: Path) -> None:
        """Pre-analysis should skip issue linking when no .impl/issue.json exists."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # No .impl/issue.json created

        fake_git = FakeGit(
            current_branches={repo_root: "feature"},
            trunk_branches={repo_root: "main"},
            repository_roots={repo_root: repo_root},
            commits_ahead={(repo_root, "main"): 1},
        )

        fake_graphite = FakeGraphite(
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="abc123",
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha="def456",
                ),
            },
        )

        fake_github = FakeGitHub()

        ops = FakeGtKit(fake_git, fake_github, fake_graphite)
        result = _get_completion_result(ops, repo_root)

        assert isinstance(result, PreAnalysisResult)
        assert result.success is True
        assert result.issue_number is None

        # No amend_commit should have been called
        assert len(fake_git.commits) == 0
