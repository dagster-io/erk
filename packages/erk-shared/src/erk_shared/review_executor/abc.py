"""Abstract base class for review execution.

This provides a minimal interface for executing code reviews via different AI providers.
Each provider (Claude, Codex) has its own implementation with provider-specific CLI invocation.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class ReviewExecutor(ABC):
    """Abstract interface for executing code reviews.

    This abstraction enables multi-provider review support by providing
    a common interface for different AI CLI tools.

    Each provider implementation handles its own CLI invocation pattern:
    - Claude: Uses `claude --print -p <prompt> --model <model>`
    - Codex: Uses `codex exec --full-auto <prompt> --model <model>`

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

    @abstractmethod
    def execute_review(
        self,
        prompt: str,
        *,
        model: str,
        tools: list[str] | None,
        cwd: Path,
    ) -> int:
        """Execute review with passthrough output. Returns exit code.

        The review output streams directly to stdout/stderr (passthrough mode).
        This is designed for CI use cases where Claude's output should be
        visible immediately.

        Args:
            prompt: The review prompt text to send to the AI
            model: Model to use (provider-specific, e.g., "claude-sonnet-4-5" or "gpt-5-codex")
            tools: List of allowed tools or None for provider defaults
            cwd: Working directory for execution

        Returns:
            Exit code from the CLI (0 for success, non-zero for failure)
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider CLI is installed and available in PATH.

        Returns:
            True if the provider CLI is available, False otherwise.
        """
        ...
