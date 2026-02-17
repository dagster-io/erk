"""Unit tests for download-remote-session exec script.

Tests downloading session files from GitHub Gist URLs.
Uses fake URL fetchers injected into _execute_download.
"""

import urllib.error
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.download_remote_session import (
    _execute_download,
    _get_remote_sessions_dir,
    normalize_gist_url,
)
from erk.cli.commands.exec.scripts.download_remote_session import (
    download_remote_session as download_remote_session_command,
)

# ============================================================================
# 1. Helper Function Tests (2 tests)
# ============================================================================


def test_get_remote_sessions_dir_creates_directory(tmp_path: Path) -> None:
    """Test that the remote sessions directory is created if it doesn't exist."""
    session_id = "test-session-123"

    result = _get_remote_sessions_dir(tmp_path, session_id)

    expected = tmp_path / ".erk" / "scratch" / "remote-sessions" / session_id
    assert result == expected
    assert result.exists()
    assert result.is_dir()


def test_get_remote_sessions_dir_returns_existing(tmp_path: Path) -> None:
    """Test that existing directory is returned without error."""
    session_id = "existing-session"
    expected = tmp_path / ".erk" / "scratch" / "remote-sessions" / session_id
    expected.mkdir(parents=True)

    result = _get_remote_sessions_dir(tmp_path, session_id)

    assert result == expected


# ============================================================================
# 2. URL Normalization Tests (4 tests)
# ============================================================================


def test_normalize_gist_url_webpage_to_raw() -> None:
    """Test that gist.github.com webpage URL is converted to raw URL.

    Uses /raw/ without filename - GitHub redirects to the first file in single-file gists.
    """
    webpage_url = "https://gist.github.com/schrockn/33680528033dc162ed0d563c063c70bb"

    result = normalize_gist_url(webpage_url)

    expected = "https://gist.githubusercontent.com/schrockn/33680528033dc162ed0d563c063c70bb/raw/"
    assert result == expected


def test_normalize_gist_url_webpage_with_trailing_slash() -> None:
    """Test that webpage URL with trailing slash is handled correctly."""
    webpage_url = "https://gist.github.com/schrockn/33680528033dc162ed0d563c063c70bb/"

    result = normalize_gist_url(webpage_url)

    expected = "https://gist.githubusercontent.com/schrockn/33680528033dc162ed0d563c063c70bb/raw/"
    assert result == expected


def test_normalize_gist_url_raw_passthrough() -> None:
    """Test that gist.githubusercontent.com raw URL passes through unchanged."""
    raw_url = "https://gist.githubusercontent.com/user/abc123/raw/session.jsonl"

    result = normalize_gist_url(raw_url)

    assert result == raw_url


def test_normalize_gist_url_unknown_format_passthrough() -> None:
    """Test that unknown URL formats pass through unchanged."""
    unknown_url = "https://example.com/some/path"

    result = normalize_gist_url(unknown_url)

    assert result == unknown_url


# ============================================================================
# 3. CLI Argument Validation Tests (2 tests)
# ============================================================================


def test_cli_missing_gist_url() -> None:
    """Test CLI requires --gist-url option."""
    runner = CliRunner()

    result = runner.invoke(
        download_remote_session_command,
        ["--session-id", "test-123"],
    )

    assert result.exit_code != 0
    assert "gist-url" in result.output.lower() or "missing" in result.output.lower()


def test_cli_missing_session_id() -> None:
    """Test CLI requires --session-id option."""
    runner = CliRunner()

    result = runner.invoke(
        download_remote_session_command,
        ["--gist-url", "https://gist.githubusercontent.com/user/abc/raw/session.jsonl"],
    )

    assert result.exit_code != 0
    assert "session-id" in result.output.lower() or "missing" in result.output.lower()


# ============================================================================
# 4. Core Logic Tests (4 tests) — call _execute_download with fake fetchers
# ============================================================================


def test_success_download(tmp_path: Path) -> None:
    """Test successful download from gist URL."""
    session_id = "abc-123"
    gist_url = "https://gist.githubusercontent.com/user/abc123/raw/session.jsonl"
    session_content = '{"type": "assistant"}\n{"type": "user"}\n'

    exit_code, output = _execute_download(
        repo_root=tmp_path,
        gist_url=gist_url,
        session_id=session_id,
        url_fetcher=lambda url: session_content.encode("utf-8"),
    )

    assert exit_code == 0
    assert output["success"] is True
    assert output["session_id"] == session_id
    assert output["source"] == "gist"
    assert "session.jsonl" in str(output["path"])

    session_file = Path(str(output["path"]))
    assert session_file.exists()
    assert session_file.read_text(encoding="utf-8") == session_content


def test_error_download_fails(tmp_path: Path) -> None:
    """Test error when gist URL cannot be fetched."""
    session_id = "bad-session"
    gist_url = "https://gist.githubusercontent.com/user/nonexistent/raw/session.jsonl"

    def failing_fetcher(url: str) -> bytes:
        raise urllib.error.URLError("404 Not Found")

    exit_code, output = _execute_download(
        repo_root=tmp_path,
        gist_url=gist_url,
        session_id=session_id,
        url_fetcher=failing_fetcher,
    )

    assert exit_code == 1
    assert output["success"] is False
    assert "Failed to download from gist URL" in str(output["error"])


def test_cleanup_existing_directory_on_redownload(tmp_path: Path) -> None:
    """Test that existing directory contents are cleaned up on re-download."""
    session_id = "redownload-session"
    gist_url = "https://gist.githubusercontent.com/user/abc/raw/session.jsonl"
    new_content = '{"new": true}\n'

    # Pre-create the session directory with old files
    session_dir = tmp_path / ".erk" / "scratch" / "remote-sessions" / session_id
    session_dir.mkdir(parents=True)
    old_file = session_dir / "old-session.jsonl"
    old_file.write_text('{"old": true}\n', encoding="utf-8")

    exit_code, output = _execute_download(
        repo_root=tmp_path,
        gist_url=gist_url,
        session_id=session_id,
        url_fetcher=lambda url: new_content.encode("utf-8"),
    )

    assert exit_code == 0
    assert output["success"] is True

    # Verify old file was cleaned up and new file exists as session.jsonl
    assert not old_file.exists()
    session_file = session_dir / "session.jsonl"
    assert session_file.exists()
    content = session_file.read_text(encoding="utf-8")
    assert "new" in content


def test_webpage_url_normalized_before_download(tmp_path: Path) -> None:
    """Test successful download from gist.github.com webpage URL (normalized to raw)."""
    session_id = "webpage-session"
    webpage_url = "https://gist.github.com/schrockn/33680528033dc162ed0d563c063c70bb"
    session_content = '{"type": "assistant"}\n'

    captured_urls: list[str] = []

    def capturing_fetcher(url: str) -> bytes:
        captured_urls.append(url)
        return session_content.encode("utf-8")

    exit_code, output = _execute_download(
        repo_root=tmp_path,
        gist_url=webpage_url,
        session_id=session_id,
        url_fetcher=capturing_fetcher,
    )

    assert exit_code == 0
    assert output["success"] is True
    assert output["session_id"] == session_id

    # Verify the URL was normalized before download (uses /raw/ without filename)
    expected_raw_url = (
        "https://gist.githubusercontent.com/schrockn/33680528033dc162ed0d563c063c70bb/raw/"
    )
    assert captured_urls == [expected_raw_url]
