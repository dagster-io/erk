"""Fake implementation of PromptExecutor for testing."""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.prompt_executor.abc import PromptExecutor, PromptResult


@dataclass
class PromptCall:
    """Record of a prompt execution call."""

    prompt: str
    model: str
    cwd: Path | None


class FakePromptExecutor(PromptExecutor):
    """In-memory fake implementation of PromptExecutor for testing.

    Constructor injection pattern: all behavior is configured via constructor
    parameters. No magic, no post-construction setup methods.

    Attributes:
        prompt_calls: Read-only list of all prompt calls made (for assertions)

    Example:
        >>> executor = FakePromptExecutor(output="Generated summary text")
        >>> result = executor.execute_prompt("Generate summary", model="haiku")
        >>> assert result.success
        >>> assert result.output == "Generated summary text"
        >>> assert len(executor.prompt_calls) == 1
    """

    def __init__(
        self,
        *,
        output: str = "Fake output",
        error: str | None = None,
        should_fail: bool = False,
    ) -> None:
        """Create FakePromptExecutor with pre-configured behavior.

        Args:
            output: Output to return on successful calls
            error: Error message to return on failure (requires should_fail=True)
            should_fail: If True, execute_prompt returns failure
        """
        self._output = output
        self._error = error
        self._should_fail = should_fail
        self._prompt_calls: list[PromptCall] = []

    @property
    def prompt_calls(self) -> list[PromptCall]:
        """Read-only access to recorded prompt calls."""
        return self._prompt_calls

    def execute_prompt(
        self,
        prompt: str,
        *,
        model: str = "haiku",
        cwd: Path | None = None,
    ) -> PromptResult:
        """Execute a prompt and return configured result.

        Records the call for later assertion.

        Args:
            prompt: The prompt text
            model: Model to use
            cwd: Working directory

        Returns:
            PromptResult based on configured behavior
        """
        self._prompt_calls.append(PromptCall(prompt=prompt, model=model, cwd=cwd))

        if self._should_fail:
            return PromptResult(
                success=False,
                output="",
                error=self._error or "Simulated failure",
            )

        return PromptResult(
            success=True,
            output=self._output,
            error=None,
        )
