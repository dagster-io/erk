"""Unit tests for codespace SSH command builder."""

from erk.core.codespace_run import (
    _sanitize_tmux_session_name,
    build_codespace_ssh_command,
    build_codespace_tmux_command,
)


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


def test_build_codespace_tmux_command_includes_bootstrap() -> None:
    """build_codespace_tmux_command wraps with git pull, uv sync, and venv activation."""
    result = build_codespace_tmux_command("erk objective plan 42", session_name="plan-42")

    assert "git pull" in result
    assert "uv sync" in result
    assert "source .venv/bin/activate" in result


def test_build_codespace_tmux_command_wraps_in_tmux() -> None:
    """build_codespace_tmux_command wraps the command in a tmux session."""
    result = build_codespace_tmux_command("erk objective plan 42", session_name="plan-42")

    assert "tmux new-session -A -s plan-42" in result
    assert "erk objective plan 42" in result


def test_build_codespace_tmux_command_sanitizes_session_name() -> None:
    """build_codespace_tmux_command sanitizes special characters in session names."""
    result = build_codespace_tmux_command(
        "erk objective plan 42",
        session_name="plan/42_foo.bar",
    )

    # Slashes, underscores, dots become hyphens
    assert "tmux new-session -A -s plan-42-foo-bar" in result


def test_build_codespace_tmux_command_uses_login_shell() -> None:
    """build_codespace_tmux_command uses bash login shell."""
    result = build_codespace_tmux_command("erk objective plan 42", session_name="plan-42")

    assert result.startswith("bash -l -c '")


def test_sanitize_tmux_session_name_collapses_consecutive_hyphens() -> None:
    """_sanitize_tmux_session_name collapses multiple hyphens into one."""
    assert _sanitize_tmux_session_name("a---b") == "a-b"


def test_sanitize_tmux_session_name_strips_leading_trailing_hyphens() -> None:
    """_sanitize_tmux_session_name strips leading and trailing hyphens."""
    assert _sanitize_tmux_session_name("-abc-") == "abc"


def test_sanitize_tmux_session_name_lowercases() -> None:
    """_sanitize_tmux_session_name lowercases the input."""
    assert _sanitize_tmux_session_name("Plan-42") == "plan-42"
