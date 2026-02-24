"""Shared utilities for PR commands.

This module contains common functionality used by multiple PR commands
(rewrite, submit) to avoid code duplication.
"""

from __future__ import annotations

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
from erk_shared.gateway.github.metadata.schemas import LIFECYCLE_STAGE
from erk_shared.gateway.github.pr_footer import (
    build_pr_body_footer,
)
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.diff_extraction import execute_diff_extraction
from erk_shared.plan_store.conversion import header_str
from erk_shared.plan_store.planned_pr_lifecycle import (
    PLAN_CONTENT_SEPARATOR,
    build_original_plan_section,
)
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
                f"   Incorporating plan from issue #{plan_context.plan_id}",
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
        f"<summary><strong>Implementation Plan</strong> (Issue #{issue_num})</summary>",
        "",
        plan_context.plan_content,
        "",
        "</details>",
    ]
    return "\n".join(parts)


def assemble_pr_body(
    *,
    body: str,
    plan_context: PlanContext | None,
    pr_number: int,
    issue_number: int | None,
    plans_repo: str | None,
    header: str,
    metadata_prefix: str,
) -> str:
    """Assemble final PR body with plan details and footer.

    Args:
        body: AI-generated body content
        plan_context: Optional plan context for <details> section
        pr_number: PR number for footer checkout command
        issue_number: Optional issue number for "Closes #N"
        plans_repo: Optional plans repo for cross-repo references
        header: Existing PR header to preserve (may be empty)
        metadata_prefix: Draft PR metadata block + separator to preserve.
            When non-empty, uses original-plan details format instead of
            issue-based plan details format.

    Returns:
        Complete PR body ready for GitHub API
    """
    pr_body_content = body
    if plan_context is not None:
        if metadata_prefix:
            # Draft PR: use original-plan format (from lifecycle module)
            pr_body_content = body + build_original_plan_section(plan_context.plan_content)
        else:
            # Issue-based: use existing format
            pr_body_content = body + build_plan_details_section(plan_context)

    footer = build_pr_body_footer(
        pr_number,
        issue_number=issue_number,
        plans_repo=plans_repo,
    )

    # Place metadata and header below content, above footer
    suffix = ""
    if metadata_prefix:
        # Strip the content separator that was used when metadata was at top
        stripped = metadata_prefix
        if stripped.endswith(PLAN_CONTENT_SEPARATOR):
            stripped = stripped[: -len(PLAN_CONTENT_SEPARATOR)]
        suffix = "\n\n" + stripped
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
) -> CommitMessageResult:
    """Run commit message generation and return result.

    Args:
        generator: CommitMessageGenerator instance
        diff_file: Path to the diff file
        repo_root: Repository root path
        current_branch: Current branch name
        parent_branch: Parent branch name
        commit_messages: Optional list of existing commit messages for context
        plan_context: Optional plan context from linked erk-plan issue
        debug: Whether to show debug output (currently unused, progress always shown)

    Returns:
        CommitMessageResult with the generated title/body or error info
    """
    result: CommitMessageResult | None = None

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
        if isinstance(event, ProgressEvent):
            render_progress(event)
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
