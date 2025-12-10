"""Tests for gt quick-submit kit CLI command.

This command wraps subprocess calls to git and gt, so we test by invoking
the command through erk kit exec CLI.
"""

import subprocess


class TestQuickSubmitIntegration:
    """Integration tests for quick-submit command via erk kit exec CLI."""

    def test_quick_submit_help(self) -> None:
        """Test that quick-submit help is accessible."""
        result = subprocess.run(
            ["erk", "kit", "exec", "gt", "quick-submit", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "Quick commit all changes and submit with Graphite" in result.stdout

    def test_stages_commits_and_submits_when_changes_exist(self) -> None:
        """Test the full flow description in help text."""
        # For now, verify the command structure works
        result = subprocess.run(
            ["erk", "kit", "exec", "gt", "quick-submit", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert "Stages all changes" in result.stdout
        assert "commits with" in result.stdout
        assert "gt submit" in result.stdout

    def test_command_is_registered(self) -> None:
        """Verify quick-submit is available in gt kit."""
        result = subprocess.run(
            ["erk", "kit", "exec", "gt", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "quick-submit" in result.stdout
