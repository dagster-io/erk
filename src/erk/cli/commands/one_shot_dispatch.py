"""Shared dispatch logic for one-shot autonomous execution.

Extracts the branch-create/push/PR/workflow-trigger sequence into reusable
pieces so both `erk one-shot` and `erk objective next-plan --one-shot` can
dispatch tasks through the same CI workflow.
"""

from dataclasses import dataclass

import click

from erk.cli.ensure import Ensure
from erk.core.context import ErkContext, NoRepoSentinel, RepoContext
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.time.abc import Time
from erk_shared.naming import format_branch_timestamp_suffix, sanitize_worktree_name
from erk_shared.output.output import user_output

ONE_SHOT_WORKFLOW = "one-shot.yml"


@dataclass(frozen=True)
class OneShotDispatchParams:
    """Parameters for dispatching a one-shot workflow."""

    instruction: str
    model: str | None
    extra_workflow_inputs: dict[str, str]


@dataclass(frozen=True)
class OneShotDispatchResult:
    """Result of a successful one-shot dispatch."""

    pr_number: int
    run_id: str
    branch_name: str


def generate_branch_name(instruction: str, *, time: Time) -> str:
    """Generate a branch name from the instruction.

    Format: oneshot-{slug}-{MM-DD-HHMM}

    Args:
        instruction: The task description
        time: Time gateway for deterministic timestamps

    Returns:
        Branch name string
    """
    slug = sanitize_worktree_name(instruction)
    # Truncate slug to leave room for prefix and timestamp
    prefix = "oneshot-"
    max_slug_len = 31 - len(prefix)
    if len(slug) > max_slug_len:
        slug = slug[:max_slug_len].rstrip("-")
    timestamp = format_branch_timestamp_suffix(time.now())
    return f"{prefix}{slug}{timestamp}"


def dispatch_one_shot(
    ctx: ErkContext,
    *,
    params: OneShotDispatchParams,
    dry_run: bool,
) -> OneShotDispatchResult | None:
    """Execute the full dispatch sequence for a one-shot workflow.

    Creates branch, pushes, creates draft PR, triggers workflow,
    then restores original branch. In dry-run mode, prints what
    would happen without executing.

    Args:
        ctx: Erk context with git/github gateways
        params: Dispatch parameters
        dry_run: If True, print preview without executing

    Returns:
        OneShotDispatchResult with pr_number, run_id, branch_name,
        or None in dry-run mode
    """
    # Validate we're in a git repo
    Ensure.invariant(
        not isinstance(ctx.repo, NoRepoSentinel),
        "Not in a git repository",
    )
    assert not isinstance(ctx.repo, NoRepoSentinel)
    repo: RepoContext = ctx.repo

    # Validate GitHub authentication
    Ensure.gh_authenticated(ctx)

    # Get GitHub username
    _, username, _ = ctx.github.check_auth_status()
    submitted_by = username or "unknown"

    # Detect trunk branch
    trunk = ctx.git.branch.detect_trunk_branch(repo.root)

    # Generate branch name
    branch_name = generate_branch_name(params.instruction, time=ctx.time)

    # Build PR title
    max_title_len = 60
    suffix = "..." if len(params.instruction) > max_title_len else ""
    pr_title = f"One-shot: {params.instruction[:max_title_len]}{suffix}"

    if dry_run:
        user_output(
            click.style("Dry-run mode:", fg="cyan", bold=True) + " No changes will be made\n"
        )
        user_output(f"Instruction: {params.instruction}")
        user_output(f"Branch: {branch_name}")
        user_output(f"PR title: {pr_title}")
        user_output(f"Base branch: {trunk}")
        user_output(f"Submitted by: {submitted_by}")
        if params.model is not None:
            user_output(f"Model: {params.model}")
        user_output(f"Workflow: {ONE_SHOT_WORKFLOW}")
        if params.extra_workflow_inputs:
            for key, value in params.extra_workflow_inputs.items():
                user_output(f"Extra input: {key}={value}")
        return None

    # Save current branch for restoration after workflow trigger
    original_branch = ctx.git.branch.get_current_branch(repo.root)
    if original_branch is None:
        user_output(
            click.style("Error: ", fg="red")
            + "Not on a branch (detached HEAD state). Cannot submit from here."
        )
        raise SystemExit(1)

    # Create branch from trunk
    user_output("Creating branch...")
    ctx.git.branch.create_branch(repo.root, branch_name, trunk, force=False)

    try:
        ctx.branch_manager.checkout_branch(repo.root, branch_name)

        # Make empty commit
        ctx.git.commit.commit(repo.root, f"One-shot: {params.instruction}")

        # Push to remote
        user_output("Pushing to remote...")
        push_result = ctx.git.remote.push_to_remote(
            repo.root, "origin", branch_name, set_upstream=True, force=False
        )
        if isinstance(push_result, PushError):
            Ensure.invariant(False, f"Failed to push branch: {push_result.message}")

        # Create draft PR
        user_output("Creating draft PR...")
        pr_number = ctx.github.create_pr(
            repo.root,
            branch_name,
            pr_title,
            f"Autonomous one-shot execution.\n\n**Instruction:** {params.instruction}",
            trunk,
            draft=True,
        )
        user_output(f"Created draft PR #{pr_number}")

        # Build workflow inputs
        inputs: dict[str, str] = {
            "instruction": params.instruction,
            "branch_name": branch_name,
            "pr_number": str(pr_number),
            "submitted_by": submitted_by,
        }
        if params.model is not None:
            inputs["model_name"] = params.model

        # Merge extra workflow inputs
        inputs.update(params.extra_workflow_inputs)

        # Trigger workflow
        user_output("Triggering one-shot workflow...")
        run_id = ctx.github.trigger_workflow(
            repo_root=repo.root,
            workflow=ONE_SHOT_WORKFLOW,
            inputs=inputs,
        )

        # Restore original branch after successful workflow trigger
        ctx.branch_manager.checkout_branch(repo.root, original_branch)

        # Display results
        user_output("")
        user_output(click.style("Done!", fg="green", bold=True))
        if repo.github is not None:
            pr_url = f"https://github.com/{repo.github.owner}/{repo.github.repo}/pull/{pr_number}"
            run_url = (
                f"https://github.com/{repo.github.owner}/{repo.github.repo}/actions/runs/{run_id}"
            )
            user_output(f"PR: {click.style(pr_url, fg='cyan')}")
            user_output(f"Run: {click.style(run_url, fg='cyan')}")
        else:
            user_output(f"PR #{pr_number} created, workflow run {run_id} triggered")

        return OneShotDispatchResult(
            pr_number=pr_number,
            run_id=run_id,
            branch_name=branch_name,
        )
    finally:
        # Always ensure we're back on original branch, even on error
        current = ctx.git.branch.get_current_branch(repo.root)
        if current != original_branch:
            user_output(click.style("Restoring original branch...", fg="yellow"))
            ctx.branch_manager.checkout_branch(repo.root, original_branch)
