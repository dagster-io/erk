"""Synchronize current PR branch with remote base.

This command has two modes:

**With Graphite enabled:**
Registers a checked-out PR branch with Graphite so it can be managed
using gt commands (gt pr, gt land, etc.). Requires --dangerous flag.

Flow:
1. Validate preconditions (gh/gt auth, on branch, PR exists and is OPEN)
2. Check if already tracked by Graphite (idempotent)
3. Get PR base branch from GitHub
4. Track with Graphite: gt track --branch <current> --parent <base>
5. Squash commits: gt squash --no-edit --no-interactive
6. Update local commit message with PR title/body from GitHub
7. Restack: gt restack (manual conflict resolution if needed)
8. Submit: gt submit --no-edit --no-interactive (force-push to link with Graphite)

**Without Graphite (git-only mode):**
Rebases the current branch onto its PR base branch and force pushes.

Flow:
1. Validate preconditions (gh auth, on branch, PR exists and is OPEN)
2. Check PR is not from a fork
3. Fetch base branch from origin
4. Rebase onto origin/<base>
5. Force push to origin
"""

from pathlib import Path

import click

from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.gateway.gt.events import CompletionEvent
from erk_shared.gateway.gt.operations import execute_squash
from erk_shared.gateway.gt.types import RestackError, SquashError, SquashSuccess
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
    if isinstance(squash_result, SquashError):
        Ensure.invariant(False, squash_result.message)
    assert isinstance(squash_result, SquashSuccess)  # Type narrowing after error check
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


def _git_only_sync(
    ctx: ErkContext,
    repo: RepoContext,
    current_branch: str,
    base_branch: str,
    pr_number: int,
) -> None:
    """Execute git-only sync: fetch base → rebase → force push.

    This is the non-Graphite path for syncing PR branches.

    Args:
        ctx: ErkContext
        repo: Repository context
        current_branch: Current branch name
        base_branch: PR base branch from GitHub
        pr_number: PR number for output messages
    """
    # Fetch the base branch
    user_output(f"Fetching origin/{base_branch}...")
    ctx.git.fetch_branch(repo.root, "origin", base_branch)
    user_output(click.style("✓", fg="green") + f" Fetched origin/{base_branch}")

    # Rebase onto origin/<base>
    user_output(f"Rebasing onto origin/{base_branch}...")
    rebase_result = ctx.git.rebase_onto(repo.root, f"origin/{base_branch}")

    if not rebase_result.success:
        # Conflict occurred - provide instructions
        user_output(click.style("\nRebase paused due to merge conflicts.", fg="yellow"))
        if rebase_result.conflict_files:
            user_output("Conflicted files:")
            for file in rebase_result.conflict_files:
                user_output(f"  - {file}")
        user_output("\nTo resolve conflicts:")
        user_output("  1. Resolve conflicts in the listed files")
        user_output("  2. Run: git add <files>")
        user_output("  3. Run: git rebase --continue")
        user_output("  4. Run: git push --force origin " + current_branch)
        raise SystemExit(1)

    user_output(click.style("✓", fg="green") + " Rebase complete")

    # Force push to origin
    user_output(f"Force pushing to origin/{current_branch}...")
    ctx.git.push_to_remote(repo.root, "origin", current_branch, force=True)
    user_output(click.style("✓", fg="green") + f" PR #{pr_number} synchronized")

    user_output(f"\nBranch '{current_branch}' is now up to date with origin/{base_branch}.")


