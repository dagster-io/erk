"""Sync branch with remote and resolve divergence.

Uses Claude to sync a diverged local branch with its remote tracking branch,
handling rebase and conflicts as needed. Invokes the /erk:sync-divergence
Claude slash command.
"""

import click

from erk.cli.output import stream_sync_divergence
from erk.core.context import ErkContext


@click.command("sync-divergence")
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Acknowledge that this command invokes Claude with --dangerously-skip-permissions.",
)
@click.pass_obj
def pr_sync_divergence(ctx: ErkContext, *, dangerous: bool) -> None:
    """Sync branch with remote and resolve divergence.

    When gt submit fails with "Branch has been updated remotely", this command
    fetches remote changes, analyzes divergence, rebases if needed, and resolves
    any conflicts using Claude.

    Examples:

    \b
      # Sync with remote and resolve divergence
      erk pr sync-divergence --dangerous

    To disable the --dangerous flag requirement:

    \b
      erk config set fix_conflicts_require_dangerous_flag false
    """
    # Runtime validation: require --dangerous unless config disables requirement
    if not dangerous:
        require_flag = (
            ctx.global_config is None or ctx.global_config.fix_conflicts_require_dangerous_flag
        )
        if require_flag:
            raise click.UsageError(
                "Missing option '--dangerous'.\n"
                "To disable: erk config set fix_conflicts_require_dangerous_flag false"
            )

    cwd = ctx.cwd

    # Get current branch
    current_branch = ctx.git.branch.get_current_branch(cwd)
    if current_branch is None:
        raise click.ClickException("Not on a branch (detached HEAD)")

    # Check if remote tracking branch exists
    if not ctx.git.branch.branch_exists_on_remote(cwd, "origin", current_branch):
        raise click.ClickException(f"No remote tracking branch: origin/{current_branch}")

    # Fetch to get latest remote state
    click.echo(click.style("Fetching remote state...", fg="yellow"))
    ctx.git.fetch_branch(cwd, "origin", current_branch)

    # Check divergence status
    divergence = ctx.git.branch.is_branch_diverged_from_remote(cwd, current_branch, "origin")

    if not divergence.is_diverged and divergence.behind == 0:
        click.echo("Branch is already in sync with remote. No action needed.")
        return

    if not divergence.is_diverged and divergence.behind > 0 and divergence.ahead == 0:
        click.echo(f"Branch is {divergence.behind} commit(s) behind remote. Fast-forward possible.")
    elif divergence.is_diverged:
        click.echo(
            f"Branch has diverged: {divergence.ahead} local, {divergence.behind} remote commit(s). "
            "Rebase required."
        )

    # Check Claude availability
    executor = ctx.claude_executor
    if not executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI is required for divergence resolution.\n\n"
            "Install from: https://claude.com/download"
        )

    click.echo(click.style("Analyzing divergence and invoking Claude...", fg="yellow"))

    # Execute sync divergence
    result = stream_sync_divergence(executor, cwd)

    if result.requires_interactive:
        raise click.ClickException("Semantic decision requires interactive resolution")
    if not result.success:
        raise click.ClickException(result.error_message or "Sync divergence failed")

    click.echo(click.style("\nBranch synced with remote!", fg="green", bold=True))
