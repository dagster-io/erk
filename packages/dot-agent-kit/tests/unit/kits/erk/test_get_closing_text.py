"""Tests for get-closing-text kit CLI command.

Tests the closing text generation for PR body based on .impl/issue.json.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.scripts.erk.get_closing_text import get_closing_text


def test_get_closing_text_with_issue_reference(tmp_path: Path, monkeypatch) -> None:
    """Test get-closing-text outputs 'Closes #N' when issue.json exists."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    issue_json = impl_dir / "issue.json"
    issue_json.write_text(
        json.dumps(
            {
                "issue_number": 776,
                "issue_url": "https://github.com/org/repo/issues/776",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text)

    assert result.exit_code == 0
    assert result.output.strip() == "Closes #776"


def test_get_closing_text_no_impl_folder(tmp_path: Path, monkeypatch) -> None:
    """Test get-closing-text outputs nothing when no .impl/ folder exists."""
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text)

    assert result.exit_code == 0
    assert result.output == ""


def test_get_closing_text_no_issue_json(tmp_path: Path, monkeypatch) -> None:
    """Test get-closing-text outputs nothing when .impl/ exists but no issue.json."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text)

    assert result.exit_code == 0
    assert result.output == ""


def test_get_closing_text_with_worker_impl(tmp_path: Path, monkeypatch) -> None:
    """Test get-closing-text works with .worker-impl/ folder."""
    impl_dir = tmp_path / ".worker-impl"
    impl_dir.mkdir()

    issue_json = impl_dir / "issue.json"
    issue_json.write_text(
        json.dumps(
            {
                "issue_number": 2935,
                "issue_url": "https://github.com/dagster-io/erk/issues/2935",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text)

    assert result.exit_code == 0
    assert result.output.strip() == "Closes #2935"


def test_get_closing_text_prefers_impl_over_worker_impl(tmp_path: Path, monkeypatch) -> None:
    """Test get-closing-text prefers .impl/ when both folders exist."""
    # Create both folders with different issue numbers
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    (impl_dir / "issue.json").write_text(
        json.dumps(
            {
                "issue_number": 100,
                "issue_url": "https://github.com/org/repo/issues/100",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    worker_impl_dir = tmp_path / ".worker-impl"
    worker_impl_dir.mkdir()
    (worker_impl_dir / "issue.json").write_text(
        json.dumps(
            {
                "issue_number": 200,
                "issue_url": "https://github.com/org/repo/issues/200",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text)

    assert result.exit_code == 0
    assert result.output.strip() == "Closes #100"


def test_get_closing_text_invalid_json(tmp_path: Path, monkeypatch) -> None:
    """Test get-closing-text handles invalid JSON gracefully."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    issue_json = impl_dir / "issue.json"
    issue_json.write_text("not valid json {{{", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text)

    # Should exit successfully but output nothing (graceful degradation)
    assert result.exit_code == 0
    assert result.output == ""
