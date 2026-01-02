"""Synchronize current PR branch with Graphite.

This command registers a checked-out PR branch with Graphite so it can be managed
using gt commands (gt pr, gt land, etc.). Useful after checking out a PR from a
remote source (like GitHub Actions).

Flow:
1. Validate preconditions (gh/gt auth, on branch, PR exists and is OPEN)
2. Check if already tracked by Graphite (idempotent)
3. Get PR base branch from GitHub
4. Track with Graphite: gt track --branch <current> --parent <base>
5. Squash commits: gt squash --no-edit --no-interactive
6. Update local commit message with PR title/body from GitHub
7. Restack: erk pr auto-restack (AI-powered conflict resolution)
8. Submit: gt submit --no-edit --no-interactive (force-push to link with Graphite)
"""

from pathlib import Path

import click

from erk.cli.ensure import Ensure
from erk.cli.output import stream_auto_restack
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.gateway.gt.events import CompletionEvent
from erk_shared.gateway.gt.operations import execute_squash
from erk_shared.gateway.gt.types import SquashError
from erk_shared.github.types import PRNotFound
from erk_shared.output.output import user_output


def _squash_commits(ctx: ErkContext, repo_root: Path) -> None:
    """Squash all commits on the current branch into one."""
    user_output("Squashing commits...")
    squash_result = None
    for event in execute_squash(ctx, repo_root):
        if isinstance(event, CompletionEvent):
            squash_result = event.result
    squash_result = Ensure.not_none(squash_result, "Squash operation produced no result")
    Ensure.invariant(not isinstance(squash_result, SquashError), squash_result.message)
    user_output(click.style("✓", fg="green") + f" {squash_result.message}")


def _update_commit_message_from_pr(ctx: ErkContext, repo_root: Path, pr_number: int) -> None:
    """Update the commit message with PR title and body from GitHub."""
    pr = ctx.github.get_pr(repo_root, pr_number)
    if isinstance(pr, PRNotFound):
        # PR was verified to exist earlier, so this shouldn't happen
        return
    if pr.title:
        commit_message = pr.title
        if pr.body:
            commit_message = f"{pr.title}\n\n{pr.body}"
        user_output("Updating commit message from PR...")
        ctx.git.amend_commit(repo_root, commit_message)
        user_output(click.style("✓", fg="green") + " Commit message updated")


@click.command("sync")
@click.option(
    "--dangerous",
    is_flag=True,
    required=True,
    help="Acknowledge that this command invokes Claude with --dangerously-skip-permissions.",
)
@click.pass_obj
def pr_sync(ctx: ErkContext, *, dangerous: bool) -> None:
    """Synchronize current PR branch with Graphite.

    Registers the current PR branch with Graphite for stack management.
    After syncing, you can use standard gt commands (gt pr, gt land, etc.).

    This is typically used after 'erk pr checkout' to enable Graphite workflows
    on a PR that was created elsewhere (like from a GitHub Actions run).

    Examples:

        # Checkout and sync a PR
        erk pr checkout 1973
        erk pr sync --dangerous

        # Now you can use Graphite commands
        gt pr
        gt land

    Requirements:
    - On a branch (not detached HEAD)
    - PR exists and is OPEN
    - PR is not from a fork (cross-repo PRs cannot be tracked)
    """
    # dangerous flag is required to indicate acknowledgment
    _ = dangerous
    # Step 1: Validate preconditions
    Ensure.graphite_available(ctx)
    Ensure.gh_authenticated(ctx)
    Ensure.gt_authenticated(ctx)
    Ensure.invariant(
        not isinstance(ctx.repo, NoRepoSentinel),
        "Not in a git repository",
    )
    assert not isinstance(ctx.repo, NoRepoSentinel)  # Type narrowing for pyright
    repo: RepoContext = ctx.repo

    # Check we're on a branch (not detached HEAD)
    current_branch = Ensure.not_none(
        ctx.git.get_current_branch(ctx.cwd),
        "Not on a branch - checkout a branch before syncing",
    )

    # Step 2: Check if PR exists and get status
    pr = ctx.github.get_pr_for_branch(repo.root, current_branch)
    Ensure.invariant(
        not isinstance(pr, PRNotFound),
        f"No pull request found for branch '{current_branch}'",
    )
    # Type narrowing after invariant check
    assert not isinstance(pr, PRNotFound)
    Ensure.invariant(
        pr.state == "OPEN",
        f"Cannot sync {pr.state} PR - only OPEN PRs can be synchronized",
    )

    pr_number = pr.number

    # Check if PR is from a fork (cross-repo)
    Ensure.invariant(
        not pr.is_cross_repository,
        "Cannot sync fork PRs - Graphite cannot track branches from forks",
    )

    # Step 3: Check if already tracked by Graphite (idempotent)
    parent_branch = ctx.graphite.get_parent_branch(ctx.git, repo.root, current_branch)
    if parent_branch is not None:
        user_output(
            click.style("✓", fg="green")
            + f" Branch '{current_branch}' already tracked by Graphite (parent: {parent_branch})"
        )
        return

    # Step 4: Get PR base branch from GitHub (use same PRDetails object)
    base_branch = pr.base_ref_name
    user_output(f"Base branch: {base_branch}")

    # Step 5: Track with Graphite
    user_output(f"Tracking branch '{current_branch}' with parent '{base_branch}'...")
    ctx.graphite.track_branch(ctx.cwd, current_branch, base_branch)
    user_output(click.style("✓", fg="green") + " Branch tracked with Graphite")

    # Step 6: Squash commits (idempotent)
    _squash_commits(ctx, repo.root)

    # Step 6b: Update commit message with PR title/body
    _update_commit_message_from_pr(ctx, repo.root, pr_number)

    # Step 7: Restack with auto-conflict resolution
    executor = ctx.claude_executor
    if not executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\n\nInstall from: https://claude.com/download"
        )

    result = stream_auto_restack(executor, repo.root)

    if result.requires_interactive:
        raise click.ClickException("Semantic conflict requires interactive resolution")
    if not result.success:
        raise click.ClickException(result.error_message or "Auto-restack failed")

    # Step 8: Submit to link with Graphite
    # Force push is required because squashing rewrites history, causing divergence from remote
    user_output("Submitting to link with Graphite...")
    ctx.graphite.submit_stack(repo.root, quiet=True, force=True)
    user_output(click.style("✓", fg="green") + f" PR #{pr_number} synchronized with Graphite")

    user_output(f"\nBranch '{current_branch}' is now tracked by Graphite.")
    user_output("You can now use: gt pr, gt land, etc.")
