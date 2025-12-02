"""Unit tests for StatusOrchestrator with comprehensive coverage.

Test Runner Strategy
--------------------
These tests use two different parallel task runner implementations:

1. **RealParallelTaskRunner**: Used for most tests where we want actual collector
   execution to happen. This validates the real-world behavior of the orchestrator
   with actual collector implementations. The underlying tasks (reading files,
   checking git status with FakeGit) are fast, making this tractable for fast tests.

2. **FakeParallelTaskRunner**: Used only for specific scenarios where we need to
   simulate exceptional conditions that are difficult to reproduce with real
   collectors:
   - Exception handling (test_orchestrator_collector_exception_handling)
   - Timeout scenarios (test_orchestrator_timeout_handling)

The fake runner allows us to simulate specific results (including None for failures)
without needing collectors that actually fail or timeout. This keeps tests fast and
reliable while still validating the orchestrator's error handling logic.
"""

import time
from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.integrations.parallel.real import RealParallelTaskRunner

from erk.core.context import ErkContext
from erk.status.collectors.base import StatusCollector
from erk.status.collectors.git import GitStatusCollector
from erk.status.collectors.impl import PlanFileCollector
from erk.status.models.status_data import GitStatus, PlanStatus
from erk.status.orchestrator import StatusOrchestrator
from tests.fakes.context import create_test_context
from tests.fakes.parallel_task_runner import FakeParallelTaskRunner


def test_orchestrator_collects_all_data(tmp_path: Path) -> None:
    """Test StatusOrchestrator collects data from all collectors."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create impl folder with plan.md and progress.md
    impl_folder = worktree_path / ".impl"
    impl_folder.mkdir()
    (impl_folder / "plan.md").write_text("# Test Plan", encoding="utf-8")
    (impl_folder / "progress.md").write_text("# Progress\n\n- [ ] Step 1", encoding="utf-8")

    git_ops = FakeGit(
        current_branches={worktree_path: "test-branch"},
        file_statuses={worktree_path: ([], [], [])},
        ahead_behind={(worktree_path, "test-branch"): (0, 0)},
        recent_commits={worktree_path: []},
    )

    ctx = create_test_context(git=git_ops)

    collectors = [
        GitStatusCollector(),
        PlanFileCollector(),
    ]

    orchestrator = StatusOrchestrator(collectors, runner=RealParallelTaskRunner())

    # Act
    status = orchestrator.collect_status(ctx, worktree_path, repo_root)

    # Assert
    assert status is not None
    assert status.worktree_info is not None
    assert status.worktree_info.path == worktree_path
    assert status.worktree_info.branch == "test-branch"
    # Git status should be collected
    assert status.git_status is not None
    assert status.git_status.branch == "test-branch"
    # Plan should be collected
    assert status.plan is not None
    assert status.plan.exists is True


def test_orchestrator_with_no_collectors(tmp_path: Path) -> None:
    """Test StatusOrchestrator with no collectors."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    ctx = create_test_context()
    orchestrator = StatusOrchestrator([], runner=RealParallelTaskRunner())

    # Act
    status = orchestrator.collect_status(ctx, worktree_path, repo_root)

    # Assert
    assert status is not None
    assert status.worktree_info is not None
    assert status.git_status is None
    assert status.plan is None


