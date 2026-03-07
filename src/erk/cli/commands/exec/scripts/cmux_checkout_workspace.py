"""Create a cmux workspace with PR checkout or teleport.

This script creates a cmux workspace that automatically opens a PR
and renames the workspace to the PR's head branch.

Usage:
    erk exec cmux-open-pr --pr 8152
    erk exec cmux-open-pr --pr 8152 --mode teleport
    erk exec cmux-open-pr --pr 8152 --branch "my-branch"

Modes:
    checkout (default): lightweight -- runs `erk pr checkout {pr} --script`
    teleport: heavyweight -- runs `erk pr teleport {pr} --new-slot --script --sync`

Output:
    JSON with {success, pr_number, branch, workspace_name} on success
    JSON with {success, error} on failure

Exit Codes:
    0: Success - workspace created
    1: Error - cmux/checkout/sync failed or branch lookup failed
"""

import json
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import require_context, require_github, require_repo_root
from erk_shared.gateway.github.types import PRNotFound


@dataclass(frozen=True)
class CmuxOpenPrSuccess:
    """Success response for cmux-open-pr command."""

    success: bool
    pr_number: int
    branch: str
    workspace_name: str | None


@dataclass(frozen=True)
class CmuxOpenPrError:
    """Error response for cmux-open-pr command."""

    success: bool
    error: str


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


@click.command(name="cmux-open-pr")
@click.option(
    "--pr",
    required=True,
    type=int,
    help="PR number to open",
)
@click.option(
    "--branch",
    default=None,
    help="PR head branch name (auto-detected via gh if omitted)",
)
@click.option(
    "--mode",
    type=click.Choice(["checkout", "teleport"]),
    default="checkout",
    help="checkout (lightweight) or teleport (heavyweight with sync)",
)
@click.pass_context
def cmux_open_pr(ctx: click.Context, pr: int, branch: str | None, mode: str) -> None:
    """Create a cmux workspace to open a PR.

    Creates a new cmux workspace that:
    1. Opens the PR (checkout or teleport based on --mode)
    2. Renames the workspace to the PR's head branch

    If --branch is not provided, it will be auto-detected from GitHub.
    """
    # Auto-detect branch if not provided
    if branch is None:
        github = require_github(ctx)
        repo_root = require_repo_root(ctx)
        result = github.get_pr(repo_root, pr)
        if isinstance(result, PRNotFound):
            click.echo(
                json.dumps(
                    asdict(
                        CmuxOpenPrError(
                            success=False,
                            error=f"Failed to detect head branch for PR #{pr}. "
                            "Provide --branch explicitly.",
                        )
                    )
                )
            )
            raise SystemExit(1)
        branch = result.head_ref_name

    # Build the checkout command that will run inside the new workspace
    if mode == "teleport":
        checkout_cmd = f'source "$(erk pr teleport {pr} --new-slot --script --sync)"'
    else:
        checkout_cmd = f'source "$(erk pr checkout {pr} --script)"'

    cmux = require_context(ctx).cmux

    try:
        ws_ref = cmux.create_workspace(command=checkout_cmd)
        cmux.rename_workspace(workspace_ref=ws_ref, new_name=branch)
        workspace_name = _extract_workspace_name(ws_ref)

        click.echo(
            json.dumps(
                asdict(
                    CmuxOpenPrSuccess(
                        success=True,
                        pr_number=pr,
                        branch=branch,
                        workspace_name=workspace_name,
                    )
                )
            )
        )
    except RuntimeError as e:
        click.echo(
            json.dumps(
                asdict(
                    CmuxOpenPrError(
                        success=False,
                        error=f"Failed to create cmux workspace: {e}",
                    )
                )
            )
        )
        raise SystemExit(1) from None
