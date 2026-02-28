"""Tests for the OneShotPromptScreen modal."""

from erk.tui.screens.one_shot_prompt_screen import OneShotPromptScreen


def test_escape_binding_exists() -> None:
    """OneShotPromptScreen should have an escape binding."""
    screen = OneShotPromptScreen()
    binding_keys = [b.key for b in screen.BINDINGS]
    assert "escape" in binding_keys


def test_q_is_not_bound() -> None:
    """OneShotPromptScreen should NOT bind 'q' — user needs it for typing."""
    screen = OneShotPromptScreen()
    binding_keys = [b.key for b in screen.BINDINGS]
    assert "q" not in binding_keys
