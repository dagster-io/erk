"""Verify .impl/ folder still exists after implementation.

This kit CLI command is a guardrail for /erk:plan-implement to ensure the agent
did not delete .impl/ during implementation. The .impl/ folder MUST be preserved
for user review.

Usage:
    erk kit exec erk impl-verify

Output:
    JSON with validation status

Exit Codes:
    0: .impl/ folder exists
    1: .impl/ folder was deleted (violation of instructions)

Examples:
    $ erk kit exec erk impl-verify
    {"valid": true, "impl_dir": "/path/to/.impl"}

    $ erk kit exec erk impl-verify  # when .impl/ is missing
    {"valid": false, "error": ".impl/ folder was deleted during implementation...", ...}
"""

import json
from pathlib import Path

import click


@click.command(name="impl-verify")
def impl_verify() -> None:
    """Verify .impl/ folder still exists after implementation."""
    cwd = Path.cwd()
    impl_dir = cwd / ".impl"

    if not impl_dir.exists():
        # Hard error - agent violated instructions
        result = {
            "valid": False,
            "error": ".impl/ folder was deleted during implementation. This violates instructions.",
            "action": "The .impl/ folder must be preserved for user review.",
        }
        click.echo(json.dumps(result))
        raise SystemExit(1)

    click.echo(json.dumps({"valid": True, "impl_dir": str(impl_dir)}))
