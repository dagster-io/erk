"""Context for erk-dev CLI commands.

Provides dependency injection for gateways (Git, GitHub, etc.) to enable
testing with fakes instead of mocks.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.git.dry_run import DryRunGit
from erk_shared.gateway.git.real import RealGit
from erk_shared.gateway.github.abc import LocalGitHub
from erk_shared.gateway.github.issues.real import RealGitHubIssues
from erk_shared.gateway.github.real import RealLocalGitHub
from erk_shared.gateway.time.real import RealTime


@dataclass(frozen=True)
class ErkDevContext:
    """Context object for erk-dev commands.

    Contains gateways that can be injected for testing.
    """

    git: Git
    github: LocalGitHub
    repo_root: Path


def create_context(*, dry_run: bool = False) -> ErkDevContext:
    """Create a context with real or dry-run implementations.

    Args:
        dry_run: If True, wrap Git in DryRunGit to prevent mutations.

    Returns:
        ErkDevContext with appropriate gateway implementations.
    """
    git: Git = RealGit()
    if dry_run:
        git = DryRunGit(git)

    time = RealTime()
    github_issues = RealGitHubIssues(target_repo=None, time=time)
    github: LocalGitHub = RealLocalGitHub(time=time, repo_info=None, issues=github_issues)

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    repo_root = Path(result.stdout.strip()) if result.returncode == 0 else Path.cwd()

    return ErkDevContext(git=git, github=github, repo_root=repo_root)
