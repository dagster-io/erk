"""Unit tests for get-pr-commits command."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_pr_commits import get_pr_commits
from erk_shared.context.context import ErkContext


def test_get_pr_commits_success(monkeypatch: MagicMock, tmp_path: Path) -> None:
    """Test successful PR commits fetch."""
    commits_json = json.dumps(
        [
            {"sha": "abc123", "message": "First commit", "author": "Test User"},
            {"sha": "def456", "message": "Second commit", "author": "Test User"},
        ]
    )

    def mock_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["gh", "api"],
            returncode=0,
            stdout=commits_json,
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

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
    assert output["commits"][0]["message"] == "First commit"
    assert output["commits"][1]["sha"] == "def456"


def test_get_pr_commits_empty(monkeypatch: MagicMock, tmp_path: Path) -> None:
    """Test PR with no commits (edge case)."""

    def mock_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["gh", "api"],
            returncode=0,
            stdout="[]",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    runner = CliRunner()
    result = runner.invoke(
        get_pr_commits,
        ["99"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 99
    assert output["commits"] == []


def test_get_pr_commits_not_found(monkeypatch: MagicMock, tmp_path: Path) -> None:
    """Test error when PR does not exist."""

    def mock_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["gh", "api"],
            returncode=1,
            stdout="",
            stderr="HTTP 404: Not Found",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    runner = CliRunner()
    result = runner.invoke(
        get_pr_commits,
        ["999"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "999" in output["error"]
    assert "404" in output["error"] or "Not Found" in output["error"]


def test_get_pr_commits_api_error(monkeypatch: MagicMock, tmp_path: Path) -> None:
    """Test error when API call fails."""

    def mock_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["gh", "api"],
            returncode=1,
            stdout="",
            stderr="gh: authentication failed",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    runner = CliRunner()
    result = runner.invoke(
        get_pr_commits,
        ["42"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "authentication failed" in output["error"]


@pytest.mark.parametrize(
    "commit_data",
    [
        pytest.param(
            [{"sha": "a" * 40, "message": "feat: add new feature", "author": "Alice"}],
            id="single_commit",
        ),
        pytest.param(
            [
                {
                    "sha": "b" * 40,
                    "message": "fix: bug fix\n\nDetailed description",
                    "author": "Bob",
                },
                {"sha": "c" * 40, "message": "chore: update deps", "author": "Charlie"},
                {"sha": "d" * 40, "message": "docs: improve readme", "author": "Diana"},
            ],
            id="multiple_commits_with_multiline",
        ),
    ],
)
def test_get_pr_commits_various_formats(
    monkeypatch: MagicMock,
    tmp_path: Path,
    commit_data: list[dict[str, str]],
) -> None:
    """Test parsing various commit message formats."""

    def mock_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["gh", "api"],
            returncode=0,
            stdout=json.dumps(commit_data),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    runner = CliRunner()
    result = runner.invoke(
        get_pr_commits,
        ["100"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["commits"]) == len(commit_data)
    for i, commit in enumerate(commit_data):
        assert output["commits"][i]["sha"] == commit["sha"]
        assert output["commits"][i]["message"] == commit["message"]
        assert output["commits"][i]["author"] == commit["author"]