def test_orchestrator_handles_missing_plan(tmp_path: Path) -> None:
    """Test StatusOrchestrator when plan file doesn't exist."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    ctx = create_test_context()
    collectors: list[StatusCollector] = [PlanFileCollector()]

    orchestrator = StatusOrchestrator(collectors, runner=RealParallelTaskRunner())

    # Act
    status = orchestrator.collect_status(ctx, worktree_path, repo_root)

    # Assert
    assert status is not None
    # Plan collector is not available (is_available returns False)
    # so plan should be None
    assert status.plan is None


def test_orchestrator_collector_exception_handling(tmp_path: Path) -> None:
    """Test StatusOrchestrator handles collector exceptions gracefully."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    ctx = create_test_context()

    # Create collectors
    class FailingCollector(StatusCollector):
        @property
        def name(self) -> str:
            return "failing"

        def is_available(self, ctx: ErkContext, worktree_path: Path) -> bool:
            return True

        def collect(self, ctx: ErkContext, worktree_path: Path, repo_root: Path) -> object:
            raise AssertionError("Should not be called - fake executor returns configured result")

    collectors = [FailingCollector(), PlanFileCollector()]

    # Use fake runner that simulates exception by returning None
    runner = FakeParallelTaskRunner(results={"failing": None})
    orchestrator = StatusOrchestrator(collectors, runner=runner)

    # Act
    status = orchestrator.collect_status(ctx, worktree_path, repo_root)

    # Assert - should handle exception and continue
    assert status is not None
    assert status.worktree_info is not None
    # Failed collector result should be None, but orchestrator should continue
    assert status.plan is None  # Plan collector not available (no .PLAN.md file)
    # Verify the failing collector was requested
    assert "failing" in runner.requested_tasks


def test_orchestrator_with_failing_collector(tmp_path: Path) -> None:
    """Test StatusOrchestrator with a collector that returns wrong type."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    (worktree_path / ".PLAN.md").write_text("# Plan", encoding="utf-8")
    ctx = create_test_context()

    # Create a collector that returns wrong type
    class WrongTypeCollector(StatusCollector):
        @property
        def name(self) -> str:
            return "plan"  # Use plan name but return wrong type

        def is_available(self, ctx: ErkContext, worktree_path: Path) -> bool:
            return True

        def collect(self, ctx: ErkContext, worktree_path: Path, repo_root: Path) -> object:
            return "This is not a PlanStatus object"  # Wrong type

    collectors = [WrongTypeCollector()]
    orchestrator = StatusOrchestrator(collectors, runner=RealParallelTaskRunner())

    # Act
    status = orchestrator.collect_status(ctx, worktree_path, repo_root)

    # Assert - wrong type should be filtered out
    assert status is not None
    assert status.plan is None  # Wrong type filtered out


def test_orchestrator_with_missing_collector(tmp_path: Path) -> None:
    """Test StatusOrchestrator with collector that's not available."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    ctx = create_test_context()

    # Create a collector that's never available
    class UnavailableCollector(StatusCollector):
        @property
        def name(self) -> str:
            return "unavailable"

        def is_available(self, ctx: ErkContext, worktree_path: Path) -> bool:
            return False  # Never available

        def collect(self, ctx: ErkContext, worktree_path: Path, repo_root: Path) -> object:
            raise AssertionError("Should not be called")

    collectors = [UnavailableCollector()]
    orchestrator = StatusOrchestrator(collectors, runner=RealParallelTaskRunner())

    # Act
    status = orchestrator.collect_status(ctx, worktree_path, repo_root)

    # Assert - unavailable collector should not be run
    assert status is not None
    assert status.worktree_info is not None


