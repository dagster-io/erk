"""Resolve an objective reference to an objective number.

Consolidates argument parsing + branch inference for objective-plan command.

Resolution cascade:
1. Non-empty ref → parse as number/URL
2. Empty ref + branch matches objective pattern → extract from branch name
3. Empty ref + plan metadata lookup → get objective_id from branch's plan
4. All fail → {"resolved": false}

Usage:
    erk exec resolve-objective-ref
    erk exec resolve-objective-ref 3679
    erk exec resolve-objective-ref https://github.com/owner/repo/issues/3679

Output:
    JSON with resolution result:
    {"resolved": true, "objective_number": 3679, "source": "argument"}
    {"resolved": true, "objective_number": 456, "source": "branch_name"}
    {"resolved": true, "objective_number": 123, "source": "plan_metadata"}
    {"resolved": false}

Exit Codes:
    0: Always (caller decides how to handle not-resolved)
"""

import json
from collections.abc import Callable

import click

from erk_shared.context.helpers import (
    require_cwd,
    require_git,
    require_plan_backend,
    require_repo_root,
)
from erk_shared.gateway.github.parsing import parse_issue_number_from_url
from erk_shared.naming import extract_objective_number
from erk_shared.plan_store.types import PlanNotFound


def _resolve_objective_ref_impl(
    *,
    ref: str,
    current_branch: str | None,
    get_objective_for_branch: Callable[[str], int | None],
) -> dict[str, object]:
    """Core resolution logic, separated for testability.

    Args:
        ref: User-provided reference (number, URL, or empty string).
        current_branch: Current branch name, or None if detached HEAD.
        get_objective_for_branch: Callable that returns objective number from
            branch plan metadata, or None.

    Returns:
        Resolution result dict with 'resolved', and optionally
        'objective_number' and 'source'.
    """
    # Step 1: Parse explicit ref argument
    if ref:
        # Try as plain number
        if ref.isdigit():
            return {"resolved": True, "objective_number": int(ref), "source": "argument"}

        # Try as URL
        number = parse_issue_number_from_url(ref)
        if number is not None:
            return {"resolved": True, "objective_number": number, "source": "argument"}

        # Not parseable
        return {"resolved": False}

    # Step 2: Try branch name pattern
    if current_branch is not None:
        obj_number = extract_objective_number(current_branch)
        if obj_number is not None:
            return {"resolved": True, "objective_number": obj_number, "source": "branch_name"}

    # Step 3: Try plan metadata
    if current_branch is not None:
        obj_number = get_objective_for_branch(current_branch)
        if obj_number is not None:
            return {"resolved": True, "objective_number": obj_number, "source": "plan_metadata"}

    return {"resolved": False}


@click.command(name="resolve-objective-ref")
@click.argument("ref", default="")
@click.pass_context
def resolve_objective_ref(ctx: click.Context, ref: str) -> None:
    """Resolve an objective reference to an objective number.

    REF can be an issue number, GitHub URL, or empty (for branch inference).

    Always exits with code 0 - caller decides how to handle not-resolved.
    """
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    repo_root = require_repo_root(ctx)
    plan_backend = require_plan_backend(ctx)

    current_branch = git.branch.get_current_branch(cwd)

    def get_objective_for_branch(branch: str) -> int | None:
        try:
            result = plan_backend.get_managed_pr_for_branch(repo_root, branch)
        except RuntimeError:
            return None
        if isinstance(result, PlanNotFound):
            return None
        if result.objective_id is not None:
            return result.objective_id
        return None

    result = _resolve_objective_ref_impl(
        ref=ref,
        current_branch=current_branch,
        get_objective_for_branch=get_objective_for_branch,
    )
    click.echo(json.dumps(result))
