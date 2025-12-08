"""Real subprocess-based implementations of git-only PR operations interfaces.

This module provides concrete implementations that wrap subprocess.run calls
for git and GitHub CLI commands. These are the production implementations
used by git-only PR workflow CLI commands (no Graphite required).

Design:
- RealGitPrKit composes git and GitHub (from erk_shared.github)
- Satisfies GitPrKit Protocol through structural typing
- Uses existing RealGit and RealGitHub implementations
"""

from erk_shared.git.abc import Git
from erk_shared.git.real import RealGit
from erk_shared.github.abc import GitHub
from erk_shared.github.real import RealGitHub
from erk_shared.integrations.time.real import RealTime


class RealGitPrKit:
    """Real composite operations implementation for git-only PR workflows.

    Combines real git and GitHub operations for production use.
    Satisfies the GitPrKit Protocol through structural typing.

    Unlike RealGtKit, this does not include Graphite operations.
    """

    git: Git
    github: GitHub

    def __init__(self) -> None:
        """Initialize real operations instances."""
        self.git = RealGit()
        self.github = RealGitHub(time=RealTime())
