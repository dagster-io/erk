"""Real subprocess-based implementations of GT kit operations interfaces.

This module provides concrete implementations that wrap subprocess.run calls
for git and Graphite (gt) commands. These are the production implementations
used by GT kit CLI commands.

Design:
- Each implementation wraps existing subprocess patterns from CLI commands
- Returns match interface contracts (str | None, bool, tuple)
- Uses check=False to allow LBYL error handling
- RealGtKit composes git, graphite, GitHub, and AI (from erk_shared integrations)
- Satisfies GtKit Protocol through structural typing
"""

from erk_shared.git.abc import Git
from erk_shared.git.real import RealGit
from erk_shared.github.abc import GitHub
from erk_shared.github.real import RealGitHub
from erk_shared.integrations.claude.abc import ClaudeExecutor
from erk_shared.integrations.claude.real import RealClaudeExecutor
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.real import RealGraphite
from erk_shared.integrations.time.abc import Time
from erk_shared.integrations.time.real import RealTime


class RealGtKit:
    """Real composite operations implementation.

    Combines real git, GitHub, Graphite, and AI operations for production use.
    Satisfies the GtKit Protocol through structural typing.

    GitHub operations now use the main RealGitHub from erk_shared.github
    which provides repo_root-based methods.
    """

    git: Git
    github: GitHub
    graphite: Graphite
    claude: ClaudeExecutor
    time: Time

    def __init__(self) -> None:
        """Initialize real operations instances."""
        self.time = RealTime()
        self.git = RealGit()
        self.github = RealGitHub(time=self.time)
        self.graphite = RealGraphite()
        self.claude = RealClaudeExecutor()
