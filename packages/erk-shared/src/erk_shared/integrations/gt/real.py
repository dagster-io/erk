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

from erk_shared.git.abc import Git
from erk_shared.git.real import RealGit
from erk_shared.github.auth.real import RealGitHubAuthGateway
from erk_shared.github.gateway import GitHubGateway
from erk_shared.github.issue.real import RealGitHubIssueGateway
from erk_shared.github.pr.real import RealGitHubPrGateway
from erk_shared.github.repo.real import RealGitHubRepoGateway
from erk_shared.github.run.real import RealGitHubRunGateway
from erk_shared.github.workflow.real import RealGitHubWorkflowGateway
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.real import RealGraphite
from erk_shared.integrations.time.real import RealTime


class RealGtKit:
    """Real composite operations implementation.

    Combines real git, GitHub, and Graphite operations for production use.
    Satisfies the GtKit Protocol through structural typing.

    GitHub operations use the GitHubGateway composite which provides access to
    sub-gateways (pr, issue, run, workflow, auth, repo) for different operations.
    """

    git: Git
    github: GitHubGateway
    graphite: Graphite

    def __init__(self) -> None:
        """Initialize real operations instances."""
        time = RealTime()
        self.git = RealGit()
        self.github = GitHubGateway(
            auth=RealGitHubAuthGateway(),
            pr=RealGitHubPrGateway(),
            issue=RealGitHubIssueGateway(),
            run=RealGitHubRunGateway(time),
            workflow=RealGitHubWorkflowGateway(time),
            repo=RealGitHubRepoGateway(),
        )
        self.graphite = RealGraphite()
