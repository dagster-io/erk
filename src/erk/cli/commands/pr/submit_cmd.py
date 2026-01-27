"""Submit current branch as a pull request.

Unified PR submission with two-layer architecture:
1. Core layer: git push + gh pr create (works without Graphite)
2. Graphite layer: Optional enhancement via gt submit

The workflow:
1. Core submit: git push + gh pr create
2. Get diff for AI: GitHub API
3. Fetch plan context: Get plan from linked erk-plan issue
4. Generate: AI-generated commit message via Claude CLI
5. Graphite enhance: Optional gt submit for stack metadata
6. Finalize: Update PR with AI-generated title/body
"""

import os
import uuid
from pathlib import Path

import click

from erk.cli.commands.pr.shared import (
    render_progress,
    require_claude_available,
    run_commit_message_generation,
)
from erk.core.commit_message_generator import CommitMessageGenerator
from erk.core.context import ErkContext
from erk.core.plan_context_provider import PlanContextProvider
from erk_shared.gateway.github.parsing import parse_git_remote_url
from erk_shared.gateway.github.types import GitHubRepoId, PRNotFound
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.gt.operations.finalize import execute_finalize
from erk_shared.gateway.gt.types import FinalizeResult, PostAnalysisError
from erk_shared.gateway.pr.diff_extraction import execute_diff_extraction
from erk_shared.gateway.pr.graphite_enhance import (
    execute_graphite_enhance,
    should_enhance_with_graphite,
)
from erk_shared.gateway.pr.submit import execute_core_submit
from erk_shared.gateway.pr.types import (
    CoreSubmitError,
    CoreSubmitResult,
    GraphiteEnhanceError,
    GraphiteEnhanceResult,
    GraphiteSkipped,
)

# Set to False to disable polling for PR in Graphite cache after submission.
# This feature ensures the status line can immediately display the PR number.
ENABLE_PR_CACHE_POLLING = True

# Polling configuration for PR cache
PR_CACHE_POLL_MAX_WAIT_SECONDS = 10.0
PR_CACHE_POLL_INTERVAL_SECONDS = 0.5


def _wait_for_pr_in_cache(
    ctx: ErkContext,
    repo_root: Path,
    branch: str,
    *,
    max_wait_seconds: float,
    poll_interval: float,
) -> bool:
    """Wait for PR to appear in Graphite cache after submission.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        branch: Branch name to check
        max_wait_seconds: Maximum time to wait
        poll_interval: Time between checks

    Returns:
        True if PR found in cache, False if timeout
    """
    start = ctx.time.now()
    while (ctx.time.now() - start).total_seconds() < max_wait_seconds:
        prs = ctx.graphite.get_prs_from_graphite(ctx.git, repo_root)
        if branch in prs:
            return True
        ctx.time.sleep(poll_interval)
    return False


@click.command("submit")
@click.option("--debug", is_flag=True, help="Show diagnostic output")
@click.option(
    "--no-graphite",
    is_flag=True,
    help="Skip Graphite enhancement (use git + gh only)",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Force push (use when branch has diverged from remote)",
)
@click.pass_obj
def pr_submit(ctx: ErkContext, debug: bool, no_graphite: bool, force: bool) -> None:
    """Submit PR with AI-generated commit message.

    Uses a two-layer architecture:
    - Core layer (always): git push + gh pr create
    - Graphite layer (optional): gt submit for stack metadata

    The core layer works without Graphite installed. When Graphite is
    available and the branch is tracked, it will enhance the PR with
    stack metadata unless --no-graphite is specified.

    Examples:

    \b
      # Submit PR (with Graphite if available)
      erk pr submit

      # Submit PR without Graphite enhancement
      erk pr submit --no-graphite

      # Force push when branch has diverged
      erk pr submit -f
    """
    _execute_pr_submit(ctx, debug=debug, use_graphite=not no_graphite, force=force)


