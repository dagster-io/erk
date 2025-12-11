"""Unit tests for Graphite enhancement operation.

Tests the execute_graphite_enhance() function which adds Graphite stack metadata
to an existing PR created via git + gh.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.git.abc import Git
from erk_shared.git.fake import FakeGit
from erk_shared.github.abc import GitHub
from erk_shared.github.fake import FakeGitHub
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.pr.graphite_enhance import (
    execute_graphite_enhance,
    should_enhance_with_graphite,
)
from erk_shared.integrations.pr.types import (
    GraphiteEnhanceError,
    GraphiteEnhanceResult,
    GraphiteSkipped,
)


# Helper to create BranchMetadata for tests
def _make_branch(name: str, parent: str | None) -> BranchMetadata:
    """Create a BranchMetadata for tests."""
    return BranchMetadata(
        name=name,
        parent=parent,
        children=[],
        is_trunk=parent is None,
        commit_sha="abc123",
    )


@dataclass
class FakePrKit:
    """Fake PrKit implementation for testing."""

    git: Git
    github: GitHub
    graphite: Graphite


class TestExecuteGraphiteEnhance:
    """Tests for execute_graphite_enhance function."""

    def test_skips_when_graphite_not_authenticated(self, tmp_path: Path) -> None:
        """Test that unauthenticated Graphite skips enhancement gracefully."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite(authenticated=False)
        ops = FakePrKit(git=git, github=github, graphite=graphite)

        events = list(execute_graphite_enhance(ops, tmp_path, pr_number=42))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, GraphiteSkipped)
        assert result.success is True
        assert result.reason == "not_authenticated"

    def test_skips_when_branch_not_tracked(self, tmp_path: Path) -> None:
        """Test that untracked branch skips enhancement gracefully."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub(authenticated=True)
        # Empty branches dict means branch is not tracked
        graphite = FakeGraphite(authenticated=True, branches={})
        ops = FakePrKit(git=git, github=github, graphite=graphite)

        events = list(execute_graphite_enhance(ops, tmp_path, pr_number=42))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, GraphiteSkipped)
        assert result.success is True
        assert result.reason == "not_tracked"

    def test_skips_when_not_on_branch(self, tmp_path: Path) -> None:
        """Test that detached HEAD skips enhancement."""
        git = FakeGit(
            current_branches={tmp_path: None},  # Detached HEAD
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite(authenticated=True)
        ops = FakePrKit(git=git, github=github, graphite=graphite)

        events = list(execute_graphite_enhance(ops, tmp_path, pr_number=42))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, GraphiteSkipped)
        assert result.reason == "no_branch"

    def test_enhances_pr_when_branch_is_tracked(self, tmp_path: Path) -> None:
        """Test successful Graphite enhancement when branch is tracked."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature-branch": _make_branch("feature-branch", "main"),
            },
        )
        ops = FakePrKit(git=git, github=github, graphite=graphite)

        events = list(execute_graphite_enhance(ops, tmp_path, pr_number=42))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, GraphiteEnhanceResult)
        assert result.success is True
        assert result.graphite_url.startswith("https://app.graphite.com/")

        # Verify submit_stack was called
        assert len(graphite._submit_stack_calls) == 1
        repo_root, publish, restack, quiet, force = graphite._submit_stack_calls[0]
        assert repo_root == tmp_path
        assert publish is True

    def test_returns_error_on_graphite_submit_failure(self, tmp_path: Path) -> None:
        """Test that Graphite submission failure returns error."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature-branch": _make_branch("feature-branch", "main"),
            },
            submit_stack_raises=RuntimeError("Graphite submit failed: network error"),
        )
        ops = FakePrKit(git=git, github=github, graphite=graphite)

        events = list(execute_graphite_enhance(ops, tmp_path, pr_number=42))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, GraphiteEnhanceError)
        assert result.success is False
        assert result.error_type == "graphite_submit_failed"

    def test_handles_conflict_during_submit(self, tmp_path: Path) -> None:
        """Test that conflicts during Graphite submit are reported."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature-branch": _make_branch("feature-branch", "main"),
            },
            submit_stack_raises=RuntimeError("Merge conflict detected during rebase"),
        )
        ops = FakePrKit(git=git, github=github, graphite=graphite)

        events = list(execute_graphite_enhance(ops, tmp_path, pr_number=42))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, GraphiteEnhanceError)
        assert result.error_type == "graphite_conflict"

    def test_emits_progress_events(self, tmp_path: Path) -> None:
        """Test that progress events are emitted throughout enhancement."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature-branch": _make_branch("feature-branch", "main"),
            },
        )
        ops = FakePrKit(git=git, github=github, graphite=graphite)

        events = list(execute_graphite_enhance(ops, tmp_path, pr_number=42))

        progress_events = [e for e in events if isinstance(e, ProgressEvent)]
        assert len(progress_events) >= 3  # Auth check, track check, submit

        messages = [e.message for e in progress_events]
        assert any("authentication" in m.lower() for m in messages)
        assert any("tracked" in m.lower() for m in messages)


class TestShouldEnhanceWithGraphite:
    """Tests for should_enhance_with_graphite helper function."""

    def test_returns_false_when_not_authenticated(self, tmp_path: Path) -> None:
        """Test returns False when Graphite is not authenticated."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite(authenticated=False)
        ops = FakePrKit(git=git, github=github, graphite=graphite)

        should_enhance, reason = should_enhance_with_graphite(ops, tmp_path)

        assert should_enhance is False
        assert reason == "not_authenticated"

    def test_returns_false_when_branch_not_tracked(self, tmp_path: Path) -> None:
        """Test returns False when branch is not tracked by Graphite."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite(authenticated=True, branches={})
        ops = FakePrKit(git=git, github=github, graphite=graphite)

        should_enhance, reason = should_enhance_with_graphite(ops, tmp_path)

        assert should_enhance is False
        assert reason == "not_tracked"

    def test_returns_true_when_authenticated_and_tracked(self, tmp_path: Path) -> None:
        """Test returns True when Graphite is authenticated and branch is tracked."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature-branch": _make_branch("feature-branch", "main"),
            },
        )
        ops = FakePrKit(git=git, github=github, graphite=graphite)

        should_enhance, reason = should_enhance_with_graphite(ops, tmp_path)

        assert should_enhance is True
        assert reason == "tracked"
