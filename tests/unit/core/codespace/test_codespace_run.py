"""Unit tests for codespace SSH command builder."""

from erk.core.codespace_run import build_codespace_ssh_command


def test_build_codespace_ssh_command_includes_setup() -> None:
    """build_codespace_ssh_command wraps with git pull, uv sync, and venv activation."""
    result = build_codespace_ssh_command("erk objective implement 42")

    assert "git pull" in result
    assert "uv sync" in result
    assert "source .venv/bin/activate" in result


def test_build_codespace_ssh_command_runs_in_foreground() -> None:
    """build_codespace_ssh_command runs in foreground (no nohup, no &, no log redirect)."""
    result = build_codespace_ssh_command("erk objective implement 42")

    assert "nohup" not in result
    assert "/tmp/erk-run.log" not in result
    assert "2>&1 &" not in result


def test_build_codespace_ssh_command_uses_login_shell() -> None:
    """build_codespace_ssh_command uses bash login shell."""
    result = build_codespace_ssh_command("erk objective implement 42")

    assert result.startswith("bash -l -c '")


def test_build_codespace_ssh_command_preserves_erk_command() -> None:
    """build_codespace_ssh_command preserves the exact erk command string."""
    result = build_codespace_ssh_command("erk plan replan 123")

    assert "erk plan replan 123" in result
    assert "nohup" not in result
