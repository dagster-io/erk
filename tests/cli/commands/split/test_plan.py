"""Tests for split planning functions.

These tests verify the pure business logic for worktree split operations.
All tests are fast and don't require filesystem I/O.
"""

from pathlib import Path

from erk.cli.commands.stack.split_old.plan import (
    SplitPlan,
    create_split_plan,
    execute_split_plan,
    identify_splittable_branches,
)
from erk_shared.git.abc import WorktreeInfo

# Tests for identify_splittable_branches function


def test_identify_splittable_branches_excludes_trunk() -> None:
    """Trunk branch should stay in root worktree and not be split."""
    stack_branches = ["main", "feat-1", "feat-2"]
    trunk_branch = "main"
    current_branch = "feat-2"
    all_worktrees = [
        WorktreeInfo(Path("/repo"), "main", is_root=True),
        WorktreeInfo(Path("/repo/erks/feat-2"), "feat-2", is_root=False),
    ]

    branches_to_split, existing, skipped_current, skipped_trunk = identify_splittable_branches(
        stack_branches, trunk_branch, current_branch, all_worktrees
    )

    assert "main" not in branches_to_split
    assert skipped_trunk is True
    assert "feat-1" in branches_to_split  # Only feat-1 needs a worktree


def test_identify_splittable_branches_excludes_current() -> None:
    """Current branch cannot be split (already checked out)."""
    stack_branches = ["main", "feat-1", "feat-2"]
    trunk_branch = "main"
    current_branch = "feat-1"
    all_worktrees = [
        WorktreeInfo(Path("/repo"), "main", is_root=True),
        WorktreeInfo(Path("/repo/erks/feat-1"), "feat-1", is_root=False),
    ]

    branches_to_split, existing, skipped_current, skipped_trunk = identify_splittable_branches(
        stack_branches, trunk_branch, current_branch, all_worktrees
    )

    assert "feat-1" not in branches_to_split
    assert skipped_current is True
    assert "feat-2" in branches_to_split  # Only feat-2 needs a worktree


def test_identify_splittable_branches_excludes_existing_worktrees() -> None:
    """Branches that already have worktrees should not be split again."""
    stack_branches = ["main", "feat-1", "feat-2", "feat-3"]
    trunk_branch = "main"
    current_branch = "feat-3"
    all_worktrees = [
        WorktreeInfo(Path("/repo"), "main", is_root=True),
        WorktreeInfo(Path("/repo/erks/feat-1"), "feat-1", is_root=False),
        WorktreeInfo(Path("/repo/erks/feat-2"), "feat-2", is_root=False),
        WorktreeInfo(Path("/repo/erks/feat-3"), "feat-3", is_root=False),
    ]

    branches_to_split, existing, skipped_current, skipped_trunk = identify_splittable_branches(
        stack_branches, trunk_branch, current_branch, all_worktrees
    )

    assert len(branches_to_split) == 0
    assert "feat-1" in existing
    assert "feat-2" in existing
    assert "feat-3" not in existing  # Current branch not in existing list


def test_identify_splittable_branches_full_stack() -> None:
    """Test splitting a full stack with no existing worktrees."""
    stack_branches = ["main", "feat-1", "feat-2", "feat-3"]
    trunk_branch = "main"
    current_branch = "feat-2"
    all_worktrees = [
        WorktreeInfo(Path("/repo"), "main", is_root=True),
        WorktreeInfo(Path("/repo/current"), "feat-2", is_root=False),
    ]

    branches_to_split, existing, skipped_current, skipped_trunk = identify_splittable_branches(
        stack_branches, trunk_branch, current_branch, all_worktrees
    )

    assert branches_to_split == ["feat-1", "feat-3"]
    assert len(existing) == 0
    assert skipped_current is True
    assert skipped_trunk is True


def test_identify_splittable_branches_empty_stack() -> None:
    """Handle edge case of empty or single-branch stack."""
    stack_branches = ["main"]
    trunk_branch = "main"
    current_branch = "main"
    all_worktrees = [WorktreeInfo(Path("/repo"), "main", is_root=True)]

    branches_to_split, existing, skipped_current, skipped_trunk = identify_splittable_branches(
        stack_branches, trunk_branch, current_branch, all_worktrees
    )

    assert len(branches_to_split) == 0
    assert len(existing) == 0
    assert skipped_current is True  # main is current
    assert skipped_trunk is True  # main is trunk


