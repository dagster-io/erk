"""Squash, regenerate AI commit message, push, and update remote PR.

Replaces the old multi-step workflow (gt squash → erk pr summarize → push)
with a single command that handles the full cycle: squash commits, generate
an AI-powered commit message, amend the local commit, force-push, and update
the remote PR title/body.
"""

from pathlib import Path

import click

from erk.cli.commands.pr.shared import (
    IssueLinkageMismatch,
    assemble_pr_body,
    discover_issue_for_footer,
    render_progress,
    require_claude_available,
    run_commit_message_generation,
)
from erk.core.command_log import get_or_generate_session_id
from erk.core.commit_message_generator import CommitMessageGenerator
from erk.core.context import ErkContext
from erk.core.plan_context_provider import PlanContextProvider
from erk_shared.gateway.branch_manager.types import SubmitBranchError
from erk_shared.gateway.github.pr_footer import extract_header_from_body
from erk_shared.gateway.github.types import BodyText, PRNotFound
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.gt.operations.finalize import ERK_SKIP_LEARN_LABEL, is_learn_plan
from erk_shared.gateway.gt.operations.squash import execute_squash
from erk_shared.gateway.gt.types import SquashError
from erk_shared.gateway.pr.diff_extraction import execute_diff_extraction


@click.command("rewrite")
@click.option("--debug", is_flag=True, help="Show diagnostic output")
@click.pass_obj
def pr_rewrite(ctx: ErkContext, debug: bool) -> None:
    """Squash, regenerate AI commit message, push, and update remote PR.

    Combines squashing, AI message generation, amending, pushing, and
    PR updating into a single command. Replaces the manual workflow of
    running gt squash, erk pr summarize, and pushing separately.

    \b
    Phases:
      1. Validate preconditions (branch, PR)
      2. Squash commits (idempotent)
      3. Extract diff
      4. Generate AI title/body
      5. Amend local commit
      6. Push and update remote PR

    Examples:

    \b
      # Rewrite current PR with AI-generated message
      erk pr rewrite

      # Show debug output
      erk pr rewrite --debug
    """
    _execute_pr_rewrite(ctx, debug=debug)