def _execute_pr_submit(ctx: ErkContext, debug: bool, use_graphite: bool, force: bool) -> None:
    """Execute PR submission with positively-named parameters."""
    # Verify Claude is available (needed for commit message generation)
    require_claude_available(ctx)

    click.echo(click.style("🚀 Submitting PR...", bold=True))
    click.echo("")

    cwd = Path.cwd()
    session_id = os.environ.get("SESSION_ID", str(uuid.uuid4()))

    # Determine if Graphite will handle the push (to avoid tracking divergence)
    graphite_handles_push = False
    if use_graphite:
        check_result = should_enhance_with_graphite(ctx, cwd)
        graphite_handles_push = check_result.should_enhance

    # Branch on flow: Graphite-first vs standard
    if graphite_handles_push:
        # Graphite-first flow: gt submit handles push + PR creation
        pr_number, base_branch, graphite_url = _run_graphite_first_flow(ctx, cwd, debug, force)
    else:
        # Standard flow: core submit handles push + PR creation
        click.echo(click.style("Phase 1: Creating or Updating PR", bold=True))
        core_result = _run_core_submit(ctx, cwd, debug, force)

        if isinstance(core_result, CoreSubmitError):
            raise click.ClickException(core_result.message)

        action = "created" if core_result.was_created else "found (already exists)"
        click.echo(click.style(f"   PR #{core_result.pr_number} {action}", fg="green"))
        click.echo("")

        pr_number = core_result.pr_number
        base_branch = core_result.base_branch
        graphite_url = None

        # Standard flow: Graphite enhancement happens later (Phase 4)
        # This handles the case where use_graphite=True but branch isn't tracked yet

    # Phase 2: Get diff for AI
    click.echo(click.style("Phase 2: Getting diff", bold=True))
    diff_file = _run_diff_extraction(
        ctx,
        cwd=cwd,
        pr_number=pr_number,
        session_id=session_id,
        base_branch=base_branch,
        debug=debug,
    )

    if diff_file is None:
        raise click.ClickException("Failed to extract diff for AI analysis")

    click.echo("")

    # Get branch info for AI context
    repo_root = ctx.git.get_repository_root(cwd)
    current_branch = ctx.git.branch.get_current_branch(cwd)
    if current_branch is None:
        raise click.ClickException("Not on a branch (detached HEAD state)")
    trunk_branch = ctx.git.branch.detect_trunk_branch(repo_root)

    # Get parent branch (Graphite-aware, falls back to trunk)
    parent_branch = (
        ctx.branch_manager.get_parent_branch(Path(repo_root), current_branch) or trunk_branch
    )

    # Get commit messages for AI context (only from current branch)
    commit_messages = ctx.git.commit.get_commit_messages_since(cwd, parent_branch)

    # Phase 3: Fetch plan context
    click.echo(click.style("Phase 3: Fetching plan context", bold=True))
    plan_provider = PlanContextProvider(ctx.github_issues)
    plan_context = plan_provider.get_plan_context(
        repo_root=Path(repo_root),
        branch_name=current_branch,
    )
    if plan_context is not None:
        msg = f"   Incorporating plan from issue #{plan_context.issue_number}"
        click.echo(click.style(msg, fg="green"))
        if plan_context.objective_summary is not None:
            click.echo(click.style(f"   Linked to {plan_context.objective_summary}", fg="green"))
    else:
        click.echo(click.style("   No linked plan found", dim=True))
    click.echo("")

    # Phase 4: Generate commit message
    click.echo(click.style("Phase 4: Generating PR description", bold=True))
    msg_gen = CommitMessageGenerator(ctx.claude_executor)
    msg_result = run_commit_message_generation(
        generator=msg_gen,
        diff_file=diff_file,
        repo_root=Path(repo_root),
        current_branch=current_branch,
        parent_branch=parent_branch,
        commit_messages=commit_messages,
        plan_context=plan_context,
        debug=debug,
    )

    if not msg_result.success:
        raise click.ClickException(f"Failed to generate message: {msg_result.error_message}")

    click.echo("")

    # Phase 5: Graphite enhancement (only for standard flow, when branch not already tracked)
    # Skip if graphite_handles_push=True since gt submit already ran
    if use_graphite and not graphite_handles_push:
        click.echo(click.style("Phase 5: Graphite enhancement", bold=True))
        graphite_result = _run_graphite_enhance(
            ctx, cwd=cwd, pr_number=pr_number, debug=debug, force=force
        )

        if isinstance(graphite_result, GraphiteEnhanceResult):
            graphite_url = graphite_result.graphite_url
            click.echo("")
        elif isinstance(graphite_result, GraphiteSkipped):
            if debug:
                click.echo(click.style(f"   {graphite_result.message}", dim=True))
            click.echo("")
        elif isinstance(graphite_result, GraphiteEnhanceError):
            # Graphite errors are warnings, not fatal
            click.echo(click.style(f"   Warning: {graphite_result.message}", fg="yellow"))
            click.echo("")

    # Phase 6: Finalize (update PR metadata)
    click.echo(click.style("Phase 6: Updating PR metadata", bold=True))
    finalize_result = _run_finalize(
        ctx,
        cwd=cwd,
        pr_number=pr_number,
        title=msg_result.title or "Update",
        body=msg_result.body or "",
        diff_file=str(diff_file),
        debug=debug,
    )

    if isinstance(finalize_result, PostAnalysisError):
        raise click.ClickException(finalize_result.message)

    click.echo(click.style("   PR metadata updated", fg="green"))
    click.echo("")

    # Wait for PR to appear in Graphite cache for immediate status line display
    # This runs after all Graphite operations so the status line can show the PR number
    if ENABLE_PR_CACHE_POLLING and graphite_url is not None:
        _wait_for_pr_in_cache(
            ctx,
            Path(repo_root),
            current_branch,
            max_wait_seconds=PR_CACHE_POLL_MAX_WAIT_SECONDS,
            poll_interval=PR_CACHE_POLL_INTERVAL_SECONDS,
        )

    # Success output with clickable URL
    styled_url = click.style(finalize_result.pr_url, fg="cyan", underline=True)
    clickable_url = f"\033]8;;{finalize_result.pr_url}\033\\{styled_url}\033]8;;\033\\"
    click.echo(f"✅ {clickable_url}")

    # Show Graphite URL if available
    if graphite_url:
        styled_graphite = click.style(graphite_url, fg="cyan", underline=True)
        clickable_graphite = f"\033]8;;{graphite_url}\033\\{styled_graphite}\033]8;;\033\\"
        click.echo(f"📊 {clickable_graphite}")


