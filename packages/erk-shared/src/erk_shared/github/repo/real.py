"""Production implementation of GitHub repository operations."""

import json
from pathlib import Path

from erk_shared.github.parsing import execute_gh_command
from erk_shared.github.repo.abc import GitHubRepoGateway
from erk_shared.github.types import RepoInfo


class RealGitHubRepoGateway(GitHubRepoGateway):
    """Production implementation using gh CLI.

    All GitHub repository operations execute actual gh commands via subprocess.
    """

    def get_repo_info(self, repo_root: Path) -> RepoInfo:
        """Get repository owner and name from GitHub CLI.

        Uses `gh repo view --json owner,name` to get repo info.

        Raises:
            RuntimeError: If gh command fails (auth issues, network errors, etc.)
        """
        cmd = ["gh", "repo", "view", "--json", "owner,name"]
        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)
        owner = data["owner"]["login"]
        name = data["name"]
        return RepoInfo(owner=owner, name=name)
