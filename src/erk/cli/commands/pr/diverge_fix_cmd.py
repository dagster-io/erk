"""Fix branch divergence with remote.

Uses Claude to reconcile a diverged local branch with its remote tracking branch,
handling rebase and conflicts as needed. Invokes the /erk:diverge-fix
Claude slash command.
"""

import click

from erk.cli.ensure import Ensure
from erk.cli.output import stream_diverge_fix
from erk.core.context import ErkContext


@click.command("diverge-fix")
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Acknowledge that this command invokes Claude with --dangerously-skip-permissions.",
)
@click.pass_obj
def pr_diverge_fix(ctx: ErkContext, *, dangerous: bool) -> None:
    """Fix branch divergence with remote.

    When gt submit fails with "Branch has been updated remotely", this command
    fetches remote changes, analyzes divergence, rebases if needed, and resolves
    any conflicts using Claude.

    Examples:

    \b
      # Fix divergence with remote
      erk pr diverge-fix --dangerous

    To disable the --dangerous flag requirement:

    \b
      erk config set require_dangerous_flag_for_implicitly_dangerous_operations false
    """
    Ensure.dangerous_flag(ctx, dangerous=dangerous)

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
    ctx.git.remote.fetch_branch(cwd, "origin", current_branch)

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
    executor = ctx.prompt_executor
    if not executor.is_available():
        raise click.ClickException(
            "Claude CLI is required for divergence resolution.\n\n"
            "Install from: https://claude.com/download"
        )

    click.echo(click.style("Analyzing divergence and invoking Claude...", fg="yellow"))

    # Execute diverge fix
    result = stream_diverge_fix(executor, cwd)

    if result.requires_interactive:
        raise click.ClickException("Semantic decision requires interactive resolution")
    if not result.success:
        raise click.ClickException(result.error_message or "Diverge fix failed")

    click.echo(click.style("\nBranch synced with remote!", fg="green", bold=True))
