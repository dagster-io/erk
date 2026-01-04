"""Tests for get-closing-text kit CLI command.

Tests the closing text generation for PR body based on .impl/issue.json or branch name.
"""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_closing_text import get_closing_text


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

    # Mock _get_current_branch to return a matching branch
    with patch("erk.cli.commands.exec.scripts.get_closing_text._get_current_branch") as mock_branch:
        mock_branch.return_value = "P776-feature-01-04-1234"
        runner = CliRunner()
        result = runner.invoke(get_closing_text)

    assert result.exit_code == 0
    assert result.output.strip() == "Closes #776"


def test_get_closing_text_no_impl_folder_with_branch_fallback(tmp_path: Path, monkeypatch) -> None:
    """Test get-closing-text uses branch name when no .impl/ folder exists."""
    monkeypatch.chdir(tmp_path)

    # Branch name encodes issue number
    with patch("erk.cli.commands.exec.scripts.get_closing_text._get_current_branch") as mock_branch:
        mock_branch.return_value = "P123-add-feature-01-04-1234"
        runner = CliRunner()
        result = runner.invoke(get_closing_text)

    assert result.exit_code == 0
    assert result.output.strip() == "Closes #123"


def test_get_closing_text_no_impl_folder_no_issue_in_branch(tmp_path: Path, monkeypatch) -> None:
    """Test get-closing-text outputs nothing when no .impl/ and branch has no issue."""
    monkeypatch.chdir(tmp_path)

    # Branch name without issue number pattern
    with patch("erk.cli.commands.exec.scripts.get_closing_text._get_current_branch") as mock_branch:
        mock_branch.return_value = "feature-branch"
        runner = CliRunner()
        result = runner.invoke(get_closing_text)

    assert result.exit_code == 0
    assert result.output == ""


def test_get_closing_text_no_issue_json(tmp_path: Path, monkeypatch) -> None:
    """Test get-closing-text outputs nothing when .impl/ exists but no issue.json."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    # Branch without issue prefix
    with patch("erk.cli.commands.exec.scripts.get_closing_text._get_current_branch") as mock_branch:
        mock_branch.return_value = "main"
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

    # Mock branch to match the issue
    with patch("erk.cli.commands.exec.scripts.get_closing_text._get_current_branch") as mock_branch:
        mock_branch.return_value = "P2935-feature"
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

    with patch("erk.cli.commands.exec.scripts.get_closing_text._get_current_branch") as mock_branch:
        mock_branch.return_value = "P100-feature"
        runner = CliRunner()
        result = runner.invoke(get_closing_text)

    assert result.exit_code == 0
    assert result.output.strip() == "Closes #100"


def test_get_closing_text_invalid_json(tmp_path: Path, monkeypatch) -> None:
    """Test get-closing-text handles invalid JSON gracefully via branch fallback."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    issue_json = impl_dir / "issue.json"
    issue_json.write_text("not valid json {{{", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    # With invalid JSON, validate_issue_linkage returns the branch issue number
    with patch("erk.cli.commands.exec.scripts.get_closing_text._get_current_branch") as mock_branch:
        mock_branch.return_value = "P42-feature"
        runner = CliRunner()
        result = runner.invoke(get_closing_text)

    # Falls back to branch issue number (invalid JSON means no impl_issue)
    assert result.exit_code == 0
    assert result.output.strip() == "Closes #42"


def test_get_closing_text_detached_head(tmp_path: Path, monkeypatch) -> None:
    """Test get-closing-text outputs nothing when on detached HEAD."""
    monkeypatch.chdir(tmp_path)

    # Detached HEAD - _get_current_branch returns None
    with patch("erk.cli.commands.exec.scripts.get_closing_text._get_current_branch") as mock_branch:
        mock_branch.return_value = None
        runner = CliRunner()
        result = runner.invoke(get_closing_text)

    assert result.exit_code == 0
    assert result.output == ""


def test_get_closing_text_branch_issue_json_mismatch(tmp_path: Path, monkeypatch) -> None:
    """Test get-closing-text fails when branch and issue.json disagree."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    issue_json = impl_dir / "issue.json"
    issue_json.write_text(
        json.dumps(
            {
                "issue_number": 99,
                "issue_url": "https://github.com/org/repo/issues/99",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    # Branch says issue 42, issue.json says issue 99 - mismatch!
    with patch("erk.cli.commands.exec.scripts.get_closing_text._get_current_branch") as mock_branch:
        mock_branch.return_value = "P42-wrong-issue-01-04-1234"
        runner = CliRunner()
        result = runner.invoke(get_closing_text)

    assert result.exit_code == 1
    assert "disagrees" in result.output
    assert "P42" in result.output
    assert "#99" in result.output
