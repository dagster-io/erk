"""Extract the latest plan from Claude session files.

Usage:
    erk kit exec erk extract-latest-plan [--session-id SESSION_ID]

This command searches Claude session files for the most recent ExitPlanMode
tool use and extracts the plan text. It can search either the current session
(if --session-id is provided) or all sessions for the project.

Output:
    Plan text on stdout
    Error message on stderr with exit code 1 on failure

Exit Codes:
    0: Success - plan found and output
    1: Error - no plan found or other error
"""

import click

from erk_shared.context.helpers import require_cwd, require_session_store


@click.command(name="extract-latest-plan")
@click.option(
    "--session-id",
    help="Session ID to search within (optional, searches all sessions if not provided)",
)
@click.pass_context
def extract_latest_plan(ctx: click.Context, session_id: str | None) -> None:
    """Extract the latest plan from Claude session files.

    Searches for the most recent ExitPlanMode tool use and extracts the plan text.
    """
    # Get dependencies from context
    cwd = require_cwd(ctx)
    session_store = require_session_store(ctx)

    # Extract latest plan
    plan_text = session_store.get_latest_plan(cwd, session_id=session_id)

    if not plan_text:
        click.echo(
            click.style("Error: ", fg="red") + "No plan found in Claude session files", err=True
        )
        raise SystemExit(1)

    # Output plan text to stdout
    click.echo(plan_text)
