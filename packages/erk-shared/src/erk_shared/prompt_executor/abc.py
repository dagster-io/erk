"""Abstract base class for prompt execution.

This provides a minimal interface for executing single-shot prompts via Claude CLI,
designed for use in kit CLI commands that need to generate content via AI.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PromptResult:
    """Result of executing a single prompt.

    Attributes:
        success: Whether the prompt completed successfully
        output: The output text from Claude (empty string on failure)
        error: Error message if command failed, None otherwise
    """

    success: bool
    output: str
    error: str | None


class PromptExecutor(ABC):
    """Abstract interface for executing single-shot prompts.

    This is a minimal abstraction for Claude CLI prompt execution,
    designed for dependency injection in kit CLI commands.

    Unlike the full ClaudeExecutor in erk core, this only supports
    single-shot prompts (no streaming, no interactive commands).

    Example:
        >>> executor = RealPromptExecutor()
        >>> result = executor.execute_prompt(
        ...     "Generate a commit message for this diff",
        ...     model="haiku",
        ...     cwd=repo_root,
        ... )
        >>> if result.success:
        ...     print(result.output)
    """

    @abstractmethod
    def execute_prompt(
        self,
        prompt: str,
        *,
        model: str = "haiku",
        cwd: Path | None = None,
    ) -> PromptResult:
        """Execute a single prompt and return the result.

        Args:
            prompt: The prompt text to send to Claude
            model: Model to use (default "haiku" for speed/cost)
            cwd: Optional working directory for the command

        Returns:
            PromptResult with success status and output text
        """
        ...
