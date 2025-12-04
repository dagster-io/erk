"""Unit tests for shell integration command routing."""

from erk.cli.shell_integration.handler import SHELL_INTEGRATION_COMMANDS


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
