"""Shared utilities for PR commands.

This module contains common functionality used by multiple PR commands
(rewrite, submit) to avoid code duplication.
"""

from __future__ import annotations

import queue
import re
import threading
from dataclasses import dataclass
from pathlib import Path

import click

from erk.core.commit_message_generator import (
    CommitMessageGenerator,
    CommitMessageRequest,
    CommitMessageResult,
)
from erk.core.context import ErkContext
from erk.core.plan_context_provider import PlanContext
from erk_shared.gateway.github.metadata.core import find_metadata_block, render_metadata_block
from erk_shared.gateway.github.metadata.schemas import (
    CREATED_AT,
    CREATED_BY,
    LIFECYCLE_STAGE,
    SCHEMA_VERSION,
)
from erk_shared.gateway.github.metadata.types import BlockKeys, MetadataBlock
from erk_shared.gateway.github.pr_footer import build_pr_body_footer
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.diff_extraction import execute_diff_extraction
from erk_shared.gateway.time.abc import Time
from erk_shared.plan_store.conversion import header_str
from erk_shared.plan_store.planned_pr_lifecycle import build_original_plan_section
from erk_shared.plan_store.types import PlanNotFound

# ---------------------------------------------------------------------------
# Branch Discovery
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BranchDiscovery:
    """Result of discovering branch context for PR commands."""

    current_branch: str
    repo_root: Path
    trunk_branch: str
    parent_branch: str


def discover_branch_context(ctx: ErkContext, *, cwd: Path) -> BranchDiscovery:
    """Discover branch context: current branch, repo root, trunk, and parent.

    Raises:
        click.ClickException: If in detached HEAD state
    """
    current_branch = ctx.git.branch.get_current_branch(cwd)
    if current_branch is None:
        raise click.ClickException("Not on a branch (detached HEAD state)")

    repo_root = ctx.git.repo.get_repository_root(cwd)
    trunk_branch = ctx.git.branch.detect_trunk_branch(repo_root)
    parent_branch = ctx.branch_manager.get_parent_branch(repo_root, current_branch) or trunk_branch

    return BranchDiscovery(
        current_branch=current_branch,
        repo_root=repo_root,
        trunk_branch=trunk_branch,
        parent_branch=parent_branch,
    )


# ---------------------------------------------------------------------------
# Diff Extraction
# ---------------------------------------------------------------------------


