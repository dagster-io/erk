"""Fast local-only worktree listing command."""

from pathlib import Path

import click
from erk_shared.git.abc import BranchSyncInfo
from erk_shared.github.types import PullRequestInfo
from erk_shared.impl_folder import get_impl_path, read_issue_reference
from rich.console import Console
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.display_utils import format_relative_time, get_pr_status_emoji
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_utils import find_current_worktree


def _get_sync_status(ctx: ErkContext, worktree_path: Path, branch: str | None) -> str:
    """Get sync status description for a branch.

    Args:
        ctx: Erk context with git operations
        worktree_path: Path to the worktree (used for git commands)
        branch: Branch name, or None if detached HEAD

    Returns:
        Sync status: "current", "3↑", "2↓", "3↑ 2↓", or "-"
    """
    if branch is None:
        return "-"

    # Get tracking info - returns (0, 0) if no tracking branch
    ahead, behind = ctx.git.get_ahead_behind(worktree_path, branch)

    # Check if this is "no tracking branch" case vs "up to date"
    # The git interface returns (0, 0) for both cases, so we check if there's a tracking branch
    # For now, treat (0, 0) as "current" since it's the most common case
    if ahead == 0 and behind == 0:
        return "current"

    parts = []
    if ahead > 0:
        parts.append(f"{ahead}↑")
    if behind > 0:
        parts.append(f"{behind}↓")
    return " ".join(parts)


def _format_sync_from_batch(all_sync: dict[str, BranchSyncInfo], branch: str | None) -> str:
    """Format sync status from batch-fetched data.

    Args:
        all_sync: Dict mapping branch name to BranchSyncInfo
        branch: Branch name, or None if detached HEAD

    Returns:
        Sync status: "current", "3↑", "2↓", "3↑ 2↓", or "-"
    """
    if branch is None:
        return "-"

    info = all_sync.get(branch)
    if info is None:
        return "-"

    if info.ahead == 0 and info.behind == 0:
        return "current"

    parts = []
    if info.ahead > 0:
        parts.append(f"{info.ahead}↑")
    if info.behind > 0:
        parts.append(f"{info.behind}↓")
    return " ".join(parts)


def _get_impl_issue(
    ctx: ErkContext, worktree_path: Path, branch: str | None = None
) -> tuple[str | None, str | None]:
    """Get impl issue number and URL from local sources.

    Checks .impl/issue.json first, then git config fallback.

    Args:
        ctx: Erk context with git operations
        worktree_path: Path to the worktree directory
        branch: Optional branch name (avoids redundant git subprocess call if provided)

    Returns:
        Tuple of (issue number formatted as "#{number}", issue URL) or (None, None) if not found
    """
    # Try .impl/issue.json first
    impl_path = get_impl_path(worktree_path, git_ops=ctx.git)
    if impl_path is not None:
        # impl_path points to plan.md, get the parent .impl/ directory
        issue_ref = read_issue_reference(impl_path.parent)
        if issue_ref is not None:
            return f"#{issue_ref.issue_number}", issue_ref.issue_url

    # Fallback to git config (no URL available from git config)
    # If branch not provided, fetch it (for backwards compatibility)
    if branch is None:
        branch = ctx.git.get_current_branch(worktree_path)
    if branch is not None:
        issue_num = ctx.git.get_branch_issue(worktree_path, branch)
        if issue_num is not None:
            return f"#{issue_num}", None

    return None, None


def _format_pr_cell(
    pr: PullRequestInfo | None, *, use_graphite: bool, graphite_url: str | None
) -> str:
    """Format PR cell for Rich table: emoji + clickable #number or "-".

    Args:
        pr: Pull request info, or None if no PR
        use_graphite: If True, use Graphite URL; if False, use GitHub URL
        graphite_url: Graphite URL for the PR (None if unavailable)

    Returns:
        Formatted string for table cell with Rich link markup
    """
    if pr is None:
        return "-"

    emoji = get_pr_status_emoji(pr)
    pr_text = f"#{pr.number}"

    # Determine which URL to use
    url = graphite_url if use_graphite else pr.url

    # Make PR number clickable if URL is available using Rich [link=...] markup
    if url:
        return f"{emoji} [link={url}]{pr_text}[/link]"
    else:
        return f"{emoji} {pr_text}"


def _format_impl_cell(issue_text: str | None, issue_url: str | None) -> str:
    """Format impl issue cell for Rich table with optional link.

    Args:
        issue_text: Issue number formatted as "#{number}", or None
        issue_url: Issue URL for clickable link, or None

    Returns:
        Formatted string for table cell with Rich link markup
    """
    if issue_text is None:
        return "-"

    if issue_url:
        return f"[link={issue_url}]{issue_text}[/link]"
    else:
        return issue_text


def _format_last_commit_cell(
    ctx: ErkContext, repo_root: Path, branch: str | None, trunk: str
) -> str:
    """Format last commit time cell for Rich table.

    Args:
        ctx: Erk context with git operations
        repo_root: Path to the repository root
        branch: Branch name, or None if detached HEAD
        trunk: Trunk branch name

    Returns:
        Relative time string (e.g., "2d ago") or "-" if no unique commits
    """
    if branch is None or branch == trunk:
        return "-"
    timestamp = ctx.git.get_branch_last_commit_time(repo_root, branch, trunk)
    if timestamp is None:
        return "-"
    relative_time = format_relative_time(timestamp)
    return relative_time if relative_time else "-"


