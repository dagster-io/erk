"""Tests for erk create command output behavior."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.fakes.git import FakeGit
from erk_shared.gateway.git.abc import WorktreeInfo
from tests.test_utils.env_helpers import erk_inmem_env


def test_create_from_current_branch_outputs_script_path_to_stdout() -> None:
    """Test that create --from-current-branch outputs script path to stdout, not stderr.

    This test verifies that the shell integration handler can read the script path
    from stdout. If the script path is written to stderr, the handler will miss it
    and display 'no directory change needed' instead of switching to the new worktree.

    See: https://github.com/anthropics/erk/issues/XXX
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # Set up git state: in root worktree on feature branch
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "my-feature"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Create worktree from current branch with --script flag
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-current-branch", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Assert: Script path is in stdout (for shell integration)
        assert result.stdout.strip() != "", (
            "Script path should be in stdout for shell integration to read. "
            "Currently it's being written to stderr via user_output(), "
            "but should be written to stdout via machine_output()."
        )

        # Assert: Script path is a valid path to activation script
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None, "Script path should reference a valid script"

        # Assert: Script contains cd command to new worktree
        expected_worktree_path = repo_dir / "worktrees" / "my-feature"
        assert str(expected_worktree_path) in script_content, (
            f"Script should cd to {expected_worktree_path}"
        )


def test_create_with_from_branch_trunk_errors() -> None:
    """Test that create --from-branch prevents creating worktree for trunk branch.

    This test verifies that ensure_worktree_for_branch() validation catches
    attempts to create a worktree for the trunk branch via --from-branch flag.
    The error should match the one from checkout command for consistency.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Setup: root worktree on a feature branch (NOT trunk)
        # This way we can test creating a worktree for trunk without "already checked out" error
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "feature-1"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-1"]},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        # Try to create worktree from trunk branch - should error
        result = runner.invoke(
            cli,
            ["wt", "create", "foo", "--from-branch", "main"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Should fail with error
        assert result.exit_code == 1

        # Error message should match checkout command for consistency
        assert "Cannot create worktree for trunk branch" in result.stderr
        assert "main" in result.stderr
        assert "erk br co root" in result.stderr
        assert "root worktree" in result.stderr

        # Verify no worktree was created
        assert len(git_ops.added_worktrees) == 0


def test_create_from_current_branch_shows_shell_integration_instructions() -> None:
    """Test that create --from-current-branch shows setup instructions without --script."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up git state: in root worktree on feature branch
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "my-feature"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Create worktree from current branch WITHOUT --script flag
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-current-branch"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Assert: Output contains worktree creation message
        assert "Created worktree at" in result.stderr


def test_create_from_current_branch_with_stay_flag() -> None:
    """Test that create --from-current-branch --stay shows minimal output."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up git state: in root worktree on feature branch
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "my-feature"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Create worktree with --stay flag
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-current-branch", "--stay"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Assert: Output contains creation message, no shell integration instructions
        assert "Created worktree at" in result.stderr
        assert "Shell integration not detected" not in result.stderr
        assert "erk init --shell" not in result.stderr
        # Note: "source" IS present for activation instructions,
        # but not "source <(" for shell integration
        assert "source <(" not in result.stderr


def test_create_prints_activation_instructions() -> None:
    """Test that create command prints activation script instructions.

    Part of objective #4954, Phase 5: Activation output for create commands.
    Verifies that erk wt create prints the activation path after worktree creation.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # Set up git state: in root worktree on feature branch
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "my-feature"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Create worktree from current branch (without --script flag)
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-current-branch"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Assert: Output contains activation instructions
        assert "To activate the worktree environment:" in result.stderr
        assert "source" in result.stderr
        assert ".erk/bin/activate.sh" in result.stderr
        # Should NOT contain implement hint (only shown for up/down navigation)
        assert "erk implement --here" not in result.stderr

        # Assert: Activation script file was created
        expected_worktree_path = repo_dir / "worktrees" / "my-feature"
        activate_script = expected_worktree_path / ".erk" / "bin" / "activate.sh"
        assert activate_script.exists()


def test_create_with_stay_flag_prints_activation_instructions() -> None:
    """Test that create --stay prints activation script instructions.

    Part of objective #4954, Phase 5: Activation output for create commands.
    Verifies that --stay mode still prints activation instructions.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # Set up git state: in root worktree on feature branch
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "my-feature"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Create worktree with --stay flag
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-current-branch", "--stay"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: Output contains activation instructions
        assert "To activate the worktree environment:" in result.stderr
        assert "source" in result.stderr
        assert ".erk/bin/activate.sh" in result.stderr
        # Should NOT contain implement hint (only shown for up/down navigation)
        assert "erk implement --here" not in result.stderr

        # Assert: Activation script file was created
        expected_worktree_path = repo_dir / "worktrees" / "my-feature"
        activate_script = expected_worktree_path / ".erk" / "bin" / "activate.sh"
        assert activate_script.exists()


def test_create_script_mode_does_not_print_activation_instructions() -> None:
    """Test that create --script does NOT print activation instructions.

    Part of objective #4954, Phase 5: Activation output for create commands.
    In script mode, shell integration handles navigation automatically,
    so activation instructions would be redundant.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up git state: in root worktree on feature branch
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "my-feature"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Create worktree with --script flag
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-current-branch", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: Output does NOT contain activation instructions
        # (shell integration handles navigation)
        assert "To activate the worktree environment:" not in result.stderr
        assert "erk implement --here" not in result.stderr