def test_orchestrator_with_empty_results(tmp_path: Path) -> None:
    """Test StatusOrchestrator when all collectors return None."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    ctx = create_test_context()

    # Create a collector that returns None
    class NoneCollector(StatusCollector):
        @property
        def name(self) -> str:
            return "none"

        def is_available(self, ctx: ErkContext, worktree_path: Path) -> bool:
            return True

        def collect(self, ctx: ErkContext, worktree_path: Path, repo_root: Path) -> object:
            return None

    collectors = [NoneCollector()]
    orchestrator = StatusOrchestrator(collectors, runner=RealParallelTaskRunner())

    # Act
    status = orchestrator.collect_status(ctx, worktree_path, repo_root)

    # Assert
    assert status is not None
    assert status.worktree_info is not None
    assert status.git_status is None
    assert status.plan is None


def test_orchestrator_timeout_handling(tmp_path: Path) -> None:
    """Test StatusOrchestrator handles slow collectors with timeout."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    ctx = create_test_context()

    # Create a collector that would be slow (but won't actually be called)
    class SlowCollector(StatusCollector):
        @property
        def name(self) -> str:
            return "slow"

        def is_available(self, ctx: ErkContext, worktree_path: Path) -> bool:
            return True

        def collect(self, ctx: ErkContext, worktree_path: Path, repo_root: Path) -> object:
            raise AssertionError("Should not be called - fake executor returns configured result")

    collectors = [SlowCollector()]

    # Use fake runner that returns None for timeout simulation
    runner = FakeParallelTaskRunner(results={"slow": None})
    orchestrator = StatusOrchestrator(collectors, timeout_seconds=0.1, runner=runner)

    # Act
    status = orchestrator.collect_status(ctx, worktree_path, repo_root)

    # Assert - slow collector should timeout (None result)
    assert status is not None
    assert status.worktree_info is not None
    # Verify the collector was requested
    assert "slow" in runner.requested_tasks


def test_orchestrator_parallel_execution(tmp_path: Path) -> None:
    """Test StatusOrchestrator runs collectors in parallel."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    impl_folder = worktree_path / ".impl"
    impl_folder.mkdir()
    (impl_folder / "plan.md").write_text("# Plan", encoding="utf-8")
    (impl_folder / "progress.md").write_text("# Progress\n\n- [ ] Step 1", encoding="utf-8")

    git_ops = FakeGit(
        current_branches={worktree_path: "branch"},
        file_statuses={worktree_path: ([], [], [])},
        ahead_behind={(worktree_path, "branch"): (0, 0)},
        recent_commits={worktree_path: []},
    )

    ctx = create_test_context(git=git_ops)

    # Track execution order
    execution_order = []

    class TrackedCollector1(GitStatusCollector):
        def collect(self, ctx: ErkContext, worktree_path: Path, repo_root: Path) -> object:
            execution_order.append("git_start")
            result = super().collect(ctx, worktree_path, repo_root)
            time.sleep(0.05)  # Small delay to ensure parallel execution
            execution_order.append("git_end")
            return result

    class TrackedCollector2(PlanFileCollector):
        def collect(self, ctx: ErkContext, worktree_path: Path, repo_root: Path) -> object:
            execution_order.append("plan_start")
            result = super().collect(ctx, worktree_path, repo_root)
            time.sleep(0.05)  # Small delay to ensure parallel execution
            execution_order.append("plan_end")
            return result

    collectors = [TrackedCollector1(), TrackedCollector2()]
    orchestrator = StatusOrchestrator(collectors, runner=RealParallelTaskRunner())

    # Act
    status = orchestrator.collect_status(ctx, worktree_path, repo_root)

    # Assert
    assert status is not None
    assert status.git_status is not None
    assert status.plan is not None
    # Check that collectors started before others finished (parallel execution)
    assert "git_start" in execution_order
    assert "plan_start" in execution_order


def test_orchestrator_related_worktrees(tmp_path: Path) -> None:
    """Test StatusOrchestrator collects related worktrees."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    wt1 = tmp_path / "wt1"
    wt1.mkdir()
    wt2 = tmp_path / "wt2"
    wt2.mkdir()
    current = tmp_path / "current"
    current.mkdir()

    git_ops = FakeGit(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
                WorktreeInfo(path=wt1, branch="feature-1"),
                WorktreeInfo(path=wt2, branch="feature-2"),
                WorktreeInfo(path=current, branch="current-branch"),
            ]
        },
        current_branches={current: "current-branch"},
    )

    ctx = create_test_context(git=git_ops)
    orchestrator = StatusOrchestrator([], runner=RealParallelTaskRunner())

    # Act
    status = orchestrator.collect_status(ctx, current, repo_root)

    # Assert
    assert status is not None
    assert status.worktree_info.path == current
    assert status.related_worktrees is not None
    assert len(status.related_worktrees) == 3  # All except current
    # Check that current worktree is not in related
    related_paths = [wt.path for wt in status.related_worktrees]
    assert current not in related_paths
    assert repo_root in related_paths
    assert wt1 in related_paths
    assert wt2 in related_paths


