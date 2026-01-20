"""Unit tests for docker_executor module."""

from pathlib import Path

from erk.cli.commands.docker_executor import (
    build_claude_command_args,
    build_docker_run_args,
)


def test_build_docker_run_args_interactive(tmp_path: Path) -> None:
    """Test Docker run args for interactive mode."""
    args = build_docker_run_args(
        worktree_path=Path("/path/to/worktree"),
        image_name="erk-local:latest",
        interactive=True,
        home_dir=tmp_path,  # Use fake home for testability
    )

    assert "docker" in args
    assert "run" in args
    assert "--rm" in args
    assert "-it" in args
    assert "-w" in args
    assert "/workspace" in args
    assert "erk-local:latest" in args


def test_build_docker_run_args_non_interactive(tmp_path: Path) -> None:
    """Test Docker run args for non-interactive mode."""
    args = build_docker_run_args(
        worktree_path=Path("/path/to/worktree"),
        image_name="erk-local:latest",
        interactive=False,
        home_dir=tmp_path,
    )

    assert "docker" in args
    assert "run" in args
    assert "--rm" in args
    assert "-it" not in args  # No TTY in non-interactive mode


def test_build_docker_run_args_includes_user_mapping(tmp_path: Path) -> None:
    """Test Docker run args include user UID/GID mapping."""
    args = build_docker_run_args(
        worktree_path=Path("/path/to/worktree"),
        image_name="erk-local:latest",
        interactive=True,
        home_dir=tmp_path,
    )

    assert "--user" in args
    # Find the user argument
    user_idx = args.index("--user")
    user_value = args[user_idx + 1]
    # Should be in format "UID:GID"
    assert ":" in user_value


def test_build_docker_run_args_mounts_worktree(tmp_path: Path) -> None:
    """Test Docker run args mount the worktree to /workspace."""
    worktree = Path("/path/to/worktree")
    args = build_docker_run_args(
        worktree_path=worktree,
        image_name="erk-local:latest",
        interactive=True,
        home_dir=tmp_path,
    )

    assert "-v" in args
    # Find volume mount for worktree
    mount_found = False
    for i, arg in enumerate(args):
        if arg == "-v" and i + 1 < len(args):
            mount = args[i + 1]
            if str(worktree) in mount and "/workspace" in mount:
                mount_found = True
                break
    assert mount_found, "Worktree volume mount not found"


def test_build_docker_run_args_mounts_claude_dir_when_exists(tmp_path: Path) -> None:
    """Test Docker run args mount ~/.claude/ when it exists."""
    # Create .claude directory in fake home
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    args = build_docker_run_args(
        worktree_path=Path("/path/to/worktree"),
        image_name="erk-local:latest",
        interactive=True,
        home_dir=tmp_path,
    )

    # Should have volume mount for .claude
    claude_mount_found = False
    for i, arg in enumerate(args):
        if arg == "-v" and i + 1 < len(args):
            mount = args[i + 1]
            if str(claude_dir) in mount and "/home/ci-user/.claude" in mount:
                claude_mount_found = True
                break
    assert claude_mount_found, "Claude dir volume mount not found"


def test_build_docker_run_args_skips_claude_dir_when_missing(tmp_path: Path) -> None:
    """Test Docker run args skip ~/.claude/ mount when it doesn't exist."""
    # Don't create .claude directory
    args = build_docker_run_args(
        worktree_path=Path("/path/to/worktree"),
        image_name="erk-local:latest",
        interactive=True,
        home_dir=tmp_path,
    )

    # Should NOT have volume mount for .claude
    for i, arg in enumerate(args):
        if arg == "-v" and i + 1 < len(args):
            mount = args[i + 1]
            assert "/home/ci-user/.claude" not in mount, "Claude dir should not be mounted"


def test_build_claude_command_args_interactive() -> None:
    """Test Claude command args for interactive mode."""
    args = build_claude_command_args(
        interactive=True,
        dangerous=True,
        model=None,
        command="/erk:plan-implement",
    )

    assert "claude" in args
    assert "--dangerously-skip-permissions" in args
    assert "/erk:plan-implement" in args
    # Interactive mode should NOT have print/verbose flags
    assert "--print" not in args
    assert "--output-format" not in args


def test_build_claude_command_args_non_interactive() -> None:
    """Test Claude command args for non-interactive mode."""
    args = build_claude_command_args(
        interactive=False,
        dangerous=True,
        model=None,
        command="/erk:plan-implement",
    )

    assert "claude" in args
    assert "--dangerously-skip-permissions" in args
    assert "--print" in args
    assert "--verbose" in args
    assert "--output-format" in args
    assert "stream-json" in args
    assert "/erk:plan-implement" in args


def test_build_claude_command_args_with_model() -> None:
    """Test Claude command args include model when specified."""
    args = build_claude_command_args(
        interactive=True,
        dangerous=True,
        model="sonnet",
        command="/erk:plan-implement",
    )

    assert "--model" in args
    assert "sonnet" in args


def test_build_claude_command_args_always_skips_permissions() -> None:
    """Test Claude command always includes --dangerously-skip-permissions in Docker."""
    # Even if dangerous=False, Docker mode implies skip permissions
    args = build_claude_command_args(
        interactive=True,
        dangerous=False,  # This parameter is ignored in Docker mode
        model=None,
        command="/erk:plan-implement",
    )

    # The implementation always adds --dangerously-skip-permissions
    assert "--dangerously-skip-permissions" in args
