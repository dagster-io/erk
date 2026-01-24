"""Shared utilities for PR commands.

This module contains common functionality used by multiple PR commands
(summarize, submit) to avoid code duplication.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import click

from erk.core.commit_message_generator import (
    CommitMessageGenerator,
    CommitMessageRequest,
    CommitMessageResult,
)
from erk.core.context import ErkContext
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent

if TYPE_CHECKING:
    from erk.core.plan_context_provider import PlanContext


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
        ctx: ErkContext providing claude_executor

    Raises:
        click.ClickException: If Claude CLI is not available
    """
    if not ctx.claude_executor.is_claude_available():
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
