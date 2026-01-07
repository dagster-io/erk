"""Tests for FakeTerminal implementation.

Layer 1 tests: Verify the fake implementation works correctly.
"""

from erk_shared.gateway.terminal.fake import FakeTerminal


def test_fake_terminal_returns_configured_interactive_true() -> None:
    """Test FakeTerminal returns True when configured as interactive."""
    terminal = FakeTerminal(is_interactive=True)
    assert terminal.is_stdin_interactive() is True


def test_fake_terminal_returns_configured_interactive_false() -> None:
    """Test FakeTerminal returns False when configured as non-interactive."""
    terminal = FakeTerminal(is_interactive=False)
    assert terminal.is_stdin_interactive() is False
