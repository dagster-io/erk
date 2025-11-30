#!/usr/bin/env python3
"""Get open PR number for a branch.

This command retrieves the open PR number for a given branch via
`gh pr list --state open --head <branch_name> --json number`.

This replaces bash-based parsing in CI workflows with tested Python code.

Usage:
    dot-agent run erk get-pr-for-branch <branch_name>

Output:
    JSON object with success status, branch name, and PR info

Exit Codes:
    0: Success (PR found or not found - check pr_exists field)
    1: Error (gh command failed)

Examples:
    $ dot-agent run erk get-pr-for-branch 123-feature
    {
      "success": true,
      "branch_name": "123-feature",
      "pr_number": 456,
      "pr_exists": true
    }

    $ dot-agent run erk get-pr-for-branch some-branch
    {
      "success": true,
      "branch_name": "some-branch",
      "pr_number": null,
      "pr_exists": false
    }
"""

import json
import subprocess
from dataclasses import asdict, dataclass
from typing import Literal

import click


@dataclass(frozen=True)
class PrForBranchResult:
    """Success result with PR information."""

    success: Literal[True]
    branch_name: str
    pr_number: int | None
    pr_exists: bool


@dataclass(frozen=True)
class PrForBranchError:
    """Error result when PR lookup fails."""

    success: Literal[False]
    error: Literal["gh_command_failed"]
    message: str


def _run_gh_pr_list(branch_name: str) -> subprocess.CompletedProcess[str]:
    """Run gh pr list and return result.

    Separated from business logic for easier testing.
    """
    return subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--head", branch_name, "--json", "number"],
        capture_output=True,
        text=True,
        check=False,
    )


def _get_pr_for_branch_impl(
    branch_name: str,
    *,
    run_command: (
        subprocess.CompletedProcess[str] | None  # Accept result for testing
    ) = None,
) -> PrForBranchResult | PrForBranchError:
    """Get open PR number for a branch.

    Args:
        branch_name: Git branch name
        run_command: Optional CompletedProcess for testing

    Returns:
        PrForBranchResult on success, PrForBranchError on failure
    """
    if run_command is None:
        result = _run_gh_pr_list(branch_name)
    else:
        result = run_command

    # Check for gh command failure
    if result.returncode != 0:
        return PrForBranchError(
            success=False,
            error="gh_command_failed",
            message=f"gh pr list failed: {result.stderr.strip()}",
        )

    # Parse JSON output
    stdout = result.stdout.strip()
    if not stdout:
        # Empty output means no PRs
        return PrForBranchResult(
            success=True,
            branch_name=branch_name,
            pr_number=None,
            pr_exists=False,
        )

    # Parse JSON - gh pr list --json returns array of PRs
    pr_list = json.loads(stdout)

    if not pr_list:
        return PrForBranchResult(
            success=True,
            branch_name=branch_name,
            pr_number=None,
            pr_exists=False,
        )

    # Return the first PR number (should only be one open PR per head branch)
    pr_number = pr_list[0].get("number")

    return PrForBranchResult(
        success=True,
        branch_name=branch_name,
        pr_number=pr_number,
        pr_exists=True,
    )


@click.command(name="get-pr-for-branch")
@click.argument("branch_name")
def get_pr_for_branch(branch_name: str) -> None:
    """Get open PR number for a branch.

    Retrieves the open PR number for a branch via `gh pr list --head`.
    Returns structured JSON for workflow integration.
    """
    result = _get_pr_for_branch_impl(branch_name)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if gh command failed
    if isinstance(result, PrForBranchError):
        raise SystemExit(1)
