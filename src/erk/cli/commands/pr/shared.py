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
from erk_shared.gateway.github.pr_footer import (
    build_pr_body_footer,
    extract_closing_reference,
    extract_footer_from_body,
)
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.diff_extraction import execute_diff_extraction
from erk_shared.impl_folder import read_plan_ref
from erk_shared.naming import extract_leading_issue_number
from erk_shared.plan_store.draft_pr_lifecycle import build_original_plan_section

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


@dataclass(frozen=True)
class IssueDiscovery:
    """Result of discovering issue number for PR footer."""

    issue_number: int | None
    plans_repo: str | None


@dataclass(frozen=True)
class IssueLinkageMismatch:
    """Branch name and .impl/issue.json disagree on issue number."""

    message: str


def discover_issue_for_footer(
    *,
    impl_dir: Path,
    branch_name: str,
    existing_pr_body: str | None,
    plans_repo: str | None,
) -> IssueDiscovery | IssueLinkageMismatch:
    """Discover issue number for PR footer from .impl/ or existing PR body.

    Tries two sources in order:
    1. .impl/plan-ref.json (or legacy issue.json) or branch name pattern
       (``P{N}-{slug}`` for issue-based, ``plan-{slug}`` for draft-PR)
    2. Closing reference in existing PR footer (fallback)

    For draft-PR branches (``plan-{slug}-{timestamp}``), ``branch_issue`` is None,
    so the function relies entirely on plan-ref.json for the issue number.

    Args:
        impl_dir: Path to .impl/ directory
        branch_name: Current git branch name
        existing_pr_body: Current PR body text (for closing ref fallback)
        plans_repo: Default plans_repo from local config

    Returns:
        IssueDiscovery with issue_number and plans_repo, or
        IssueLinkageMismatch if branch and .impl/issue.json disagree
    """
    # Primary: discover from .impl/plan-ref.json (or legacy issue.json) or branch name
    # For issue-based branches (P{N}-...), branch_issue is extracted from the prefix.
    # For draft-PR branches (plan-...), branch_issue is None.
    branch_issue = extract_leading_issue_number(branch_name)
    plan_ref = read_plan_ref(impl_dir) if impl_dir.exists() else None
    impl_issue = int(plan_ref.plan_id) if plan_ref is not None else None

    if branch_issue is not None and impl_issue is not None and branch_issue != impl_issue:
        return IssueLinkageMismatch(
            message=(
                f"Branch issue ({branch_issue}) disagrees with "
                f".impl/plan-ref.json (#{impl_issue}). Fix the mismatch before proceeding."
            )
        )

    issue_number = branch_issue if impl_issue is None else impl_issue

    effective_plans_repo = plans_repo

    # Fallback: preserve existing closing reference from PR body
    if issue_number is None and existing_pr_body is not None:
        existing_footer = extract_footer_from_body(existing_pr_body)
        if existing_footer is not None:
            closing_ref = extract_closing_reference(existing_footer)
            if closing_ref is not None:
                issue_number = closing_ref.issue_number
                effective_plans_repo = closing_ref.plans_repo

    return IssueDiscovery(issue_number=issue_number, plans_repo=effective_plans_repo)


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
    return metadata_prefix + header + pr_body_content + footer


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
