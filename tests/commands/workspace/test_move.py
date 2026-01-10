"""Tests for the erk move command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def test_move_from_current_to_new_worktree() -> None:
    """Test moving branch from current worktree to a new worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        source_wt = env.cwd
        target_wt = env.erk_root / "repos" / env.cwd.name / "worktrees" / "target-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=source_wt, branch="feature-x"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["stack", "move", "target-wt"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Moving 'feature-x'" in result.output
        assert "✓ Moved 'feature-x'" in result.output

        worktrees = git_ops.list_worktrees(env.cwd)
        assert len(worktrees) == 2
        assert any(wt.path == target_wt and wt.branch == "feature-x" for wt in worktrees)


def test_move_with_explicit_current_flag() -> None:
    """Test move with explicit --current flag."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="feature-y"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["stack", "move", "--current", "new-wt"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Moving 'feature-y'" in result.output


def test_move_with_branch_flag_auto_detect() -> None:
    """Test move with --branch flag to auto-detect source worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        source_wt = env.erk_root / "repos" / env.cwd.name / "worktrees" / "old-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=source_wt, branch="feature-auth"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, existing_paths={source_wt})

        result = runner.invoke(
            cli, ["stack", "move", "--branch", "feature-auth", "new-wt"], obj=test_ctx
        )

        assert result.exit_code == 0
        assert "Moving 'feature-auth'" in result.output


def test_move_with_worktree_flag() -> None:
    """Test move with explicit --worktree flag."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        source_wt = env.erk_root / "repos" / env.cwd.name / "worktrees" / "source-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=source_wt, branch="feature-db"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, existing_paths={source_wt})

        result = runner.invoke(
            cli, ["stack", "move", "--worktree", "source-wt", "target-wt"], obj=test_ctx
        )

        assert result.exit_code == 0
        assert "Moving 'feature-db'" in result.output


def test_move_swap_between_two_worktrees() -> None:
    """Test swapping branches between two existing worktrees."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        source_wt = env.erk_root / "repos" / env.cwd.name / "worktrees" / "wt1"
        target_wt = env.erk_root / "repos" / env.cwd.name / "worktrees" / "wt2"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=source_wt, branch="branch-a"),
                    WorktreeInfo(path=target_wt, branch="branch-b"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                source_wt: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, existing_paths={source_wt, target_wt})

        result = runner.invoke(
            cli, ["stack", "move", "--worktree", "wt1", "wt2", "--force"], obj=test_ctx
        )

        assert result.exit_code == 0
        assert "Swapping branches between 'wt1' and 'wt2'" in result.output
        assert "✓ Swapped 'branch-a' ↔ 'branch-b'" in result.output


