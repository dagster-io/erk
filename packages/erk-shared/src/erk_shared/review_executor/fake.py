"""Fake implementation of ReviewExecutor for testing."""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.review_executor.abc import ReviewExecutor


@dataclass(frozen=True)
class ReviewCall:
    """Record of a review execution call."""

    prompt: str
    model: str
    tools: tuple[str, ...] | None
    cwd: Path


class FakeReviewExecutor(ReviewExecutor):
    """In-memory fake implementation of ReviewExecutor for testing.

    Constructor injection pattern: all behavior is configured via constructor
    parameters. No magic, no post-construction setup methods.

    Attributes:
        review_calls: Read-only list of all review calls made (for assertions)

    Example:
        >>> executor = FakeReviewExecutor(exit_code=0)
        >>> result = executor.execute_review(
        ...     prompt="Review this code",
        ...     model="claude-sonnet-4-5",
        ...     tools=["Read"],
        ...     cwd=Path("/fake/repo"),
        ... )
        >>> assert result == 0
        >>> assert len(executor.review_calls) == 1
        >>> assert executor.review_calls[0].model == "claude-sonnet-4-5"
    """

    def __init__(
        self,
        *,
        exit_code: int = 0,
        is_available: bool = True,
    ) -> None:
        """Create FakeReviewExecutor with pre-configured behavior.

        Args:
            exit_code: Exit code to return from execute_review (default: 0 for success)
            is_available: Whether is_available() returns True (default: True)
        """
        self._exit_code = exit_code
        self._is_available = is_available
        self._review_calls: list[ReviewCall] = []

    @property
    def review_calls(self) -> list[ReviewCall]:
        """Read-only access to recorded review calls."""
        return self._review_calls

    def execute_review(
        self,
        prompt: str,
        *,
        model: str,
        tools: list[str] | None,
        cwd: Path,
    ) -> int:
        """Execute a review and return configured exit code.

        Records the call for later assertion.

        Args:
            prompt: The review prompt text
            model: Model to use
            tools: Allowed tools
            cwd: Working directory

        Returns:
            Pre-configured exit code
        """
        self._review_calls.append(
            ReviewCall(
                prompt=prompt,
                model=model,
                tools=tuple(tools) if tools is not None else None,
                cwd=cwd,
            )
        )
        return self._exit_code

    def is_available(self) -> bool:
        """Return pre-configured availability."""
        return self._is_available
