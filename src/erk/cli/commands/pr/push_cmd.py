"""Push current branch as a pull request (git-only, no Graphite).

Orchestrates the git-only PR submission workflow using Python:
1. Preflight: Auth checks, stage changes, push, create PR, get diff
2. Generate: AI-generated commit message via Claude CLI
3. Finalize: Update PR metadata with generated message

This is the git-only alternative to `erk pr submit` which uses Graphite.
"""

import uuid
from pathlib import Path

import click
from erk_shared.integrations.git_pr.operations.finalize import execute_finalize
from erk_shared.integrations.git_pr.operations.preflight import execute_preflight
from erk_shared.integrations.git_pr.types import (
    GitFinalizeError,
    GitFinalizeResult,
    GitPreflightError,
    GitPreflightResult,
)
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent

from erk.core.commit_message_generator import (
    CommitMessageGenerator,
    CommitMessageRequest,
    CommitMessageResult,
)
from erk.core.context import ErkContext


def _render_progress(event: ProgressEvent) -> None:
    """Render a progress event to the CLI."""
    style_map = {
        "info": {"dim": True},
        "success": {"fg": "green"},
        "warning": {"fg": "yellow"},
        "error": {"fg": "red"},
    }
    style = style_map.get(event.style, {})
    click.echo(click.style(f"   {event.message}", **style))


@click.command("push")
@click.option("--debug", is_flag=True, help="Show diagnostic output")
@click.pass_obj
def pr_push(ctx: ErkContext, debug: bool) -> None:
    """Push PR with AI-generated commit message (git-only).

    Analyzes your changes, generates a commit message via AI, and
    creates a pull request using standard git + GitHub CLI.

    This command does NOT use Graphite. For Graphite-based submission,
    use `erk pr submit` instead.

    Examples:

    \b
      # Push PR (git-only)
      erk pr push
    """
    # Verify Claude is available (needed for commit message generation)
    if not ctx.claude_executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\n\nInstall from: https://claude.com/download"
        )

    click.echo(click.style("🚀 Pushing PR (git-only)...", bold=True))
    click.echo("")

    cwd = ctx.cwd
    session_id = ctx.session_store.get_current_session_id() or str(uuid.uuid4())

    # Phase 1: Preflight (auth, stage, push, create PR, get diff)
    click.echo(click.style("Phase 1: Preflight checks", bold=True))
    preflight_result = _run_preflight(ctx, cwd, session_id, debug)

    if isinstance(preflight_result, GitPreflightError):
        raise click.ClickException(preflight_result.message)

    action_verb = "created" if preflight_result.pr_created else "found existing"
    click.echo(click.style(f"   PR #{preflight_result.pr_number} {action_verb}", fg="green"))
    click.echo("")

    # Phase 2: Generate commit message
    click.echo(click.style("Phase 2: Generating PR description", bold=True))
    msg_gen = CommitMessageGenerator(ctx.claude_executor)
    msg_result = _run_commit_message_generation(
        msg_gen,
        diff_file=Path(preflight_result.diff_file),
        repo_root=Path(preflight_result.repo_root),
        current_branch=preflight_result.branch_name,
        parent_branch=preflight_result.parent_branch,
        commit_messages=preflight_result.commit_messages,
        debug=debug,
    )

    if not msg_result.success:
        raise click.ClickException(f"Failed to generate message: {msg_result.error_message}")

    click.echo("")

    # Phase 3: Finalize (update PR metadata)
    click.echo(click.style("Phase 3: Updating PR metadata", bold=True))
    finalize_result = _run_finalize(
        ctx,
        cwd,
        pr_number=preflight_result.pr_number,
        title=msg_result.title or "Update",
        body=msg_result.body or "",
        diff_file=preflight_result.diff_file,
        debug=debug,
    )

    if isinstance(finalize_result, GitFinalizeError):
        raise click.ClickException(finalize_result.message)

    click.echo(click.style("   PR metadata updated", fg="green"))
    click.echo("")

    # Success output with clickable URL
    styled_url = click.style(finalize_result.pr_url, fg="cyan", underline=True)
    clickable_url = f"\033]8;;{finalize_result.pr_url}\033\\{styled_url}\033]8;;\033\\"
    click.echo(f"✅ {clickable_url}")


def _run_preflight(
    ctx: ErkContext,
    cwd: Path,
    session_id: str,
    debug: bool,
) -> GitPreflightResult | GitPreflightError:
    """Run preflight phase and return result."""
    result: GitPreflightResult | GitPreflightError | None = None

    for event in execute_preflight(ctx, cwd, session_id):
        if isinstance(event, ProgressEvent):
            if debug:
                _render_progress(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    if result is None:
        return GitPreflightError(
            success=False,
            error_type="push_failed",
            message="Preflight did not complete",
            details={},
        )

    return result


def _run_finalize(
    ctx: ErkContext,
    cwd: Path,
    pr_number: int,
    title: str,
    body: str,
    diff_file: str,
    debug: bool,
) -> GitFinalizeResult | GitFinalizeError:
    """Run finalize phase and return result."""
    result: GitFinalizeResult | GitFinalizeError | None = None

    for event in execute_finalize(
        ctx,
        cwd,
        pr_number=pr_number,
        pr_title=title,
        pr_body=body,
        diff_file=diff_file,
    ):
        if isinstance(event, ProgressEvent):
            if debug:
                _render_progress(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    if result is None:
        return GitFinalizeError(
            success=False,
            error_type="pr_update_failed",
            message="Finalize did not complete",
            details={},
        )

    return result


def _run_commit_message_generation(
    generator: CommitMessageGenerator,
    diff_file: Path,
    repo_root: Path,
    current_branch: str,
    parent_branch: str,
    commit_messages: list[str] | None,
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
            commit_messages=commit_messages,
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