def test_identify_splittable_branches_detached_head() -> None:
    """Handle detached HEAD state (current_branch is None)."""
    stack_branches = ["main", "feat-1", "feat-2"]
    trunk_branch = "main"
    current_branch = None  # Detached HEAD
    all_worktrees = [
        WorktreeInfo(Path("/repo"), "main", is_root=True),
        WorktreeInfo(Path("/repo/current"), None, is_root=False),  # Detached
    ]

    branches_to_split, existing, skipped_current, skipped_trunk = identify_splittable_branches(
        stack_branches, trunk_branch, current_branch, all_worktrees
    )

    assert branches_to_split == ["feat-1", "feat-2"]
    assert skipped_current is False  # No current branch to skip
    assert skipped_trunk is True


# Tests for create_split_plan function


def test_create_split_plan_full_stack() -> None:
    """Create complete plan for splitting full stack."""
    stack_branches = ["main", "feat-1", "feat-2"]
    trunk_branch = "main"
    current_branch = "main"
    all_worktrees = [WorktreeInfo(Path("/repo"), "main", is_root=True)]
    repo_dir = Path("/repo/erks")

    def sanitize_name(name: str) -> str:
        return name.lower().replace("/", "-")

    plan = create_split_plan(
        stack_branches,
        trunk_branch,
        current_branch,
        all_worktrees,
        repo_dir,
        sanitize_name,
        Path("/repo"),
        Path("/repo"),  # repo_root
    )

    assert plan.branches_to_split == ["feat-1", "feat-2"]
    assert plan.target_paths["feat-1"] == Path("/repo/erks/feat-1")
    assert plan.target_paths["feat-2"] == Path("/repo/erks/feat-2")
    assert plan.skipped_trunk is True
    assert plan.skipped_current is True


def test_create_split_plan_with_exclusions() -> None:
    """Plan respects trunk, current, and existing worktree exclusions."""
    stack_branches = ["main", "feat-1", "feat-2", "feat-3"]
    trunk_branch = "main"
    current_branch = "feat-2"
    all_worktrees = [
        WorktreeInfo(Path("/repo"), "main", is_root=True),
        WorktreeInfo(Path("/repo/erks/feat-1"), "feat-1", is_root=False),
        WorktreeInfo(Path("/repo/erks/feat-2"), "feat-2", is_root=False),
    ]
    repo_dir = Path("/repo/erks")

    def sanitize_name(name: str) -> str:
        return name

    plan = create_split_plan(
        stack_branches,
        trunk_branch,
        current_branch,
        all_worktrees,
        repo_dir,
        sanitize_name,
        Path("/repo/erks/feat-2"),
        Path("/repo"),  # repo_root
    )

    assert plan.branches_to_split == ["feat-3"]
    assert plan.existing_worktrees == ["feat-1"]
    assert plan.target_paths["feat-3"] == Path("/repo/erks/feat-3")


def test_create_split_plan_generates_correct_paths() -> None:
    """Paths use sanitized worktree names."""
    stack_branches = ["main", "feature/test-branch", "bugfix/issue-123"]
    trunk_branch = "main"
    current_branch = "main"
    all_worktrees = [WorktreeInfo(Path("/repo"), "main", is_root=True)]
    repo_dir = Path("/repo/.erks")

    def sanitize_name(name: str) -> str:
        # Simulate actual sanitization
        return name.replace("/", "-").lower()

    plan = create_split_plan(
        stack_branches,
        trunk_branch,
        current_branch,
        all_worktrees,
        repo_dir,
        sanitize_name,
        Path("/repo"),
        Path("/repo"),  # repo_root
    )

    assert plan.target_paths["feature/test-branch"] == Path("/repo/.erks/feature-test-branch")
    assert plan.target_paths["bugfix/issue-123"] == Path("/repo/.erks/bugfix-issue-123")