@click.command("sync")
@click.option(
    "--dangerous",
    is_flag=True,
    help="Required for Graphite mode (invokes Claude with --dangerously-skip-permissions).",
)
@click.pass_obj
def pr_sync(ctx: ErkContext, *, dangerous: bool) -> None:
    """Synchronize current PR branch with remote base.

    With Graphite enabled (requires --dangerous):
        Registers the current PR branch with Graphite for stack management.
        After syncing, you can use standard gt commands (gt pr, gt land, etc.).

    Without Graphite (git-only mode):
        Fetches the PR base branch, rebases onto it, and force pushes.
        This is the simpler mode for teams not using Graphite.

    Examples:

        # Git-only sync (no Graphite)
        erk pr sync

        # Graphite sync
        erk pr sync --dangerous

    Requirements:
    - On a branch (not detached HEAD)
    - PR exists and is OPEN
    - PR is not from a fork (cross-repo PRs cannot be tracked)
    """
    # Step 1: Validate common preconditions
    Ensure.gh_authenticated(ctx)
    Ensure.invariant(
        not isinstance(ctx.repo, NoRepoSentinel),
        "Not in a git repository",
    )
    assert not isinstance(ctx.repo, NoRepoSentinel)  # Type narrowing for ty
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
        "Cannot sync fork PRs - branches from forks cannot be synced",
    )

    # Get PR base branch from GitHub
    base_branch = pr.base_ref_name

    # Determine which mode to use based on Graphite availability
    if not ctx.branch_manager.is_graphite_managed():
        # Git-only mode: fetch → rebase → force push
        user_output(f"Base branch: {base_branch}")
        _git_only_sync(ctx, repo, current_branch, base_branch, pr_number)
        return

    # Graphite mode: requires --dangerous flag
    if not dangerous:
        user_output(
            click.style("Error: ", fg="red")
            + "Graphite mode requires --dangerous flag.\n\n"
            + "This command invokes Claude with --dangerously-skip-permissions.\n\n"
            + "Run with --dangerous to proceed with Graphite sync."
        )
        raise SystemExit(1)

    # Validate Graphite auth
    Ensure.gt_authenticated(ctx)

    # Step 3: Check if already tracked by Graphite (idempotent)
    parent_branch = ctx.graphite.get_parent_branch(ctx.git, repo.root, current_branch)
    if parent_branch is not None:
        user_output(
            click.style("✓", fg="green")
            + f" Branch '{current_branch}' already tracked by Graphite (parent: {parent_branch})"
        )
        return

    user_output(f"Base branch: {base_branch}")

    # Step 5: Track with Graphite
    user_output(f"Tracking branch '{current_branch}' with parent '{base_branch}'...")
    ctx.graphite.track_branch(ctx.cwd, current_branch, base_branch)
    user_output(click.style("✓", fg="green") + " Branch tracked with Graphite")

    # Step 6: Squash commits (idempotent)
    _squash_commits(ctx, repo.root)

    # Step 6b: Update commit message with PR title/body
    _update_commit_message_from_pr(ctx, repo.root, pr_number)

    # Step 7: Restack with Graphite (manual conflict resolution if needed)
    user_output("Restacking branch...")
    restack_result = ctx.graphite.restack_idempotent(repo.root, no_interactive=True, quiet=False)
    if isinstance(restack_result, RestackError):
        if restack_result.error_type == "restack-conflict":
            user_output(click.style("\nRestack paused due to merge conflicts.", fg="yellow"))
            user_output("To resolve conflicts, run:")
            user_output(click.style("  erk pr fix-conflicts --dangerous", fg="cyan"))
            user_output("\nOr manually:")
            user_output("  1. Resolve conflicts in the listed files")
            user_output("  2. Run: gt add -A")
            user_output("  3. Run: gt continue")
            raise SystemExit(1)
        # Non-conflict error
        raise click.ClickException(restack_result.message)
    user_output(click.style("✓", fg="green") + " Branch restacked")

    # Step 8: Submit to link with Graphite
    # Force push is required because squashing rewrites history, causing divergence from remote
    user_output("Submitting to link with Graphite...")
    ctx.graphite.submit_stack(repo.root, quiet=True, force=True)
    user_output(click.style("✓", fg="green") + f" PR #{pr_number} synchronized with Graphite")

    user_output(f"\nBranch '{current_branch}' is now tracked by Graphite.")
    user_output("You can now use: gt pr, gt land, etc.")
