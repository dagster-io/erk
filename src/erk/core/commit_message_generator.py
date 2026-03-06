"""Commit message generation via Anthropic API.

This module provides commit message generation for PR submissions,
using direct Anthropic API calls to analyze diffs and generate descriptive messages.

The commit message prompt is loaded from the shared prompt file at:
packages/erk-shared/src/erk_shared/gateway/gt/commit_message_prompt.md
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from erk_shared.core.llm_caller import LlmCaller, LlmCallFailed, LlmResponse, NoApiKey
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.gt.prompts import get_commit_message_prompt
from erk_shared.gateway.time.abc import Time

if TYPE_CHECKING:
    from erk.core.plan_context_provider import PlanContext

logger = logging.getLogger(__name__)

_PROGRESS_INTERVAL_SECONDS = 5.0


@dataclass(frozen=True)
class CommitMessageRequest:
    """Request for generating a commit message.

    Attributes:
        diff_file: Path to the file containing the diff content
        repo_root: Path to the repository root directory
        current_branch: Name of the current branch
        parent_branch: Name of the parent branch
        commit_messages: Optional list of existing commit messages for context
        plan_context: Optional plan context from linked erk plan
    """

    diff_file: Path
    repo_root: Path
    current_branch: str
    parent_branch: str
    commit_messages: list[str] | None
    plan_context: PlanContext | None


@dataclass(frozen=True)
class CommitMessageResult:
    """Result of commit message generation.

    Attributes:
        success: Whether generation succeeded
        title: PR title (first line of commit message) if successful
        body: PR body (remaining lines) if successful
        error_message: Error description if generation failed
    """

    success: bool
    title: str | None
    body: str | None
    error_message: str | None


class CommitMessageGenerator:
    """Generates commit messages via direct Anthropic API calls.

    Uses LlmCaller for fast, direct API access instead of spawning
    a Claude CLI subprocess.
    """

    def __init__(self, llm_caller: LlmCaller, *, time: Time) -> None:
        self._llm_caller = llm_caller
        self._time = time

    def generate(
        self, request: CommitMessageRequest
    ) -> Generator[ProgressEvent | CompletionEvent[CommitMessageResult]]:
        """Generate commit message from diff with progress updates.

        Reads the diff file, sends it to the LLM with the commit message prompt,
        and parses the response into title and body.

        Args:
            request: CommitMessageRequest with diff file and context

        Yields:
            ProgressEvent for status updates
            CompletionEvent with CommitMessageResult on completion
        """
        # LBYL: Check diff file exists
        yield ProgressEvent("Reading diff file...")
        if not request.diff_file.exists():
            yield CompletionEvent(
                CommitMessageResult(
                    success=False,
                    title=None,
                    body=None,
                    error_message=f"Diff file not found: {request.diff_file}",
                )
            )
            return

        # Read diff content
        diff_content = request.diff_file.read_text(encoding="utf-8")
        if not diff_content.strip():
            yield CompletionEvent(
                CommitMessageResult(
                    success=False,
                    title=None,
                    body=None,
                    error_message="Diff file is empty",
                )
            )
            return

        diff_size = len(diff_content)
        yield ProgressEvent(f"Diff loaded ({diff_size:,} chars)", style="success")

        # Build prompt with context
        yield ProgressEvent("Analyzing changes with Claude...")

        user_prompt = self._build_user_prompt(
            diff_content=diff_content,
            current_branch=request.current_branch,
            parent_branch=request.parent_branch,
            commit_messages=request.commit_messages,
            plan_context=request.plan_context,
        )
        system_prompt = get_commit_message_prompt(request.repo_root)

        result_holder: list[LlmResponse | NoApiKey | LlmCallFailed] = []
        error_holder: list[Exception] = []

        def _run_call() -> None:
            try:
                result_holder.append(
                    self._llm_caller.call(user_prompt, system_prompt=system_prompt, max_tokens=4096)
                )
            except Exception as exc:
                error_holder.append(exc)

        thread = threading.Thread(target=_run_call, daemon=True)
        start_time = self._time.monotonic()
        thread.start()

        while thread.is_alive():
            thread.join(timeout=_PROGRESS_INTERVAL_SECONDS)
            if thread.is_alive():
                elapsed = int(self._time.monotonic() - start_time)
                yield ProgressEvent(f"Still waiting... ({elapsed}s)")

        if error_holder:
            yield CompletionEvent(
                CommitMessageResult(
                    success=False,
                    title=None,
                    body=None,
                    error_message=f"LLM call failed: {error_holder[0]}",
                )
            )
            return

        if not result_holder:
            yield CompletionEvent(
                CommitMessageResult(
                    success=False,
                    title=None,
                    body=None,
                    error_message="LLM call completed without result",
                )
            )
            return

        result = result_holder[0]

        if isinstance(result, (NoApiKey, LlmCallFailed)):
            yield CompletionEvent(
                CommitMessageResult(
                    success=False,
                    title=None,
                    body=None,
                    error_message=result.message,
                )
            )
            return

        # Parse output into title and body
        title, body = self._parse_output(result.text)

        yield ProgressEvent("PR description generated", style="success")
        yield CompletionEvent(
            CommitMessageResult(
                success=True,
                title=title,
                body=body,
                error_message=None,
            )
        )

    def _build_context_section(
        self,
        *,
        current_branch: str,
        parent_branch: str,
        commit_messages: list[str] | None,
        plan_context: PlanContext | None,
    ) -> str:
        """Build the context section with branch info, commit messages, and plan context."""
        context_section = f"""## Context

