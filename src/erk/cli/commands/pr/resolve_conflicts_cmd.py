"""Resolve conflicts from an in-progress rebase via Claude TUI.

Only handles in-progress rebases with conflicts. Does NOT initiate rebases.
For remote rebase via CI, use: erk launch pr-rebase
"""

import click

from erk.cli.ensure import Ensure
from erk.core.context import ErkContext


@click.command("resolve-conflicts")
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Force dangerous mode (skip permission prompts).",
)
@click.option(
    "--safe",
    is_flag=True,
    help="Disable dangerous mode (permission prompts enabled).",
)
@click.pass_obj
def resolve_conflicts(ctx: ErkContext, *, dangerous: bool, safe: bool) -> None:
    """Resolve merge conflicts from an in-progress rebase via Claude TUI.

    This command picks up where a rebase left off when conflicts arise.
    It does NOT initiate a rebase -- that's your job (git rebase, gt restack, etc.).

    Examples:

    \b
      # Start a rebase, then resolve conflicts
      git rebase main        # hits conflicts
      erk pr resolve-conflicts

    \b
      # After gt restack hits conflicts
      gt restack --no-interactive
      erk pr resolve-conflicts

    \b
      # Safe mode (permission prompts enabled)
      erk pr resolve-conflicts --safe

    To disable dangerous mode by default:

    \b
      erk config set live_dangerously false
    """
    effective_dangerous = Ensure.resolve_dangerous(ctx, dangerous=dangerous, safe=safe)

    cwd = ctx.cwd
    executor = ctx.prompt_executor
    Ensure.invariant(
        executor.is_available(),
        "Claude CLI is required for conflict resolution.\n\n"
        "Install from: https://claude.com/download",
    )

    Ensure.invariant(
        ctx.git.rebase.is_rebase_in_progress(cwd),
        "No rebase in progress. Start a rebase first with 'git rebase <branch>', "
        "'gt restack', etc., then run this command when conflicts arise.",
    )

    conflicted = ctx.git.status.get_conflicted_files(cwd)
    if conflicted:
        click.echo(click.style("\nConflicted files:", fg="red", bold=True))
        for filepath in conflicted:
            click.echo(f"  {filepath}")
        click.echo()

    if not click.confirm("Launch Claude to resolve conflicts?", default=True):
        click.echo("Conflicts remain -- run 'erk pr resolve-conflicts' again when ready.")
        return

    click.echo("Launching Claude...", err=True)
    executor.execute_interactive(
        worktree_path=cwd,
        dangerous=effective_dangerous,
        command="/erk:pr-resolve-conflicts",
        target_subpath=None,
        model=None,
        permission_mode="edits",
    )
    # Never returns -- process replaced by os.execvp
