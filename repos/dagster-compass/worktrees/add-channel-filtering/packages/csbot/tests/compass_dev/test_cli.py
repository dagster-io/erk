"""Tests for compass-dev CLI core functionality."""

from click.testing import CliRunner

from csbot.compass_dev.cli import cli


class TestCompassDevCLI:
    """Tests for the main compass-dev CLI interface."""

    def test_cli_help(self):
        """Test that the main CLI help is displayed correctly."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Compass developer tools" in result.output

        # Verify key commands are listed (not checking exact text to avoid brittleness)
        assert "ai-update-pr" in result.output
        assert "generate-mock-data" in result.output

    def test_ai_update_pr_help(self):
        """Test ai-update-pr command help text."""
        runner = CliRunner()
        result = runner.invoke(cli, ["ai-update-pr", "--help"])

        assert result.exit_code == 0
        assert "Update pull request using AI" in result.output
        assert "AI-powered PR update functionality" in result.output

    def test_bq_provision_help(self):
        """Test bq-provision command help text."""
        runner = CliRunner()
        result = runner.invoke(cli, ["bq-provision", "--help"])

        assert result.exit_code == 0
        assert "Provision BigQuery service account" in result.output
        assert "--dry-run" in result.output

    def test_generate_mock_data_help(self):
        """Test generate-mock-data command help text."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate-mock-data", "--help"])

        assert result.exit_code == 0
        assert "Generate realistic CRM mock data" in result.output
        assert "--output-dir" in result.output
        assert "--preview" in result.output

    def test_land_pr_help(self):
        """Test land-pr command help text."""
        runner = CliRunner()
        result = runner.invoke(cli, ["land-pr", "--help"])

        assert result.exit_code == 0
        assert "Land a pull request using Graphite workflow" in result.output
        assert "--dry-run" in result.output

    def test_pr_operations_help(self):
        """Test pr-ops command help text."""
        runner = CliRunner()
        result = runner.invoke(cli, ["pr-ops", "--help"])

        assert result.exit_code == 0
        # Just verify it's a group command with subcommands
        assert "Commands:" in result.output or "Usage:" in result.output

    def test_invalid_command(self):
        """Test behavior with invalid command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["invalid-command"])

        assert result.exit_code != 0
        assert "No such command" in result.output

    def test_cli_without_arguments(self):
        """Test CLI behavior when called without arguments."""
        runner = CliRunner()
        result = runner.invoke(cli)

        # Click exits with code 2 when no command is provided, which is expected
        assert result.exit_code == 2
        # Should show usage information
        assert "Usage:" in result.output
