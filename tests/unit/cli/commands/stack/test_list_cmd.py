"""Tests for erk stack list command."""

from click.testing import CliRunner
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.output_helpers import strip_ansi

from erk.cli.cli import cli


def test_list_stack_shows_branches_with_worktrees() -> None:
    """Test that list shows stack branches that have worktrees."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        # Create FakeGit with worktrees
        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "feat-1", branch="feat-1", is_root=False),
                    WorktreeInfo(path=repo_dir / "feat-2", branch="feat-2", is_root=False),
                ],
            },
            current_branches={env.cwd: "feat-2"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Create FakeGraphite with stack
        graphite = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"]),
                "feat-1": BranchMetadata.branch("feat-1", "main", children=["feat-2"]),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1"),
            },
            stacks={
                "feat-2": ["main", "feat-1", "feat-2"],
            },
        )

        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["stack", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)

        # Should show branches (not trunk)
        assert "feat-1" in output
        assert "feat-2" in output

        # Should show worktree names
        assert "feat-1" in output
        assert "feat-2" in output

        # Current branch should have marker
        assert "→" in output


def test_list_stack_filters_branches_without_worktrees() -> None:
    """Test that branches without worktrees are filtered out."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        # Create FakeGit with only some branches having worktrees
        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "feat-1", branch="feat-1", is_root=False),
                    # feat-2 has NO worktree
                ],
            },
            current_branches={env.cwd: "feat-1"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Stack includes feat-2, but it has no worktree
        graphite = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"]),
                "feat-1": BranchMetadata.branch("feat-1", "main", children=["feat-2"]),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1"),
            },
            stacks={
                "feat-1": ["main", "feat-1", "feat-2"],
            },
        )

        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["stack", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)

        # feat-1 has worktree, should be shown
        assert "feat-1" in output
        # feat-2 has no worktree, should NOT be in output as a branch entry
        # (feat-2 appears in worktree path for feat-1, so we need to be specific)
        # Count occurrences - should only appear once if it's just in a path
        lines = output.strip().split("\n")
        feat_2_in_branch_col = any(
            "feat-2" in line.split()[1] for line in lines if len(line.split()) > 1
        )
        # feat-2 should NOT appear as a branch name
        first_cols = [line.split()[0] for line in lines if line.strip()]
        assert not feat_2_in_branch_col or "feat-2" not in first_cols


def test_list_stack_includes_trunk_branch() -> None:
    """Test that trunk branches with worktrees ARE included in output."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "feat-1", branch="feat-1", is_root=False),
                ],
            },
            current_branches={env.cwd: "feat-1"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        graphite = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"]),
                "feat-1": BranchMetadata.branch("feat-1", "main"),
            },
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["stack", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)

        # main is trunk but has a worktree, should appear
        assert "main" in output
        # trunk worktree should show as "root"
        assert "root" in output
        # feat-1 should also appear
        assert "feat-1" in output


def test_list_stack_current_branch_highlighted() -> None:
    """Test that current branch is highlighted with bold and marker."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "feat-1", branch="feat-1", is_root=False),
                    WorktreeInfo(path=repo_dir / "feat-2", branch="feat-2", is_root=False),
                ],
            },
            current_branches={env.cwd: "feat-2"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        graphite = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"]),
                "feat-1": BranchMetadata.branch("feat-1", "main", children=["feat-2"]),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1"),
            },
            stacks={
                "feat-2": ["main", "feat-1", "feat-2"],
            },
        )

        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["stack", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)

        # Current branch (feat-2) should have the → marker
        assert "→" in output

        # Find the line with the marker
        for line in output.split("\n"):
            if "→" in line:
                assert "feat-2" in line


def test_list_stack_branch_not_tracked_by_graphite() -> None:
    """Test error when branch is not tracked by Graphite."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="untracked-branch", is_root=True),
                ],
            },
            current_branches={env.cwd: "untracked-branch"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # No stacks configured - branch not tracked
        graphite = FakeGraphite()

        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["stack", "list"], obj=test_ctx)
        assert result.exit_code == 1

        output = strip_ansi(result.output)
        assert "not tracked by Graphite" in output
        assert "untracked-branch" in output


def test_list_stack_trunk_only_shows_trunk() -> None:
    """Test that when only trunk is in stack and has worktree, it is shown."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Only trunk has a worktree
        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ],
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        graphite = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main"),
            },
            stacks={
                "main": ["main"],
            },
        )

        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["stack", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)
        # Trunk is now included, so main should appear
        assert "main" in output
        assert "root" in output