- Current branch: {current_branch}
- Parent branch: {parent_branch}"""

        # Add plan context section if present (highest priority context)
        if plan_context is not None:
            context_section += f"""

## Implementation Plan (Plan #{plan_context.plan_id})

The following plan describes the intent and rationale for these changes:

{plan_context.plan_content}"""

            if plan_context.objective_summary is not None:
                context_section += f"""

### Parent Objective

{plan_context.objective_summary}"""

            context_section += """

Use this plan as the primary source of truth for understanding WHY changes were made."""

        # Add commit messages section if present
        if commit_messages:
            messages_text = "\n\n---\n\n".join(commit_messages)
            context_section += f"""

## Developer's Commit Messages

The following commit messages were written by the developer during implementation:

{messages_text}

Use these commit messages as additional context. They describe the developer's intent
and may contain details not visible in the diff alone."""

        return context_section

    def _build_user_prompt(
        self,
        *,
        diff_content: str,
        current_branch: str,
        parent_branch: str,
        commit_messages: list[str] | None,
        plan_context: PlanContext | None,
    ) -> str:
        """Build user prompt with context and diff only (no system prompt).

        System prompt is passed separately to the LLM caller.
        """
        context_section = self._build_context_section(
            current_branch=current_branch,
            parent_branch=parent_branch,
            commit_messages=commit_messages,
            plan_context=plan_context,
        )

        return f"""{context_section}

## Diff

```diff
{diff_content}
```

Generate a commit message for this diff:"""

    def _parse_output(self, output: str) -> tuple[str, str]:
        """Parse Claude output into title and body.

        The first non-empty line is the title, the rest is the body.
        Handles case where output is wrapped in markdown code fences.

        Args:
            output: Raw output from Claude

        Returns:
            Tuple of (title, body)
        """
        lines = output.strip().split("\n")

        # Strip leading code fence if present (handles ```markdown, ```text, ```, etc.)
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        # Strip trailing code fence if present
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        # Find first non-empty line as title
        title = ""
        body_start_idx = 0
        for i, line in enumerate(lines):
            if line.strip():
                title = line.strip()
                body_start_idx = i + 1
                break

        # Rest is body (skip empty lines between title and body)
        body_lines = lines[body_start_idx:]
        while body_lines and not body_lines[0].strip():
            body_lines = body_lines[1:]

        body = "\n".join(body_lines).strip()

        return title, body
