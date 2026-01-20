"""Unit tests for download_gist_sessions exec script.

Tests for the `erk exec download-gist-sessions` command which downloads
preprocessed session files from a GitHub gist.
"""

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.download_gist_sessions import (
    _extract_gist_id,
    download_gist_sessions,
)


def test_extract_gist_id_from_full_url() -> None:
    """Test extracting gist ID from full GitHub gist URL with username."""
    url = "https://gist.github.com/username/abc123def456"
    assert _extract_gist_id(url) == "abc123def456"


def test_extract_gist_id_from_url_without_username() -> None:
    """Test extracting gist ID from gist URL without username."""
    url = "https://gist.github.com/abc123def456"
    assert _extract_gist_id(url) == "abc123def456"


def test_extract_gist_id_from_url_with_trailing_slash() -> None:
    """Test extracting gist ID from URL with trailing slash."""
    url = "https://gist.github.com/username/abc123def456/"
    assert _extract_gist_id(url) == "abc123def456"


def test_extract_gist_id_raw_id() -> None:
    """Test extracting gist ID when just the ID is passed."""
    raw_id = "abc123def456"
    assert _extract_gist_id(raw_id) == "abc123def456"


def test_extract_gist_id_invalid_url() -> None:
    """Test that invalid URL returns None."""
    url = "https://example.com/not-a-gist"
    assert _extract_gist_id(url) is None


def test_download_gist_sessions_requires_gist_url() -> None:
    """Test that --gist-url is required."""
    runner = CliRunner()

    result = runner.invoke(
        download_gist_sessions,
        ["--output-dir=/tmp/test"],
    )

    assert result.exit_code == 2
    assert "Missing option '--gist-url'" in result.output


def test_download_gist_sessions_requires_output_dir() -> None:
    """Test that --output-dir is required."""
    runner = CliRunner()

    result = runner.invoke(
        download_gist_sessions,
        ["--gist-url=https://gist.github.com/abc123"],
    )

    assert result.exit_code == 2
    assert "Missing option '--output-dir'" in result.output


def test_download_gist_sessions_command_registered() -> None:
    """Test that download-gist-sessions command is registered in exec group."""
    from erk.cli.commands.exec.group import exec_group

    command_names = [cmd.name for cmd in exec_group.commands.values()]
    assert "download-gist-sessions" in command_names