def _run_graphite_first_flow(
    ctx: ErkContext,
    cwd: Path,
    debug: bool,
    force: bool,
) -> tuple[int, str, str]:
    """Run Graphite-first flow: gt submit handles push and PR creation.

    This flow is used when Graphite is authenticated and the branch is tracked.
    It avoids the "tracking divergence" issue by letting Graphite control the push.

    Returns:
        Tuple of (pr_number, base_branch, graphite_url)

    Raises:
        click.ClickException: If gt submit fails or PR not found after submit
    """
    repo_root = ctx.git.get_repository_root(cwd)
    branch_name = ctx.git.branch.get_current_branch(cwd)
    if branch_name is None:
        raise click.ClickException("Not on a branch (detached HEAD state)")

    # Commit any uncommitted changes first
    if ctx.git.has_uncommitted_changes(cwd):
        click.echo(click.style("   Committing uncommitted changes...", dim=True))
        ctx.git.commit.add_all(cwd)
        ctx.git.commit.commit(cwd, "WIP: Prepare for PR submission")

    # Phase 1: Run gt submit (handles push + PR creation)
    click.echo(click.style("Phase 1: Graphite Submit", bold=True))
    click.echo(click.style("   Running gt submit...", dim=True))
    try:
        ctx.graphite.submit_stack(
            repo_root,
            publish=True,
            restack=False,
            quiet=False,
            force=force,
        )
    except RuntimeError as e:
        raise click.ClickException(f"Graphite submit failed: {e}") from e
    click.echo(click.style("   Graphite submit completed", fg="green"))
    click.echo("")

    # Query GitHub to get PR info
    click.echo(click.style("   Getting PR info...", dim=True))
    pr_info = ctx.github.get_pr_for_branch(repo_root, branch_name)
    if isinstance(pr_info, PRNotFound):
        raise click.ClickException(
            f"PR not found for branch '{branch_name}' after gt submit.\n"
            "This may happen if gt submit didn't create a PR. Try running:\n"
            "  gt submit --publish"
        )

    # Get parent branch for base_branch
    trunk_branch = ctx.git.branch.detect_trunk_branch(repo_root)
    parent_branch = (
        ctx.branch_manager.get_parent_branch(Path(repo_root), branch_name) or trunk_branch
    )

    # Get Graphite URL
    remote_url = ctx.git.remote.get_remote_url(repo_root, "origin")
    owner, repo_name = parse_git_remote_url(remote_url)
    repo_id = GitHubRepoId(owner=owner, repo=repo_name)
    graphite_url = ctx.graphite.get_graphite_url(repo_id, pr_info.number)

    click.echo(click.style(f"   PR #{pr_info.number} ready", fg="green"))
    click.echo("")

    return pr_info.number, parent_branch, graphite_url


