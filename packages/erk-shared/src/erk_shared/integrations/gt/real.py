"""Real subprocess-based implementations of GT kit operations interfaces.

This module provides concrete implementations that wrap subprocess.run calls
for git and Graphite (gt) commands. These are the production implementations
used by GT kit CLI commands.

Design:
- Each implementation wraps existing subprocess patterns from CLI commands
- Returns match interface contracts (str | None, bool, tuple)
- Uses check=False to allow LBYL error handling
- RealGtKit composes git, graphite, and GitHub (from erk_shared.github)
- Satisfies GtKit Protocol through structural typing
"""

from pathlib import Path

from erk_shared.context.factories import get_repo_info
from erk_shared.git.abc import Git
from erk_shared.git.real import RealGit
from erk_shared.github.abc import GitHub
from erk_shared.github.real import RealGitHub
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.real import RealGraphite
from erk_shared.integrations.time.abc import Time
from erk_shared.integrations.time.real import RealTime


class RealGtKit:
    """Real composite operations implementation.

    Combines real git, GitHub, and Graphite operations for production use.
    Satisfies the GtKit Protocol through structural typing.

    GitHub operations now use the main RealGitHub from erk_shared.github
    which provides repo_root-based methods.
    """

    git: Git
    github: GitHub
    graphite: Graphite
    time: Time

    def __init__(self, cwd: Path) -> None:
        """Initialize real operations instances.

        Args:
            cwd: Working directory for determining repo info. Required for
                 GitHub operations that need repo_info (like get_pr_for_branch).
        """
        self.time = RealTime()
        self.git = RealGit()

        # Compute repo_info from cwd
        repo_root = self.git.get_repository_root(cwd)
        repo_info = get_repo_info(self.git, repo_root)

        self.github = RealGitHub(time=self.time, repo_info=repo_info)
        self.graphite = RealGraphite()
