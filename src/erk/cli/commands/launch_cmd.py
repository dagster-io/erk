"""Trigger GitHub Actions workflows via unified interface.

Usage examples:
    erk launch pr-address --pr 456
    erk launch pr-fix-conflicts --pr 456
    erk launch pr-fix-conflicts --pr 456 --no-squash
    erk launch plan-implement --issue 789
    erk launch learn --issue 789
    erk launch one-shot --pr 456 --prompt "fix the auth bug"
    erk launch one-shot --pr 456 -f prompt.md
"""

from pathlib import Path

import click

from erk.cli.commands.pr.metadata_helpers import maybe_update_plan_dispatch_metadata
from erk.cli.constants import WORKFLOW_COMMAND_MAP
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.output.output import user_output


def _trigger_workflow(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    workflow_name: str,
    inputs: dict[str, str],
    branch_name: str,
    pr_owner: str,
    pr_repo: str,
) -> None:
    """Trigger a workflow and report the run URL."""
    workflow_file = _get_workflow_file(workflow_name)
    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=workflow_file,
        inputs=inputs,
        ref=None,
    )
    user_output(click.style("\u2713", fg="green") + " Workflow triggered")

    maybe_update_plan_dispatch_metadata(ctx, repo, branch_name, run_id)

    user_output("")
    run_url = f"https://github.com/{pr_owner}/{pr_repo}/actions/runs/{run_id}"
    user_output(f"Run URL: {click.style(run_url, fg='cyan')}")


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
            ctx.git.branch.get_current_branch(ctx.cwd),
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
    plan_id = ctx.plan_backend.resolve_plan_id_for_branch(repo.root, branch_name)
    inputs: dict[str, str] = {
        "branch_name": branch_name,
        "base_branch": pr.base_ref_name,
        "pr_number": str(pr_number),
        "squash": "false" if no_squash else "true",
        "plan_number": plan_id if plan_id is not None else "",
    }
    if model is not None:
        inputs["model_name"] = model

    # Trigger workflow
    user_output("Triggering pr-fix-conflicts workflow...")
    _trigger_workflow(
        ctx,
        repo,
        workflow_name="pr-fix-conflicts",
        inputs=inputs,
        branch_name=branch_name,
        pr_owner=pr.owner,
        pr_repo=pr.repo,
    )


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
    plan_id = ctx.plan_backend.resolve_plan_id_for_branch(repo.root, branch_name)
    inputs: dict[str, str] = {
        "pr_number": str(pr_number),
        "plan_number": plan_id if plan_id is not None else "",
    }
    if model is not None:
        inputs["model_name"] = model

    # Trigger workflow
    user_output("Triggering pr-address workflow...")
    _trigger_workflow(
        ctx,
        repo,
        workflow_name="pr-address",
        inputs=inputs,
        branch_name=branch_name,
        pr_owner=pr.owner,
        pr_repo=pr.repo,
    )


def _trigger_pr_rewrite(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    pr_number: int,
    model: str | None,
) -> None:
    """Trigger pr-rewrite workflow."""
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
        f"Cannot rewrite {pr.state} PR - only OPEN PRs can be rewritten",
    )

    user_output(f"PR #{pr_number}: {click.style(pr.title, fg='cyan')} ({pr.state})")
    user_output(f"Base branch: {pr.base_ref_name}")
    user_output("")

    # Build workflow inputs
    plan_id = ctx.plan_backend.resolve_plan_id_for_branch(repo.root, branch_name)
    inputs: dict[str, str] = {
        "branch_name": branch_name,
        "base_branch": pr.base_ref_name,
        "pr_number": str(pr_number),
        "plan_number": plan_id if plan_id is not None else "",
    }
    if model is not None:
        inputs["model_name"] = model

    # Trigger workflow
    user_output("Triggering pr-rewrite workflow...")
    _trigger_workflow(
        ctx,
        repo,
        workflow_name="pr-rewrite",
        inputs=inputs,
        branch_name=branch_name,
        pr_owner=pr.owner,
        pr_repo=pr.repo,
    )


