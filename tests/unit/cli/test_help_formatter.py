"""Tests for CLI help formatter with alias display."""

from click.testing import CliRunner

from erk.cli.cli import cli


def test_help_shows_branch_with_alias() -> None:
    """Help output shows 'branch (br)' on a single line."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    # Should show combined format: "branch (br)"
    assert "branch (br)" in result.output


def test_help_shows_dash_command() -> None:
    """Help output shows 'dash' command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    # Should show dash command (no alias since it's been renamed from list/ls)
    assert "dash" in result.output


def test_help_does_not_show_br_as_separate_row() -> None:
    """Help output does not show 'br' as a separate row."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    output_lines = result.output.split("\n")

    # Check that 'br' doesn't appear as standalone commands
    # It should only appear as part of "branch (br)"
    for line in output_lines:
        # Skip lines that are the combined format
        if "branch (br)" in line:
            continue
        # Standalone alias would be at start of line with spaces
        stripped = line.strip()
        if stripped.startswith("br ") or stripped == "br":
            raise AssertionError(f"Found 'br' as standalone command: {line}")


def test_br_alias_still_works_as_command() -> None:
    """Alias 'br' still works as an invokable command."""
    runner = CliRunner()

    # Test 'br --help' works (even though we can't invoke branch without args)
    br_result = runner.invoke(cli, ["br", "--help"])
    assert br_result.exit_code == 0
    assert "branch" in br_result.output.lower() or "manage" in br_result.output.lower()
