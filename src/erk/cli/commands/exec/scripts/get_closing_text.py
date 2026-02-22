#!/usr/bin/env python3
"""Get closing text for PR body based on .impl/plan-ref.json or branch name.

This command determines the issue number from .impl/plan-ref.json or the branch
name (P{issue_number}-... pattern) and outputs the appropriate closing text.

Usage:
    erk exec get-closing-text

Output:
    Plain text "Closes #N" (same-repo) or "Closes owner/repo#N" (cross-repo)
    Empty output if no issue reference found

Exit Codes:
    0: Success (whether issue reference exists or not)
    1: Error (branch/issue.json mismatch)

Examples:
    $ erk exec get-closing-text
    Closes #776

    $ erk exec get-closing-text  # Cross-repo plans
    Closes owner/plans-repo#776

    $ erk exec get-closing-text  # No .impl/issue.json but branch is P123-feature
    Closes #123

    $ erk exec get-closing-text  # No .impl/ and branch is feature-branch
    (no output)
"""

from pathlib import Path

import click

from erk.cli.config import load_config
from erk_shared.context.helpers import get_current_branch, require_cwd
from erk_shared.impl_folder import read_plan_ref, validate_plan_linkage


def _find_repo_root(start: Path) -> Path | None:
    """Find repository root by looking for .git directory."""
    current = start
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


@click.command(name="get-closing-text")
@click.pass_context
def get_closing_text(ctx: click.Context) -> None:
    """Get closing text for PR body based on .impl/plan-ref.json or branch name.

    Validates that branch name and plan reference agree (if both present).
    Falls back to branch name if no .impl/ folder exists.

    Outputs nothing and exits successfully if no issue number is discoverable.
    """
    cwd = require_cwd(ctx)

    # Get current branch name for validation and fallback
    branch_name = get_current_branch(ctx)
    if branch_name is None:
        # Not on a branch (detached HEAD) - can't determine issue number
        return

    # Check .impl/ first, then .erk/impl-context/
    impl_dir = cwd / ".impl"
    if not impl_dir.exists():
        impl_dir = cwd / ".erk" / "impl-context"

    # Validate linkage and get plan ID (branch fallback if no .impl/)
    try:
        plan_id = validate_plan_linkage(impl_dir, branch_name)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from None

    if plan_id is None:
        # No issue to close (neither branch nor .impl/ has one)
        return

    # Draft-PR plans close themselves on merge - no closing keyword needed
    if impl_dir.exists():
        plan_ref = read_plan_ref(impl_dir)
        if plan_ref is not None and plan_ref.provider == "github-draft-pr":
            return

    # Load config to check for cross-repo plans
    repo_root = _find_repo_root(cwd)
    plans_repo: str | None = None
    if repo_root is not None:
        config = load_config(repo_root)
        plans_repo = config.plans_repo

    # Format closing text
    if plans_repo is None:
        closing_text = f"Closes #{plan_id}"
    else:
        closing_text = f"Closes {plans_repo}#{plan_id}"

    click.echo(closing_text)
