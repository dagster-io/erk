"""Tests for CLI help formatter with alias display."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import context_for_test
from erk_shared.context.types import GlobalConfig


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


def test_help_shows_hidden_commands_when_config_enabled() -> None:
    """Help output shows hidden commands when show_hidden_commands is True in config."""
    runner = CliRunner()

    # Create context with show_hidden_commands=True
    ctx = context_for_test(
        global_config=GlobalConfig(
            erk_root=Path("/tmp/erks"),
            use_graphite=False,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
            show_hidden_commands=True,
        ),
    )

    # Invoke CLI with pre-configured context
    result = runner.invoke(cli, ["--help"], obj=ctx)

    assert result.exit_code == 0
    # When show_hidden is True, there should be a "Hidden" section
    # or the hidden shell-integration command should be visible
    # The exact assertion depends on whether there are hidden commands defined
    # The hidden_shell_cmd is registered in cli.py, let's check for that
    assert "Hidden:" in result.output or "shell-integration" in result.output


def test_help_hides_hidden_commands_when_config_disabled() -> None:
    """Help output hides hidden commands when show_hidden_commands is False in config."""
    runner = CliRunner()

    # Create context with show_hidden_commands=False (default)
    ctx = context_for_test(
        global_config=GlobalConfig(
            erk_root=Path("/tmp/erks"),
            use_graphite=False,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
            show_hidden_commands=False,
        ),
    )

    # Invoke CLI with pre-configured context
    result = runner.invoke(cli, ["--help"], obj=ctx)

    assert result.exit_code == 0
    # When show_hidden is False, there should NOT be a "Hidden:" section
    assert "Hidden:" not in result.output


def test_command_hidden_options_visible_when_config_enabled() -> None:
    """Hidden options like --script are visible in a separate section when config enabled."""
    runner = CliRunner()

    # Create context with show_hidden_commands=True
    ctx = context_for_test(
        global_config=GlobalConfig(
            erk_root=Path("/tmp/erks"),
            use_graphite=False,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
            show_hidden_commands=True,
        ),
    )

    # Test the 'up' command which uses ErkCommand with @script_option
    result = runner.invoke(cli, ["up", "--help"], obj=ctx)

    assert result.exit_code == 0
    # Should have "Hidden Options" section with --script
    assert "Hidden Options:" in result.output
    assert "--script" in result.output


def test_command_hidden_options_hidden_when_config_disabled() -> None:
    """Hidden options like --script stay hidden when config disabled."""
    runner = CliRunner()

    # Create context with show_hidden_commands=False
    ctx = context_for_test(
        global_config=GlobalConfig(
            erk_root=Path("/tmp/erks"),
            use_graphite=False,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
            show_hidden_commands=False,
        ),
    )

    # Test the 'up' command which uses ErkCommand with @script_option
    result = runner.invoke(cli, ["up", "--help"], obj=ctx)

    assert result.exit_code == 0
    # Should NOT have "Hidden Options" section
    assert "Hidden Options:" not in result.output
    # The Options section should not list --script as an option
    # (Note: --script may appear in usage examples in the docstring, which is fine)
    lines = result.output.split("\n")
    in_options_section = False
    for line in lines:
        if line.strip().startswith("Options:"):
            in_options_section = True
        elif in_options_section and line.strip() and not line.startswith(" "):
            # End of options section (new section header)
            in_options_section = False
        elif in_options_section and "--script" in line:
            raise AssertionError("--script should not appear in Options section when hidden")


def test_script_option_help_text_clarifies_not_dry_run() -> None:
    """The --script option help text clarifies it is NOT a dry run."""
    runner = CliRunner()

    # Create context with show_hidden_commands=True to see the help text
    ctx = context_for_test(
        global_config=GlobalConfig(
            erk_root=Path("/tmp/erks"),
            use_graphite=False,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
            show_hidden_commands=True,
        ),
    )

    # Test the 'up' command
    result = runner.invoke(cli, ["up", "--help"], obj=ctx)

    assert result.exit_code == 0
    # The help text should clarify this is NOT a dry run
    assert "NOT a dry run" in result.output
