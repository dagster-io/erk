"""Unit tests for shell integration command routing."""

from erk.cli.shell_integration.handler import (
    GLOBAL_FLAGS,
    SHELL_INTEGRATION_COMMANDS,
    handle_shell_request,
)


def test_pr_land_compound_command_registered() -> None:
    """Verify 'pr land' compound command is registered for shell integration.

    This prevents regression of the bug where 'erk pr land' via shell wrapper
    failed with "requires shell integration" error because the compound command
    was not registered in SHELL_INTEGRATION_COMMANDS.

    When compound commands are missing:
    1. Shell wrapper intercepts → calls 'erk __shell pr land'
    2. Handler checks for "pr land" compound command → NOT FOUND
    3. Falls back to "pr" (the group) → --script goes to pr_group, not pr_land
    4. pr_land never receives --script flag → fails with error
    """
    assert "pr land" in SHELL_INTEGRATION_COMMANDS


def test_compound_commands_have_all_expected_entries() -> None:
    """Verify all expected compound commands are registered.

    Compound commands use "group subcommand" format and must be registered
    explicitly so shell integration routes --script to the correct handler.
    """
    expected_compound_commands = [
        "wt create",
        "wt goto",
        "stack consolidate",
        "pr land",
    ]

    for cmd in expected_compound_commands:
        assert cmd in SHELL_INTEGRATION_COMMANDS, f"Missing compound command: {cmd}"


def test_top_level_commands_registered() -> None:
    """Verify top-level commands are registered for shell integration."""
    expected_top_level = [
        "checkout",
        "co",  # alias
        "up",
        "down",
        "implement",
        "pr",  # group
    ]

    for cmd in expected_top_level:
        assert cmd in SHELL_INTEGRATION_COMMANDS, f"Missing top-level command: {cmd}"


def test_legacy_aliases_registered() -> None:
    """Verify legacy top-level aliases for backward compatibility."""
    expected_aliases = [
        "create",
        "goto",
        "consolidate",
    ]

    for alias in expected_aliases:
        assert alias in SHELL_INTEGRATION_COMMANDS, f"Missing legacy alias: {alias}"


def test_global_flags_stripped_before_command_matching() -> None:
    """Global flags like --debug should not prevent command recognition.

    When running 'erk --debug pr land', the handler receives args like
    ('--debug', 'pr', 'land'). Without stripping global flags, the handler
    tries to match '--debug pr' as a compound command (not found), then
    '--debug' as a single command (not found), and falls back to passthrough.

    This test verifies that global flags are stripped before command matching,
    so 'pr land' is correctly recognized as a compound command.
    """
    # With --help present, the handler should recognize 'pr land' and passthrough
    # (since --help causes passthrough behavior for recognized commands)
    result = handle_shell_request(("--debug", "pr", "land", "--help"))
    assert result.passthrough is True

    # Multiple global flags should all be stripped
    result = handle_shell_request(("--debug", "--verbose", "pr", "land", "--help"))
    assert result.passthrough is True


def test_global_flags_constant_contains_expected_flags() -> None:
    """Verify GLOBAL_FLAGS contains all expected top-level flags."""
    expected_flags = ["--debug", "--dry-run", "--verbose", "-v"]
    for flag in expected_flags:
        assert flag in GLOBAL_FLAGS, f"Missing global flag: {flag}"


def test_only_global_flags_returns_passthrough() -> None:
    """If args contain only global flags, handler should passthrough."""
    result = handle_shell_request(("--debug",))
    assert result.passthrough is True

    result = handle_shell_request(("--debug", "--verbose"))
    assert result.passthrough is True
