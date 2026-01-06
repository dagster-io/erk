"""Tests for shell-init command."""

from click.testing import CliRunner

from erk.cli.commands.shell_init import shell_init_cmd


def test_shell_init_outputs_wrapper_function() -> None:
    """shell-init outputs shell code with claude wrapper function."""
    runner = CliRunner()
    result = runner.invoke(shell_init_cmd)

    assert result.exit_code == 0
    assert "function claude()" in result.output


def test_shell_init_includes_switch_request_handling() -> None:
    """shell-init output handles switch-request marker file."""
    runner = CliRunner()
    result = runner.invoke(shell_init_cmd)

    assert result.exit_code == 0
    assert "~/.erk/switch-request" in result.output


def test_shell_init_includes_resume_command_handling() -> None:
    """shell-init output handles switch-request-command file."""
    runner = CliRunner()
    result = runner.invoke(shell_init_cmd)

    assert result.exit_code == 0
    assert "~/.erk/switch-request-command" in result.output


def test_shell_init_calls_implement_path_only() -> None:
    """shell-init output calls erk implement with --path-only flag."""
    runner = CliRunner()
    result = runner.invoke(shell_init_cmd)

    assert result.exit_code == 0
    assert "erk implement" in result.output
    assert "--path-only" in result.output


def test_shell_init_uses_claude_continue() -> None:
    """shell-init output passes --continue flag to claude."""
    runner = CliRunner()
    result = runner.invoke(shell_init_cmd)

    assert result.exit_code == 0
    assert "claude --continue" in result.output


def test_shell_init_activates_venv() -> None:
    """shell-init output activates venv if present."""
    runner = CliRunner()
    result = runner.invoke(shell_init_cmd)

    assert result.exit_code == 0
    assert ".venv/bin/activate" in result.output
