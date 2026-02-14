"""Shared utilities for PR commands.

This module contains common functionality used by multiple PR commands
(rewrite, submit) to avoid code duplication.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import click

from erk.core.commit_message_generator import (
    CommitMessageGenerator,
    CommitMessageRequest,
    CommitMessageResult,
)
from erk.core.context import ErkContext
from erk_shared.gateway.github.pr_footer import (
    build_pr_body_footer,
    extract_closing_reference,
    extract_footer_from_body,
)
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.impl_folder import validate_issue_linkage

if TYPE_CHECKING:
    from erk.core.plan_context_provider import PlanContext


# ---------------------------------------------------------------------------
# PR Body Assembly
# ---------------------------------------------------------------------------


def build_plan_details_section(plan_context: PlanContext) -> str:
    """Build a collapsed <details> section embedding the plan in the PR body."""
    issue_num = plan_context.issue_number
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


def discover_issue_for_footer(
    *,
    impl_dir: Path,
    branch_name: str,
    existing_pr_body: str | None,
    plans_repo: str | None,
) -> IssueDiscovery:
    """Discover issue number for PR footer from .impl/ or existing PR body.

    Tries two sources in order:
    1. .impl/issue.json or branch name pattern (P{N}-{slug})
    2. Closing reference in existing PR footer (fallback)

    Args:
        impl_dir: Path to .impl/ directory
        branch_name: Current git branch name
        existing_pr_body: Current PR body text (for closing ref fallback)
        plans_repo: Default plans_repo from local config

    Returns:
        IssueDiscovery with issue_number and plans_repo
    """
    # Primary: discover from .impl/issue.json or branch name
    issue_number: int | None = None
    try:
        issue_number = validate_issue_linkage(impl_dir, branch_name)
    except ValueError:
        pass

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
) -> str:
    """Assemble final PR body with plan details and footer.

    Args:
        body: AI-generated body content
        plan_context: Optional plan context for <details> section
        pr_number: PR number for footer checkout command
        issue_number: Optional issue number for "Closes #N"
        plans_repo: Optional plans repo for cross-repo references
        header: Existing PR header to preserve (may be empty)

    Returns:
        Complete PR body ready for GitHub API
    """
    pr_body_content = body
    if plan_context is not None:
        pr_body_content = body + build_plan_details_section(plan_context)

    metadata_section = build_pr_body_footer(
        pr_number,
        issue_number=issue_number,
        plans_repo=plans_repo,
    )
    return header + pr_body_content + metadata_section


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