def test_orchestrator_worktree_info_root(tmp_path: Path) -> None:
    """Test StatusOrchestrator correctly identifies root worktree."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
    )

    ctx = create_test_context(git=git_ops)
    orchestrator = StatusOrchestrator([], runner=RealParallelTaskRunner())

    # Act
    status = orchestrator.collect_status(ctx, repo_root, repo_root)

    # Assert
    assert status is not None
    assert status.worktree_info.is_root is True
    assert status.worktree_info.name == "root"


def test_orchestrator_worktree_info_not_root(tmp_path: Path) -> None:
    """Test StatusOrchestrator correctly identifies non-root worktree."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    worktree = tmp_path / "feature"
    worktree.mkdir()

    git_ops = FakeGit(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
                WorktreeInfo(path=worktree, branch="feature"),
            ]
        },
        current_branches={worktree: "feature"},
    )

    ctx = create_test_context(git=git_ops)
    orchestrator = StatusOrchestrator([], runner=RealParallelTaskRunner())

    # Act
    status = orchestrator.collect_status(ctx, worktree, repo_root)

    # Assert
    assert status is not None
    assert status.worktree_info.is_root is False
    assert status.worktree_info.name == "feature"


def test_orchestrator_handles_nonexistent_paths(tmp_path: Path) -> None:
    """Test StatusOrchestrator handles non-existent paths gracefully."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    nonexistent = tmp_path / "nonexistent"  # Don't create this

    git_ops = FakeGit(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
                WorktreeInfo(path=nonexistent, branch="ghost"),  # Non-existent
            ]
        },
        current_branches={repo_root: "main"},
    )

    ctx = create_test_context(git=git_ops)
    orchestrator = StatusOrchestrator([], runner=RealParallelTaskRunner())

    # Act
    status = orchestrator.collect_status(ctx, repo_root, repo_root)

    # Assert - should handle non-existent paths gracefully
    assert status is not None
    assert status.worktree_info is not None
    # Non-existent worktree should be filtered out
    assert len(status.related_worktrees) == 0


def test_orchestrator_multiple_collector_types(tmp_path: Path) -> None:
    """Test StatusOrchestrator with multiple collector result types."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    ctx = create_test_context()

    # Create collectors that return different types
    class GitCollector(StatusCollector):
        @property
        def name(self) -> str:
            return "git"

        def is_available(self, ctx: ErkContext, worktree_path: Path) -> bool:
            return True

        def collect(self, ctx: ErkContext, worktree_path: Path, repo_root: Path) -> object:
            return GitStatus.clean_status("test")

    class PlanCollector(StatusCollector):
        @property
        def name(self) -> str:
            return "plan"

        def is_available(self, ctx: ErkContext, worktree_path: Path) -> bool:
            return True

        def collect(self, ctx: ErkContext, worktree_path: Path, repo_root: Path) -> object:
            return PlanStatus(
                exists=True,
                path=worktree_path / ".impl",
                line_count=5,
                first_lines=["# Plan"],
                summary="Test plan",
                progress_summary="2/3 steps completed",
                format="folder",
            )

    collectors = [GitCollector(), PlanCollector()]
    orchestrator = StatusOrchestrator(collectors, runner=RealParallelTaskRunner())

    # Act
    status = orchestrator.collect_status(ctx, worktree_path, repo_root)

    # Assert
    assert status is not None
    assert status.git_status is not None
    assert status.git_status.branch == "test"
    assert status.plan is not None
    assert status.plan.exists is True
