"""Detect plan number from the current git branch name.

Replaces inline branch-detection bash logic in plan-implement.md Step 1b-branch.
Uses extract_leading_issue_number() from erk_shared.naming for branch name parsing,
with a fallback to github.get_pr_for_branch() for planned-PR branches.

Usage:
    erk exec detect-plan-from-branch

Output:
    JSON with detection result:
    {"found": true, "plan_number": 2521, "detection_method": "branch_name"}
    {"found": true, "plan_number": 2521, "detection_method": "pr_lookup"}
    {"found": false}

Exit Codes:
    0: Always (caller decides how to handle not-found)

Examples:
    $ erk exec detect-plan-from-branch
    {"found": true, "plan_number": 2521, "detection_method": "branch_name"}
"""

import json
from collections.abc import Callable

import click

from erk_shared.context.helpers import require_cwd, require_git, require_github, require_repo_root
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.naming import extract_leading_issue_number


def _detect_plan_from_branch_impl(
    *,
    current_branch: str | None,
    pr_lookup: Callable[[], int | None],
) -> dict[str, object]:
    """Core detection logic, separated for testability.

    Args:
        current_branch: Current branch name, or None if detached HEAD.
        pr_lookup: Callable that returns PR number or None for the current branch.
            Signature: () -> int | None

    Returns:
        Detection result dict with 'found', and optionally 'plan_number' and 'detection_method'.
    """
    if current_branch is None:
        return {"found": False}

    # Try branch name pattern: P{number}-slug or {number}-slug
    issue_number = extract_leading_issue_number(current_branch)
    if issue_number is not None:
        return {"found": True, "plan_number": issue_number, "detection_method": "branch_name"}

    # Fall back to PR lookup
    pr_number = pr_lookup()
    if pr_number is not None:
        return {"found": True, "plan_number": pr_number, "detection_method": "pr_lookup"}

    return {"found": False}


@click.command(name="detect-plan-from-branch")
@click.pass_context
def detect_plan_from_branch(ctx: click.Context) -> None:
    """Detect plan number from the current git branch name.

    Checks branch name for P{number}- or {number}- prefix patterns.
    Falls back to looking up an associated PR for the current branch.

    Always exits with code 0 - caller decides how to handle not-found.
    """
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    current_branch = git.branch.get_current_branch(cwd)

    def pr_lookup() -> int | None:
        if current_branch is None:
            return None
        pr_result = github.get_pr_for_branch(repo_root, current_branch)
        if isinstance(pr_result, PRNotFound):
            return None
        return pr_result.number

    result = _detect_plan_from_branch_impl(
        current_branch=current_branch,
        pr_lookup=pr_lookup,
    )
    click.echo(json.dumps(result))
