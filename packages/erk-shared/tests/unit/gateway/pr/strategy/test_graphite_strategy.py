"""Tests for GraphiteSubmitStrategy."""

from pathlib import Path

from erk_shared.context.testing import context_for_test
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.graphite import GraphiteSubmitStrategy
from erk_shared.gateway.pr.strategy.types import (
    SubmitStrategyError,
    SubmitStrategyResult,
)
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo


def _create_pr_details(number: int, branch: str, base: str) -> PRDetails:
    """Create PRDetails for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title="My PR",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name=base,
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
        labels=(),
    )


def _create_pr_info(number: int) -> PullRequestInfo:
    """Create PullRequestInfo for testing."""
    return PullRequestInfo(
        number=number,
        state="OPEN",
        url=f"https://github.com/owner/repo/pull/{number}",
        is_draft=False,
        title="My PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )


class TestGraphiteSubmitStrategy:
    """Tests for GraphiteSubmitStrategy.execute()."""

    def test_happy_path_gt_submit_succeeds(self, tmp_path: Path) -> None:
        """Test successful submission via Graphite."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
        )
        # Configure with prs_by_branch for simple lookup
        github = FakeGitHub(
            authenticated=True,
            prs_by_branch={"feature-branch": _create_pr_details(42, "feature-branch", "main")},
        )
        graphite = FakeGraphite(authenticated=True)
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = GraphiteSubmitStrategy()
        events = list(strategy.execute(ctx, tmp_path, force=False))

        # Find the completion event
        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result

        assert isinstance(result, SubmitStrategyResult)
        assert result.pr_number == 42
        assert result.base_branch == "main"
        assert result.graphite_url == "https://app.graphite.com/github/pr/owner/repo/42"
        assert result.pr_url == "https://github.com/owner/repo/pull/42"
        assert result.branch_name == "feature-branch"
        assert result.was_created is True

    def test_returns_error_when_detached_head(self, tmp_path: Path) -> None:
        """Test that detached HEAD state returns error."""
        git = FakeGit(
            current_branches={tmp_path: None},  # Detached HEAD
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite(authenticated=True)
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = GraphiteSubmitStrategy()
        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result

        assert isinstance(result, SubmitStrategyError)
        assert result.error_type == "detached-head"
        assert "detached HEAD" in result.message

    def test_returns_error_when_gt_submit_fails(self, tmp_path: Path) -> None:
        """Test that gt submit failure returns error."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub(authenticated=True)
        graphite = FakeGraphite(
            authenticated=True,
            submit_stack_raises=RuntimeError("gt submit failed: network error"),
        )
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = GraphiteSubmitStrategy()
        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result

        assert isinstance(result, SubmitStrategyError)
        assert result.error_type == "graphite-submit-failed"
        assert "network error" in result.message

    def test_returns_error_when_pr_not_found_after_submit(self, tmp_path: Path) -> None:
        """Test error when PR not found after gt submit."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
        )
        # No PR exists for the branch
        github = FakeGitHub(authenticated=True, prs={})
        graphite = FakeGraphite(authenticated=True)
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = GraphiteSubmitStrategy()
        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result

        assert isinstance(result, SubmitStrategyError)
        assert result.error_type == "pr-not-found"
        assert "PR not found" in result.message
        assert "feature-branch" in result.message

    def test_commits_uncommitted_changes(self, tmp_path: Path) -> None:
        """Test that uncommitted changes are committed before submit."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
            file_statuses={tmp_path: ([], ["modified.py"], [])},  # Has uncommitted changes
        )
        github = FakeGitHub(
            authenticated=True,
            prs_by_branch={"feature-branch": _create_pr_details(42, "feature-branch", "main")},
        )
        graphite = FakeGraphite(authenticated=True)
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = GraphiteSubmitStrategy()
        list(strategy.execute(ctx, tmp_path, force=False))

        # Should have committed WIP changes
        assert len(git._commits) == 1
        cwd, message, _files = git._commits[0]
        assert cwd == tmp_path
        assert "WIP" in message

    def test_progress_events_are_yielded(self, tmp_path: Path) -> None:
        """Test that progress events are emitted during execution."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
        )
        github = FakeGitHub(
            authenticated=True,
            prs_by_branch={"feature-branch": _create_pr_details(42, "feature-branch", "main")},
        )
        graphite = FakeGraphite(authenticated=True)
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = GraphiteSubmitStrategy()
        events = list(strategy.execute(ctx, tmp_path, force=False))

        progress_events = [e for e in events if isinstance(e, ProgressEvent)]
        # Should have progress for: gt submit, getting PR info, ready
        assert len(progress_events) >= 3

        # Check specific progress messages
        messages = [e.message for e in progress_events]
        assert any("gt submit" in m.lower() for m in messages)
        assert any("pr info" in m.lower() for m in messages)

    def test_force_flag_is_passed_to_graphite(self, tmp_path: Path) -> None:
        """Test that force flag is passed through to Graphite submit."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
        )
        github = FakeGitHub(
            authenticated=True,
            prs_by_branch={"feature-branch": _create_pr_details(42, "feature-branch", "main")},
        )
        graphite = FakeGraphite(authenticated=True)
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = GraphiteSubmitStrategy()
        list(strategy.execute(ctx, tmp_path, force=True))

        # Verify force was passed to submit_stack
        assert len(graphite._submit_stack_calls) == 1
        repo_root, publish, restack, quiet, force = graphite._submit_stack_calls[0]
        assert repo_root == tmp_path
        assert force is True

    def test_uses_parent_branch_from_branch_manager(self, tmp_path: Path) -> None:
        """Test that parent branch comes from branch manager (via Graphite metadata)."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
        )
        github = FakeGitHub(
            authenticated=True,
            prs_by_branch={"feature-branch": _create_pr_details(42, "feature-branch", "main")},
        )
        # Configure Graphite with branch parent metadata
        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature-branch": BranchMetadata(
                    name="feature-branch",
                    parent="other-feature",  # Parent is different from trunk
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "other-feature": BranchMetadata(
                    name="other-feature",
                    parent="main",
                    children=["feature-branch"],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["other-feature"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = GraphiteSubmitStrategy()
        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        result = completion[0].result
        assert isinstance(result, SubmitStrategyResult)
        assert result.base_branch == "other-feature"