def run_diff_extraction(
    ctx: ErkContext,
    *,
    cwd: Path,
    session_id: str,
    base_branch: str,
    debug: bool,
) -> Path | None:
    """Run diff extraction with progress rendering.

    Wraps execute_diff_extraction() with event loop processing.

    Args:
        ctx: ErkContext providing gateways
        cwd: Current working directory
        session_id: Session ID for scratch file isolation
        base_branch: Branch to diff against
        debug: Whether to show progress output

    Returns:
        Path to diff file, or None if extraction failed
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


# ---------------------------------------------------------------------------
# Plan Context Display
# ---------------------------------------------------------------------------


def echo_plan_context_status(plan_context: PlanContext | None) -> None:
    """Echo plan context status to the CLI."""
    if plan_context is not None:
        click.echo(
            click.style(
                f"   Incorporating plan #{plan_context.plan_id}",
                fg="green",
            )
        )
        if plan_context.objective_summary is not None:
            click.echo(click.style(f"   Linked to {plan_context.objective_summary}", fg="green"))
    else:
        click.echo(click.style("   No linked plan found", dim=True))
    click.echo("")


# ---------------------------------------------------------------------------
# Lifecycle Stage
# ---------------------------------------------------------------------------

_STAGES_BEFORE_IMPL = {None, "prompted", "planning", "planned"}


def maybe_advance_lifecycle_to_impl(
    ctx: ErkContext,
    *,
    repo_root: Path,
    plan_id: str,
    quiet: bool,
) -> None:
    """Advance a linked plan's lifecycle_stage to "impl" if not already there.

    Intended for use after PR submission or rewrite so that plans are correctly
    marked as being implemented even when the user bypasses the /erk:plan-implement
    pipeline.

    Silently returns on any failure — lifecycle updates must never block submission.
    """
    plan_result = ctx.plan_backend.get_plan(repo_root, plan_id)
    if isinstance(plan_result, PlanNotFound):
        return

    current_stage = header_str(plan_result.header_fields, LIFECYCLE_STAGE)
    if current_stage not in _STAGES_BEFORE_IMPL:
        return

    try:
        ctx.plan_backend.update_metadata(repo_root, plan_id, {"lifecycle_stage": "impl"})
    except RuntimeError as e:
        if not quiet:
            msg = f"   Warning: failed to update lifecycle stage: {e}"
            click.echo(click.style(msg, fg="yellow"))
        return

    if not quiet:
        click.echo(click.style("   Plan lifecycle stage updated to impl", dim=True))


# ---------------------------------------------------------------------------
# Plan-Header Recovery
# ---------------------------------------------------------------------------


def recover_plan_header(
    ctx: ErkContext,
    *,
    repo_root: Path,
    plan_id: str,
) -> MetadataBlock | None:
    """Attempt to recover a plan-header metadata block from the plan backend.

    When the plan-header block is destroyed (e.g., by a rogue ``gh pr edit``),
    this function reconstructs it from the plan's stored metadata so that
    ``assemble_pr_body`` can re-embed it in the PR body.

    Returns None if the plan cannot be found, allowing callers to proceed
    without a plan-header (current behavior).
    """
    plan_result = ctx.plan_backend.get_plan(repo_root, plan_id)
    if isinstance(plan_result, PlanNotFound):
        return None

    # If the plan still has header_fields, use them directly
    if plan_result.header_fields:
        return MetadataBlock(key=BlockKeys.PLAN_HEADER, data=dict(plan_result.header_fields))

    # Otherwise, construct a minimal plan-header from PR metadata
    created_at_value = plan_result.created_at.isoformat()
    raw_author = plan_result.metadata.get("author")
    if isinstance(raw_author, str) and raw_author:
        created_by_value = raw_author
    else:
        created_by_value = "unknown"

    return MetadataBlock(
        key=BlockKeys.PLAN_HEADER,
        data={
            SCHEMA_VERSION: "2",
            CREATED_AT: created_at_value,
            CREATED_BY: created_by_value,
        },
    )


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def cleanup_diff_file(diff_file: Path | None) -> None:
    """Clean up a temporary diff file if it exists."""
    if diff_file is not None and diff_file.exists():
        try:
            diff_file.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# PR Body Assembly
# ---------------------------------------------------------------------------


def build_plan_details_section(plan_context: PlanContext) -> str:
    """Build a collapsed <details> section embedding the plan in the PR body."""
    issue_num = plan_context.plan_id
    parts = [
        "",
        "## Implementation Plan",
        "",
        "<details>",
        f"<summary><strong>Implementation Plan</strong> (Plan #{issue_num})</summary>",
        "",
        plan_context.plan_content,
        "",
        "</details>",
    ]
    return "\n".join(parts)


def _insert_objective_link(body: str, objective_summary: str) -> str:
    """Insert an objective link between summary and Key Changes sections."""
    match = re.match(r"Objective #(\d+): (.+)", objective_summary)
    if match is not None:
        objective_line = f"**Objective #{match.group(1)}:** {match.group(2)}"
    else:
        objective_line = f"**Objective:** {objective_summary}"

    idx = body.find("## Key Changes")
    if idx != -1:
        return body[:idx] + objective_line + "\n\n" + body[idx:]
    return body + "\n\n" + objective_line


def assemble_pr_body(
    *,
    body: str,
    plan_context: PlanContext | None,
    pr_number: int,
    header: str,
    existing_pr_body: str,
    recovered_plan_header: MetadataBlock | None,
) -> str:
    """Assemble final PR body with plan details and footer.

    Args:
        body: AI-generated body content
        plan_context: Optional plan context for <details> section
        pr_number: PR number for footer checkout command
        header: Existing PR header to preserve (may be empty)
        existing_pr_body: Full PR body captured before gt submit overwrites it.
            Used to extract plan-header metadata block. When the extracted block
            is non-empty, uses original-plan details format.
        recovered_plan_header: Fallback plan-header block recovered from the plan
            backend, used when the plan-header is missing from existing_pr_body.

    Returns:
        Complete PR body ready for GitHub API
    """
    plan_header = find_metadata_block(existing_pr_body, BlockKeys.PLAN_HEADER)
    if plan_header is None and recovered_plan_header is not None:
        plan_header = recovered_plan_header

    pr_body_content = body
    if plan_context is not None and plan_context.objective_summary is not None:
        pr_body_content = _insert_objective_link(pr_body_content, plan_context.objective_summary)
    if plan_context is not None:
        if plan_header is not None:
            # Draft PR: use original-plan format (from lifecycle module)
            pr_body_content = pr_body_content + build_original_plan_section(
                plan_context.plan_content
            )
        else:
            # Issue-based: use existing format
            pr_body_content = pr_body_content + build_plan_details_section(plan_context)

    footer = build_pr_body_footer(pr_number)

    # Place metadata and header below content, above footer
    suffix = ""
    if plan_header is not None:
        suffix = "\n\n" + render_metadata_block(plan_header)
    if header:
        suffix = "\n\n" + header.rstrip("\n") + suffix

    return pr_body_content + suffix + footer


def render_progress(event: ProgressEvent) -> None:
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


def require_claude_available(ctx: ErkContext) -> None:
    """Verify Claude CLI is available, raising ClickException if not.

    Args:
        ctx: ErkContext providing prompt_executor

    Raises:
        click.ClickException: If Claude CLI is not available
    """
    if not ctx.prompt_executor.is_available():
        raise click.ClickException(
            "Claude CLI not found\n\nInstall from: https://claude.com/download"
        )


_PROGRESS_TIMEOUT_SECONDS = 5.0


def run_commit_message_generation(
    *,
    generator: CommitMessageGenerator,
    diff_file: Path,
    repo_root: Path,
    current_branch: str,
    parent_branch: str,
    commit_messages: list[str] | None,
    plan_context: PlanContext | None,
    debug: bool,
    time: Time,
) -> CommitMessageResult:
    """Run commit message generation and return result.

    Runs the generator in a background thread and polls for events via a queue.
    If no event arrives within the timeout, emits a "Still waiting..." message
    so the user knows the system is alive during slow API calls.

    Args:
        generator: CommitMessageGenerator instance
        diff_file: Path to the diff file
        repo_root: Repository root path
        current_branch: Current branch name
        parent_branch: Parent branch name
        commit_messages: Optional list of existing commit messages for context
        plan_context: Optional plan context from linked erk-pr issue
        debug: Whether to show debug output (currently unused, progress always shown)

    Returns:
        CommitMessageResult with the generated title/body or error info
    """
    event_queue: queue.Queue[ProgressEvent | CompletionEvent[CommitMessageResult] | None] = (
        queue.Queue()
    )

    def _produce() -> None:
        for event in generator.generate(
            CommitMessageRequest(
                diff_file=diff_file,
                repo_root=repo_root,
                current_branch=current_branch,
                parent_branch=parent_branch,
                commit_messages=commit_messages,
                plan_context=plan_context,
            )
        ):
            event_queue.put(event)
        event_queue.put(None)

    thread = threading.Thread(target=_produce, daemon=True)
    start = time.monotonic()
    thread.start()

    result: CommitMessageResult | None = None
    while True:
        try:
            event = event_queue.get(timeout=_PROGRESS_TIMEOUT_SECONDS)
        except queue.Empty:
            elapsed = int(time.monotonic() - start)
            render_progress(ProgressEvent(f"Still waiting... ({elapsed}s)"))
            continue

        if event is None:
            break
        if isinstance(event, ProgressEvent):
            render_progress(event)
            start = time.monotonic()
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