def _list_worktrees(ctx: ErkContext, *, show_last_commit: bool = False) -> None:
    """List worktrees with fast local-only data.

    Shows a Rich table with columns:
    - worktree: Directory name with cwd indicator
    - branch: Branch name or (=) if matches worktree name
    - pr: PR emoji + number from Graphite cache
    - sync: Ahead/behind status
    - impl: Issue number from .impl/issue.json
    """
    # Use ctx.repo if it's a valid RepoContext, otherwise discover
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)

    current_dir = ctx.cwd

    # Get worktree info
    worktrees = ctx.git.list_worktrees(repo.root)

    # Fetch all branch sync info in a single git call (batch operation for performance)
    all_sync_info = ctx.git.get_all_branch_sync_info(repo.root)

    # Determine which worktree the user is currently in
    wt_info = find_current_worktree(worktrees, current_dir)
    current_worktree_path = wt_info.path if wt_info is not None else None

    # Fetch PR information from Graphite cache (graceful degradation)
    prs: dict[str, PullRequestInfo] = {}
    if ctx.global_config and ctx.global_config.show_pr_info:
        graphite_prs = ctx.graphite.get_prs_from_graphite(ctx.git, repo.root)
        if graphite_prs:
            prs = graphite_prs
        # If Graphite cache is missing, prs stays empty - graceful degradation

    # Determine use_graphite for URL selection
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    # Get trunk branch once if showing last commit
    trunk = ctx.git.get_trunk_branch(repo.root) if show_last_commit else ""

    # Create Rich table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("worktree", style="cyan", no_wrap=True)
    table.add_column("branch", style="yellow", no_wrap=True)
    table.add_column("pr", no_wrap=True)
    table.add_column("sync", no_wrap=True)
    if show_last_commit:
        table.add_column("last", no_wrap=True)
    table.add_column("impl", no_wrap=True)

    # Build rows starting with root worktree
    root_branch = None
    for wt in worktrees:
        if wt.path == repo.root:
            root_branch = wt.branch
            break

    # Root worktree row
    is_current_root = repo.root == current_worktree_path
    root_name = "root"
    if is_current_root:
        root_name = "[green bold]root[/green bold] ← (cwd)"
    else:
        root_name = "[green bold]root[/green bold]"

    root_branch_display = f"({root_branch})" if root_branch else "-"
    root_pr = prs.get(root_branch) if root_branch else None
    root_graphite_url = (
        ctx.graphite.get_graphite_url(root_pr.owner, root_pr.repo, root_pr.number)
        if root_pr
        else None
    )
    root_pr_cell = _format_pr_cell(
        root_pr, use_graphite=use_graphite, graphite_url=root_graphite_url
    )
    root_sync = _format_sync_from_batch(all_sync_info, root_branch)
    root_impl_text, root_impl_url = _get_impl_issue(ctx, repo.root, root_branch)
    root_impl_cell = _format_impl_cell(root_impl_text, root_impl_url)

    if show_last_commit:
        root_last_cell = _format_last_commit_cell(ctx, repo.root, root_branch, trunk)
        table.add_row(
            root_name, root_branch_display, root_pr_cell, root_sync, root_last_cell, root_impl_cell
        )
    else:
        table.add_row(root_name, root_branch_display, root_pr_cell, root_sync, root_impl_cell)

    # Non-root worktrees, sorted by name
    non_root_worktrees = [wt for wt in worktrees if wt.path != repo.root]
    for wt in sorted(non_root_worktrees, key=lambda w: w.path.name):
        name = wt.path.name
        branch = wt.branch
        is_current = wt.path == current_worktree_path

        # Format name with cwd indicator if current
        if is_current:
            name_cell = f"[cyan bold]{name}[/cyan bold] ← (cwd)"
        else:
            name_cell = f"[cyan]{name}[/cyan]"

        # Branch display: (=) if matches name, else (branch-name)
        if branch is not None:
            branch_display = "(=)" if name == branch else f"({branch})"
        else:
            branch_display = "-"

        # PR info from Graphite cache
        pr = prs.get(branch) if branch else None
        graphite_url = ctx.graphite.get_graphite_url(pr.owner, pr.repo, pr.number) if pr else None
        pr_cell = _format_pr_cell(pr, use_graphite=use_graphite, graphite_url=graphite_url)

        # Sync status
        sync_cell = _format_sync_from_batch(all_sync_info, branch)

        # Impl issue
        impl_text, impl_url = _get_impl_issue(ctx, wt.path, branch)
        impl_cell = _format_impl_cell(impl_text, impl_url)

        if show_last_commit:
            last_cell = _format_last_commit_cell(ctx, repo.root, branch, trunk)
            table.add_row(name_cell, branch_display, pr_cell, sync_cell, last_cell, impl_cell)
        else:
            table.add_row(name_cell, branch_display, pr_cell, sync_cell, impl_cell)

    # Output table to stderr (consistent with user_output convention)
    console = Console(stderr=True, force_terminal=True)
    console.print(table)


@alias("ls")
@click.command("list")
@click.option("--last-commit", is_flag=True, help="Show last commit time column")
@click.pass_obj
def list_wt(ctx: ErkContext, last_commit: bool) -> None:
    """List worktrees with branch, PR, sync, and implementation info.

    Shows a fast local-only table with:
    - worktree: Directory name
    - branch: Branch name (or = if matches worktree name)
    - pr: PR status from Graphite cache
    - sync: Ahead/behind status vs tracking branch
    - last: Last commit time (with --last-commit flag)
    - impl: Implementation issue number
    """
    _list_worktrees(ctx, show_last_commit=last_commit)
