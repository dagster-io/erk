"""Unit tests for trigger_async_learn exec script.

Tests triggering the learn.yml workflow for async learn.
Uses FakeGitHub for dependency injection.

NOTE: Full orchestration testing (session preprocessing, gist upload, etc.)
requires mocking subprocess.run calls since the script orchestrates multiple
erk exec commands via subprocess.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.trigger_async_learn import (
    trigger_async_learn as trigger_async_learn_command,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import RepoInfo


def _parse_json_output(output: str) -> dict[str, object]:
    """Parse JSON from CliRunner output, skipping stderr progress lines.

    Click 8.x mixes stderr into result.output. The trigger-async-learn script
    writes progress messages to stderr and JSON to stdout. This helper extracts
    the JSON line from the mixed output.
    """
    for line in reversed(output.strip().splitlines()):
        if line.startswith("{"):
            return json.loads(line)  # type: ignore[no-any-return]
    raise ValueError(f"No JSON found in output: {output!r}")


def test_trigger_async_learn_success(tmp_path: Path) -> None:
    """Test successful workflow trigger with full orchestration pipeline."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    # Create the .erk/scratch directory that the script expects
    learn_dir = tmp_path / ".erk" / "scratch" / "learn-123"
    learn_dir.mkdir(parents=True)

    # Mock subprocess calls to simulate the orchestration pipeline
    mock_subprocess_results = [
        # get-learn-sessions
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "session_sources": [
                        {
                            "source": "local",
                            "session_path": "/fake/path.jsonl",
                            "session_type": "planning",
                        }
                    ],
                }
            ),
            stderr="",
        ),
        # preprocess-session (planning)
        MagicMock(returncode=0, stdout=json.dumps({"success": True}), stderr=""),
        # get-pr-for-plan
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": True, "pr_number": 456}),
            stderr="",
        ),
        # get-pr-review-comments
        MagicMock(returncode=0, stdout=json.dumps({"success": True, "threads": []}), stderr=""),
        # get-pr-discussion-comments
        MagicMock(returncode=0, stdout=json.dumps({"success": True, "comments": []}), stderr=""),
        # upload-learn-materials
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "gist_url": "https://gist.github.com/user/abc123",
                    "file_count": 1,
                }
            ),
            stderr="",
        ),
    ]

    with patch("subprocess.run", side_effect=mock_subprocess_results):
        result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 0
    output = _parse_json_output(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 123
    assert output["workflow_triggered"] is True
    assert output["run_id"] == "1234567890"
    assert (
        output["workflow_url"] == "https://github.com/test-owner/test-repo/actions/runs/1234567890"
    )
    assert output["gist_url"] == "https://gist.github.com/user/abc123"


def test_trigger_async_learn_verifies_workflow_call(tmp_path: Path) -> None:
    """Test that workflow trigger is called with correct parameters including gist_url."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    learn_dir = tmp_path / ".erk" / "scratch" / "learn-456"
    learn_dir.mkdir(parents=True)

    # Mock the subprocess pipeline
    mock_subprocess_results = [
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": True, "session_sources": []}),
            stderr="",
        ),
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": False}),
            stderr="",
        ),  # get-pr-for-plan (no PR)
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "gist_url": "https://gist.github.com/user/xyz789",
                    "file_count": 0,
                }
            ),
            stderr="",
        ),
    ]

    with patch("subprocess.run", side_effect=mock_subprocess_results):
        runner.invoke(trigger_async_learn_command, ["456"], obj=ctx)

    assert len(github.triggered_workflows) == 1
    workflow, inputs = github.triggered_workflows[0]
    assert workflow == "learn.yml"
    assert inputs["issue_number"] == "456"
    assert inputs["gist_url"] == "https://gist.github.com/user/xyz789"


def test_trigger_async_learn_no_repo_info(tmp_path: Path) -> None:
    """Test error when not in a GitHub repository."""
    runner = CliRunner()
    github = FakeGitHub()
    # Not passing repo_info leaves it as None, simulating not being in a GitHub repo
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github)

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 1
    output = _parse_json_output(result.output)
    assert output["success"] is False
    assert "GitHub repository" in output["error"]


def test_trigger_async_learn_no_context(tmp_path: Path) -> None:
    """Test error when context is not initialized."""
    runner = CliRunner()

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=None)

    assert result.exit_code == 1
    output = _parse_json_output(result.output)
    assert output["success"] is False
    assert "Context not initialized" in output["error"]


def test_trigger_async_learn_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure on success including gist_url."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="dagster-io", name="erk")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    learn_dir = tmp_path / ".erk" / "scratch" / "learn-789"
    learn_dir.mkdir(parents=True)

    # Mock the subprocess pipeline
    mock_subprocess_results = [
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": True, "session_sources": []}),
            stderr="",
        ),
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": False}),
            stderr="",
        ),  # get-pr-for-plan (no PR)
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "gist_url": "https://gist.github.com/user/test123",
                    "file_count": 0,
                }
            ),
            stderr="",
        ),
    ]

    with patch("subprocess.run", side_effect=mock_subprocess_results):
        result = runner.invoke(trigger_async_learn_command, ["789"], obj=ctx)

    assert result.exit_code == 0
    output = _parse_json_output(result.output)

    # Verify expected keys
    assert "success" in output
    assert "issue_number" in output
    assert "workflow_triggered" in output
    assert "run_id" in output
    assert "workflow_url" in output
    assert "gist_url" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["workflow_triggered"], bool)
    assert isinstance(output["run_id"], str)
    assert isinstance(output["workflow_url"], str)
    assert isinstance(output["gist_url"], str)
