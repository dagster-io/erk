"""Unit tests for WtStack.

Tests the WtStack class which provides worktree stack operations
with internal Graphite availability handling.
"""

from pathlib import Path

from erk_shared.git.fake import FakeGit
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata
from erk_shared.integrations.wt_stack.wt_stack import WtStack


class TestGetParent:
    """Tests for WtStack.get_parent() method."""

    def test_returns_none_when_graphite_unavailable(self, tmp_path: Path) -> None:
        """When Graphite is None, get_parent() returns None."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
        )
        wt_stack = WtStack(git=git, repo_root=tmp_path, graphite=None)

        result = wt_stack.get_parent("feature-branch")

        assert result is None

    def test_returns_none_when_branch_not_tracked(self, tmp_path: Path) -> None:
        """When branch is not tracked by Graphite, get_parent() returns None."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
        )
        graphite = FakeGraphite(authenticated=True, branches={})
        wt_stack = WtStack(git=git, repo_root=tmp_path, graphite=graphite)

        result = wt_stack.get_parent("feature-branch")

        assert result is None

    def test_returns_parent_when_tracked(self, tmp_path: Path) -> None:
        """When branch is tracked, get_parent() returns the parent branch."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
        )
        branches = {
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=["feature-branch"],
                is_trunk=True,
                commit_sha="abc123",
            ),
            "feature-branch": BranchMetadata(
                name="feature-branch",
                parent="main",
                children=[],
                is_trunk=False,
                commit_sha="def456",
            ),
        }
        graphite = FakeGraphite(authenticated=True, branches=branches)
        wt_stack = WtStack(git=git, repo_root=tmp_path, graphite=graphite)

        result = wt_stack.get_parent("feature-branch")

        assert result == "main"

    def test_returns_none_for_trunk_branch(self, tmp_path: Path) -> None:
        """Trunk branch has no parent, so get_parent() returns None."""
        git = FakeGit(
            current_branches={tmp_path: "main"},
            repository_roots={tmp_path: tmp_path},
        )
        branches = {
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=["feature-branch"],
                is_trunk=True,
                commit_sha="abc123",
            ),
        }
        graphite = FakeGraphite(authenticated=True, branches=branches)
        wt_stack = WtStack(git=git, repo_root=tmp_path, graphite=graphite)

        result = wt_stack.get_parent("main")

        assert result is None
