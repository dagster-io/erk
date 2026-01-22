"""Tests for GraphiteSubmitStrategy."""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.branch_manager.abc import BranchManager
from erk_shared.branch_manager.fake import FakeBranchManager
from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.graphite import GraphiteSubmitStrategy
from erk_shared.gateway.pr.strategy.types import SubmitStrategyError, SubmitStrategyResult
from erk_shared.gateway.time.abc import Time
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.git.abc import Git
from erk_shared.git.fake import FakeGit
from erk_shared.github.abc import GitHub
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails


@dataclass(frozen=True)
class FakeGtKitContext:
    """Test implementation of GtKit Protocol."""

    git: Git
    github: GitHub
    graphite: Graphite
    time: Time
    branch_manager: BranchManager


def create_test_ops(
    *,
    current_branch: str = "feature-branch",
    has_uncommitted_changes: bool = False,
    pr_number: int = 123,
    parent_branch: str | None = None,
    submit_raises: Exception | None = None,
    pr_exists: bool = True,
) -> FakeGtKitContext:
    """Create a FakeGtKitContext with common test defaults."""
    repo_root = Path("/repo")

    # file_statuses controls has_uncommitted_changes: tuple of (staged, modified, untracked)
    file_statuses = None
    if has_uncommitted_changes:
        file_statuses = {repo_root: (["file.py"], [], [])}

    git = FakeGit(
        repository_roots={repo_root: repo_root},
        current_branches={repo_root: current_branch},
        trunk_branches={repo_root: "main"},
        file_statuses=file_statuses,
        remote_urls={(repo_root, "origin"): "https://github.com/test-owner/test-repo.git"},
    )

    pr_details = PRDetails(
        number=pr_number,
        url=f"https://github.com/test-owner/test-repo/pull/{pr_number}",
        title="Test PR",
        body="Test body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name=current_branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs_by_branch={current_branch: pr_details} if pr_exists else {},
    )

    graphite = FakeGraphite(
        submit_stack_raises=submit_raises,
        authenticated=True,
    )

    time = FakeTime()

    branch_manager = FakeBranchManager(
        parent_branches={current_branch: parent_branch} if parent_branch is not None else {},
    )

    return FakeGtKitContext(
        git=git,
        github=github,
        graphite=graphite,
        time=time,
        branch_manager=branch_manager,
    )


class TestGraphiteSubmitStrategyHappyPath:
    """Tests for successful GraphiteSubmitStrategy execution."""

    def test_returns_submit_strategy_result_on_success(self) -> None:
        """Happy path: gt submit succeeds and returns SubmitStrategyResult."""
        ops = create_test_ops(current_branch="feature-branch", pr_number=123)
        cwd = Path("/repo")
        strategy = GraphiteSubmitStrategy()

        events = list(strategy.execute(ops, cwd, force=False))

        # Should have progress events and completion
        assert len(events) > 0
        completion = events[-1]
        assert isinstance(completion, CompletionEvent)
        result = completion.result
        assert isinstance(result, SubmitStrategyResult)
        assert result.pr_number == 123
        assert result.branch_name == "feature-branch"
        assert result.graphite_url is not None
        assert "graphite" in result.graphite_url

    def test_uses_parent_branch_for_base_branch(self) -> None:
        """Base branch comes from branch_manager.get_parent_branch()."""
        ops = create_test_ops(
            current_branch="feature",
            parent_branch="develop",
            pr_number=456,
        )
        cwd = Path("/repo")
        strategy = GraphiteSubmitStrategy()

        events = list(strategy.execute(ops, cwd, force=False))

        completion = events[-1]
        assert isinstance(completion, CompletionEvent)
        result = completion.result
        assert isinstance(result, SubmitStrategyResult)
        assert result.base_branch == "develop"

    def test_falls_back_to_trunk_when_no_parent(self) -> None:
        """Falls back to trunk branch when no parent configured."""
        ops = create_test_ops(
            current_branch="feature",
            parent_branch=None,  # No parent
            pr_number=789,
        )
        cwd = Path("/repo")
        strategy = GraphiteSubmitStrategy()

        events = list(strategy.execute(ops, cwd, force=False))

        completion = events[-1]
        assert isinstance(completion, CompletionEvent)
        result = completion.result
        assert isinstance(result, SubmitStrategyResult)
        assert result.base_branch == "main"  # Trunk branch

    def test_commits_uncommitted_changes_first(self) -> None:
        """Uncommitted changes are committed before gt submit."""
        ops = create_test_ops(
            current_branch="feature",
            has_uncommitted_changes=True,
            pr_number=111,
        )
        cwd = Path("/repo")
        strategy = GraphiteSubmitStrategy()

        # Execute strategy to trigger commit
        list(strategy.execute(ops, cwd, force=False))

        # Verify commit happened
        # FakeGit.commits is a list of (cwd, message, options) tuples
        assert isinstance(ops.git, FakeGit)
        assert len(ops.git.commits) == 1
        commit_message = ops.git.commits[0][1]
        assert "WIP" in commit_message

    def test_yields_progress_events(self) -> None:
        """Progress events are yielded during execution."""
        ops = create_test_ops(current_branch="feature", pr_number=222)
        cwd = Path("/repo")
        strategy = GraphiteSubmitStrategy()

        events = list(strategy.execute(ops, cwd, force=False))

        progress_events = [e for e in events if isinstance(e, ProgressEvent)]
        assert len(progress_events) >= 2  # At least "Running gt submit" and "Getting PR info"


