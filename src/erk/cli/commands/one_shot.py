"""Command to dispatch a task for fully autonomous remote execution.

No local planning — the remote Claude explores the codebase, plans the change,
implements it, and creates a PR.

Usage:
    erk one-shot "fix the import in config.py"
    erk one-shot "add type hints to utils.py" --model opus
    erk one-shot "fix the typo in README.md" --dry-run
"""

import click

from erk.cli.commands.implement_shared import normalize_model_name
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext, NoRepoSentinel, RepoContext
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.time.abc import Time
from erk_shared.naming import format_branch_timestamp_suffix, sanitize_worktree_name
from erk_shared.output.output import user_output

ONE_SHOT_WORKFLOW = "one-shot.yml"


def _generate_branch_name(instruction: str, *, time: Time) -> str:
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


@click.command("one-shot", hidden=True)
@click.argument("instruction")
@click.option(
    "-m",
    "--model",
    type=str,
    default=None,
    help="Model to use (haiku/h, sonnet/s, opus/o)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would happen without executing",
)
@click.pass_obj
def one_shot(
    ctx: ErkContext,
    *,
    instruction: str,
    model: str | None,
    dry_run: bool,
) -> None:
    """Submit a task for fully autonomous remote execution.

    Creates a branch, draft PR, and dispatches a GitHub Actions workflow
    where Claude autonomously explores, plans, implements, and submits.

    Examples:

    \b
      erk one-shot "fix the import in config.py"
      erk one-shot "add type hints to utils.py" --model opus
      erk one-shot "fix the typo in README.md" --dry-run
    """
    # Validate instruction is non-empty
    Ensure.invariant(
        len(instruction.strip()) > 0,
        "Instruction must not be empty",
    )

    # Normalize model name
    model = normalize_model_name(model)

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
    branch_name = _generate_branch_name(instruction, time=ctx.time)

    # Build PR title
    max_title_len = 60
    suffix = "..." if len(instruction) > max_title_len else ""
    pr_title = f"One-shot: {instruction[:max_title_len]}{suffix}"

    if dry_run:
        user_output(
            click.style("Dry-run mode:", fg="cyan", bold=True) + " No changes will be made\n"
        )
        user_output(f"Instruction: {instruction}")
        user_output(f"Branch: {branch_name}")
        user_output(f"PR title: {pr_title}")
        user_output(f"Base branch: {trunk}")
        user_output(f"Submitted by: {submitted_by}")
        if model is not None:
            user_output(f"Model: {model}")
        user_output(f"Workflow: {ONE_SHOT_WORKFLOW}")
        return

    # Create branch from trunk
    user_output("Creating branch...")
    ctx.git.branch.create_branch(repo.root, branch_name, trunk, force=False)
    ctx.git.branch.checkout_branch(repo.root, branch_name)

    # Make empty commit
    ctx.git.commit.commit(repo.root, f"One-shot: {instruction}")

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
        f"Autonomous one-shot execution.\n\n**Instruction:** {instruction}",
        trunk,
        draft=True,
    )
    user_output(f"Created draft PR #{pr_number}")

    # Build workflow inputs
    inputs: dict[str, str] = {
        "instruction": instruction,
        "branch_name": branch_name,
        "pr_number": str(pr_number),
        "submitted_by": submitted_by,
    }
    if model is not None:
        inputs["model_name"] = model

    # Trigger workflow
    user_output("Triggering one-shot workflow...")
    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=ONE_SHOT_WORKFLOW,
        inputs=inputs,
    )

    # Display results
    user_output("")
    user_output(click.style("Done!", fg="green", bold=True))
    if repo.github is not None:
        pr_url = f"https://github.com/{repo.github.owner}/{repo.github.repo}/pull/{pr_number}"
        run_url = f"https://github.com/{repo.github.owner}/{repo.github.repo}/actions/runs/{run_id}"
        user_output(f"PR: {click.style(pr_url, fg='cyan')}")
        user_output(f"Run: {click.style(run_url, fg='cyan')}")
    else:
        user_output(f"PR #{pr_number} created, workflow run {run_id} triggered")
