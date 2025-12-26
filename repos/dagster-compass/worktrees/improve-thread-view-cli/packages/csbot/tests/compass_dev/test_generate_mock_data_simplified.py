"""Simplified tests for generate-mock-data CLI command focusing on core functionality."""

from click.testing import CliRunner

from csbot.compass_dev.cli import cli


class TestGenerateMockDataBasic:
    """Basic smoke tests for generate-mock-data command."""

    def test_preview_mode_works(self):
        """Test generate-mock-data preview mode shows expected content."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate-mock-data", "--preview"])

        assert result.exit_code == 0
        # Just verify it shows preview content without crashing
        assert "Mock data generation preview:" in result.output
        assert "accounts" in result.output.lower()
        assert "opportunities" in result.output.lower()

    def test_help_text_accessible(self):
        """Test that help text is accessible and contains key info."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate-mock-data", "--help"])

        assert result.exit_code == 0
        assert "Generate realistic CRM mock data" in result.output
        assert "--preview" in result.output
        assert "--output-dir" in result.output

    def test_can_invoke_without_crashing(self):
        """Test that generate-mock-data can be invoked without crashing."""
        runner = CliRunner()

        # Use preview mode to avoid file I/O
        result = runner.invoke(cli, ["generate-mock-data", "--preview"])

        assert result.exit_code == 0
        assert "Mock data generation preview:" in result.output

    def test_validates_output_directory_option(self):
        """Test that the output-dir option is recognized."""
        runner = CliRunner()

        # This should at least parse the option correctly before failing
        result = runner.invoke(
            cli, ["generate-mock-data", "--output-dir", "/nonexistent/path", "--preview"]
        )

        # Should still work in preview mode regardless of output path
        assert result.exit_code == 0