def test_list_stack_ls_alias() -> None:
    """Test that 'erk stack ls' works as alias for 'erk stack list'."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "feat-1", branch="feat-1", is_root=False),
                ],
            },
            current_branches={env.cwd: "feat-1"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        graphite = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"]),
                "feat-1": BranchMetadata.branch("feat-1", "main"),
            },
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        test_ctx = env.build_context(git=git, graphite=graphite)

        # Use 'ls' alias
        result = runner.invoke(cli, ["stack", "ls"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)
        assert "feat-1" in output


def test_list_stack_displays_children_above_parents() -> None:
    """Test that stack displays upstack (children) above downstack (parents).

    Graphite's mental model: children are "up" the stack, parents are "down".
    So the most child-like branches should appear at TOP, trunk at BOTTOM.

    Stack: main → feat-1 → feat-2
    Display order (top to bottom): feat-2, feat-1, main
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "feat-1", branch="feat-1", is_root=False),
                    WorktreeInfo(path=repo_dir / "feat-2", branch="feat-2", is_root=False),
                ],
            },
            current_branches={env.cwd: "feat-2"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        graphite = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"]),
                "feat-1": BranchMetadata.branch("feat-1", "main", children=["feat-2"]),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1"),
            },
            stacks={
                "feat-2": ["main", "feat-1", "feat-2"],
            },
        )

        test_ctx = env.build_context(git=git, graphite=graphite)

        result = runner.invoke(cli, ["stack", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)
        lines = [line for line in output.strip().split("\n") if line.strip()]

        # Find lines with branch names (skip header)
        branch_lines = [line for line in lines if "feat-" in line or "main" in line]

        # Extract branch order from output
        branch_order: list[str] = []
        for line in branch_lines:
            if "feat-2" in line:
                branch_order.append("feat-2")
            elif "feat-1" in line:
                branch_order.append("feat-1")
            elif "main" in line:
                branch_order.append("main")

        # Children (upstack) should be at TOP, trunk (downstack) at BOTTOM
        # Expected order: feat-2 (child), feat-1 (middle), main (trunk)
        assert branch_order == ["feat-2", "feat-1", "main"], (
            f"Expected children above parents. Got order: {branch_order}. "
            "Upstack branches should be at top, trunk at bottom."
        )


def test_list_stack_worktree_name_uses_is_root_flag() -> None:
    """Test that worktree name uses is_root flag, not path comparison.

    This test ensures we use wt.is_root to determine if a worktree is root,
    not by comparing paths. The bug was comparing wt.path != repo.root which
    could fail when running from within a worktree where repo.root equals cwd.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / env.cwd.name
        # Create a worktree path that matches the pattern from real usage
        worktree_path = repo_dir / "worktrees" / "my-feature-branch-worktree"

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(
                        path=worktree_path,
                        branch="my-feature-branch",
                        is_root=False,
                    ),
                ],
            },
            current_branches={worktree_path: "my-feature-branch"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
        )

        graphite = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["my-feature-branch"]),
                "my-feature-branch": BranchMetadata.branch("my-feature-branch", "main"),
            },
            stacks={
                "my-feature-branch": ["main", "my-feature-branch"],
            },
        )

        # Run from the NON-ROOT worktree
        test_ctx = env.build_context(git=git, graphite=graphite, cwd=worktree_path)

        result = runner.invoke(cli, ["stack", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        output = strip_ansi(result.output)

        # The worktree name should be the directory name, NOT "root"
        # This is the key assertion that would catch the is_root bug
        assert "my-feature-branch-worktree" in output
        # And "root" should only appear for the main branch's worktree
        lines = [line for line in output.strip().split("\n") if line.strip()]
        # Find the line with my-feature-branch
        for line in lines:
            if "my-feature-branch" in line and "main" not in line:
                # This line should NOT say "root" as worktree
                assert "root" not in line, f"Non-root worktree incorrectly shown as 'root': {line}"
