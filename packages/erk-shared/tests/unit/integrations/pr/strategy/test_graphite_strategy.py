"""Tests for GraphiteSubmitStrategy.

Tests the Graphite-first PR submission strategy that uses gt submit
for push and PR creation.
"""

from pathlib import Path

from erk_shared.context.testing import context_for_test
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.graphite import GraphiteSubmitStrategy
from erk_shared.gateway.pr.strategy.types import SubmitStrategyError, SubmitStrategyResult
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails


def _make_pr_details(
    *,
    number: int,
    branch: str,
    owner: str,
    repo: str,
) -> PRDetails:
    """Helper to create PRDetails for tests."""
    return PRDetails(
        number=number,
        url=f"https://github.com/{owner}/{repo}/pull/{number}",
        title="Feature PR",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner=owner,
        repo=repo,
        labels=(),
    )


class TestGraphiteSubmitStrategy:
    """Tests for GraphiteSubmitStrategy."""

    def test_returns_error_when_not_on_branch(self, tmp_path: Path) -> None:
        """Test that detached HEAD state returns error."""
        git = FakeGit(
            current_branches={tmp_path: None},  # Detached HEAD
            repository_roots={tmp_path: tmp_path},
        )
        github = FakeGitHub()
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = GraphiteSubmitStrategy()
        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, SubmitStrategyError)
        assert result.error_type == "no_branch"

    def test_returns_error_when_gt_submit_fails(self, tmp_path: Path) -> None:
        """Test that gt submit failure returns error."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
        )
        github = FakeGitHub()
        graphite = FakeGraphite(
            submit_stack_raises=RuntimeError("Conflict during submit"),
        )
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = GraphiteSubmitStrategy()
        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, SubmitStrategyError)
        assert result.error_type == "graphite_submit_failed"
        assert "Conflict during submit" in result.message

    def test_returns_error_when_pr_not_found_after_submit(self, tmp_path: Path) -> None:
        """Test that missing PR after gt submit returns error."""
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
        )
        github = FakeGitHub()  # No PR configured
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = GraphiteSubmitStrategy()
        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, SubmitStrategyError)
        assert result.error_type == "pr_not_found"
        assert "feature-branch" in result.message

    def test_returns_success_when_gt_submit_succeeds(self, tmp_path: Path) -> None:
        """Test successful submission via Graphite."""
        pr_details = _make_pr_details(
            number=42,
            branch="feature-branch",
            owner="owner",
            repo="repo",
        )
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
        )
        github = FakeGitHub(
            prs_by_branch={"feature-branch": pr_details},
        )
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = GraphiteSubmitStrategy()
        events = list(strategy.execute(ctx, tmp_path, force=False))

        # Find progress events
        progress_events = [e for e in events if isinstance(e, ProgressEvent)]
        assert len(progress_events) >= 3  # submit, getting PR info, ready

        # Find the completion event
        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        result = completion[0].result
        assert isinstance(result, SubmitStrategyResult)
        assert result.pr_number == 42
        assert result.base_branch == "main"
        assert result.branch_name == "feature-branch"
        assert result.pr_url == "https://github.com/owner/repo/pull/42"
        # Graphite URL is computed
        assert "graphite" in result.graphite_url.lower() or "owner/repo" in result.graphite_url
        assert result.was_created is True

        # Verify gt submit was called
        assert len(graphite.submit_stack_calls) == 1

    def test_passes_force_flag_to_gt_submit(self, tmp_path: Path) -> None:
        """Test that force flag is propagated to gt submit."""
        pr_details = _make_pr_details(
            number=42,
            branch="feature-branch",
            owner="owner",
            repo="repo",
        )
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
        )
        github = FakeGitHub(
            prs_by_branch={"feature-branch": pr_details},
        )
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = GraphiteSubmitStrategy()
        list(strategy.execute(ctx, tmp_path, force=True))

        # Verify force was passed to submit_stack
        assert graphite.last_submit_stack_force is True

    def test_uses_parent_branch_when_tracked(self, tmp_path: Path) -> None:
        """Test that parent branch is used as base_branch when available."""
        from erk_shared.gateway.graphite.types import BranchMetadata

        pr_details = _make_pr_details(
            number=42,
            branch="feature-branch",
            owner="owner",
            repo="repo",
        )
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
        )
        github = FakeGitHub(
            prs_by_branch={"feature-branch": pr_details},
        )
        # Configure branches with parent relationship via BranchMetadata
        graphite = FakeGraphite(
            branches={
                "feature-branch": BranchMetadata(
                    name="feature-branch",
                    parent="parent-branch",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "parent-branch": BranchMetadata(
                    name="parent-branch",
                    parent="main",
                    children=["feature-branch"],
                    is_trunk=False,
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
        assert result.base_branch == "parent-branch"

    def test_emits_progress_events(self, tmp_path: Path) -> None:
        """Test that progress events are emitted throughout execution."""
        pr_details = _make_pr_details(
            number=42,
            branch="feature-branch",
            owner="owner",
            repo="repo",
        )
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            repository_roots={tmp_path: tmp_path},
            trunk_branches={tmp_path: "main"},
            remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
        )
        github = FakeGitHub(
            prs_by_branch={"feature-branch": pr_details},
        )
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, github=github, graphite=graphite, cwd=tmp_path)

        strategy = GraphiteSubmitStrategy()
        events = list(strategy.execute(ctx, tmp_path, force=False))

        progress_events = [e for e in events if isinstance(e, ProgressEvent)]
        messages = [e.message for e in progress_events]

        # Should have progress messages for key steps
        assert any("gt submit" in m.lower() for m in messages)
        assert any("pr" in m.lower() for m in messages)
