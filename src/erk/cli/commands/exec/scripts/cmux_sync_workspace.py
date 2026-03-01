"""Create a cmux workspace with PR checkout and sync.

This script creates a cmux workspace that automatically checks out a PR,
syncs it with the trunk, and renames the workspace to the PR's head branch.

Usage:
    erk exec cmux-sync-workspace --pr 8152
    erk exec cmux-sync-workspace --pr 8152 --branch "my-branch"

Output:
    JSON with {success, pr_number, branch, workspace_name} on success
    JSON with {success, error} on failure

Exit Codes:
    0: Success - workspace created
    1: Error - cmux/checkout/sync failed or branch lookup failed
"""

import json
import subprocess
from dataclasses import asdict, dataclass

import click


@dataclass(frozen=True)
class CmuxSyncSuccess:
    """Success response for cmux-sync-workspace command."""

    success: bool
    pr_number: int
    branch: str
    workspace_name: str | None


@dataclass(frozen=True)
class CmuxSyncError:
    """Error response for cmux-sync-workspace command."""

    success: bool
    error: str


def _get_pr_head_branch(pr_number: int) -> str | None:
    """Fetch PR head branch name using gh."""
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--json",
                "headRefName",
                "--jq",
                ".headRefName",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        return branch if branch else None
    except subprocess.CalledProcessError:
        return None


def _extract_workspace_name(output: str) -> str | None:
    """Extract workspace name from cmux new-workspace output.

    The output format is typically: "Created workspace: <name>"
    or just the workspace name.
    """
    lines = output.strip().split("\n")
    if lines:
        last_line = lines[-1].strip()
        # Try to extract name from "Created workspace: <name>" format
        if ":" in last_line:
            parts = last_line.split(":", 1)
            return parts[1].strip() if len(parts) > 1 else last_line
        return last_line if last_line else None
    return None


@click.command(name="cmux-sync-workspace")
@click.option(
    "--pr",
    required=True,
    type=int,
    help="PR number to checkout and sync",
)
@click.option(
    "--branch",
    default=None,
    help="PR head branch name (auto-detected via gh if omitted)",
)
def cmux_sync_workspace(pr: int, branch: str | None) -> None:
    """Create a cmux workspace with PR checkout and sync.

    Creates a new cmux workspace that:
    1. Checks out the PR and syncs it with trunk
    2. Submits changes via Graphite
    3. Renames the workspace to the PR's head branch

    If --branch is not provided, it will be auto-detected from GitHub.
    """
    # Auto-detect branch if not provided
    if branch is None:
        branch = _get_pr_head_branch(pr)
        if branch is None:
            click.echo(
                json.dumps(
                    asdict(
                        CmuxSyncError(
                            success=False,
                            error=f"Failed to detect head branch for PR #{pr}. "
                            "Provide --branch explicitly.",
                        )
                    )
                )
            )
            raise SystemExit(1)

    # Build the checkout command that will run inside the new workspace
    checkout_cmd = (
        f'source "$(erk pr checkout {pr} --script --sync)" '
        "&& gt submit --no-interactive"
    )

    # Build the shell pipeline:
    # 1. Create workspace with checkout command
    # 2. Extract workspace name
    # 3. Rename workspace to branch name
    shell_cmd = (
        f"WS=$(cmux new-workspace --command '{checkout_cmd}' | awk '{{print $2}}') && "
        f'cmux rename-workspace --workspace "$WS" "{branch}" && '
        "echo $WS"
    )

    try:
        result = subprocess.run(
            ["bash", "-c", shell_cmd],
            capture_output=True,
            text=True,
            check=True,
        )

        workspace_name = _extract_workspace_name(result.stdout)

        click.echo(
            json.dumps(
                asdict(
                    CmuxSyncSuccess(
                        success=True,
                        pr_number=pr,
                        branch=branch,
                        workspace_name=workspace_name,
                    )
                )
            )
        )
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.strip() if e.stderr else e.stdout.strip()
        click.echo(
            json.dumps(
                asdict(
                    CmuxSyncError(
                        success=False,
                        error=f"Failed to create cmux workspace: {error_output}",
                    )
                )
            )
        )
        raise SystemExit(1)
