"""Unit tests for trigger_async_learn exec script.

Tests triggering the learn.yml workflow for async learn.
Uses FakeGitHub for dependency injection.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.trigger_async_learn import (
    trigger_async_learn as trigger_async_learn_command,
)
from erk_shared.context.context import ErkContext
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import RepoInfo


def test_trigger_async_learn_success(tmp_path: Path) -> None:
    """Test successful workflow trigger returns correct JSON."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 123
    assert output["workflow_triggered"] is True
    assert output["run_id"] == "1234567890"
    assert (
        output["workflow_url"] == "https://github.com/test-owner/test-repo/actions/runs/1234567890"
    )


def test_trigger_async_learn_verifies_workflow_call(tmp_path: Path) -> None:
    """Test that workflow trigger is called with correct parameters."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    runner.invoke(trigger_async_learn_command, ["456"], obj=ctx)

    assert len(github.triggered_workflows) == 1
    workflow, inputs = github.triggered_workflows[0]
    assert workflow == "learn.yml"
    assert inputs["issue_number"] == "456"


def test_trigger_async_learn_no_repo_info(tmp_path: Path) -> None:
    """Test error when not in a GitHub repository."""
    runner = CliRunner()
    github = FakeGitHub()
    # Not passing repo_info leaves it as None, simulating not being in a GitHub repo
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github)

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "GitHub repository" in output["error"]


def test_trigger_async_learn_no_context(tmp_path: Path) -> None:
    """Test error when context is not initialized."""
    runner = CliRunner()

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=None)

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Context not initialized" in output["error"]


def test_trigger_async_learn_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure on success."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="dagster-io", name="erk")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    result = runner.invoke(trigger_async_learn_command, ["789"], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "issue_number" in output
    assert "workflow_triggered" in output
    assert "run_id" in output
    assert "workflow_url" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["workflow_triggered"], bool)
    assert isinstance(output["run_id"], str)
    assert isinstance(output["workflow_url"], str)
