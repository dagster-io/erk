"""Unit tests for codespace SSH command builder."""

from erk.core.codespace_run import build_codespace_ssh_command


def test_build_codespace_ssh_command_includes_setup() -> None:
    """build_codespace_ssh_command wraps with git pull, uv sync, and venv activation."""
    result = build_codespace_ssh_command("erk objective plan 42")

    assert "git pull" in result
    assert "uv sync" in result
    assert "source .venv/bin/activate" in result


def test_build_codespace_ssh_command_runs_in_foreground() -> None:
    """build_codespace_ssh_command runs in foreground (no nohup, no &, no log redirect)."""
    result = build_codespace_ssh_command("erk objective plan 42")

    assert "nohup" not in result
    assert "/tmp/erk-run.log" not in result
    assert "2>&1 &" not in result


def test_build_codespace_ssh_command_uses_login_shell() -> None:
    """build_codespace_ssh_command uses bash login shell."""
    result = build_codespace_ssh_command("erk objective plan 42")

    assert result.startswith("bash -l -c '")


def test_build_codespace_ssh_command_preserves_erk_command() -> None:
    """build_codespace_ssh_command preserves the exact erk command string."""
    result = build_codespace_ssh_command("erk pr replan 123")

    assert "erk pr replan 123" in result
    assert "nohup" not in result


def test_build_codespace_ssh_command_with_working_directory() -> None:
    """build_codespace_ssh_command prepends cd when working_directory is set."""
    result = build_codespace_ssh_command(
        "erk objective plan 42",
        working_directory="/workspaces/dagster-compass",
    )

    assert result.startswith("bash -l -c 'cd /workspaces/dagster-compass && git pull")
    assert "erk objective plan 42" in result


def test_build_codespace_ssh_command_quotes_working_directory() -> None:
    """build_codespace_ssh_command quotes working_directory with spaces."""
    result = build_codespace_ssh_command(
        "erk objective plan 42",
        working_directory="/workspaces/my project",
    )

    assert "cd '/workspaces/my project'" in result


def test_build_codespace_ssh_command_no_cd_when_working_directory_is_none() -> None:
    """build_codespace_ssh_command has no cd prefix when working_directory is None."""
    result = build_codespace_ssh_command("erk objective plan 42", working_directory=None)

    assert "cd " not in result
    assert result.startswith("bash -l -c 'git pull")
