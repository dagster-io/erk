"""Generate AI-powered commit message and amend current commit.

This command generates a commit message using Claude CLI based on the diff
between the current branch and its parent branch, then amends the current
commit with the generated message.

This is a subset of `erk pr submit` focused only on local commit message
generation, without creating or updating a PR.
"""

from pathlib import Path

import click

from erk.cli.commands.pr.shared import (
    render_progress,
    require_claude_available,
    run_commit_message_generation,
)
from erk.core.commit_message_generator import CommitMessageGenerator
from erk.core.context import ErkContext
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.diff_extraction import execute_diff_extraction


@click.command("summarize")
@click.option("--debug", is_flag=True, help="Show diagnostic output")
@click.pass_obj
def pr_summarize(ctx: ErkContext, debug: bool) -> None:
    """Generate AI-powered commit message and amend current commit.

    Analyzes the diff between the current branch and its parent branch,
    generates a descriptive commit message using Claude, and amends
    the current commit with the new message.

    Requirements:
    - Must have exactly 1 commit ahead of parent branch
    - If multiple commits exist, run `gt squash` first

    Examples:

    \b
      # Generate and apply AI commit message
      erk pr summarize

      # Show debug output
      erk pr summarize --debug
    """
    _execute_pr_summarize(ctx, debug=debug)


def _execute_pr_summarize(ctx: ErkContext, *, debug: bool) -> None:
    """Execute PR summarize with positively-named parameters."""
    from erk.core.command_log import get_or_generate_session_id

    # Verify Claude is available
    require_claude_available(ctx)

    cwd = Path.cwd()

    # Auto-detect session ID for scratch file isolation
    session_id = get_or_generate_session_id(cwd)

    # Get current branch
    current_branch = ctx.git.get_current_branch(cwd)
    if current_branch is None:
        raise click.ClickException("Not on a branch (detached HEAD state)")

    repo_root = ctx.git.get_repository_root(cwd)
    trunk_branch = ctx.git.detect_trunk_branch(repo_root)

    # Get parent branch (Graphite-aware, falls back to trunk)
    parent_branch = (
        ctx.branch_manager.get_parent_branch(Path(repo_root), current_branch) or trunk_branch
    )

    # Count commits ahead of parent
    commits_ahead = ctx.git.count_commits_ahead(cwd, parent_branch)

    if commits_ahead == 0:
        raise click.ClickException(
            f"No commits ahead of '{parent_branch}'\n\n"
            "Make a commit first before running summarize."
        )

    if commits_ahead > 1:
        raise click.ClickException(
            f"Multiple commits ({commits_ahead}) ahead of '{parent_branch}'\n\n"
            "Run `gt squash` first to combine commits into one, then run summarize again."
        )

    click.echo(click.style("📝 Generating commit message...", bold=True))
    click.echo("")

    # Phase 1: Get diff using shared diff extraction
    click.echo(click.style("Phase 1: Getting diff", bold=True))
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

    # Phase 2: Generate commit message
    click.echo(click.style("Phase 2: Generating commit message", bold=True))
    msg_gen = CommitMessageGenerator(ctx.claude_executor)
    msg_result = run_commit_message_generation(
        generator=msg_gen,
        diff_file=diff_file,
        repo_root=Path(repo_root),
        current_branch=current_branch,
        parent_branch=parent_branch,
        commit_messages=None,
        debug=debug,
    )

    if not msg_result.success:
        raise click.ClickException(f"Failed to generate message: {msg_result.error_message}")

    click.echo("")

    # Phase 3: Amend the commit with new message
    click.echo(click.style("Phase 3: Amending commit", bold=True))
    title = msg_result.title or "Update"
    body = msg_result.body or ""

    # Combine title and body for commit message
    if body:
        commit_message = f"{title}\n\n{body}"
    else:
        commit_message = title

    ctx.git.amend_commit(cwd, commit_message)
    click.echo(click.style("   Commit amended", fg="green"))
    click.echo("")

    # Success output
    click.echo(f"✅ Commit message updated: {title}")


def _run_diff_extraction(
    ctx: ErkContext,
    *,
    cwd: Path,
    session_id: str,
    base_branch: str,
    debug: bool,
) -> Path | None:
    """Run diff extraction phase for summarize command.

    Uses the same execute_diff_extraction as submit, but with pr_number=0
    since summarize doesn't have a PR yet.
    """
    result: Path | None = None

    # pr_number=0 is used as a placeholder since summarize doesn't have a PR yet
    for event in execute_diff_extraction(
        ctx, cwd, pr_number=0, session_id=session_id, base_branch=base_branch
    ):
        if isinstance(event, ProgressEvent):
            if debug:
                render_progress(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    return result
