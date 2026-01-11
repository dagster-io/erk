"""Tests for interactive Claude launcher utilities."""

from erk.core.interactive_claude import build_claude_args, build_claude_command_string
from erk_shared.context.types import InteractiveClaudeConfig


def test_build_claude_args_default_config() -> None:
    """build_claude_args with default config returns base args."""
    config = InteractiveClaudeConfig.default()

    args = build_claude_args(config, command="/test-cmd")

    assert args == ["claude", "--permission-mode", "acceptEdits", "/test-cmd"]


def test_build_claude_args_with_model() -> None:
    """build_claude_args includes --model when set."""
    config = InteractiveClaudeConfig(
        model="opus",
        verbose=False,
        permission_mode="acceptEdits",
        dangerous=False,
    )

    args = build_claude_args(config, command="/test-cmd")

    assert args == [
        "claude",
        "--permission-mode",
        "acceptEdits",
        "--model",
        "opus",
        "/test-cmd",
    ]


def test_build_claude_args_with_dangerous() -> None:
    """build_claude_args includes --dangerously-skip-permissions when dangerous=True."""
    config = InteractiveClaudeConfig(
        model=None,
        verbose=False,
        permission_mode="acceptEdits",
        dangerous=True,
    )

    args = build_claude_args(config, command="/test-cmd")

    assert "--dangerously-skip-permissions" in args


def test_build_claude_args_plan_mode() -> None:
    """build_claude_args uses permission_mode from config."""
    config = InteractiveClaudeConfig(
        model=None,
        verbose=False,
        permission_mode="plan",
        dangerous=False,
    )

    args = build_claude_args(config, command="/test-cmd")

    assert args == ["claude", "--permission-mode", "plan", "/test-cmd"]


def test_build_claude_args_empty_command() -> None:
    """build_claude_args with empty command omits command arg."""
    config = InteractiveClaudeConfig.default()

    args = build_claude_args(config, command="")

    # Empty command should not be appended
    assert args == ["claude", "--permission-mode", "acceptEdits"]


def test_build_claude_args_all_options() -> None:
    """build_claude_args with all options set."""
    config = InteractiveClaudeConfig(
        model="claude-opus-4-5",
        verbose=True,
        permission_mode="plan",
        dangerous=True,
    )

    args = build_claude_args(config, command="/erk:objective-next-plan 123")

    assert args == [
        "claude",
        "--permission-mode",
        "plan",
        "--dangerously-skip-permissions",
        "--model",
        "claude-opus-4-5",
        "/erk:objective-next-plan 123",
    ]


def test_build_claude_command_string_default() -> None:
    """build_claude_command_string with default config."""
    config = InteractiveClaudeConfig.default()

    cmd = build_claude_command_string(config, command="/test-cmd")

    assert cmd == 'claude --permission-mode acceptEdits "/test-cmd"'


def test_build_claude_command_string_plan_mode() -> None:
    """build_claude_command_string with plan mode."""
    config = InteractiveClaudeConfig(
        model=None,
        verbose=False,
        permission_mode="plan",
        dangerous=False,
    )

    cmd = build_claude_command_string(config, command="/test-cmd")

    assert cmd == 'claude --permission-mode plan "/test-cmd"'


def test_build_claude_command_string_all_options() -> None:
    """build_claude_command_string with all options set."""
    config = InteractiveClaudeConfig(
        model="opus",
        verbose=True,
        permission_mode="plan",
        dangerous=True,
    )

    cmd = build_claude_command_string(config, command="/test-cmd")

    expected = (
        'claude --permission-mode plan --dangerously-skip-permissions --model opus "/test-cmd"'
    )
    assert cmd == expected


def test_build_claude_command_string_empty_command() -> None:
    """build_claude_command_string with empty command omits command."""
    config = InteractiveClaudeConfig.default()

    cmd = build_claude_command_string(config, command="")

    assert cmd == "claude --permission-mode acceptEdits"