class TestGraphiteSubmitStrategyErrorCases:
    """Tests for error handling in GraphiteSubmitStrategy."""

    def test_returns_error_on_detached_head(self) -> None:
        """Error: detached HEAD returns SubmitStrategyError."""
        repo_root = Path("/repo")
        git = FakeGit(
            repository_roots={repo_root: repo_root},
            current_branches={repo_root: None},  # Detached HEAD
            trunk_branches={repo_root: "main"},
            remote_urls={(repo_root, "origin"): "https://github.com/test-owner/test-repo.git"},
        )

        ops = FakeGtKitContext(
            git=git,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            time=FakeTime(),
            branch_manager=FakeBranchManager(),
        )
        cwd = Path("/repo")
        strategy = GraphiteSubmitStrategy()

        events = list(strategy.execute(ops, cwd, force=False))

        # Should return error immediately
        assert len(events) == 1
        completion = events[0]
        assert isinstance(completion, CompletionEvent)
        error = completion.result
        assert isinstance(error, SubmitStrategyError)
        assert error.error_type == "detached_head"
        assert "detached HEAD" in error.message

    def test_returns_error_on_gt_submit_failure(self) -> None:
        """Error: gt submit fails returns SubmitStrategyError."""
        ops = create_test_ops(
            current_branch="feature",
            submit_raises=RuntimeError("Network timeout"),
        )
        cwd = Path("/repo")
        strategy = GraphiteSubmitStrategy()

        events = list(strategy.execute(ops, cwd, force=False))

        completion = events[-1]
        assert isinstance(completion, CompletionEvent)
        error = completion.result
        assert isinstance(error, SubmitStrategyError)
        assert error.error_type == "gt_submit_failed"
        assert "Network timeout" in error.message

    def test_returns_error_when_pr_not_found(self) -> None:
        """Error: PR not found after gt submit returns SubmitStrategyError."""
        ops = create_test_ops(
            current_branch="feature",
            pr_exists=False,
        )
        cwd = Path("/repo")
        strategy = GraphiteSubmitStrategy()

        events = list(strategy.execute(ops, cwd, force=False))

        completion = events[-1]
        assert isinstance(completion, CompletionEvent)
        error = completion.result
        assert isinstance(error, SubmitStrategyError)
        assert error.error_type == "pr_not_found"
        assert "PR not found" in error.message


class TestGraphiteSubmitStrategyForceFlag:
    """Tests for force flag behavior."""

    def test_passes_force_flag_to_gt_submit(self) -> None:
        """Force flag is passed to gt submit."""
        ops = create_test_ops(current_branch="feature", pr_number=333)
        cwd = Path("/repo")
        strategy = GraphiteSubmitStrategy()

        list(strategy.execute(ops, cwd, force=True))

        # Verify force flag was passed
        assert isinstance(ops.graphite, FakeGraphite)
        assert len(ops.graphite.submit_stack_calls) == 1
        _, publish, restack, quiet, force = ops.graphite.submit_stack_calls[0]
        assert force is True
        assert publish is True  # Always publishes


class TestFakeSubmitStrategy:
    """Tests for FakeSubmitStrategy."""

    def test_yields_configured_progress_and_result(self) -> None:
        """FakeSubmitStrategy yields configured progress messages and result."""
        from erk_shared.gateway.pr.strategy.fake import FakeSubmitStrategy

        result = SubmitStrategyResult(
            pr_number=999,
            base_branch="main",
            graphite_url="https://app.graphite.dev/...",
            pr_url="https://github.com/owner/repo/pull/999",
            branch_name="test-branch",
            was_created=True,
        )
        fake_strategy = FakeSubmitStrategy(
            result=result,
            progress_messages=("Step 1...", "Step 2..."),
        )

        # Create minimal ops for execute signature
        ops = create_test_ops(current_branch="test-branch", pr_number=999)
        cwd = Path("/repo")

        events = list(fake_strategy.execute(ops, cwd, force=False))

        assert len(events) == 3  # 2 progress + 1 completion
        assert isinstance(events[0], ProgressEvent)
        assert events[0].message == "Step 1..."
        assert isinstance(events[1], ProgressEvent)
        assert events[1].message == "Step 2..."
        assert isinstance(events[2], CompletionEvent)
        assert events[2].result == result

    def test_yields_error_result(self) -> None:
        """FakeSubmitStrategy can yield error results."""
        from erk_shared.gateway.pr.strategy.fake import FakeSubmitStrategy

        error = SubmitStrategyError(
            error_type="test_error",
            message="Test error message",
            details={"key": "value"},
        )
        fake_strategy = FakeSubmitStrategy(result=error)

        ops = create_test_ops(current_branch="test", pr_number=1)
        cwd = Path("/repo")

        events = list(fake_strategy.execute(ops, cwd, force=False))

        assert len(events) == 1
        completion = events[0]
        assert isinstance(completion, CompletionEvent)
        assert completion.result == error
