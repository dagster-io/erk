"""Basic smoke tests for all compass-dev CLI commands.

These tests focus on verifying that commands can be invoked without crashing
and show appropriate help text, rather than testing detailed implementation.
"""

from click.testing import CliRunner

from csbot.compass_dev.cli import cli


class TestCompassDevSmokeTests:
    """Smoke tests to ensure all CLI commands are accessible."""

    def test_all_commands_show_help(self):
        """Test that all main commands show help without crashing."""
        commands = ["ai-update-pr", "bq-provision", "generate-mock-data", "land-pr", "pr-ops"]

        runner = CliRunner()

        for cmd in commands:
            result = runner.invoke(cli, [cmd, "--help"])
            assert result.exit_code == 0, f"Command '{cmd}' failed help test"
            assert "help" in result.output.lower() or "usage" in result.output.lower()

    def test_dry_run_commands_work(self):
        """Test that dry-run modes work for commands that support them."""
        dry_run_commands = [["bq-provision", "--dry-run"], ["land-pr", "--dry-run"]]

        runner = CliRunner()

        for cmd_args in dry_run_commands:
            result = runner.invoke(cli, cmd_args)
            assert result.exit_code == 0, f"Dry run failed for {' '.join(cmd_args)}"
            # Should contain some indication it's a dry run
            assert "dry run" in result.output.lower() or "would" in result.output.lower()

    def test_pr_operations_subcommands_help(self):
        """Test that pr-ops subcommands show help."""
        subcommands = ["prepare", "execute", "auto-update", "squash-push-draft"]

        runner = CliRunner()

        for subcmd in subcommands:
            result = runner.invoke(cli, ["pr-ops", subcmd, "--help"])
            assert result.exit_code == 0, f"PR operations '{subcmd}' help failed"

    def test_invalid_command_handled(self):
        """Test that invalid commands are handled gracefully."""
        runner = CliRunner()
        result = runner.invoke(cli, ["nonexistent-command"])

        assert result.exit_code != 0
        assert "No such command" in result.output or "not found" in result.output.lower()

    def test_missing_required_args_handled(self):
        """Test that missing required arguments are handled gracefully."""
        runner = CliRunner()

        # pr-ops execute requires title, description, and pr-url
        result = runner.invoke(cli, ["pr-ops", "execute"])

        assert result.exit_code != 0
        assert "missing" in result.output.lower() or "required" in result.output.lower()


class TestGenerateMockDataSmoke:
    """Focused smoke tests for generate-mock-data command."""

    def test_preview_mode_safe(self):
        """Test that preview mode is safe and informative."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate-mock-data", "--preview"])

        assert result.exit_code == 0
        assert "preview" in result.output.lower()
        # Should mention key datasets
        output_lower = result.output.lower()
        assert any(dataset in output_lower for dataset in ["accounts", "opportunities", "tickets"])


class TestBQProvisionSmoke:
    """Focused smoke tests for bq-provision command."""

    def test_dry_run_informative(self):
        """Test that dry-run shows what would be done."""
        runner = CliRunner()
        result = runner.invoke(cli, ["bq-provision", "--dry-run"])

        assert result.exit_code == 0
        assert "dry run" in result.output.lower()
        assert "gcloud" in result.output.lower() or "service account" in result.output.lower()
