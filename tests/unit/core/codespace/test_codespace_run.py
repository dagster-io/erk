"""Unit tests for codespace run command builder."""

from erk.core.codespace_run import build_codespace_run_command


def test_build_codespace_run_command_includes_setup() -> None:
    """build_codespace_run_command wraps with git pull, uv sync, and venv activation."""
    result = build_codespace_run_command("erk objective next-plan 42")

    assert "git pull" in result
    assert "uv sync" in result
    assert "source .venv/bin/activate" in result


def test_build_codespace_run_command_includes_nohup() -> None:
    """build_codespace_run_command uses nohup for fire-and-forget execution."""
    result = build_codespace_run_command("erk objective next-plan 42")

    assert "nohup erk objective next-plan 42" in result
    assert "/tmp/erk-run.log" in result
    assert "2>&1 &" in result


def test_build_codespace_run_command_uses_login_shell() -> None:
    """build_codespace_run_command uses bash login shell."""
    result = build_codespace_run_command("erk objective next-plan 42")

    assert result.startswith("bash -l -c '")


def test_build_codespace_run_command_preserves_erk_command() -> None:
    """build_codespace_run_command preserves the exact erk command string."""
    result = build_codespace_run_command("erk plan replan 123")

    assert "nohup erk plan replan 123" in result
