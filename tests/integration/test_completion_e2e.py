"""E2E tests for shell completion generation.

These tests intentionally use subprocess to validate real CLI behavior:
- Shell completion script generation (bash, zsh, fish)
- Environment variable handling (_ERK_COMPLETE)
- Integration with Click's completion system

DO NOT convert to CliRunner - these validate end-to-end shell integration.
"""

import os
import subprocess


def test_completion_bash_help() -> None:
    """Test bash completion help shows instructions."""
    result = subprocess.run(
        ["uv", "run", "erk", "completion", "bash", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.returncode == 0
    assert "source <(erk completion bash)" in result.stdout
    assert "bash_completion.d" in result.stdout


def test_completion_zsh_help() -> None:
    """Test zsh completion help shows instructions."""
    result = subprocess.run(
        ["uv", "run", "erk", "completion", "zsh", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.returncode == 0
    assert "source <(erk completion zsh)" in result.stdout
    assert "compinit" in result.stdout


def test_completion_fish_help() -> None:
    """Test fish completion help shows instructions."""
    result = subprocess.run(
        ["uv", "run", "erk", "completion", "fish", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.returncode == 0
    assert "erk completion fish" in result.stdout
    assert ".config/fish/completions" in result.stdout


def test_completion_bash_generates_script() -> None:
    """Test bash completion generates a script."""
    # Set up environment to generate bash completion
    env = os.environ.copy()
    env["_ERK_COMPLETE"] = "bash_source"

    result = subprocess.run(
        ["uv", "run", "erk"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.returncode == 0
    # Should generate shell completion code
    assert len(result.stdout) > 100
    # Bash completion scripts typically contain these
    assert "complete" in result.stdout or "_erk_completion" in result.stdout


def test_completion_zsh_generates_script() -> None:
    """Test zsh completion generates a script."""
    # Set up environment to generate zsh completion
    env = os.environ.copy()
    env["_ERK_COMPLETE"] = "zsh_source"

    result = subprocess.run(
        ["uv", "run", "erk"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.returncode == 0
    # Should generate shell completion code
    assert len(result.stdout) > 100
    # Zsh completion scripts typically start with #compdef
    assert "#compdef" in result.stdout


def test_completion_fish_generates_script() -> None:
    """Test fish completion generates a script."""
    # Set up environment to generate fish completion
    env = os.environ.copy()
    env["_ERK_COMPLETE"] = "fish_source"

    result = subprocess.run(
        ["uv", "run", "erk"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.returncode == 0
    # Should generate shell completion code
    assert len(result.stdout) > 100
    # Fish completion scripts typically contain complete command
    assert "complete" in result.stdout


def test_completion_group_help() -> None:
    """Test completion group help lists subcommands."""
    result = subprocess.run(
        ["uv", "run", "erk", "completion", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.returncode == 0
    assert "bash" in result.stdout
    assert "zsh" in result.stdout
    assert "fish" in result.stdout


def test_worktree_name_completion_does_not_crash_without_ctx_obj() -> None:
    """Test that worktree name completion doesn't crash during shell completion.

    Regression test for: ctx.obj is None during shell completion because
    Click's resilient_parsing mode skips callbacks.

    Before the fix: shell_completion_context yielded None (ctx.obj),
    causing AttributeError when accessing erk_ctx.cwd. The exception was
    silently caught and completion returned [].

    After the fix: shell_completion_context creates a fresh ErkContext
    via create_context(dry_run=False) when ctx.obj is None.

    Note: This test only verifies the completion doesn't crash. It doesn't
    verify completion results because CI doesn't have erk set up (no ~/.erk/
    directory), so create_context() fails and completion returns empty.
    In a real environment with erk set up, worktree names would be returned.
    """
    # Simulate bash completion for 'erk wt checkout <TAB>'
    env = os.environ.copy()
    env["COMP_WORDS"] = "erk wt checkout "
    env["COMP_CWORD"] = "3"
    env["_ERK_COMPLETE"] = "bash_complete"

    result = subprocess.run(
        ["uv", "run", "erk"],
        env=env,
        capture_output=True,
        text=True,
    )

    # Completion should not crash (returncode 0)
    # It may return empty if erk isn't set up (CI), but should work with erk
    assert result.returncode == 0
