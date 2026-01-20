"""Dispatch the learn-extract-dispatch workflow on GitHub.

This exec script triggers the remote learn workflow after landing a PR:
1. Calls gh workflow run learn-extract-dispatch.yml with parameters
2. Returns the workflow run URL

Usage:
    erk exec dispatch-learn-workflow --plan-issue 123 --pr-number 456 --gist-url https://gist.github.com/...

Output:
    JSON object with dispatch results:
    {
        "success": true,
        "workflow_name": "learn-extract-dispatch.yml",
        "inputs": {
            "plan_issue_number": "123",
            "pr_number": "456",
            "gist_url": "https://gist.github.com/...",
            "auto_implement": "false"
        }
    }

Exit Codes:
    0: Success
    1: Error (workflow dispatch failure)
"""

import json
import subprocess
from dataclasses import asdict, dataclass

import click


@dataclass(frozen=True)
class DispatchSuccess:
    """Success result for dispatch-learn-workflow command."""

    success: bool
    workflow_name: str
    inputs: dict[str, str]


@dataclass(frozen=True)
class DispatchError:
    """Error result when dispatch fails."""

    success: bool
    error: str


@click.command(name="dispatch-learn-workflow")
@click.option(
    "--plan-issue",
    "plan_issue",
    type=int,
    required=True,
    help="Plan issue number",
)
@click.option(
    "--pr-number",
    "pr_number",
    type=int,
    required=True,
    help="Merged PR number",
)
@click.option(
    "--gist-url",
    "gist_url",
    type=str,
    required=False,
    default=None,
    help="URL of preprocessed sessions gist (optional)",
)
@click.option(
    "--auto-implement/--no-auto-implement",
    "auto_implement",
    default=False,
    help="Auto-implement resulting docs plan",
)
def dispatch_learn_workflow(
    *,
    plan_issue: int,
    pr_number: int,
    gist_url: str | None,
    auto_implement: bool,
) -> None:
    """Dispatch the learn-extract-dispatch workflow.

    Triggers the GitHub Actions workflow that runs /erk:learn remotely
    with session data from a gist (if provided).

    Outputs JSON with dispatch confirmation.
    """
    workflow_name = "learn-extract-dispatch.yml"

    # Build workflow dispatch command
    cmd = [
        "gh",
        "workflow",
        "run",
        workflow_name,
        "-f",
        f"plan_issue_number={plan_issue}",
        "-f",
        f"pr_number={pr_number}",
        "-f",
        f"auto_implement={'true' if auto_implement else 'false'}",
    ]

    if gist_url is not None:
        cmd.extend(["-f", f"gist_url={gist_url}"])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        error = DispatchError(
            success=False,
            error=f"Failed to dispatch workflow: {error_msg}",
        )
        click.echo(json.dumps(asdict(error), indent=2))
        raise SystemExit(1)

    # Build inputs dict for response
    inputs: dict[str, str] = {
        "plan_issue_number": str(plan_issue),
        "pr_number": str(pr_number),
        "auto_implement": str(auto_implement).lower(),
    }
    if gist_url is not None:
        inputs["gist_url"] = gist_url

    success = DispatchSuccess(
        success=True,
        workflow_name=workflow_name,
        inputs=inputs,
    )
    click.echo(json.dumps(asdict(success), indent=2))
