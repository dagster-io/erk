"""Claude implementation of ReviewExecutor.

This module provides the real Claude CLI implementation for code review execution.
"""

import shutil
import subprocess
from pathlib import Path

from erk_shared.review_executor.abc import ReviewExecutor


class RealClaudeReviewExecutor(ReviewExecutor):
    """Production implementation using Claude CLI for code reviews.

    Uses the Claude CLI with passthrough output mode, allowing
    Claude's output to stream directly to stdout/stderr.

    Example:
        >>> executor = RealClaudeReviewExecutor()
        >>> if executor.is_available():
        ...     exit_code = executor.execute_review(
        ...         prompt="Review this code...",
        ...         model="claude-sonnet-4-5",
        ...         tools=["Read", "Bash"],
        ...         cwd=repo_root,
        ...     )
    """

    def execute_review(
        self,
        prompt: str,
        *,
        model: str,
        tools: list[str] | None,
        cwd: Path,
    ) -> int:
        """Execute review using Claude CLI with passthrough output.

        Uses subprocess.run with stdin=subprocess.DEVNULL to prevent
        interactive prompts, while allowing stdout/stderr to pass through.

        Args:
            prompt: The review prompt text
            model: Claude model to use (e.g., "claude-sonnet-4-5")
            tools: List of allowed tools or None for defaults
            cwd: Working directory for execution

        Returns:
            Exit code from Claude CLI (0 for success)
        """
        cmd = [
            "claude",
            "--print",
            "-p",
            prompt,
            "--model",
            model,
        ]
        if tools is not None:
            cmd.extend(["--allowedTools", ",".join(tools)])
        cmd.append("--dangerously-skip-permissions")

        result = subprocess.run(
            cmd,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode

    def is_available(self) -> bool:
        """Check if Claude CLI is in PATH."""
        return shutil.which("claude") is not None
