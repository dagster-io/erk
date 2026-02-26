"""Verify .impl/ folder still exists after implementation.

This exec command is a guardrail for /erk:plan-implement to ensure the agent
did not delete .impl/ during implementation. The .impl/ folder MUST be preserved
for user review.

Usage:
    erk exec impl-verify

Output:
    JSON with validation status

Exit Codes:
    0: .impl/ folder exists
    1: .impl/ folder was deleted (violation of instructions)

Examples:
    $ erk exec impl-verify
    {"valid": true, "impl_dir": "/path/to/.impl"}

    $ erk exec impl-verify  # when .impl/ is missing
    {"valid": false, "error": ".impl/ folder was deleted during implementation...", ...}
"""

import json

import click

from erk_shared.context.helpers import require_cwd, require_git
from erk_shared.impl_folder import resolve_impl_dir


@click.command(name="impl-verify")
@click.pass_context
def impl_verify(ctx: click.Context) -> None:
    """Verify implementation folder still exists after implementation."""
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    branch_name = git.branch.get_current_branch(cwd)

    impl_dir = resolve_impl_dir(cwd, branch_name=branch_name)

    if impl_dir is None:
        # Hard error - agent violated instructions
        result = {
            "valid": False,
            "error": (
                "Implementation folder was deleted during implementation."
                " This violates instructions."
            ),
            "action": "The implementation folder must be preserved for user review.",
        }
        click.echo(json.dumps(result))
        raise SystemExit(1)

    click.echo(json.dumps({"valid": True, "impl_dir": str(impl_dir)}))
