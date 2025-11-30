"""Production implementation of issue-linked branch development using gh CLI."""

import logging
from pathlib import Path

from erk_shared.github.issue_link_branches import DevelopmentBranch, IssueLinkBranches
from erk_shared.subprocess_utils import execute_gh_command

logger = logging.getLogger(__name__)


class RealIssueLinkBranches(IssueLinkBranches):
    """Production implementation using gh issue develop.

    Uses GitHub CLI to create branches that are automatically linked to issues,
    appearing in the issue sidebar under "Development".
    """

    def __init__(self) -> None:
        """Initialize RealIssueLinkBranches."""

    def create_development_branch(
        self,
        repo_root: Path,
        issue_number: int,
        *,
        branch_name: str,
        base_branch: str | None = None,
    ) -> DevelopmentBranch:
        """Create a development branch linked to an issue via gh issue develop.

        If a development branch already exists for the issue, returns that
        branch with already_existed=True.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, or command error).
        """
        logger.debug(
            "create_development_branch: repo_root=%s, issue_number=%d, "
            "branch_name=%s, base_branch=%s",
            repo_root,
            issue_number,
            branch_name,
            base_branch,
        )

        # Check for existing linked branch first
        logger.debug("Checking for existing linked branch...")
        existing = self.get_linked_branch(repo_root, issue_number)
        if existing is not None:
            logger.debug("Found existing linked branch: %s", existing)
            return DevelopmentBranch(
                branch_name=existing,
                issue_number=issue_number,
                already_existed=True,
            )

        # Create via gh issue develop with explicit branch name
        logger.debug("No existing linked branch. Creating new one...")
        cmd = ["gh", "issue", "develop", str(issue_number), "--name", branch_name]
        if base_branch is not None:
            cmd.extend(["--base", base_branch])

        logger.debug("About to execute: %s", " ".join(cmd))
        execute_gh_command(cmd, repo_root)
        logger.debug("gh issue develop command completed")

        return DevelopmentBranch(
            branch_name=branch_name,
            issue_number=issue_number,
            already_existed=False,
        )

    def get_linked_branch(
        self,
        repo_root: Path,
        issue_number: int,
    ) -> str | None:
        """Get existing development branch linked to an issue.

        Uses gh issue develop --list to check for existing linked branches.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, or command error).
        """
        logger.debug("get_linked_branch: repo_root=%s, issue_number=%d", repo_root, issue_number)
        cmd = ["gh", "issue", "develop", "--list", str(issue_number)]
        logger.debug("Executing: %s", " ".join(cmd))
        stdout = execute_gh_command(cmd, repo_root)
        logger.debug("Raw stdout: %s", repr(stdout))

        # Parse output - gh issue develop --list outputs branch names, one per line
        # If no branches are linked, output is empty
        lines = stdout.strip().split("\n") if stdout.strip() else []
        logger.debug("Parsed lines: %s", lines)

        if not lines:
            logger.debug("No linked branches found")
            return None

        # Return the first linked branch (there may be multiple)
        # gh issue develop --list outputs: "branch-name\tURL" - extract just the branch name
        branch = lines[0].split("\t")[0]
        logger.debug("Returning linked branch: %s", branch)
        return branch
