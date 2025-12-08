"""Submit current branch as a pull request.

Orchestrates the PR submission workflow using Python:
1. Preflight: Auth checks, squash, submit branch, get diff
2. Generate: AI-generated commit message via Claude CLI
3. Finalize: Update PR metadata with generated message
"""

import os
import uuid
from pathlib import Path

import click
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.operations.finalize import execute_finalize
from erk_shared.integrations.gt.operations.preflight import execute_preflight
from erk_shared.integrations.gt.types import (
    FinalizeResult,
    PostAnalysisError,
    PreAnalysisError,
    PreflightResult,
)

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


@click.command("submit")
@click.option("--debug", is_flag=True, help="Show diagnostic output")
@click.pass_obj
def pr_submit(ctx: ErkContext, debug: bool) -> None:
    """Submit PR with AI-generated commit message.

    Analyzes your changes, generates a commit message via AI, and
    creates a pull request using Graphite.

    Examples:

    \b
      # Submit PR
      erk pr submit
    """
    # Verify Claude is available (needed for commit message generation)
    if not ctx.claude_executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\n\nInstall from: https://claude.com/download"
        )

    click.echo(click.style("🚀 Submitting PR...", bold=True))
    click.echo("")

    cwd = Path.cwd()
    session_id = os.environ.get("SESSION_ID", str(uuid.uuid4()))

    # Phase 1: Preflight (auth, squash, submit, get diff)
    click.echo(click.style("Phase 1: Preflight checks", bold=True))
    preflight_result = _run_preflight(ctx, cwd, session_id, debug)

    if isinstance(preflight_result, PreAnalysisError):
        raise click.ClickException(preflight_result.message)
    if isinstance(preflight_result, PostAnalysisError):
        raise click.ClickException(preflight_result.message)

    click.echo(click.style(f"   PR #{preflight_result.pr_number} created", fg="green"))
    click.echo("")

    # Phase 2: Generate commit message
    click.echo(click.style("Phase 2: Generating PR description", bold=True))
    msg_gen = CommitMessageGenerator(ctx.claude_executor)
    msg_result = _run_commit_message_generation(
        msg_gen,
        diff_file=Path(preflight_result.diff_file),
        repo_root=Path(preflight_result.repo_root),
        current_branch=preflight_result.current_branch,
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

    if isinstance(finalize_result, PostAnalysisError):
        raise click.ClickException(finalize_result.message)

    click.echo(click.style("   PR metadata updated", fg="green"))
    click.echo("")

    # Success output with clickable URL
    styled_url = click.style(finalize_result.pr_url, fg="cyan", underline=True)
    clickable_url = f"\033]8;;{finalize_result.pr_url}\033\\{styled_url}\033]8;;\033\\"
    click.echo(f"✅ {clickable_url}")

    # Show Graphite URL if available
    if finalize_result.graphite_url:
        styled_graphite = click.style(finalize_result.graphite_url, fg="cyan", underline=True)
        clickable_graphite = (
            f"\033]8;;{finalize_result.graphite_url}\033\\{styled_graphite}\033]8;;\033\\"
        )
        click.echo(f"📊 {clickable_graphite}")


def _run_preflight(
    ctx: ErkContext,
    cwd: Path,
    session_id: str,
    debug: bool,
) -> PreflightResult | PreAnalysisError | PostAnalysisError:
    """Run preflight phase and return result."""
    result: PreflightResult | PreAnalysisError | PostAnalysisError | None = None

    for event in execute_preflight(ctx, cwd, session_id):
        if isinstance(event, ProgressEvent):
            if debug:
                _render_progress(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    if result is None:
        return PostAnalysisError(
            success=False,
            error_type="submit_failed",
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
) -> FinalizeResult | PostAnalysisError:
    """Run finalize phase and return result."""
    result: FinalizeResult | PostAnalysisError | None = None

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
        return PostAnalysisError(
            success=False,
            error_type="submit_failed",
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