def _run_core_submit(
    ctx: ErkContext,
    cwd: Path,
    debug: bool,
    force: bool,
) -> CoreSubmitResult | CoreSubmitError:
    """Run core submit phase (git push + gh pr create)."""
    result: CoreSubmitResult | CoreSubmitError | None = None
    plans_repo = ctx.local_config.plans_repo if ctx.local_config else None

    for event in execute_core_submit(
        ctx,
        cwd,
        pr_title="WIP",
        pr_body="",
        force=force,
        plans_repo=plans_repo,
    ):
        if isinstance(event, ProgressEvent):
            if debug:
                render_progress(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    if result is None:
        return CoreSubmitError(
            success=False,
            error_type="submit-failed",
            message="Core submit did not complete",
            details={},
        )

    return result


def _run_diff_extraction(
    ctx: ErkContext,
    *,
    cwd: Path,
    pr_number: int,
    session_id: str,
    base_branch: str,
    debug: bool,
) -> Path | None:
    """Run diff extraction phase."""
    result: Path | None = None

    for event in execute_diff_extraction(ctx, cwd, pr_number, session_id, base_branch=base_branch):
        if isinstance(event, ProgressEvent):
            if debug:
                render_progress(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    return result


def _run_graphite_enhance(
    ctx: ErkContext, *, cwd: Path, pr_number: int, debug: bool, force: bool
) -> GraphiteEnhanceResult | GraphiteEnhanceError | GraphiteSkipped:
    """Run Graphite enhancement phase."""
    result: GraphiteEnhanceResult | GraphiteEnhanceError | GraphiteSkipped | None = None

    for event in execute_graphite_enhance(ctx, cwd, pr_number, force=force):
        if isinstance(event, ProgressEvent):
            if debug:
                render_progress(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    if result is None:
        return GraphiteSkipped(
            success=True,
            reason="incomplete",
            message="Graphite enhancement did not complete",
        )

    return result


def _run_finalize(
    ctx: ErkContext,
    *,
    cwd: Path,
    pr_number: int,
    title: str,
    body: str,
    diff_file: str,
    debug: bool,
) -> FinalizeResult | PostAnalysisError:
    """Run finalize phase and return result."""
    result: FinalizeResult | PostAnalysisError | None = None

    plans_repo = ctx.local_config.plans_repo if ctx.local_config else None
    for event in execute_finalize(
        ops=ctx,
        cwd=cwd,
        pr_number=pr_number,
        pr_title=title,
        pr_body=body,
        pr_body_file=None,
        diff_file=diff_file,
        plans_repo=plans_repo,
    ):
        if isinstance(event, ProgressEvent):
            if debug:
                render_progress(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    if result is None:
        return PostAnalysisError(
            success=False,
            error_type="submit-failed",
            message="Finalize did not complete",
            details={},
        )

    return result
