"""Commit message generation via Claude CLI.

This module provides commit message generation for PR submissions,
using Claude CLI to analyze diffs and generate descriptive messages.
"""

from dataclasses import dataclass
from pathlib import Path

from erk.core.claude_executor import ClaudeExecutor


@dataclass
class CommitMessageRequest:
    """Request for generating a commit message.

    Attributes:
        diff_file: Path to the file containing the diff content
        repo_root: Path to the repository root directory
        current_branch: Name of the current branch
        parent_branch: Name of the parent branch
    """

    diff_file: Path
    repo_root: Path
    current_branch: str
    parent_branch: str


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


# System prompt for commit message generation
COMMIT_MESSAGE_PROMPT = """You are a commit message generator. \
Analyze the provided git diff and return ONLY a commit message.

## Output Format

[Clear one-line PR title describing the change]

[2-3 sentence summary explaining what changed and why]

## Files Changed

### Added (N files)
- `path/to/file.py` - Purpose

### Modified (N files)
- `path/to/file.py` - What changed

## Key Changes

- [3-5 component-level changes]

## Rules

- Output ONLY the commit message (no preamble, no explanation)
- NO Claude attribution or footer
- Use relative paths from repository root
- Be concise (15-30 lines total)
- First line = PR title, rest = PR body
"""


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

    def generate(self, request: CommitMessageRequest) -> CommitMessageResult:
        """Generate commit message from diff.

        Reads the diff file, sends it to Claude with the commit message prompt,
        and parses the response into title and body.

        Args:
            request: CommitMessageRequest with diff file and context

        Returns:
            CommitMessageResult with title/body on success, or error on failure
        """
        # LBYL: Check diff file exists
        if not request.diff_file.exists():
            return CommitMessageResult(
                success=False,
                title=None,
                body=None,
                error_message=f"Diff file not found: {request.diff_file}",
            )

        # Read diff content
        diff_content = request.diff_file.read_text(encoding="utf-8")
        if not diff_content.strip():
            return CommitMessageResult(
                success=False,
                title=None,
                body=None,
                error_message="Diff file is empty",
            )

        # Build prompt with context
        prompt = self._build_prompt(
            diff_content=diff_content,
            current_branch=request.current_branch,
            parent_branch=request.parent_branch,
        )

        # Execute prompt via Claude CLI
        result = self._executor.execute_prompt(
            prompt,
            model=self._model,
            cwd=request.repo_root,
        )

        if not result.success:
            return CommitMessageResult(
                success=False,
                title=None,
                body=None,
                error_message=result.error or "Claude CLI execution failed",
            )

        # Parse output into title and body
        title, body = self._parse_output(result.output)

        return CommitMessageResult(
            success=True,
            title=title,
            body=body,
            error_message=None,
        )

    def _build_prompt(
        self,
        diff_content: str,
        current_branch: str,
        parent_branch: str,
    ) -> str:
        """Build the full prompt with diff and context."""
        return f"""{COMMIT_MESSAGE_PROMPT}

## Context

- Current branch: {current_branch}
- Parent branch: {parent_branch}

## Diff

```diff
{diff_content}
```

Generate a commit message for this diff:"""

    def _parse_output(self, output: str) -> tuple[str, str]:
        """Parse Claude output into title and body.

        The first non-empty line is the title, the rest is the body.

        Args:
            output: Raw output from Claude

        Returns:
            Tuple of (title, body)
        """
        lines = output.strip().split("\n")

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
