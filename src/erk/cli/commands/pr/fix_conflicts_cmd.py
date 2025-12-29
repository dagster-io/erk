"""Fix merge conflicts during an active rebase using Claude.

This command detects if a rebase is in progress and invokes Claude to
resolve any conflicts. It's useful when you've run `gt restack` and
hit conflicts that need AI assistance.

Workflow:
    1. gt restack              # Starts restack, may hit conflicts
    2. erk pr fix-conflicts    # Claude resolves conflicts
    3. (repeat until rebase completes)
"""

import click

from erk.cli.output import stream_auto_restack
from erk.core.context import ErkContext
from erk_shared.output.output import user_output


@click.command("fix-conflicts")
@click.pass_obj
def pr_fix_conflicts(ctx: ErkContext) -> None:
    """Fix merge conflicts during an active rebase.

    Detects if a rebase is in progress and invokes Claude to resolve
    any conflicts. The command loops until the rebase completes.

    Examples:

    \b
      # After hitting conflicts during gt restack
      erk pr fix-conflicts

    Requires:
    - An active rebase in progress (run 'gt restack' first)
    - Claude CLI installed (https://claude.com/download)
    """
    cwd = ctx.cwd

    # Check if rebase is in progress
    if not ctx.git.is_rebase_in_progress(cwd):
        conflicts = ctx.git.get_conflicted_files(cwd)
        if not conflicts:
            user_output(
                click.style("Error: ", fg="red")
                + "No rebase in progress and no conflicts detected.\n\n"
                + "To fix conflicts during a restack:\n"
                + "  1. Run: gt restack\n"
                + "  2. If conflicts occur, run: erk pr fix-conflicts"
            )
            raise SystemExit(1)
        # Conflicts exist but no rebase - still try to help
        user_output(
            click.style("⚠", fg="yellow")
            + f" Found {len(conflicts)} conflicted file(s) but no rebase in progress"
        )

    # Check for conflicted files
    conflicts = ctx.git.get_conflicted_files(cwd)
    if not conflicts:
        user_output(
            click.style("✓", fg="green")
            + " No conflicts detected. Rebase may already be complete."
        )
        return

    user_output(
        click.style("🔧", fg="cyan")
        + f" Fixing {len(conflicts)} conflict(s): {', '.join(conflicts)}"
    )

    # Check Claude availability
    executor = ctx.claude_executor
    if not executor.is_claude_available():
        user_output(
            click.style("Error: ", fg="red")
            + "Conflicts require Claude for resolution.\n\n"
            + "Install from: https://claude.com/download"
        )
        raise SystemExit(1)

    # Invoke Claude for conflict resolution
    result = stream_auto_restack(executor, cwd)

    if result.requires_interactive:
        user_output(
            click.style("Error: ", fg="red")
            + "Semantic conflict requires interactive resolution.\n\n"
            + "Run: claude /erk:auto-restack"
        )
        raise SystemExit(1)

    if not result.success:
        user_output(
            click.style("Error: ", fg="red")
            + (result.error_message or "Conflict resolution failed")
        )
        raise SystemExit(1)

    user_output(click.style("✓", fg="green") + " Conflicts resolved successfully!")
