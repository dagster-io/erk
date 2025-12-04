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
7. Restack: gt restack --no-interactive (delegate to auto-restack on conflict)
8. Submit: gt submit --no-edit --no-interactive (force-push to link with Graphite)
"""

from pathlib import Path

import click
from erk_shared.integrations.gt.events import CompletionEvent
from erk_shared.integrations.gt.operations import execute_squash
from erk_shared.integrations.gt.types import SquashError
from erk_shared.output.output import user_output

from erk.cli.ensure import Ensure
from erk.cli.output import stream_auto_restack
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext


@click.command("sync")
@click.pass_obj
def pr_sync(ctx: ErkContext) -> None:
    """Synchronize current PR branch with Graphite.

    Registers the current PR branch with Graphite for stack management.
    After syncing, you can use standard gt commands (gt pr, gt land, etc.).

    This is typically used after 'erk pr checkout' to enable Graphite workflows
    on a PR that was created elsewhere (like from a GitHub Actions run).

    Examples:

        # Checkout and sync a PR
        erk pr checkout 1973
        erk pr sync

        # Now you can use Graphite commands
        gt pr
        gt land

    Requirements:
    - On a branch (not detached HEAD)
    - PR exists and is OPEN
    - PR is not from a fork (cross-repo PRs cannot be tracked)
    """
    # Step 1: Validate preconditions
    Ensure.gh_authenticated(ctx)
    Ensure.gt_authenticated(ctx)

    if isinstance(ctx.repo, NoRepoSentinel):
        ctx.feedback.error("Not in a git repository")
        raise SystemExit(1)
    repo: RepoContext = ctx.repo

    # Check we're on a branch (not detached HEAD)
    current_branch = ctx.git.get_current_branch(ctx.cwd)
    if current_branch is None:
        user_output(
            click.style("Error: ", fg="red") + "Not on a branch - checkout a branch before syncing"
        )
        raise SystemExit(1)

    # Step 2: Check if PR exists and get status
    pr_info = ctx.github.get_pr_status(repo.root, current_branch, debug=False)
    if pr_info.state == "NONE":
        user_output(
            click.style("Error: ", fg="red")
            + f"No pull request found for branch '{current_branch}'"
        )
        raise SystemExit(1)

    # Check PR state (must be OPEN)
    if pr_info.state != "OPEN":
        user_output(
            click.style("Error: ", fg="red")
            + f"Cannot sync {pr_info.state} PR - only OPEN PRs can be synchronized"
        )
        raise SystemExit(1)

    # Get PR number for further checks
    pr_number = pr_info.pr_number
    if pr_number is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"Could not determine PR number for branch '{current_branch}'"
        )
        raise SystemExit(1)

    # Check if PR is from a fork (cross-repo)
    pr_checkout_info = ctx.github.get_pr_checkout_info(repo.root, pr_number)
    if pr_checkout_info is None:
        user_output(click.style("Error: ", fg="red") + f"Could not fetch PR #{pr_number} details")
        raise SystemExit(1)

    if pr_checkout_info.is_cross_repository:
        user_output(
            click.style("Error: ", fg="red")
            + "Cannot sync fork PRs - Graphite cannot track branches from forks"
        )
        raise SystemExit(1)

    # Step 3: Check if already tracked by Graphite (idempotent)
    parent_branch = ctx.graphite.get_parent_branch(ctx.git, repo.root, current_branch)
    if parent_branch is not None:
        user_output(
            click.style("✓", fg="green")
            + f" Branch '{current_branch}' already tracked by Graphite (parent: {parent_branch})"
        )
        return

    # Step 4: Get PR base branch from GitHub
    base_branch = ctx.github.get_pr_base_branch(repo.root, pr_number)
    user_output(f"Base branch: {base_branch}")

    # Step 5: Track with Graphite
    user_output(f"Tracking branch '{current_branch}' with parent '{base_branch}'...")
    ctx.graphite.track_branch(ctx.cwd, current_branch, base_branch)
    user_output(click.style("✓", fg="green") + " Branch tracked with Graphite")

    # Step 6: Squash commits (idempotent)
    user_output("Squashing commits...")
    squash_result = None
    for event in execute_squash(ctx, repo.root):
        if isinstance(event, CompletionEvent):
            squash_result = event.result
    if squash_result is None:
        user_output(click.style("Error: ", fg="red") + "Squash operation produced no result")
        raise SystemExit(1)
    if isinstance(squash_result, SquashError):
        user_output(click.style("Error: ", fg="red") + squash_result.message)
        raise SystemExit(1)
    user_output(click.style("✓", fg="green") + f" {squash_result.message}")

    # Step 6b: Update commit message with PR title/body
    pr_title = ctx.github.get_pr_title(repo.root, pr_number)
    pr_body = ctx.github.get_pr_body(repo.root, pr_number)
    if pr_title:
        commit_message = pr_title
        if pr_body:
            commit_message = f"{pr_title}\n\n{pr_body}"
        user_output("Updating commit message from PR...")
        ctx.git.amend_commit(repo.root, commit_message)
        user_output(click.style("✓", fg="green") + " Commit message updated")

    # Step 7: Restack with auto-conflict resolution
    user_output("Restacking...")
    try:
        ctx.graphite.restack(repo.root, no_interactive=True, quiet=True)
        user_output(click.style("✓", fg="green") + " Restack complete")
    except RuntimeError as e:
        # If restack fails with conflicts, delegate to auto-restack
        error_message = str(e).lower()
        if "conflict" in error_message or "merge" in error_message:
            user_output(
                click.style("⚠", fg="yellow")
                + " Restack encountered conflicts - delegating to auto-restack..."
            )
            # Delegate to auto-restack via Claude executor
            executor = ctx.claude_executor
            if not executor.is_claude_available():
                user_output(
                    click.style("Error: ", fg="red")
                    + "Claude CLI not found - cannot auto-resolve conflicts\n\n"
                    + "Install from: https://claude.com/download\n"
                    + "Or resolve conflicts manually with: gt restack"
                )
                raise SystemExit(1)

            user_output("")
            user_output(click.style("🔄 Auto-restacking via Claude...", bold=True))
            user_output(click.style("   (Claude may take a moment to start)", dim=True))
            user_output("")

            result = stream_auto_restack(executor, Path.cwd())
            if result.requires_interactive:
                raise SystemExit(1)
            if not result.success:
                user_output(
                    click.style("Error: ", fg="red") + (result.error_message or "Auto-restack failed")
                )
                raise SystemExit(1)
            user_output("")
            user_output(click.style("✓", fg="green") + " Auto-restack complete")
        else:
            # Some other error - re-raise
            raise

    # Step 8: Submit with force to link with Graphite
    user_output("Submitting to link with Graphite...")
    try:
        ctx.graphite.submit_stack(repo.root, quiet=True)
        user_output(click.style("✓", fg="green") + f" PR #{pr_number} synchronized with Graphite")
    except RuntimeError as e:
        # Submit can fail - show error and continue
        user_output(
            click.style("⚠", fg="yellow")
            + f" Submit failed: {e}\nYou may need to run 'gt submit' manually."
        )

    user_output(f"\nBranch '{current_branch}' is now tracked by Graphite.")
    user_output("You can now use: gt pr, gt land, etc.")
