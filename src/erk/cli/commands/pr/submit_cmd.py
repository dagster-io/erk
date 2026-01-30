"""Submit current branch as a pull request.

Runs a linear pipeline of functions transforming a frozen SubmitState:
1. Prepare state (resolve repo, branch, parent, issue)
2. Commit WIP changes
3. Push and create/find PR (Graphite-first or core path)
4. Extract diff for AI
5. Fetch plan context
6. Generate AI PR description
7. Enhance with Graphite (if applicable)
8. Finalize PR metadata
"""

from pathlib import Path

import click

from erk.cli.commands.pr.shared import require_claude_available
from erk.cli.commands.pr.submit_pipeline import (
    SubmitError,
    make_initial_state,
    run_submit_pipeline,
)
from erk.core.context import ErkContext

# Set to False to disable polling for PR in Graphite cache after submission.
# This feature ensures the status line can immediately display the PR number.
ENABLE_PR_CACHE_POLLING = True

# Polling configuration for PR cache
PR_CACHE_POLL_MAX_WAIT_SECONDS = 10.0
PR_CACHE_POLL_INTERVAL_SECONDS = 0.5


def _wait_for_pr_in_cache(
    ctx: ErkContext,
    repo_root: Path,
    branch: str,
    *,
    max_wait_seconds: float,
    poll_interval: float,
) -> bool:
    """Wait for PR to appear in Graphite cache after submission.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        branch: Branch name to check
        max_wait_seconds: Maximum time to wait
        poll_interval: Time between checks

    Returns:
        True if PR found in cache, False if timeout
    """
    start = ctx.time.now()
    while (ctx.time.now() - start).total_seconds() < max_wait_seconds:
        prs = ctx.graphite.get_prs_from_graphite(ctx.git, repo_root)
        if branch in prs:
            return True
        ctx.time.sleep(poll_interval)
    return False


@click.command("submit")
@click.option("--debug", is_flag=True, help="Show diagnostic output")
@click.option(
    "--no-graphite",
    is_flag=True,
    help="Skip Graphite enhancement (use git + gh only)",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Force push (use when branch has diverged from remote)",
)
@click.option(
    "--session-id",
    default=None,
    help="Claude session ID for tracing (passed by skills via ${CLAUDE_SESSION_ID})",
)
@click.pass_obj
def pr_submit(
    ctx: ErkContext,
    debug: bool,
    no_graphite: bool,
    force: bool,
    session_id: str | None,
) -> None:
    """Submit PR with AI-generated commit message.

    Uses a two-layer architecture:
    - Core layer (always): git push + gh pr create
    - Graphite layer (optional): gt submit for stack metadata

    The core layer works without Graphite installed. When Graphite is
    available and the branch is tracked, it will enhance the PR with
    stack metadata unless --no-graphite is specified.

    Examples:

    \b
      # Submit PR (with Graphite if available)
      erk pr submit

      # Submit PR without Graphite enhancement
      erk pr submit --no-graphite

      # Force push when branch has diverged
      erk pr submit -f
    """
    # Verify Claude is available (needed for commit message generation)
    require_claude_available(ctx)

    click.echo(click.style("🚀 Submitting PR...", bold=True))
    click.echo("")

    state = make_initial_state(
        cwd=Path.cwd(),
        use_graphite=not no_graphite,
        force=force,
        debug=debug,
        session_id=session_id,
    )

    result = run_submit_pipeline(ctx, state)

    if isinstance(result, SubmitError):
        raise click.ClickException(result.message)

    # Wait for PR to appear in Graphite cache for immediate status line display
    if ENABLE_PR_CACHE_POLLING and result.graphite_url is not None:
        _wait_for_pr_in_cache(
            ctx,
            result.repo_root,
            result.branch_name,
            max_wait_seconds=PR_CACHE_POLL_MAX_WAIT_SECONDS,
            poll_interval=PR_CACHE_POLL_INTERVAL_SECONDS,
        )

    # Success output with clickable URL
    pr_url = result.pr_url or ""
    styled_url = click.style(pr_url, fg="cyan", underline=True)
    clickable_url = f"\033]8;;{pr_url}\033\\{styled_url}\033]8;;\033\\"
    click.echo(f"✅ {clickable_url}")

    # Show Graphite URL if available
    if result.graphite_url:
        styled_graphite = click.style(result.graphite_url, fg="cyan", underline=True)
        clickable_graphite = f"\033]8;;{result.graphite_url}\033\\{styled_graphite}\033]8;;\033\\"
        click.echo(f"📊 {clickable_graphite}")
