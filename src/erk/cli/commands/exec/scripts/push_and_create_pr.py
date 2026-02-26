"""Push branch and create/find PR, outputting JSON.

Runs the first three steps of the submit pipeline (prepare_state,
commit_wip, push_and_create_pr) with quiet=True so no progress output
pollutes stdout. On success, outputs structured JSON with branch, PR,
and Graphite info for agent consumption.

Usage:
    erk exec push-and-create-pr
    erk exec push-and-create-pr --force
    erk exec push-and-create-pr --no-graphite

Exit Codes:
    0: Success (JSON output on stdout)
    1: Error (JSON error output on stdout)
"""

import json
import sys
from pathlib import Path

import click

from erk.cli.commands.pr.submit_pipeline import (
    SubmitError,
    SubmitState,
    make_initial_state,
    run_push_and_create_pipeline,
)
from erk.core.context import ErkContext
from erk_shared.context.helpers import require_context


@click.command(name="push-and-create-pr")
@click.option("-f", "--force", is_flag=True, help="Force push")
@click.option("--no-graphite", is_flag=True, help="Skip Graphite (use git + gh only)")
@click.option("--session-id", default=None, help="Claude session ID for tracing")
@click.pass_context
def push_and_create_pr(
    ctx: click.Context,
    *,
    force: bool,
    no_graphite: bool,
    session_id: str | None,
) -> None:
    """Push branch and create/find PR, outputting JSON.

    Runs only the push-and-create portion of the submit pipeline.
    Designed for agent workflows that handle description generation
    separately.
    """
    erk_ctx = require_context(ctx)
    cwd = erk_ctx.cwd

    state = make_initial_state(
        cwd=cwd,
        use_graphite=not no_graphite,
        force=force,
        debug=False,
        session_id=session_id,
        skip_description=True,
        quiet=True,
    )

    result = run_push_and_create_pipeline(erk_ctx, state)

    if isinstance(result, SubmitError):
        error_output = {
            "success": False,
            "error": {
                "phase": result.phase,
                "error_type": result.error_type,
                "message": result.message,
            },
        }
        click.echo(json.dumps(error_output, indent=2))
        sys.exit(1)

    assert isinstance(result, SubmitState)

    # Wait for PR to appear in Graphite cache for status line
    if result.graphite_url is not None:
        _wait_for_pr_in_cache(erk_ctx, result.repo_root, result.branch_name)

    output = {
        "success": True,
        "branch": result.branch_name,
        "pr": {
            "number": result.pr_number,
            "url": result.pr_url,
            "was_created": result.was_created,
        },
        "graphite_url": result.graphite_url,
        "plan_id": result.plan_id,
    }
    click.echo(json.dumps(output, indent=2))


_PR_CACHE_POLL_MAX_WAIT_SECONDS = 10.0
_PR_CACHE_POLL_INTERVAL_SECONDS = 0.5


def _wait_for_pr_in_cache(
    ctx: ErkContext,
    repo_root: Path,
    branch: str,
) -> bool:
    """Wait for PR to appear in Graphite cache after submission."""
    start = ctx.time.now()
    while (ctx.time.now() - start).total_seconds() < _PR_CACHE_POLL_MAX_WAIT_SECONDS:
        prs = ctx.graphite.get_prs_from_graphite(ctx.git, repo_root)
        if branch in prs:
            return True
        ctx.time.sleep(_PR_CACHE_POLL_INTERVAL_SECONDS)
    return False
