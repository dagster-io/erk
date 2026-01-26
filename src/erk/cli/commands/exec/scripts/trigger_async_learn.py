"""Trigger async learn workflow for a plan issue.

This exec command triggers the learn.yml GitHub Actions workflow
to asynchronously run /erk:learn on a plan issue.

Usage:
    erk exec trigger-async-learn <issue_number>

Output:
    JSON with success status and workflow information:
    {"success": true, "issue_number": 123, "workflow_triggered": true,
     "run_id": "12345678", "workflow_url": "https://..."}

    On error:
    {"success": false, "error": "message"}

Examples:
    $ erk exec trigger-async-learn 5753
    {"success": true, "issue_number": 5753, "workflow_triggered": true,
     "run_id": "12345678", "workflow_url": "https://github.com/owner/repo/actions/runs/12345678"}
"""

import json
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import require_github, require_repo_root
from erk_shared.github.parsing import construct_workflow_run_url

LEARN_WORKFLOW = "learn.yml"


@dataclass(frozen=True)
class TriggerSuccess:
    """Success response for trigger-async-learn command."""

    success: bool
    issue_number: int
    workflow_triggered: bool
    run_id: str
    workflow_url: str


@dataclass(frozen=True)
class TriggerError:
    """Error response for trigger-async-learn command."""

    success: bool
    error: str


def _output_success(issue_number: int, run_id: str, workflow_url: str) -> None:
    """Output success JSON and exit."""
    result = TriggerSuccess(
        success=True,
        issue_number=issue_number,
        workflow_triggered=True,
        run_id=run_id,
        workflow_url=workflow_url,
    )
    click.echo(json.dumps(asdict(result)))
    raise SystemExit(0)


def _output_error(message: str) -> None:
    """Output error JSON and exit."""
    result = TriggerError(success=False, error=message)
    click.echo(json.dumps(asdict(result)))
    raise SystemExit(1)


@click.command(name="trigger-async-learn")
@click.argument("issue_number", type=int)
@click.pass_context
def trigger_async_learn(ctx: click.Context, issue_number: int) -> None:
    """Trigger async learn workflow for a plan issue.

    ISSUE_NUMBER is the GitHub issue number to learn from.

    Triggers the learn.yml workflow which runs /erk:learn
    on the specified plan issue asynchronously.
    """
    # Get required dependencies from context
    if ctx.obj is None:
        _output_error("Context not initialized")
        return

    repo_info = ctx.obj.repo_info
    if repo_info is None:
        _output_error("Not in a GitHub repository")
        return

    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    # Trigger the learn workflow
    workflow_inputs = {
        "issue_number": str(issue_number),
    }

    try:
        run_id = github.trigger_workflow(
            repo_root=repo_root,
            workflow=LEARN_WORKFLOW,
            inputs=workflow_inputs,
            ref="master",
        )
    except RuntimeError as e:
        _output_error(f"Failed to trigger workflow: {e}")
        return

    # Construct the workflow URL
    workflow_url = construct_workflow_run_url(
        owner=repo_info.owner,
        repo=repo_info.name,
        run_id=run_id,
    )

    _output_success(issue_number, run_id, workflow_url)
