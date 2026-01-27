"""Helper functions for submit command."""

import click

from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk_shared.output.output import user_output


def ensure_trunk_synced(ctx: ErkContext, repo: RepoContext) -> None:
    """Ensure root worktree is on trunk and synced with remote.

    Validates:
    1. Root worktree has trunk checked out
    2. Root worktree is clean (no uncommitted changes)
    3. Local trunk matches or can fast-forward to origin/trunk

    Raises SystemExit(1) on validation failure with clear error message.
    """
    trunk = ctx.git.branch.detect_trunk_branch(repo.root)

    # Find root worktree
    worktrees = ctx.git.worktree.list_worktrees(repo.root)
    root_worktree = None
    for wt in worktrees:
        if wt.is_root:
            root_worktree = wt
            break

    if root_worktree is None:
        # Should not happen, but defensive
        return

    # Check 1: Root worktree must be on trunk
    if root_worktree.branch != trunk:
        user_output(
            click.style("Error: ", fg="red")
            + f"Root worktree is on '{root_worktree.branch}', not '{trunk}'.\n\n"
            f"erk plan submit requires the root worktree to have {trunk} checked out.\n"
            f"This ensures {trunk} can be kept in sync with origin/{trunk}.\n\n"
            f"To fix:\n"
            f"  cd {repo.root}\n"
            f"  git checkout {trunk}"
        )
        raise SystemExit(1)

    # Check 2: Root worktree must be clean
    if ctx.git.has_uncommitted_changes(repo.root):
        user_output(
            click.style("Error: ", fg="red") + "Root worktree has uncommitted changes.\n\n"
            "Please commit or stash changes before running erk plan submit."
        )
        raise SystemExit(1)

    # Check 3: Sync trunk with remote
    ctx.git.remote.fetch_branch(repo.root, "origin", trunk)

    local_sha = ctx.git.branch.get_branch_head(repo.root, trunk)
    remote_sha = ctx.git.branch.get_branch_head(repo.root, f"origin/{trunk}")

    if local_sha == remote_sha:
        return  # Already synced

    # Check if we can fast-forward (local is ancestor of remote)
    # Use merge-base to determine relationship
    # If merge-base == local_sha, local is behind and can fast-forward
    merge_base = ctx.git.get_merge_base(repo.root, trunk, f"origin/{trunk}")

    if merge_base == local_sha:
        # Local is behind remote - safe to fast-forward
        user_output(f"Syncing {trunk} with origin/{trunk}...")
        ctx.git.remote.pull_branch(repo.root, "origin", trunk, ff_only=True)
        user_output(click.style("✓", fg="green") + f" {trunk} synced with origin/{trunk}")
    elif merge_base == remote_sha:
        # Local is ahead of remote - user has local commits
        user_output(
            click.style("Error: ", fg="red")
            + f"Local {trunk} has commits not pushed to origin/{trunk}.\n\n"
            f"Please push your local commits before running erk plan submit:\n"
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
