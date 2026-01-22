"""Generate AI-powered commit message and amend current commit.

This command generates a commit message using Claude CLI based on the diff
between the current branch and its parent branch, then amends the current
commit with the generated message.

This is a subset of `erk pr submit` focused only on local commit message
generation, without creating or updating a PR.
"""

from pathlib import Path

import click

from erk.core.commit_message_generator import (
    CommitMessageGenerator,
    CommitMessageRequest,
    CommitMessageResult,
)
from erk.core.context import ErkContext
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.gt.prompts import truncate_diff
from erk_shared.gateway.pr.diff_extraction import filter_diff_excluded_files
from erk_shared.scratch.scratch import write_scratch_file


def _render_progress(event: ProgressEvent) -> None:
    """Render a progress event to the CLI."""
    message = f"   {event.message}"
    if event.style == "info":
        click.echo(click.style(message, dim=True))
    elif event.style == "success":
        click.echo(click.style(message, fg="green"))
    elif event.style == "warning":
        click.echo(click.style(message, fg="yellow"))
    elif event.style == "error":
        click.echo(click.style(message, fg="red"))
    else:
        click.echo(message)


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
    if not ctx.claude_executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\n\nInstall from: https://claude.com/download"
        )

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

    # Get diff to parent branch
    click.echo(click.style("Phase 1: Getting diff", bold=True))
    diff_content = ctx.git.get_diff_to_branch(cwd, parent_branch)
    diff_lines = len(diff_content.splitlines())
    if debug:
        click.echo(click.style(f"   Diff retrieved ({diff_lines} lines)", dim=True))

    # Filter out lock files
    diff_content = filter_diff_excluded_files(diff_content)

    # Truncate if needed
    diff_content, was_truncated = truncate_diff(diff_content)
    if was_truncated:
        click.echo(click.style("   Diff truncated for size", fg="yellow"))

    # Write diff to scratch file
    diff_file = write_scratch_file(
        diff_content,
        session_id=session_id,
        suffix=".diff",
        prefix="summarize-diff-",
        repo_root=Path(repo_root),
    )
    if debug:
        click.echo(click.style(f"   Diff written to {diff_file}", dim=True))
    click.echo(click.style("   Diff ready", fg="green"))
    click.echo("")

    # Generate commit message
    click.echo(click.style("Phase 2: Generating commit message", bold=True))
    msg_gen = CommitMessageGenerator(ctx.claude_executor)
    msg_result = _run_commit_message_generation(
        generator=msg_gen,
        diff_file=diff_file,
        repo_root=Path(repo_root),
        current_branch=current_branch,
        parent_branch=parent_branch,
        debug=debug,
    )

    if not msg_result.success:
        raise click.ClickException(f"Failed to generate message: {msg_result.error_message}")

    click.echo("")

    # Amend the commit with new message
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


def _run_commit_message_generation(
    *,
    generator: CommitMessageGenerator,
    diff_file: Path,
    repo_root: Path,
    current_branch: str,
    parent_branch: str,
    debug: bool,
) -> CommitMessageResult:
    """Run commit message generation and return result."""
    result: CommitMessageResult | None = None

    for event in generator.generate(
        CommitMessageRequest(
            diff_file=diff_file,
            repo_root=repo_root,
            current_branch=current_branch,
            parent_branch=parent_branch,
            commit_messages=None,
        )
    ):
        if isinstance(event, ProgressEvent):
            _render_progress(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    if result is None:
        return CommitMessageResult(
            success=False,
            title=None,
            body=None,
            error_message="Commit message generation did not complete",
        )

    return result
