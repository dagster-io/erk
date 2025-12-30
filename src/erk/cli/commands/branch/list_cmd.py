"""List active branches - those with worktrees or open PRs."""

import click
from rich.console import Console
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.display_utils import format_relative_time, get_pr_status_emoji
from erk_shared.github.types import PullRequestInfo


@alias("ls")
@click.command("list")
@click.pass_obj
def branch_list(ctx: ErkContext) -> None:
    """List active branches with their worktrees and PR status.

    Active branches are those that have:
    - A worktree checked out, OR
    - An open pull request

    Example:
        erk br ls
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    # Detect trunk branch for last commit calculation
    trunk = ctx.git.detect_trunk_branch(repo.root)

    # Get worktrees and PR info
    worktrees = ctx.git.list_worktrees(repo.root)
    prs = ctx.graphite.get_prs_from_graphite(ctx.git, repo.root)

    # Build active branches map: branch -> (worktree_name, pr_info)
    active_branches: dict[str, tuple[str | None, PullRequestInfo | None]] = {}

    # Add branches from worktrees
    for wt in worktrees:
        if wt.branch is not None and wt.branch != ctx.trunk_branch:
            wt_name = "root" if wt.is_root else wt.path.name
            pr = prs.get(wt.branch)
            active_branches[wt.branch] = (wt_name, pr)

    # Add branches with open PRs (not already in worktrees)
    for branch, pr in prs.items():
        if branch not in active_branches and pr.state == "OPEN":
            active_branches[branch] = (None, pr)

    # Display table
    console = Console(stderr=True, force_terminal=True)
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("branch", style="yellow")
    table.add_column("worktree", style="cyan")
    table.add_column("pr")
    table.add_column("last", no_wrap=True)
    table.add_column("state", style="dim")

    for branch in sorted(active_branches.keys()):
        wt_name, pr = active_branches[branch]

        pr_cell = "-"
        state_cell = "-"
        if pr is not None:
            emoji = get_pr_status_emoji(pr)
            pr_cell = f"{emoji} #{pr.number}"
            state_cell = pr.state

        # Get last commit time for this branch
        timestamp = ctx.git.get_branch_last_commit_time(repo.root, branch, trunk)
        last_cell = format_relative_time(timestamp) if timestamp is not None else "-"

        table.add_row(
            branch,
            wt_name or "-",
            pr_cell,
            last_cell,
            state_cell,
        )

    console.print(table)
