"""Submit current branch as a pull request.

Unified PR submission with strategy pattern:
- GraphiteSubmitStrategy: Uses gt submit (when Graphite authenticated + branch tracked)
- CoreSubmitStrategy: Uses git push + gh pr create (fallback)

The workflow:
1. Pre-strategy: WIP commit (if uncommitted changes)
2. Strategy execution: Push + PR creation
3. Get diff for AI: GitHub API
4. Generate: AI-generated commit message via Claude CLI
5. Graphite enhance: Optional gt submit for stack metadata (only for Core strategy)
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
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.gt.operations.finalize import execute_finalize
from erk_shared.gateway.gt.types import FinalizeError, FinalizeResult
from erk_shared.gateway.pr.diff_extraction import execute_diff_extraction
from erk_shared.gateway.pr.graphite_enhance import (
    execute_graphite_enhance,
    should_enhance_with_graphite,
)
from erk_shared.gateway.pr.strategy.abc import SubmitStrategy
from erk_shared.gateway.pr.strategy.core import CoreSubmitStrategy
from erk_shared.gateway.pr.strategy.graphite import GraphiteSubmitStrategy
from erk_shared.gateway.pr.strategy.types import SubmitStrategyError, SubmitStrategyResult
from erk_shared.gateway.pr.types import (
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

    Uses a strategy pattern for PR submission:
    - Graphite strategy: gt submit (when Graphite authenticated + branch tracked)
    - Core strategy: git push + gh pr create (fallback)

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


def _select_strategy(ctx: ErkContext, cwd: Path, use_graphite: bool) -> SubmitStrategy:
    """Select the appropriate submission strategy based on context.

    Args:
        ctx: ErkContext
        cwd: Working directory
        use_graphite: Whether Graphite is enabled (not --no-graphite)

    Returns:
        GraphiteSubmitStrategy if Graphite is authenticated and branch is tracked,
        CoreSubmitStrategy otherwise
    """
    if use_graphite:
        check_result = should_enhance_with_graphite(ctx, cwd)
        if check_result.should_enhance:
            return GraphiteSubmitStrategy()

    plans_repo = ctx.local_config.plans_repo if ctx.local_config else None
    return CoreSubmitStrategy(plans_repo=plans_repo)


def _run_strategy(
    ctx: ErkContext,
    cwd: Path,
    strategy: SubmitStrategy,
    debug: bool,
    force: bool,
) -> SubmitStrategyResult | SubmitStrategyError:
    """Execute a submission strategy and return the result.

    Args:
        ctx: ErkContext
        cwd: Working directory
        strategy: The strategy to execute
        debug: Whether to show debug output
        force: Whether to force push

    Returns:
        SubmitStrategyResult on success, SubmitStrategyError on failure
    """
    result: SubmitStrategyResult | SubmitStrategyError | None = None

    for event in strategy.execute(ctx, cwd, force=force):
        if isinstance(event, ProgressEvent):
            if debug:
                render_progress(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    if result is None:
        return SubmitStrategyError(
            status="error",
            error_type="strategy-failed",
            message="Strategy did not complete",
            details={},
        )

    return result


def _execute_pr_submit(ctx: ErkContext, debug: bool, use_graphite: bool, force: bool) -> None:
    """Execute PR submission with positively-named parameters."""
    # Verify Claude is available (needed for commit message generation)
    require_claude_available(ctx)

    click.echo(click.style("🚀 Submitting PR...", bold=True))
    click.echo("")

    cwd = Path.cwd()
    session_id = os.environ.get("SESSION_ID", str(uuid.uuid4()))

    # Pre-strategy: WIP commit (unified, happens once before any strategy)
    if ctx.git.has_uncommitted_changes(cwd):
        click.echo(click.style("   Committing uncommitted changes...", dim=True))
        ctx.git.add_all(cwd)
        ctx.git.commit(cwd, "WIP: Prepare for PR submission")

    # Select and execute strategy
    strategy = _select_strategy(ctx, cwd, use_graphite)
    used_graphite_strategy = isinstance(strategy, GraphiteSubmitStrategy)

    click.echo(click.style("Phase 1: Creating or Updating PR", bold=True))
    result = _run_strategy(ctx, cwd, strategy, debug, force)

    if result.status == "error":
        raise click.ClickException(result.message)

    action = "created" if result.was_created else "found (already exists)"
    click.echo(click.style(f"   PR #{result.pr_number} {action}", fg="green"))
    click.echo("")

    pr_number = result.pr_number
    base_branch = result.base_branch
    graphite_url = result.graphite_url

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
    current_branch = ctx.git.get_current_branch(cwd)
    if current_branch is None:
        raise click.ClickException("Not on a branch (detached HEAD state)")
    trunk_branch = ctx.git.detect_trunk_branch(repo_root)

    # Get parent branch (Graphite-aware, falls back to trunk)
    parent_branch = (
        ctx.branch_manager.get_parent_branch(Path(repo_root), current_branch) or trunk_branch
    )

    # Get commit messages for AI context (only from current branch)
    commit_messages = ctx.git.get_commit_messages_since(cwd, parent_branch)

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

    # Phase 5: Graphite enhancement (only for Core strategy when branch not tracked)
    # Skip if GraphiteSubmitStrategy was used since gt submit already ran
    if use_graphite and not used_graphite_strategy:
        click.echo(click.style("Phase 5: Graphite enhancement", bold=True))
        graphite_result = _run_graphite_enhance(
            ctx, cwd=cwd, pr_number=pr_number, debug=debug, force=force
        )

        if graphite_result.status == "success":
            graphite_url = graphite_result.graphite_url
            click.echo("")
        elif graphite_result.status == "skipped":
            if debug:
                click.echo(click.style(f"   {graphite_result.message}", dim=True))
            click.echo("")
        elif graphite_result.status == "error":
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

    if finalize_result.status == "error":
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
            status="skipped",
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
) -> FinalizeResult | FinalizeError:
    """Run finalize phase and return result."""
    result: FinalizeResult | FinalizeError | None = None

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
        return FinalizeError(
            status="error",
            error_type="submit-failed",
            message="Finalize did not complete",
            details={},
        )

    return result