def _execute_pr_rewrite(ctx: ErkContext, *, debug: bool) -> None:
    """Execute PR rewrite with positively-named parameters."""
    # Phase 1: Validate preconditions
    require_claude_available(ctx)

    cwd = Path.cwd()
    session_id = get_or_generate_session_id(cwd)

    current_branch = ctx.git.branch.get_current_branch(cwd)
    if current_branch is None:
        raise click.ClickException("Not on a branch (detached HEAD state)")

    repo_root = ctx.git.repo.get_repository_root(cwd)

    # Verify PR exists for this branch
    pr_info = ctx.github.get_pr_for_branch(repo_root, current_branch)
    if isinstance(pr_info, PRNotFound):
        raise click.ClickException(
            f"No PR found for branch '{current_branch}'\n\nCreate a PR first with: erk pr submit"
        )

    pr_number = pr_info.number
    trunk_branch = ctx.git.branch.detect_trunk_branch(repo_root)
    parent_branch = (
        ctx.branch_manager.get_parent_branch(Path(repo_root), current_branch) or trunk_branch
    )

    click.echo(click.style("📝 Rewriting PR...", bold=True))
    click.echo("")

    # Phase 2: Squash commits (idempotent)
    click.echo(click.style("Phase 1: Squashing commits", bold=True))
    squash_result = _run_squash(ctx, cwd=cwd, debug=debug)
    if isinstance(squash_result, SquashError):
        raise click.ClickException(f"Squash failed: {squash_result.message}")
    click.echo("")

    # Phase 3: Extract diff
    click.echo(click.style("Phase 2: Getting diff", bold=True))
    diff_file = _run_diff_extraction(
        ctx,
        cwd=cwd,
        session_id=session_id,
        base_branch=parent_branch,
        debug=debug,
    )
    if diff_file is None:
        raise click.ClickException("Failed to extract diff for AI analysis")
    click.echo("")

    # Phase 4: Generate AI title/body
    click.echo(click.style("Phase 3: Generating commit message", bold=True))

    plan_provider = PlanContextProvider(ctx.github_issues)
    plan_context = plan_provider.get_plan_context(
        repo_root=Path(repo_root),
        branch_name=current_branch,
    )

    if plan_context is not None:
        click.echo(
            click.style(
                f"   Incorporating plan from issue #{plan_context.issue_number}",
                fg="green",
            )
        )
        if plan_context.objective_summary is not None:
            click.echo(click.style(f"   Linked to {plan_context.objective_summary}", fg="green"))
    else:
        click.echo(click.style("   No linked plan found", dim=True))
    click.echo("")

    msg_gen = CommitMessageGenerator(ctx.prompt_executor)
    msg_result = run_commit_message_generation(
        generator=msg_gen,
        diff_file=diff_file,
        repo_root=Path(repo_root),
        current_branch=current_branch,
        parent_branch=parent_branch,
        commit_messages=None,
        plan_context=plan_context,
        debug=debug,
    )

    if not msg_result.success:
        raise click.ClickException(f"Failed to generate message: {msg_result.error_message}")

    title = msg_result.title or "Update"
    body = msg_result.body or ""
    click.echo("")

    # Phase 5: Amend local commit
    click.echo(click.style("Phase 4: Amending commit", bold=True))
    commit_message = f"{title}\n\n{body}" if body else title
    ctx.git.commit.amend_commit(cwd, commit_message)
    click.echo(click.style("   Commit amended", fg="green"))
    click.echo("")

    # Phase 6: Push and update remote PR
    click.echo(click.style("Phase 5: Pushing and updating PR", bold=True))

    submit_result = ctx.branch_manager.submit_branch(Path(repo_root), current_branch)
    if isinstance(submit_result, SubmitBranchError):
        raise click.ClickException(f"Push failed: {submit_result.message}")
    click.echo(click.style("   Branch pushed", fg="green"))

    # Discover issue number and assemble PR body (shared with submit pipeline)
    impl_dir = cwd / ".impl"
    plans_repo = ctx.local_config.plans_repo if ctx.local_config else None

    issue_discovery = discover_issue_for_footer(
        impl_dir=impl_dir,
        branch_name=current_branch,
        existing_pr_body=pr_info.body,
        plans_repo=plans_repo,
    )
    if isinstance(issue_discovery, IssueLinkageMismatch):
        raise click.ClickException(issue_discovery.message)

    final_body = assemble_pr_body(
        body=body,
        plan_context=plan_context,
        pr_number=pr_number,
        issue_number=issue_discovery.issue_number,
        plans_repo=issue_discovery.plans_repo,
        header=extract_header_from_body(pr_info.body),
    )

    ctx.github.update_pr_title_and_body(
        repo_root=Path(repo_root),
        pr_number=pr_number,
        title=title,
        body=BodyText(content=final_body),
    )
    click.echo(click.style("   PR updated", fg="green"))

    # Add learn skip label if applicable
    is_learn_origin = is_learn_plan(impl_dir)
    if is_learn_origin:
        ctx.github.add_label_to_pr(Path(repo_root), pr_number, ERK_SKIP_LEARN_LABEL)

    # Retrack Graphite branch if needed (fix tracking divergence from amend)
    if ctx.graphite_branch_ops is not None:
        ctx.graphite_branch_ops.retrack_branch(Path(repo_root), current_branch)

    # Clean up scratch diff file
    if diff_file.exists():
        diff_file.unlink(missing_ok=True)

    click.echo("")
    click.echo(f"✅ PR rewritten: {title}")


def _run_squash(
    ctx: ErkContext,
    *,
    cwd: Path,
    debug: bool,
) -> SquashError | None:
    """Run squash phase. Returns SquashError on failure, None on success."""
    for event in execute_squash(ctx, cwd):
        if isinstance(event, ProgressEvent):
            if debug:
                render_progress(event)
        elif isinstance(event, CompletionEvent):
            result = event.result
            if isinstance(result, SquashError):
                return result
    return None


def _run_diff_extraction(
    ctx: ErkContext,
    *,
    cwd: Path,
    session_id: str,
    base_branch: str,
    debug: bool,
) -> Path | None:
    """Run diff extraction phase.

    Uses execute_diff_extraction with pr_number=0 as placeholder.
    """
    result: Path | None = None

    for event in execute_diff_extraction(
        ctx, cwd, pr_number=0, session_id=session_id, base_branch=base_branch
    ):
        if isinstance(event, ProgressEvent):
            if debug:
                render_progress(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    return result
