"""Tests for changelog-commits command functions."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk_dev.cli import cli
from erk_dev.commands.changelog_commits.command import (
    extract_pr_number,
    parse_changelog_marker,
)


class TestParseChangelogMarker:
    """Tests for parse_changelog_marker function."""

    def test_finds_marker_in_unreleased_section(self, tmp_path: Path) -> None:
        changelog = tmp_path / "CHANGELOG.md"
        content = """# Changelog

## [Unreleased]

As of `af8fa25c9`

### Added

- New feature

## [1.0.0] - 2025-01-01
"""
        changelog.write_text(content, encoding="utf-8")
        result = parse_changelog_marker(changelog)
        assert result == "af8fa25c9"

    def test_finds_short_hash(self, tmp_path: Path) -> None:
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("As of `b5e949b`\n", encoding="utf-8")
        result = parse_changelog_marker(changelog)
        assert result == "b5e949b"

    def test_finds_full_hash(self, tmp_path: Path) -> None:
        changelog = tmp_path / "CHANGELOG.md"
        # Full git SHA-1 hash is exactly 40 characters
        full_hash = "b5e949b45c6d7a8e9f0a1b2c3d4e5f67890abcde"
        changelog.write_text(f"As of `{full_hash}`\n", encoding="utf-8")
        result = parse_changelog_marker(changelog)
        assert result == full_hash

    def test_returns_none_when_no_marker(self, tmp_path: Path) -> None:
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n## [Unreleased]\n", encoding="utf-8")
        result = parse_changelog_marker(changelog)
        assert result is None

    def test_returns_none_when_file_not_exists(self, tmp_path: Path) -> None:
        changelog = tmp_path / "CHANGELOG.md"
        result = parse_changelog_marker(changelog)
        assert result is None


class TestExtractPrNumber:
    """Tests for extract_pr_number function."""

    def test_extracts_pr_number_at_end(self) -> None:
        subject = "Fix artifact sync to only copy bundled items (#3619)"
        result = extract_pr_number(subject)
        assert result == 3619

    def test_extracts_pr_number_with_trailing_space(self) -> None:
        subject = "Add new feature (#123) "
        result = extract_pr_number(subject)
        assert result == 123

    def test_returns_none_without_pr_number(self) -> None:
        subject = "Fix bug in the system"
        result = extract_pr_number(subject)
        assert result is None

    def test_returns_none_for_issue_reference_in_middle(self) -> None:
        # Only matches (#NNNN) at the end
        subject = "Fix issue #123 in the system"
        result = extract_pr_number(subject)
        assert result is None

    def test_returns_none_for_parenthesized_number_without_hash(self) -> None:
        subject = "Update version (123)"
        result = extract_pr_number(subject)
        assert result is None


class TestChangelogCommitsCommand:
    """Tests for changelog-commits CLI command."""

    def test_help_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["changelog-commits", "--help"])
        assert result.exit_code == 0
        assert "Get commits for changelog update" in result.output

    def test_error_when_no_changelog(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["changelog-commits", "--json-output"])
            assert result.exit_code == 1
            output = json.loads(result.output)
            assert output["success"] is False
            assert "CHANGELOG.md not found" in output["error"]

    def test_error_when_no_marker(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n", encoding="utf-8")
            result = runner.invoke(cli, ["changelog-commits", "--json-output"])
            assert result.exit_code == 1
            output = json.loads(result.output)
            assert output["success"] is False
            assert "No 'As of <commit>' marker found" in output["error"]

    def test_since_bypasses_marker_requirement(self) -> None:
        """Test that --since bypasses the CHANGELOG marker parsing."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # CHANGELOG has no marker, but --since is provided
            Path("CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n", encoding="utf-8")
            # Use a fake commit hash - will fail at git verification, not marker parsing
            result = runner.invoke(
                cli, ["changelog-commits", "--json-output", "--since", "abc123def"]
            )
            assert result.exit_code == 1
            output = json.loads(result.output)
            assert output["success"] is False
            # Should fail at git verification, NOT at marker parsing
            assert "Commit abc123def not found" in output["error"]
            assert "No 'As of <commit>' marker found" not in output["error"]

    def test_since_with_invalid_commit(self) -> None:
        """Test that --since with invalid commit hash returns proper error."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Even without CHANGELOG, should fail at git verification
            result = runner.invoke(
                cli, ["changelog-commits", "--json-output", "--since", "invalid123"]
            )
            # Note: Will fail either at "not in git repo" or "commit not found"
            assert result.exit_code == 1
            output = json.loads(result.output)
            assert output["success"] is False

    def test_since_does_not_require_changelog(self) -> None:
        """Test that --since doesn't require CHANGELOG.md to exist."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # No CHANGELOG.md at all, but --since is provided
            result = runner.invoke(
                cli, ["changelog-commits", "--json-output", "--since", "abc123def"]
            )
            assert result.exit_code == 1
            output = json.loads(result.output)
            assert output["success"] is False
            # Should fail at git verification, NOT at CHANGELOG not found
            assert "CHANGELOG.md not found" not in output["error"]
