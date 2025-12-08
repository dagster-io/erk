"""List Graphite stack with worktree info."""

import click
from rich.console import Console
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.core import discover_repo_context
from erk.cli.graphite import find_worktrees_containing_branch
from erk.core.context import ErkContext


@alias("ls")
@click.command("list")
@click.pass_obj
def list_stack(ctx: ErkContext) -> None:
    """List the Graphite stack with worktree info.

    Shows branches in the current stack that have associated worktrees,
    displayed top-to-bottom (upstack children at top, downstack trunk at bottom).

    Table columns:
    - Marker: → for current branch
    - branch: Branch name
    - worktree: Worktree directory name
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    current_branch = ctx.git.get_current_branch(repo.root)

    if current_branch is None:
        click.echo("Error: Not on a branch (detached HEAD state)", err=True)
        raise SystemExit(1)

    # Get the stack for current branch
    stack_branches = ctx.graphite.get_branch_stack(ctx.git, repo.root, current_branch)
    if stack_branches is None:
        click.echo(f"Error: Branch '{current_branch}' is not tracked by Graphite", err=True)
        click.echo("Run 'gt track' to track this branch, or 'gt create' to create a new branch.")
        raise SystemExit(1)

    # Get worktrees for branch-to-worktree mapping
    worktrees = ctx.git.list_worktrees(repo.root)

    # Build table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("", no_wrap=True)  # Marker column
    table.add_column("branch", style="cyan", no_wrap=True)
    table.add_column("worktree", no_wrap=True)

    # Filter stack to branches that have an associated worktree
    # Reverse order: upstack (children) at top, downstack (trunk) at bottom
    for branch in reversed(stack_branches):
        # Find worktrees containing this branch
        matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)
        if not matching_worktrees:
            continue

        # Use the first matching worktree
        wt = matching_worktrees[0]
        wt_name = "root" if wt.is_root else wt.path.name

        # Determine marker and style
        is_current = branch == current_branch
        marker = "→" if is_current else ""
        branch_display = f"[bold cyan]{branch}[/bold cyan]" if is_current else branch

        table.add_row(marker, branch_display, wt_name)

    # Check if table has any rows
    if table.row_count == 0:
        click.echo("No branches in stack have worktrees", err=True)
        return

    # Output table to stderr (consistent with erk wt list)
    console = Console(stderr=True, force_terminal=True)
    console.print(table)
