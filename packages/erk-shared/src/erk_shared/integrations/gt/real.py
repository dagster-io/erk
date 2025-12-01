"""Real subprocess-based implementations of GT kit operations interfaces.

This module provides concrete implementations that wrap subprocess.run calls
for git and Graphite (gt) commands. These are the production implementations
used by GT kit CLI commands.

Design:
- Each implementation wraps existing subprocess patterns from CLI commands
- Returns match interface contracts (str | None, bool, tuple)
- Uses check=False to allow LBYL error handling
- RealGtKit composes git, main_graphite, and GitHub (from erk_shared.github)
"""

from erk_shared.git.abc import Git
from erk_shared.git.real import RealGit
from erk_shared.github.abc import GitHub
from erk_shared.github.real import RealGitHub
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.real import RealGraphite
from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.time.real import RealTime


class RealGtKit(GtKit):
    """Real composite operations implementation.

    Combines real git, GitHub, and Graphite operations for production use.
    GitHub operations now use the main RealGitHub from erk_shared.github
    which provides repo_root-based methods.
    """

    def __init__(self) -> None:
        """Initialize real operations instances."""
        self._git = RealGit()
        self._github = RealGitHub(time=RealTime())
        self._main_graphite = RealGraphite()

    def git(self) -> Git:
        """Get the git operations interface."""
        return self._git

    def github(self) -> GitHub:
        """Get the GitHub operations interface."""
        return self._github

    def main_graphite(self) -> Graphite:
        """Get the main Graphite operations interface."""
        return self._main_graphite
