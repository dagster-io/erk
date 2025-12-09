"""Wrap a plan in a collapsible GitHub metadata block."""

import sys

import click


@click.command(name="wrap-plan-in-metadata-block")
def wrap_plan_in_metadata_block() -> None:
    """Return plan content for issue body.

    Reads plan content from stdin and returns it as-is (stripped).
    Formatting and workflow instructions will be added via a separate comment.

    Usage:
        echo "$plan" | dot-agent kit-command erk wrap-plan-in-metadata-block

    Exit Codes:
        0: Success
        1: Error (empty input)
    """
    # Read plan content from stdin
    plan_content = sys.stdin.read()

    # Validate input is not empty
    if not plan_content or not plan_content.strip():
        click.echo("Error: Empty plan content received", err=True)
        raise SystemExit(1)

    # Return plan content as-is (metadata wrapping delegated to separate comments)
    result = plan_content.strip()

    # Output the result
    click.echo(result)
