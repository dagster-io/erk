"""Prepare impl-context for the current worktree's PR.

Sets up .erk/impl-context/ folder from the PR associated with the current
branch, making the worktree ready for plan implementation.

Usage:
    erk pr prepare           # Auto-detect plan number from current branch's PR
    erk pr prepare 1234      # Explicit plan number
"""

import click

from erk.cli.commands.exec.scripts.setup_impl_from_pr import create_impl_context_from_pr
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.impl_folder import read_plan_ref, resolve_impl_dir
from erk_shared.output.output import user_output


@click.command("prepare")
@click.argument("pr_number", type=int, required=False, default=None)
@click.pass_context
def pr_prepare(ctx: click.Context, pr_number: int | None) -> None:
    """Set up impl-context for the current worktree's PR.

    Prepares the current worktree for plan implementation by creating
    the .erk/impl-context/ folder with plan content from the PR.

    \b
    PLAN_NUMBER: PR number containing the plan (optional).
                 If omitted, auto-detects from current branch's PR.

    \b
    Examples:
        erk pr prepare         # Auto-detect from current branch
        erk pr prepare 1234    # Explicit plan number

    \b
    Must be run from inside a worktree. Idempotent: if impl-context
    already exists for this plan, reports success without recreating.
    """
    erk_ctx: ErkContext = ctx.obj
    Ensure.gh_authenticated(erk_ctx)

    if isinstance(erk_ctx.repo, NoRepoSentinel):
        erk_ctx.console.error("Not in a git repository")
        raise SystemExit(1)
    repo: RepoContext = erk_ctx.repo

    branch = erk_ctx.git.branch.get_current_branch(erk_ctx.cwd)
    if branch is None:
        erk_ctx.console.error("Cannot prepare from detached HEAD state")
        raise SystemExit(1)

    # Resolve plan number: explicit argument or auto-detect from branch's PR
    if pr_number is None:
        pr_result = erk_ctx.github.get_pr_for_branch(repo.root, branch)
        if isinstance(pr_result, PRNotFound):
            erk_ctx.console.error(
                f"No PR found for branch '{branch}'\n\n"
                "Specify a plan number explicitly:\n"
                "  erk pr prepare <plan-number>"
            )
            raise SystemExit(1)
        pr_number = pr_result.number

    # Idempotent: check if impl-context already exists for this plan
    impl_dir = resolve_impl_dir(erk_ctx.cwd, branch_name=branch)
    if impl_dir is not None:
        existing_ref = read_plan_ref(impl_dir)
        if existing_ref is not None and existing_ref.pr_id == str(pr_number):
            user_output(f"Impl-context already set up for plan #{pr_number}")
            return

    result = create_impl_context_from_pr(
        ctx,
        pr_number=pr_number,
        cwd=erk_ctx.cwd,
        branch_name=branch,
    )

    user_output(f"Prepared impl-context for plan #{pr_number} at {result['impl_path']}")
