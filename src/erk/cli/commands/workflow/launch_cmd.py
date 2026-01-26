"""Trigger GitHub Actions workflows via unified interface.

Usage examples:
    erk workflow launch objective-reconcile
    erk workflow launch objective-reconcile --objective 123 --dry-run
    erk workflow launch pr-address --pr 456
    erk workflow launch pr-fix-conflicts --pr 456
    erk workflow launch pr-fix-conflicts --pr 456 --no-squash
    erk workflow launch plan-implement --issue 789
    erk workflow launch learn --issue 789
"""

import click

from erk.cli.commands.pr.metadata_helpers import maybe_update_plan_dispatch_metadata
from erk.cli.constants import WORKFLOW_COMMAND_MAP
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.github.types import PRNotFound
from erk_shared.output.output import user_output


def _get_workflow_file(workflow_name: str) -> str:
    """Get the actual workflow filename for a command name.

    Args:
        workflow_name: Command-friendly workflow name (e.g., "pr-fix-conflicts")

    Returns:
        Actual workflow filename (e.g., "erk-rebase.yml")

    Raises:
        click.UsageError: If workflow name is not recognized
    """
    if workflow_name not in WORKFLOW_COMMAND_MAP:
        available = ", ".join(sorted(WORKFLOW_COMMAND_MAP.keys()))
        raise click.UsageError(
            f"Unknown workflow '{workflow_name}'. Available workflows: {available}"
        )
    return WORKFLOW_COMMAND_MAP[workflow_name]


def _trigger_pr_fix_conflicts(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    pr_number: int | None,
    no_squash: bool,
    model: str | None,
) -> None:
    """Trigger pr-fix-conflicts workflow."""
    # Get PR details - either from explicit PR number or current branch
    user_output("Checking PR status...")
    if pr_number is not None:
        pr = ctx.github.get_pr(repo.root, pr_number)
        Ensure.invariant(
            not isinstance(pr, PRNotFound),
            f"No pull request found with number #{pr_number}",
        )
        assert not isinstance(pr, PRNotFound)
        branch_name = pr.head_ref_name
    else:
        current_branch = Ensure.not_none(
            ctx.git.get_current_branch(ctx.cwd),
            "Not on a branch - checkout a branch or provide --pr",
        )
        pr = ctx.github.get_pr_for_branch(repo.root, current_branch)
        Ensure.invariant(
            not isinstance(pr, PRNotFound),
            f"No pull request found for branch '{current_branch}'",
        )
        assert not isinstance(pr, PRNotFound)
        branch_name = current_branch
        pr_number = pr.number

    Ensure.invariant(
        pr.state == "OPEN",
        f"Cannot rebase {pr.state} PR - only OPEN PRs can be rebased",
    )

    user_output(f"PR #{pr_number}: {click.style(pr.title, fg='cyan')} ({pr.state})")
    user_output(f"Base branch: {pr.base_ref_name}")
    user_output("")

    # Build workflow inputs
    inputs: dict[str, str] = {
        "branch_name": branch_name,
        "base_branch": pr.base_ref_name,
        "pr_number": str(pr_number),
        "squash": "false" if no_squash else "true",
    }
    if model is not None:
        inputs["model_name"] = model

    # Trigger workflow
    user_output("Triggering pr-fix-conflicts workflow...")
    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=_get_workflow_file("pr-fix-conflicts"),
        inputs=inputs,
    )
    user_output(click.style("\u2713", fg="green") + " Workflow triggered")

    maybe_update_plan_dispatch_metadata(ctx, repo, branch_name, run_id)

    user_output("")
    run_url = f"https://github.com/{pr.owner}/{pr.repo}/actions/runs/{run_id}"
    user_output(f"Run URL: {click.style(run_url, fg='cyan')}")


def _trigger_pr_address(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    pr_number: int,
    model: str | None,
) -> None:
    """Trigger pr-address workflow."""
    user_output("Checking PR status...")
    pr = ctx.github.get_pr(repo.root, pr_number)
    Ensure.invariant(
        not isinstance(pr, PRNotFound),
        f"No pull request found with number #{pr_number}",
    )
    assert not isinstance(pr, PRNotFound)
    branch_name = pr.head_ref_name

    Ensure.invariant(
        pr.state == "OPEN",
        f"Cannot address comments on {pr.state} PR - only OPEN PRs can be addressed",
    )

    user_output(f"PR #{pr_number}: {click.style(pr.title, fg='cyan')} ({pr.state})")
    user_output("")

    # Build workflow inputs
    inputs: dict[str, str] = {
        "pr_number": str(pr_number),
    }
    if model is not None:
        inputs["model_name"] = model

    # Trigger workflow
    user_output("Triggering pr-address workflow...")
    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=_get_workflow_file("pr-address"),
        inputs=inputs,
    )
    user_output(click.style("\u2713", fg="green") + " Workflow triggered")

    maybe_update_plan_dispatch_metadata(ctx, repo, branch_name, run_id)

    user_output("")
    run_url = f"https://github.com/{pr.owner}/{pr.repo}/actions/runs/{run_id}"
    user_output(f"Run URL: {click.style(run_url, fg='cyan')}")


def _trigger_objective_reconcile(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    objective: int,
    dry_run: bool,
) -> None:
    """Trigger objective-reconcile workflow."""
    user_output(f"Triggering objective-reconcile workflow for objective #{objective}...")

    inputs: dict[str, str] = {
        "objective": str(objective),
    }
    if dry_run:
        inputs["dry_run"] = "true"

    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=_get_workflow_file("objective-reconcile"),
        inputs=inputs,
    )
    user_output(click.style("\u2713", fg="green") + " Workflow triggered")

    user_output("")
    # Get repo slug from RepoContext's github field
    if repo.github is not None:
        repo_slug = f"{repo.github.owner}/{repo.github.repo}"
    else:
        repo_slug = "unknown/unknown"
    run_url = f"https://github.com/{repo_slug}/actions/runs/{run_id}"
    user_output(f"Run URL: {click.style(run_url, fg='cyan')}")


