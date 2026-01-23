"""Unit tests for get-pr-commits command.

Tests use mock subprocess to simulate gh api responses.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_pr_commits import get_pr_commits
from erk_shared.context.context import ErkContext


def test_get_pr_commits_success(tmp_path: Path) -> None:
    """Test successful PR commits fetch."""
    mock_commits = [
        {"sha": "abc123", "message": "First commit"},
        {"sha": "def456", "message": "Second commit"},
    ]

    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(mock_commits)
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(
            get_pr_commits,
            ["42"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["pr_number"] == 42
        assert len(output["commits"]) == 2
        assert output["commits"][0]["sha"] == "abc123"
        assert output["commits"][1]["message"] == "Second commit"


def test_get_pr_commits_single_commit(tmp_path: Path) -> None:
    """Test fetching a single commit."""
    mock_commits = [
        {"sha": "single123", "message": "Only commit\n\nWith body"},
    ]

    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(mock_commits)
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(
            get_pr_commits,
            ["123"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["pr_number"] == 123
        assert len(output["commits"]) == 1
        assert output["commits"][0]["sha"] == "single123"


def test_get_pr_commits_empty_commits(tmp_path: Path) -> None:
    """Test handling PR with no commits (edge case)."""
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(
            get_pr_commits,
            ["999"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["commits"] == []


def test_get_pr_commits_api_error(tmp_path: Path) -> None:
    """Test error when gh api fails."""
    import subprocess

    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["gh", "api"],
            output="",
            stderr="gh: Could not resolve to a PullRequest with the number of 9999.",
        )

        runner = CliRunner()
        result = runner.invoke(
            get_pr_commits,
            ["9999"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert "9999" in output["error"]
