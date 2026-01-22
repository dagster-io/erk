"""Generate AI commit message and amend current commit.

This command is a focused subset of `erk pr submit` that only handles
local commit message generation without pushing or creating PRs.

Usage:
    erk pr summarize

Requirements:
    - Must have exactly 1 commit on the branch (compared to parent)
    - If multiple commits exist, error with instruction to run `gt squash`
"""

import os
import uuid
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
    """Generate AI commit message and amend current commit.

    Analyzes the diff between current branch and parent, generates an
    AI-powered commit message using Claude, and amends the current commit
    with the generated message.

    Requirements:
    - Must have exactly 1 commit on the branch (compared to parent)
    - If 0 commits: Make a commit first
    - If >1 commits: Run `gt squash` first to combine them

    Examples:

    \b
      # Generate and apply AI commit message
      erk pr summarize

      # Show debug output
      erk pr summarize --debug
    """
    _execute_pr_summarize(ctx, debug=debug)


def _execute_pr_summarize(ctx: ErkContext, *, debug: bool) -> None:
    """Execute PR summarize workflow."""
    # Step 1: Verify Claude CLI available
    if not ctx.claude_executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\n\nInstall from: https://claude.com/download"
        )

    cwd = Path.cwd()
    repo_root = ctx.git.get_repository_root(cwd)
    session_id = os.environ.get("SESSION_ID", str(uuid.uuid4()))

    click.echo(click.style("Summarizing commit...", bold=True))
    click.echo("")

    # Step 2: Get current branch (fail if detached HEAD)
    current_branch = ctx.git.get_current_branch(cwd)
    if current_branch is None:
        raise click.ClickException("Not on a branch (detached HEAD state)")

    # Step 3: Get parent branch (Graphite-aware, falls back to trunk)
    trunk_branch = ctx.git.detect_trunk_branch(repo_root)
    parent_branch = (
        ctx.branch_manager.get_parent_branch(Path(repo_root), current_branch) or trunk_branch
    )

    if debug:
        click.echo(click.style(f"   Branch: {current_branch}", dim=True))
        click.echo(click.style(f"   Parent: {parent_branch}", dim=True))

    # Step 4: Count commits ahead of parent
    commit_count = ctx.git.count_commits_ahead(cwd, parent_branch)

    if commit_count == 0:
        raise click.ClickException(
            "No commits to summarize\n\n"
            "Make a commit first with:\n"
            "  git add . && git commit -m 'WIP'"
        )

    if commit_count > 1:
        raise click.ClickException(
            f"Found {commit_count} commits on branch\n\n"
            "Summarize only works with a single commit. First combine commits with:\n"
            "  gt squash"
        )

    click.echo(click.style("   1 commit found", fg="green"))
    click.echo("")

    # Step 5: Get diff to parent branch
    click.echo(click.style("Getting diff...", bold=True))
    pr_diff = ctx.git.get_diff_to_branch(cwd, parent_branch)
    diff_lines = len(pr_diff.splitlines())

    if debug:
        click.echo(click.style(f"   Diff retrieved ({diff_lines} lines)", dim=True))

    # Step 6: Filter lock files
    pr_diff = filter_diff_excluded_files(pr_diff)

    # Step 7: Truncate if needed
    diff_content, was_truncated = truncate_diff(pr_diff)
    if was_truncated:
        click.echo(click.style("   Diff truncated for size", fg="yellow"))

    click.echo(click.style("   Diff prepared", fg="green"))
    click.echo("")

    # Step 8: Write diff to scratch file
    diff_file = write_scratch_file(
        diff_content,
        session_id=session_id,
        suffix=".diff",
        prefix="summarize-diff-",
        repo_root=Path(repo_root),
    )

    if debug:
        click.echo(click.style(f"   Diff written to {diff_file}", dim=True))

    # Step 9: Generate commit message via CommitMessageGenerator
    click.echo(click.style("Generating commit message...", bold=True))

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

    title = msg_result.title or "Update"
    body = msg_result.body or ""

    click.echo("")

    # Step 10: Amend commit with new message
    click.echo(click.style("Amending commit...", bold=True))

    # Build full commit message (title + body)
    if body:
        full_message = f"{title}\n\n{body}"
    else:
        full_message = title

    ctx.git.amend_commit(cwd, full_message)

    click.echo(click.style("   Commit amended", fg="green"))
    click.echo("")

    # Step 11: Show success with title preview
    click.echo(click.style("Done!", fg="green", bold=True))
    click.echo("")
    click.echo(f"Title: {title}")
    if body:
        # Show first line of body as preview
        body_preview = body.split("\n")[0]
        if len(body_preview) > 60:
            body_preview = body_preview[:57] + "..."
        click.echo(f"Body: {body_preview}")


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
            if debug:
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
