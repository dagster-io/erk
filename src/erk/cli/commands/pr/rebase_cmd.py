"""Rebase PR onto base branch with mechanical rebase and Claude TUI fallback.

Phase 1: Attempt mechanical rebase via gt restack (Graphite) or git rebase (non-Graphite).
Phase 2: If conflicts arise, launch Claude TUI interactively with /erk:pr-rebase.
"""

import subprocess

import click

from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk_shared.gateway.graphite.disabled import GraphiteDisabled
from erk_shared.gateway.graphite.dry_run import DryRunGraphite


def _is_graphite_enabled(ctx: ErkContext) -> bool:
    graphite = ctx.graphite
    if isinstance(graphite, DryRunGraphite):
        graphite = graphite._wrapped
    return not isinstance(graphite, GraphiteDisabled)


@click.command("rebase")
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
@click.option(
    "--target",
    default=None,
    help="Target branch for git rebase (non-Graphite only).",
)
@click.pass_obj
def rebase(ctx: ErkContext, *, dangerous: bool, safe: bool, target: str | None) -> None:
    """Rebase PR onto base branch with conflict resolution via Claude TUI.

    First attempts a mechanical rebase using gt restack (if Graphite is enabled)
    or git rebase --target <branch> (if Graphite is disabled). If conflicts arise,
    launches Claude TUI with /erk:pr-rebase for interactive resolution.

    Also works when a rebase is already in progress with unresolved conflicts.
    If you started a rebase manually and hit conflicts you can't resolve, run
    this command to have Claude pick up where you left off.

    For remote rebase via GitHub Actions workflow, use:

    \b
      erk launch pr-rebase [--pr <number>]

    Examples:

    \b
      # Rebase locally (dangerous mode is on by default)
      erk pr rebase

    \b
      # Rebase locally (Graphite disabled)
      erk pr rebase --target main

    \b
      # Rebase in safe mode (permission prompts enabled)
      erk pr rebase --safe

    \b
      # Resume a rebase that stopped on conflicts
      git rebase main      # hits conflicts
      erk pr rebase        # Claude resolves them

    To disable dangerous mode by default:

    \b
      erk config set live_dangerously false
    """
    effective_dangerous = Ensure.resolve_dangerous(ctx, dangerous=dangerous, safe=safe)

    cwd = ctx.cwd
    executor = ctx.prompt_executor
    Ensure.invariant(
        executor.is_available(),
        "Claude CLI is required for rebase with conflict resolution.\n\n"
        "Install from: https://claude.com/download",
    )

    graphite_enabled = _is_graphite_enabled(ctx)

    if graphite_enabled:
        branch = ctx.git.branch.get_current_branch(cwd)
        Ensure.invariant(
            branch is not None and ctx.graphite.is_branch_tracked(ctx.repo_root, branch),
            "Current branch is not tracked by Graphite. Track it with: gt track",
        )
        click.echo(click.style("Restacking with Graphite...", fg="yellow"))
        result = subprocess.run(
            ["gt", "restack", "--no-interactive"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            click.echo(click.style("Restack complete!", fg="green", bold=True))
            return
        if not ctx.git.rebase.is_rebase_in_progress(cwd):
            raise click.ClickException(f"gt restack failed:\n{result.stderr}")
        click.echo(click.style("Restack hit conflicts. Launching Claude...", fg="yellow"))
    else:
        if not ctx.git.rebase.is_rebase_in_progress(cwd):
            if target is None:
                raise click.ClickException(
                    "Specify --target <branch> for git rebase (Graphite is not enabled)"
                )
            click.echo(click.style(f"Rebasing onto {target}...", fg="yellow"))
            rebase_result = ctx.git.rebase.rebase_onto(cwd, target)
            if rebase_result.success:
                click.echo(click.style("Rebase complete!", fg="green", bold=True))
                return
            click.echo(click.style("Rebase hit conflicts. Launching Claude...", fg="yellow"))
        else:
            click.echo(click.style("Rebase in progress. Launching Claude...", fg="yellow"))

    # Both paths converge: conflicts exist, show state and confirm
    conflicted = ctx.git.status.get_conflicted_files(cwd)
    if conflicted:
        click.echo(click.style("\nConflicted files:", fg="red", bold=True))
        for f in conflicted:
            click.echo(f"  {f}")
        click.echo()

    if not click.confirm("Launch Claude to resolve conflicts?", default=True):
        click.echo("Rebase paused. Conflicts remain — run 'erk pr rebase' again when ready.")
        return

    click.echo("Launching Claude...", err=True)
    executor.execute_interactive(
        worktree_path=cwd,
        dangerous=effective_dangerous,
        command="/erk:pr-rebase",
        target_subpath=None,
        model=None,
        permission_mode="edits",
    )
    # Never returns — process replaced by os.execvp
