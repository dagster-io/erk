#!/usr/bin/env python3
"""Get development branch linked to a GitHub issue.

This command retrieves the branch linked to a GitHub issue via `gh issue develop --list`.

This replaces bash-based parsing in CI workflows with tested Python code.

Usage:
    dot-agent run erk get-linked-branch <issue_number>

Output:
    JSON object with success status and branch name (or error details)

Exit Codes:
    0: Success (branch found or not found - check success and pr_exists fields)
    1: Error (gh command failed)

Examples:
    $ dot-agent run erk get-linked-branch 123
    {
      "success": true,
      "issue_number": 123,
      "branch_name": "123-feature-name"
    }

    $ dot-agent run erk get-linked-branch 456
    {
      "success": false,
      "error": "no_linked_branch",
      "message": "No linked branch found for issue #456"
    }
"""

import json
import subprocess
from dataclasses import asdict, dataclass
from typing import Literal

import click


@dataclass(frozen=True)
class LinkedBranchResult:
    """Success result with linked branch name."""

    success: Literal[True]
    issue_number: int
    branch_name: str


@dataclass(frozen=True)
class LinkedBranchError:
    """Error result when linked branch cannot be retrieved."""

    success: Literal[False]
    error: Literal["no_linked_branch", "gh_command_failed"]
    message: str


def _run_gh_issue_develop_list(issue_number: int) -> subprocess.CompletedProcess[str]:
    """Run gh issue develop --list and return result.

    Separated from business logic for easier testing.
    """
    return subprocess.run(
        ["gh", "issue", "develop", "--list", str(issue_number)],
        capture_output=True,
        text=True,
        check=False,
    )


def _get_linked_branch_impl(
    issue_number: int,
    *,
    run_command: subprocess.CompletedProcess[str] | None = None,
) -> LinkedBranchResult | LinkedBranchError:
    """Get development branch linked to a GitHub issue.

    Args:
        issue_number: GitHub issue number
        run_command: Optional CompletedProcess for testing

    Returns:
        LinkedBranchResult on success, LinkedBranchError on failure
    """
    if run_command is None:
        result = _run_gh_issue_develop_list(issue_number)
    else:
        result = run_command

    # Check for gh command failure
    if result.returncode != 0:
        return LinkedBranchError(
            success=False,
            error="gh_command_failed",
            message=f"gh issue develop --list failed: {result.stderr.strip()}",
        )

    # Parse output - gh issue develop --list outputs: "branch-name\tURL"
    stdout = result.stdout.strip()
    if not stdout:
        return LinkedBranchError(
            success=False,
            error="no_linked_branch",
            message=f"No linked branch found for issue #{issue_number}",
        )

    # Extract branch name from first line (tab-separated: branch_name\tURL)
    lines = stdout.split("\n")
    first_line = lines[0]
    branch_name = first_line.split("\t")[0]

    return LinkedBranchResult(
        success=True,
        issue_number=issue_number,
        branch_name=branch_name,
    )


@click.command(name="get-linked-branch")
@click.argument("issue_number", type=int)
def get_linked_branch(issue_number: int) -> None:
    """Get development branch linked to a GitHub issue.

    Retrieves the branch linked to an issue via `gh issue develop --list`.
    Returns structured JSON for workflow integration.
    """
    result = _get_linked_branch_impl(issue_number)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if gh command failed
    if isinstance(result, LinkedBranchError) and result.error == "gh_command_failed":
        raise SystemExit(1)