def test_create_split_plan_empty_branches_to_split() -> None:
    """Handle case where all branches are excluded."""
    stack_branches = ["main", "feat-1"]
    trunk_branch = "main"
    current_branch = "feat-1"
    all_worktrees = [
        WorktreeInfo(Path("/repo"), "main", is_root=True),
        WorktreeInfo(Path("/repo/erks/feat-1"), "feat-1", is_root=False),
    ]
    repo_dir = Path("/repo/erks")

    def sanitize_name(name: str) -> str:
        return name

    plan = create_split_plan(
        stack_branches,
        trunk_branch,
        current_branch,
        all_worktrees,
        repo_dir,
        sanitize_name,
        Path("/repo/erks/feat-1"),
        Path("/repo"),  # repo_root
    )

    assert len(plan.branches_to_split) == 0
    assert len(plan.target_paths) == 0
    assert plan.skipped_trunk is True
    assert plan.skipped_current is True


# Tests for execute_split_plan function


def test_execute_split_plan_creates_worktrees() -> None:
    """Normal execution creates worktrees."""

    # Create fake git ops
    class FakeGit:
        def __init__(self):
            self.created_worktrees = []

        def add_worktree(self, repo_root, path, *, branch=None, ref=None, create_branch=True):
            self.created_worktrees.append((repo_root, path, branch, ref, create_branch))

    plan = SplitPlan(
        stack_branches=["main", "feat-1", "feat-2"],
        branches_to_split=["feat-1", "feat-2"],
        existing_worktrees=[],
        target_paths={
            "feat-1": Path("/repo/erks/feat-1"),
            "feat-2": Path("/repo/erks/feat-2"),
        },
        source_worktree_path=Path("/repo"),
        repo_root=Path("/repo"),
        skipped_current=False,
        skipped_trunk=True,
    )

    git_ops = FakeGit()
    results = execute_split_plan(plan, git_ops)

    assert len(results) == 2
    assert results[0] == ("feat-1", Path("/repo/erks/feat-1"))
    assert results[1] == ("feat-2", Path("/repo/erks/feat-2"))
    assert len(git_ops.created_worktrees) == 2
    # Check parameters: (repo_root, path, branch, ref, create_branch)
    assert git_ops.created_worktrees[0][0] == Path("/repo")  # repo_root
    assert git_ops.created_worktrees[0][1] == Path("/repo/erks/feat-1")  # path
    assert git_ops.created_worktrees[0][2] == "feat-1"  # branch
    assert git_ops.created_worktrees[0][3] is None  # ref
    assert git_ops.created_worktrees[0][4] is False  # create_branch=False (branch exists)


def test_execute_split_plan_with_noop_ops() -> None:
    """MockDryRunGit doesn't create actual worktrees."""

    class MockDryRunGit:
        """Test mock simulating DryRunGit behavior."""

        def __init__(self):
            self.created_worktrees = []

        def add_worktree(self, repo_root, path, *, branch=None, ref=None, create_branch=True):
            # MockDryRunGit does nothing here (simulating DryRunGit)
            pass

    plan = SplitPlan(
        stack_branches=["main", "feat-1"],
        branches_to_split=["feat-1"],
        existing_worktrees=[],
        target_paths={"feat-1": Path("/repo/erks/feat-1")},
        source_worktree_path=Path("/repo"),
        repo_root=Path("/repo"),
        skipped_current=False,
        skipped_trunk=True,
    )

    git_ops = MockDryRunGit()
    results = execute_split_plan(plan, git_ops)

    assert len(results) == 1
    assert results[0] == ("feat-1", Path("/repo/erks/feat-1"))
    assert len(git_ops.created_worktrees) == 0  # No actual creation due to MockDryRunGit


def test_execute_split_plan_empty_plan() -> None:
    """Handle empty plan with no branches to split."""

    class FakeGit:
        def __init__(self):
            self.created_worktrees = []

        def add_worktree(self, repo_root, path, *, branch=None, ref=None, create_branch=True):
            self.created_worktrees.append((repo_root, path, branch, ref, create_branch))

    plan = SplitPlan(
        stack_branches=["main"],
        branches_to_split=[],
        existing_worktrees=[],
        target_paths={},
        source_worktree_path=Path("/repo"),
        repo_root=Path("/repo"),
        skipped_current=True,
        skipped_trunk=True,
    )

    git_ops = FakeGit()
    results = execute_split_plan(plan, git_ops)

    assert len(results) == 0
    assert len(git_ops.created_worktrees) == 0
