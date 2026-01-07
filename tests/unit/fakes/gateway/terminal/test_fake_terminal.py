"""Tests for FakeTerminal implementation.

Layer 1 tests: Verify the fake implementation works correctly.
"""

from erk_shared.gateway.terminal.fake import FakeTerminal


def test_fake_terminal_returns_configured_interactive_true() -> None:
    """Test FakeTerminal returns True when configured as interactive."""
    terminal = FakeTerminal(is_interactive=True, is_stdout_tty=None, is_stderr_tty=None)
    assert terminal.is_stdin_interactive() is True


def test_fake_terminal_returns_configured_interactive_false() -> None:
    """Test FakeTerminal returns False when configured as non-interactive."""
    terminal = FakeTerminal(is_interactive=False, is_stdout_tty=None, is_stderr_tty=None)
    assert terminal.is_stdin_interactive() is False


def test_fake_terminal_stdout_tty_defaults_to_stdin() -> None:
    """Test that is_stdout_tty defaults to is_interactive when not specified."""
    terminal_interactive = FakeTerminal(is_interactive=True, is_stdout_tty=None, is_stderr_tty=None)
    terminal_non_interactive = FakeTerminal(
        is_interactive=False, is_stdout_tty=None, is_stderr_tty=None
    )

    assert terminal_interactive.is_stdout_tty() is True
    assert terminal_non_interactive.is_stdout_tty() is False


def test_fake_terminal_stderr_tty_defaults_to_stdin() -> None:
    """Test that is_stderr_tty defaults to is_interactive when not specified."""
    terminal_interactive = FakeTerminal(is_interactive=True, is_stdout_tty=None, is_stderr_tty=None)
    terminal_non_interactive = FakeTerminal(
        is_interactive=False, is_stdout_tty=None, is_stderr_tty=None
    )

    assert terminal_interactive.is_stderr_tty() is True
    assert terminal_non_interactive.is_stderr_tty() is False


def test_fake_terminal_stdout_tty_can_be_configured_independently() -> None:
    """Test that is_stdout_tty can be configured independently from stdin."""
    terminal = FakeTerminal(is_interactive=True, is_stdout_tty=False, is_stderr_tty=None)

    assert terminal.is_stdin_interactive() is True
    assert terminal.is_stdout_tty() is False
    assert terminal.is_stderr_tty() is True  # Defaults to match stdin


def test_fake_terminal_stderr_tty_can_be_configured_independently() -> None:
    """Test that is_stderr_tty can be configured independently from stdin."""
    terminal = FakeTerminal(is_interactive=True, is_stdout_tty=None, is_stderr_tty=False)

    assert terminal.is_stdin_interactive() is True
    assert terminal.is_stdout_tty() is True  # Defaults to match stdin
    assert terminal.is_stderr_tty() is False


def test_fake_terminal_all_tty_states_independent() -> None:
    """Test that all TTY states can be configured independently."""
    # Simulate a scenario where stdin is interactive but stdout/stderr are captured
    terminal = FakeTerminal(is_interactive=True, is_stdout_tty=False, is_stderr_tty=False)

    assert terminal.is_stdin_interactive() is True
    assert terminal.is_stdout_tty() is False
    assert terminal.is_stderr_tty() is False
