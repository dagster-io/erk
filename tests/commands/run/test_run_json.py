"""Tests for erk json run machine commands."""

import json
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import NoRepoSentinel
from tests.test_utils.test_context import context_for_test


def test_json_run_list_supports_target_repo_without_local_repo() -> None:
    """workflow_run_list uses explicit owner/repo in remote mode."""
    runner = CliRunner()
    ctx = context_for_test(repo=NoRepoSentinel())
    ctx.http_client.set_response(
        "repos/owner/repo/actions/runs?per_page=5",
        response={
            "workflow_runs": [
                {
                    "id": 123,
                    "node_id": "RUN_node_123",
                    "status": "in_progress",
                    "conclusion": None,
                    "head_branch": "feature/run-test",
                    "head_sha": "abc123",
                    "display_title": "one-shot:#123:abc123",
                    "created_at": "2026-03-25T12:00:00Z",
                    "path": ".github/workflows/one-shot.yml",
                }
            ]
        },
    )

    with patch(
        "erk_shared.agentclick.machine_command.read_machine_command_input",
        return_value={"target_repo": "owner/repo", "limit": 5},
    ):
        result = runner.invoke(
            cli,
            ["json", "run", "list"],
            obj=ctx,
            catch_exceptions=False,
        )

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["success"] is True
    assert data["count"] == 1
    assert data["runs"][0]["run_id"] == "123"
    assert data["runs"][0]["workflow"] == "one-shot"
    assert data["runs"][0]["url"] == "https://github.com/owner/repo/actions/runs/123"


def test_json_run_status_supports_target_repo_without_local_repo() -> None:
    """workflow_run_status fetches a specific run by explicit owner/repo."""
    runner = CliRunner()
    ctx = context_for_test(repo=NoRepoSentinel())
    ctx.http_client.set_response(
        "repos/owner/repo/actions/runs/999",
        response={
            "id": 999,
            "node_id": "RUN_node_999",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "plnd/test-branch",
            "head_sha": "deadbeef",
            "display_title": "plnd/test-branch (#77):abc999",
            "created_at": "2026-03-25T12:05:00Z",
            "path": ".github/workflows/plan-implement.yml",
        },
    )

    with patch(
        "erk_shared.agentclick.machine_command.read_machine_command_input",
        return_value={"target_repo": "owner/repo", "run_id": "999"},
    ):
        result = runner.invoke(
            cli,
            ["json", "run", "status"],
            obj=ctx,
            catch_exceptions=False,
        )

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["success"] is True
    assert data["run"]["run_id"] == "999"
    assert data["run"]["status"] == "completed"
    assert data["run"]["conclusion"] == "success"
    assert data["run"]["workflow"] == "plan-implement"


def test_json_run_logs_supports_target_repo_without_local_repo() -> None:
    """workflow_run_logs shells out with -R owner/repo instead of local cwd."""
    runner = CliRunner()
    ctx = context_for_test(repo=NoRepoSentinel())

    with patch(
        "erk_shared.agentclick.machine_command.read_machine_command_input",
        return_value={"target_repo": "owner/repo", "run_id": "456"},
    ):
        with patch(
            "erk.cli.commands.run.operation.run_subprocess_with_context",
            return_value=SimpleNamespace(stdout="job log output"),
        ) as mock_run:
            result = runner.invoke(
                cli,
                ["json", "run", "logs"],
                obj=ctx,
                catch_exceptions=False,
            )

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["success"] is True
    assert data["run_id"] == "456"
    assert data["logs"] == "job log output"
    mock_run.assert_called_once_with(
        cmd=["gh", "run", "view", "456", "--log", "-R", "owner/repo"],
        operation_context="fetch logs for run 456 in owner/repo",
        cwd=None,
    )
