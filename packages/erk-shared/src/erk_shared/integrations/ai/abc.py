"""Abstract base class for AI executor operations.

Provides an abstraction for invoking Claude from Python operations,
enabling testability and separation of concerns. Operations orchestrate;
Claude generates content.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommitMessageResult:
    """Result from generating a commit message.

    Attributes:
        title: The PR title (first line of commit message)
        body: The PR body (remaining lines of commit message)
    """

    title: str
    body: str


class ClaudeCLIExecutor(ABC):
    """Abstract interface for AI content generation.

    Provides narrowly-scoped AI generation operations that can be called
    from Python operations. Each method corresponds to a specific AI task.
    """

    @abstractmethod
    def generate_commit_message(
        self,
        diff_file: Path,
        repo_root: Path,
        current_branch: str,
        parent_branch: str,
    ) -> CommitMessageResult:
        """Generate commit message from a diff file.

        Invokes an AI model to analyze the diff and produce a structured
        commit message suitable for a pull request.

        Args:
            diff_file: Path to the diff file to analyze
            repo_root: Repository root directory
            current_branch: Name of the current branch
            parent_branch: Name of the parent branch

        Returns:
            CommitMessageResult with title and body

        Raises:
            RuntimeError: If AI generation fails
        """
        ...
