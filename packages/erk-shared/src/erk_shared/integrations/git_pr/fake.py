"""Fake implementations of git-only PR operations for testing.

This module provides in-memory fake implementations for use in tests.
Mirrors the pattern from erk_shared.integrations.gt.fake.

Design:
- FakeGitPrKit composes FakeGit and FakeGitHub
- Allows injection of pre-configured state for testing
- No subprocess calls or real git/GitHub operations
"""

from erk_shared.git.abc import Git
from erk_shared.git.fake import FakeGit
from erk_shared.github.abc import GitHub
from erk_shared.github.fake import FakeGitHub


class FakeGitPrKit:
    """Fake composite operations implementation for testing.

    Combines FakeGit and FakeGitHub for test isolation.
    Satisfies the GitPrKit Protocol through structural typing.

    Pass in pre-configured FakeGit and FakeGitHub instances
    to control test behavior.
    """

    git: Git
    github: GitHub

    def __init__(
        self,
        *,
        git: FakeGit | None = None,
        github: FakeGitHub | None = None,
    ) -> None:
        """Create FakeGitPrKit with injected fakes.

        Args:
            git: Pre-configured FakeGit instance. Created empty if None.
            github: Pre-configured FakeGitHub instance. Created empty if None.
        """
        self.git = git if git is not None else FakeGit()
        self.github = github if github is not None else FakeGitHub()