def _trigger_learn(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    issue: int,
) -> None:
    """Trigger learn workflow."""
    user_output(f"Triggering learn workflow for issue #{issue}...")

    inputs: dict[str, str] = {
        "issue_number": str(issue),
    }

    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=_get_workflow_file("learn"),
        inputs=inputs,
    )
    user_output(click.style("\u2713", fg="green") + " Workflow triggered")

    user_output("")
    # Get repo slug from RepoContext's github field
    if repo.github is not None:
        repo_slug = f"{repo.github.owner}/{repo.github.repo}"
    else:
        repo_slug = "unknown/unknown"
    run_url = f"https://github.com/{repo_slug}/actions/runs/{run_id}"
    user_output(f"Run URL: {click.style(run_url, fg='cyan')}")


def _trigger_plan_implement(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    issue: int,
    model: str | None,
) -> None:
    """Trigger plan-implement workflow.

    Note: This is a simplified trigger - the full submission flow
    (branch creation, PR creation, etc.) is handled by `erk plan submit`.
    This command only triggers the workflow directly.
    """
    raise click.UsageError(
        "Use 'erk plan submit' instead of 'erk workflow launch plan-implement'.\n"
        "The plan-implement workflow requires branch and PR setup that "
        "'erk plan submit' handles automatically."
    )


@click.command("launch")
@click.argument("workflow_name", type=str)
@click.option(
    "--pr",
    "pr_number",
    type=int,
    help="PR number (required for pr-fix-conflicts and pr-address)",
)
@click.option(
    "--issue",
    "issue_number",
    type=int,
    help="Issue number (required for learn)",
)
@click.option(
    "--objective",
    "objective_number",
    type=int,
    help="Objective issue number (required for objective-reconcile)",
)
@click.option(
    "--no-squash",
    is_flag=True,
    help="Skip squashing commits before rebase (pr-fix-conflicts only)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview actions without executing (objective-reconcile only)",
)
@click.option(
    "--model",
    type=str,
    help="Claude model to use (for workflows that support it)",
)
@click.pass_obj
def workflow_launch(
    ctx: ErkContext,
    workflow_name: str,
    *,
    pr_number: int | None,
    issue_number: int | None,
    objective_number: int | None,
    no_squash: bool,
    dry_run: bool,
    model: str | None,
) -> None:
    """Trigger a GitHub Actions workflow.

    WORKFLOW_NAME is the workflow to trigger. Available workflows:

    \b
      pr-fix-conflicts    - Rebase PR with AI-powered conflict resolution
      pr-address          - Address PR review comments remotely
      objective-reconcile - Reconcile auto-advance objectives
      learn               - Extract insights from a plan issue

    Examples:

    \b
      # Fix conflicts on current branch's PR
      erk workflow launch pr-fix-conflicts

    \b
      # Fix conflicts on specific PR
      erk workflow launch pr-fix-conflicts --pr 123

    \b
      # Address PR review comments
      erk workflow launch pr-address --pr 456

    \b
      # Reconcile all objectives
      erk workflow launch objective-reconcile

    \b
      # Reconcile specific objective in dry-run mode
      erk workflow launch objective-reconcile --objective 789 --dry-run

    \b
      # Trigger learn for a plan issue
      erk workflow launch learn --issue 123

    Requirements:

    \b
    - GitHub CLI (gh) must be authenticated
    - Required GitHub Actions secrets must be configured
    """
    # Validate preconditions
    Ensure.gh_authenticated(ctx)
    Ensure.invariant(
        not isinstance(ctx.repo, NoRepoSentinel),
        "Not in a git repository",
    )
    assert not isinstance(ctx.repo, NoRepoSentinel)
    repo: RepoContext = ctx.repo

    # Validate workflow name
    _ = _get_workflow_file(workflow_name)  # Raises UsageError if invalid

    # Dispatch to workflow-specific handler
    if workflow_name == "pr-fix-conflicts":
        _trigger_pr_fix_conflicts(
            ctx,
            repo,
            pr_number=pr_number,
            no_squash=no_squash,
            model=model,
        )
    elif workflow_name == "pr-address":
        Ensure.invariant(
            pr_number is not None,
            "--pr is required for pr-address workflow",
        )
        assert pr_number is not None
        _trigger_pr_address(ctx, repo, pr_number=pr_number, model=model)
    elif workflow_name == "objective-reconcile":
        Ensure.invariant(
            objective_number is not None,
            "--objective is required for objective-reconcile workflow. "
            "For sweep mode, use GitHub Actions UI or wait for scheduled run.",
        )
        assert objective_number is not None
        _trigger_objective_reconcile(
            ctx,
            repo,
            objective=objective_number,
            dry_run=dry_run,
        )
    elif workflow_name == "learn":
        Ensure.invariant(
            issue_number is not None,
            "--issue is required for learn workflow",
        )
        assert issue_number is not None
        _trigger_learn(ctx, repo, issue=issue_number)
    elif workflow_name == "plan-implement":
        _trigger_plan_implement(ctx, repo, issue=issue_number or 0, model=model)
    else:
        # Should never reach here due to _get_workflow_file validation
        raise click.UsageError(f"Unknown workflow: {workflow_name}")
