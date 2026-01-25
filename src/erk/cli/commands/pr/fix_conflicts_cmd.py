"""Fix merge conflicts with AI-powered resolution.

The fix-conflicts group has two variants:
- `erk pr fix-conflicts` (default): Local resolution via Claude CLI
- `erk pr fix-conflicts remote`: Remote resolution via GitHub Actions workflow
"""

import click

from erk.cli.commands.pr.metadata_helpers import maybe_update_plan_dispatch_metadata
from erk.cli.constants import REBASE_WORKFLOW_NAME
from erk.cli.ensure import Ensure
from erk.cli.help_formatter import ErkCommandGroup
from erk.cli.output import stream_fix_conflicts
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.github.types import PRNotFound
from erk_shared.output.output import user_output


def _run_local_fix_conflicts(ctx: ErkContext, *, dangerous: bool) -> None:
    """Run local conflict resolution using Claude CLI."""
    # Runtime validation: require --dangerous unless config disables requirement
    if not dangerous:
        require_flag = (
            ctx.global_config is None or ctx.global_config.fix_conflicts_require_dangerous_flag
        )
        if require_flag:
            raise click.UsageError(
                "Missing option '--dangerous'.\n"
                "To disable: erk config set fix_conflicts_require_dangerous_flag false"
            )

    cwd = ctx.cwd

    # Check for conflicts
    conflicted_files = ctx.git.get_conflicted_files(cwd)
    if not conflicted_files:
        click.echo("No merge conflicts detected.")
        return

    # Check Claude availability
    executor = ctx.claude_executor
    if not executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI is required for conflict resolution.\n\n"
            "Install from: https://claude.com/download"
        )

    # Show conflict info
    click.echo(
        click.style(
            f"Found {len(conflicted_files)} conflicted file(s). Invoking Claude...",
            fg="yellow",
        )
    )

    # Execute conflict resolution
    result = stream_fix_conflicts(executor, cwd)

    if result.requires_interactive:
        raise click.ClickException("Semantic conflict requires interactive resolution")
    if not result.success:
        raise click.ClickException(result.error_message or "Conflict resolution failed")

    click.echo(click.style("\n✅ Conflicts resolved!", fg="green", bold=True))


@click.group("fix-conflicts", cls=ErkCommandGroup, invoke_without_command=True)
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Acknowledge that this command invokes Claude with --dangerously-skip-permissions.",
)
@click.pass_context
def fix_conflicts_group(ctx: click.Context, *, dangerous: bool) -> None:
    """Fix merge conflicts with AI-powered resolution.

    When run without a subcommand, resolves merge conflicts on the current
    branch using Claude. Does not require or interact with Graphite stacks.

    Use 'erk pr fix-conflicts remote' to trigger remote resolution via
    GitHub Actions workflow.

    Examples:

    \b
      # Fix conflicts locally with Claude
      erk pr fix-conflicts --dangerous

    \b
      # Trigger remote rebase/conflict resolution
      erk pr fix-conflicts remote

    To disable the --dangerous flag requirement for local resolution:

    \b
      erk config set fix_conflicts_require_dangerous_flag false
    """
    if ctx.invoked_subcommand is None:
        # Run local fix-conflicts when no subcommand given
        erk_ctx: ErkContext = ctx.obj
        _run_local_fix_conflicts(erk_ctx, dangerous=dangerous)


@fix_conflicts_group.command("remote")
@click.argument("pr_number", type=int, required=False)
@click.option(
    "--no-squash",
    is_flag=True,
    help="Skip squashing commits before rebase.",
)
@click.option(
    "--model",
    "model_name",
    type=str,
    help="Claude model for conflict resolution (default: claude-sonnet-4-5).",
)
@click.pass_obj
def fix_conflicts_remote(
    ctx: ErkContext,
    pr_number: int | None,
    *,
    no_squash: bool,
    model_name: str | None,
) -> None:
    """Trigger remote rebase with AI-powered conflict resolution.

    This command triggers a GitHub Actions workflow that:

    \b
    1. Squashes all commits on the branch (unless --no-squash)
    2. Rebases onto the PR's base branch
    3. Uses Claude to resolve any merge conflicts
    4. Force pushes the rebased branch

    This is useful when your PR has merge conflicts and you want to resolve
    them remotely without switching to the branch locally.

    If PR_NUMBER is provided, triggers rebase for that PR (you don't need
    to be on the branch). Otherwise, uses the PR for the current branch.

    Examples:

    \b
        # Basic usage - squash and rebase current branch's PR
        erk pr fix-conflicts remote

    \b
        # Trigger rebase for a specific PR (without checking out)
        erk pr fix-conflicts remote 123

    \b
        # Rebase without squashing
        erk pr fix-conflicts remote --no-squash

    \b
        # Use a specific model
        erk pr fix-conflicts remote --model claude-sonnet-4-5

    Requirements:

    \b
    - Either be on a branch with an open PR, or provide a PR number
    - GitHub Actions secrets must be configured (ERK_QUEUE_GH_PAT, Claude credentials)
    """
    # Validate preconditions
    Ensure.gh_authenticated(ctx)
    Ensure.invariant(
        not isinstance(ctx.repo, NoRepoSentinel),
        "Not in a git repository",
    )
    assert not isinstance(ctx.repo, NoRepoSentinel)  # Type narrowing for ty
    repo: RepoContext = ctx.repo

    # Get PR details - either from explicit PR number or current branch
    user_output("Checking PR status...")
    if pr_number is not None:
        # Direct PR lookup by number
        pr = ctx.github.get_pr(repo.root, pr_number)
        Ensure.invariant(
            not isinstance(pr, PRNotFound),
            f"No pull request found with number #{pr_number}",
        )
        # Type narrowing after invariant check
        assert not isinstance(pr, PRNotFound)
        branch_name = pr.head_ref_name
    else:
        # Get PR from current branch (original behavior)
        current_branch = Ensure.not_none(
            ctx.git.get_current_branch(ctx.cwd),
            "Not on a branch - checkout a branch or provide a PR number",
        )

        pr = ctx.github.get_pr_for_branch(repo.root, current_branch)
        Ensure.invariant(
            not isinstance(pr, PRNotFound),
            f"No pull request found for branch '{current_branch}'",
        )
        # Type narrowing after invariant check
        assert not isinstance(pr, PRNotFound)
        branch_name = current_branch

    Ensure.invariant(
        pr.state == "OPEN",
        f"Cannot rebase {pr.state} PR - only OPEN PRs can be rebased",
    )

    resolved_pr_number = pr.number
    base_branch = pr.base_ref_name

    user_output(f"PR #{resolved_pr_number}: {click.style(pr.title, fg='cyan')} ({pr.state})")
    user_output(f"Base branch: {base_branch}")
    user_output("")

    # Build workflow inputs
    inputs: dict[str, str] = {
        "branch_name": branch_name,
        "base_branch": base_branch,
        "pr_number": str(resolved_pr_number),
        "squash": "false" if no_squash else "true",
    }
    if model_name is not None:
        inputs["model_name"] = model_name

    # Trigger workflow
    user_output("Triggering rebase workflow...")
    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=REBASE_WORKFLOW_NAME,
        inputs=inputs,
    )
    user_output(click.style("✓", fg="green") + " Workflow triggered")

    maybe_update_plan_dispatch_metadata(ctx, repo, branch_name, run_id)

    user_output("")

    # Build run URL
    # Get owner/repo from the PR details
    run_url = f"https://github.com/{pr.owner}/{pr.repo}/actions/runs/{run_id}"
    user_output(f"Run URL: {click.style(run_url, fg='cyan')}")
