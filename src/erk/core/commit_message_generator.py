"""Commit message generation via Claude CLI.

This module provides commit message generation for PR submissions,
using Claude CLI to analyze diffs and generate descriptive messages.

The commit message prompt is loaded from the shared prompt file at:
packages/erk-shared/src/erk_shared/integrations/gt/commit_message_prompt.md
"""

from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.prompts import COMMIT_MESSAGE_SYSTEM_PROMPT

from erk.core.claude_executor import ClaudeExecutor


@dataclass
class CommitMessageRequest:
    """Request for generating a commit message.

    Attributes:
        diff_file: Path to the file containing the diff content
        repo_root: Path to the repository root directory
        current_branch: Name of the current branch
        parent_branch: Name of the parent branch
        commit_messages: Optional list of existing commit messages for context
    """

    diff_file: Path
    repo_root: Path
    current_branch: str
    parent_branch: str
    commit_messages: list[str] | None = None


@dataclass
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
    """Generates commit messages via Claude CLI.

    This is a concrete class (not ABC) that uses ClaudeExecutor for
    testability. In tests, inject FakeClaudeExecutor with simulated_prompt_output.
    """

    def __init__(self, executor: ClaudeExecutor, model: str = "haiku") -> None:
        """Initialize generator with executor.

        Args:
            executor: Claude CLI executor for prompt execution
            model: Model to use for generation (default "haiku" for speed/cost)
        """
        self._executor = executor
        self._model = model

    def generate(
        self, request: CommitMessageRequest
    ) -> Generator[ProgressEvent | CompletionEvent[CommitMessageResult]]:
        """Generate commit message from diff with progress updates.

        Reads the diff file, sends it to Claude with the commit message prompt,
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

        prompt = self._build_prompt(
            diff_content=diff_content,
            current_branch=request.current_branch,
            parent_branch=request.parent_branch,
            commit_messages=request.commit_messages,
        )

        # Execute prompt via Claude CLI
        result = self._executor.execute_prompt(
            prompt,
            model=self._model,
            cwd=request.repo_root,
        )

        if not result.success:
            yield CompletionEvent(
                CommitMessageResult(
                    success=False,
                    title=None,
                    body=None,
                    error_message=result.error or "Claude CLI execution failed",
                )
            )
            return

        # Parse output into title and body
        title, body = self._parse_output(result.output)

        yield ProgressEvent("PR description generated", style="success")
        yield CompletionEvent(
            CommitMessageResult(
                success=True,
                title=title,
                body=body,
                error_message=None,
            )
        )

    def _build_prompt(
        self,
        diff_content: str,
        current_branch: str,
        parent_branch: str,
        commit_messages: list[str] | None = None,
    ) -> str:
        """Build the full prompt with diff and context."""
        context_section = f"""## Context

- Current branch: {current_branch}
- Parent branch: {parent_branch}"""

        # Add commit messages section if present
        if commit_messages:
            messages_text = "\n\n---\n\n".join(commit_messages)
            context_section += f"""

## Developer's Commit Messages

The following commit messages were written by the developer during implementation:

{messages_text}

Use these commit messages as additional context. They describe the developer's intent
and may contain details not visible in the diff alone."""

        return f"""{COMMIT_MESSAGE_SYSTEM_PROMPT}

{context_section}

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
