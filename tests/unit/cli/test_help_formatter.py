"""Tests for CLI help formatter with alias display."""

from click.testing import CliRunner

from erk.cli.cli import cli


def test_help_shows_checkout_with_alias() -> None:
    """Help output shows 'checkout (co)' on a single line."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    # Should show combined format: "checkout (co)"
    assert "checkout (co)" in result.output


def test_help_shows_dash_command() -> None:
    """Help output shows 'dash' command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    # Should show dash command (no alias since it's been renamed from list/ls)
    assert "dash" in result.output


def test_help_does_not_show_co_as_separate_row() -> None:
    """Help output does not show 'co' as a separate row."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    output_lines = result.output.split("\n")

    # Check that 'co' doesn't appear as standalone commands
    # It should only appear as part of "checkout (co)"
    for line in output_lines:
        # Skip lines that are the combined format
        if "checkout (co)" in line:
            continue
        # Standalone alias would be at start of line with spaces
        stripped = line.strip()
        if stripped.startswith("co ") or stripped == "co":
            raise AssertionError(f"Found 'co' as standalone command: {line}")


def test_co_alias_still_works_as_command() -> None:
    """Alias 'co' still works as an invokable command."""
    runner = CliRunner()

    # Test 'co --help' works (even though we can't invoke checkout without args)
    co_result = runner.invoke(cli, ["co", "--help"])
    assert co_result.exit_code == 0
    assert "checkout" in co_result.output.lower() or "worktree" in co_result.output.lower()