def _trigger_learn(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    issue: int,
) -> None:
    """Trigger learn workflow."""
    user_output(f"Triggering learn workflow for plan #{issue}...")

    inputs: dict[str, str] = {
        "plan_number": str(issue),
    }

    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=_get_workflow_file("learn"),
        inputs=inputs,
        ref=None,
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
    (branch creation, PR creation, etc.) is handled by `erk pr dispatch`.
    This command only triggers the workflow directly.
    """
    raise click.UsageError(
        "Use 'erk pr dispatch' instead of 'erk workflow launch plan-implement'.\n"
        "The plan-implement workflow requires branch and PR setup that "
        "'erk pr dispatch' handles automatically."
    )


def _trigger_one_shot(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    pr_number: int,
    prompt: str,
    model: str | None,
) -> None:
    """Trigger one-shot workflow against an existing PR."""
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
        f"Cannot run one-shot on {pr.state} PR - only OPEN PRs can be targeted",
    )

    user_output(f"PR #{pr_number}: {click.style(pr.title, fg='cyan')} ({pr.state})")
    user_output("")

    # Get submitter identity
    _, username, _ = ctx.github.check_auth_status()
    submitted_by = username or "unknown"

    # Build workflow inputs
    inputs: dict[str, str] = {
        "prompt": prompt,
        "branch_name": branch_name,
        "pr_number": str(pr_number),
        "submitted_by": submitted_by,
        "modify_existing": "true",
    }
    if model is not None:
        inputs["model_name"] = model

    # Trigger workflow
    user_output("Triggering one-shot workflow...")
    _trigger_workflow(
        ctx,
        repo,
        workflow_name="one-shot",
        inputs=inputs,
        branch_name=branch_name,
        pr_owner=pr.owner,
        pr_repo=pr.repo,
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
    "--plan",
    "plan_number",
    type=int,
    help="Plan number (required for learn)",
)
@click.option(
    "--no-squash",
    is_flag=True,
    help="Skip squashing commits before rebase (pr-fix-conflicts only)",
)
@click.option(
    "--model",
    type=str,
    help="Claude model to use (for workflows that support it)",
)
@click.option(
    "--prompt",
    type=str,
    default=None,
    help="Prompt text for one-shot workflow",
)
@click.option(
    "-f",
    "--file",
    "file_path",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Read prompt from a file (one-shot only)",
)
@click.pass_obj
def launch(
    ctx: ErkContext,
    workflow_name: str,
    *,
    pr_number: int | None,
    plan_number: int | None,
    no_squash: bool,
    model: str | None,
    prompt: str | None,
    file_path: str | None,
) -> None:
    """Trigger a GitHub Actions workflow.

    WORKFLOW_NAME is the workflow to trigger. Available workflows:

    \b
      pr-fix-conflicts    - Rebase PR with AI-powered conflict resolution
      pr-address          - Address PR review comments remotely
      pr-rewrite          - Rebase PR and regenerate AI PR summary
      learn               - Extract insights from a plan issue
      one-shot            - Run one-shot workflow against an existing PR

    Examples:

    \b
      # Fix conflicts on current branch's PR
      erk launch pr-fix-conflicts

    \b
      # Fix conflicts on specific PR
      erk launch pr-fix-conflicts --pr 123

    \b
      # Address PR review comments
      erk launch pr-address --pr 456

    \b
      # Trigger learn for a plan issue
      erk launch learn --issue 123

    \b
      # Run one-shot against a PR with inline prompt
      erk launch one-shot --pr 456 --prompt "fix the auth bug"

    \b
      # Run one-shot against a PR with prompt from file
      erk launch one-shot --pr 456 -f prompt.md

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
    elif workflow_name == "pr-rewrite":
        Ensure.invariant(
            pr_number is not None,
            "--pr is required for pr-rewrite workflow",
        )
        assert pr_number is not None
        _trigger_pr_rewrite(ctx, repo, pr_number=pr_number, model=model)
    elif workflow_name == "learn":
        Ensure.invariant(
            plan_number is not None,
            "--plan is required for learn workflow",
        )
        assert plan_number is not None
        _trigger_learn(ctx, repo, issue=plan_number)
    elif workflow_name == "one-shot":
        Ensure.invariant(
            pr_number is not None,
            "--pr is required for one-shot workflow",
        )
        assert pr_number is not None
        # Resolve prompt from --prompt or --file (mutually exclusive)
        Ensure.invariant(
            not (prompt is not None and file_path is not None),
            "--prompt and --file are mutually exclusive",
        )
        resolved_prompt: str | None = prompt
        if file_path is not None:
            resolved_prompt = Path(file_path).read_text(encoding="utf-8").strip()
        Ensure.invariant(
            resolved_prompt is not None and len(resolved_prompt) > 0,
            "--prompt or --file is required for one-shot workflow",
        )
        assert resolved_prompt is not None
        _trigger_one_shot(ctx, repo, pr_number=pr_number, prompt=resolved_prompt, model=model)
    elif workflow_name == "plan-implement":
        _trigger_plan_implement(ctx, repo, issue=plan_number or 0, model=model)
    else:
        # Should never reach here due to _get_workflow_file validation
        raise click.UsageError(f"Unknown workflow: {workflow_name}")