def test_move_swap_requires_confirmation() -> None:
    """Test that swap operation requires confirmation without --force."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        source_wt = env.erk_root / "repos" / env.cwd.name / "worktrees" / "wt1"
        target_wt = env.erk_root / "repos" / env.cwd.name / "worktrees" / "wt2"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=source_wt, branch="branch-a"),
                    WorktreeInfo(path=target_wt, branch="branch-b"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                source_wt: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(
            git=git_ops, existing_paths={source_wt, target_wt}, confirm_responses=[False]
        )

        result = runner.invoke(cli, ["stack", "move", "--worktree", "wt1", "wt2"], obj=test_ctx)

        assert result.exit_code == 0
        assert "This will swap branches between worktrees:" in result.output
        assert "Swap cancelled" in result.output


def test_move_with_custom_ref() -> None:
    """Test move with custom --ref fallback branch."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="feature-x"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
            },
            default_branches={env.cwd: "develop"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["stack", "move", "new-wt", "--ref", "develop"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Moving 'feature-x'" in result.output


def test_move_error_multiple_source_flags() -> None:
    """Test error when multiple source flags are specified."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={
                env.cwd: env.git_dir,
            },
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli,
            ["stack", "move", "--current", "--branch", "feature", "target"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Only one of --current, --branch, or --worktree can be specified" in result.output


def test_move_error_branch_not_found() -> None:
    """Test error when specified branch is not found in any worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
            },
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli,
            ["stack", "move", "--branch", "nonexistent", "target"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Branch 'nonexistent' not found in any worktree" in result.output


def test_move_error_worktree_not_found() -> None:
    """Test error when specified worktree does not exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={
                env.cwd: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli,
            ["stack", "move", "--worktree", "nonexistent", "target"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Worktree 'nonexistent' does not exist" in result.output


def test_move_error_source_and_target_same() -> None:
    """Test error when source and target are the same worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        wt = env.erk_root / "repos" / env.cwd.name / "worktrees" / "same-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=wt, branch="feature"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                wt: env.git_dir,
            },
        )

        test_ctx = env.build_context(git=git_ops, existing_paths={wt})

        result = runner.invoke(
            cli,
            ["stack", "move", "--worktree", "same-wt", "same-wt"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Source and target worktrees are the same" in result.output


def test_move_error_source_in_detached_head() -> None:
    """Test error when source worktree is in detached HEAD state."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch=None),  # Detached HEAD
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["stack", "move", "target"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Source worktree is in detached HEAD state" in result.output


def test_move_to_existing_worktree_in_detached_head() -> None:
    """Test moving to an existing worktree in detached HEAD (should checkout branch there)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        source_wt = env.erk_root / "repos" / env.cwd.name / "worktrees" / "source"
        target_wt = env.erk_root / "repos" / env.cwd.name / "worktrees" / "target"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=source_wt, branch="feature-x"),
                    WorktreeInfo(path=target_wt, branch=None),  # Detached HEAD
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                source_wt: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, existing_paths={source_wt, target_wt})

        result = runner.invoke(
            cli, ["stack", "move", "--worktree", "source", "target"], obj=test_ctx
        )

        assert result.exit_code == 0
        assert "Moving 'feature-x'" in result.output
        assert "✓ Moved 'feature-x'" in result.output


def test_move_to_root() -> None:
    """Test moving branch from current worktree to root."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        source_wt = env.erk_root / "repos" / env.cwd.name / "worktrees" / "feature-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=source_wt, branch="feature-x"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                source_wt: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, existing_paths={source_wt})

        # Move from feature-wt to root (should swap branches)
        result = runner.invoke(
            cli, ["stack", "move", "--worktree", "feature-wt", "root", "--force"], obj=test_ctx
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Swapping branches" in result.output
        assert "✓ Swapped 'feature-x' ↔ 'main'" in result.output


def test_move_to_root_with_explicit_current() -> None:
    """Test moving from current worktree to root with --current flag."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        source_wt = env.erk_root / "repos" / env.cwd.name / "worktrees" / "feature-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=source_wt, branch="feature-y"),
                ],
            },
            git_common_dirs={
                source_wt: env.git_dir,
                env.cwd: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        # Simulate being in source_wt by setting cwd
        test_ctx = env.build_context(git=git_ops, cwd=source_wt, existing_paths={source_wt})

        result = runner.invoke(cli, ["stack", "move", "root", "--force"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Swapping branches" in result.output or "Moved" in result.output


def test_move_to_root_when_root_is_detached_head() -> None:
    """Test moving to root when root is in detached HEAD state (move operation)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        source_wt = env.erk_root / "repos" / env.cwd.name / "worktrees" / "feature-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch=None),  # Detached HEAD at root
                    WorktreeInfo(path=source_wt, branch="feature-x"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                source_wt: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, existing_paths={source_wt})

        # Move from feature-wt to root (should be a move, not swap, since root is detached)
        result = runner.invoke(
            cli, ["stack", "move", "--worktree", "feature-wt", "root"], obj=test_ctx
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Moving 'feature-x'" in result.output
        assert "✓ Moved 'feature-x'" in result.output


def test_move_error_source_is_root_target_is_root() -> None:
    """Test error when trying to move root to root."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            git_common_dirs={
                env.cwd: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        # Try to move root to root (should fail)
        result = runner.invoke(cli, ["stack", "move", "root"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Source and target worktrees are the same" in result.output
