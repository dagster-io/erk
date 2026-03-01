"""Helper functions for dispatch command."""

import click

from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk_shared.output.output import user_output


def ensure_trunk_synced(ctx: ErkContext, repo: RepoContext) -> None:
    """Ensure local trunk ref is synced with remote, without requiring checkout.

    Uses fetch + update_local_ref to advance the local trunk branch pointer
    without needing trunk to be checked out. If trunk IS checked out in a
    worktree, falls back to requiring a clean worktree before updating.

    Raises SystemExit(1) on sync failure with clear error message.
    """
    trunk = ctx.git.branch.detect_trunk_branch(repo.root)

    # Fetch latest remote trunk
    ctx.git.remote.fetch_branch(repo.root, "origin", trunk)

    local_sha = ctx.git.branch.get_branch_head(repo.root, trunk)
    remote_sha = ctx.git.branch.get_branch_head(repo.root, f"origin/{trunk}")

    if remote_sha is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"Could not find origin/{trunk}. Run `git fetch origin` first."
        )
        raise SystemExit(1)

    if local_sha == remote_sha:
        return  # Already synced

    # Check if we can fast-forward (local is ancestor of remote)
    merge_base = ctx.git.analysis.get_merge_base(repo.root, trunk, f"origin/{trunk}")

    if merge_base == local_sha:
        # Local is behind remote - safe to fast-forward
        # Check if trunk is checked out in any worktree
        trunk_worktree = ctx.git.worktree.find_worktree_for_branch(repo.root, trunk)
        if trunk_worktree is not None:
            # Trunk is checked out — verify the worktree is clean before updating
            if ctx.git.status.has_uncommitted_changes(trunk_worktree):
                user_output(
                    click.style("Error: ", fg="red")
                    + f"Worktree at {trunk_worktree} has {trunk} checked out with "
                    f"uncommitted changes.\n\n"
                    f"Please commit or stash changes before running erk pr dispatch."
                )
                raise SystemExit(1)

        user_output(f"Syncing {trunk} with origin/{trunk}...")
        ctx.git.branch.update_local_ref(repo.root, trunk, remote_sha)
        user_output(click.style("✓", fg="green") + f" {trunk} synced with origin/{trunk}")
    elif merge_base == remote_sha:
        # Local is ahead of remote - user has local commits
        user_output(
            click.style("Error: ", fg="red")
            + f"Local {trunk} has commits not pushed to origin/{trunk}.\n\n"
            f"Please push your local commits before running erk pr dispatch:\n"
            f"  git push origin {trunk}"
        )
        raise SystemExit(1)
    else:
        # True divergence - both have unique commits
        user_output(
            click.style("Error: ", fg="red")
            + f"Local {trunk} has diverged from origin/{trunk}.\n\n"
            f"To fix, sync your local branch:\n"
            f"  git fetch origin && git reset --hard origin/{trunk}\n\n"
            f"Warning: This will discard any local commits on {trunk}."
        )
        raise SystemExit(1)
