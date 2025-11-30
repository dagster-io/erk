"""Production implementation of issue-linked branch development using gh CLI."""

from pathlib import Path

from erk_shared.github.issue_development import DevelopmentBranch, IssueDevelopment
from erk_shared.subprocess_utils import execute_gh_command


class RealIssueDevelopment(IssueDevelopment):
    """Production implementation using gh issue develop.

    Uses GitHub CLI to create branches that are automatically linked to issues,
    appearing in the issue sidebar under "Development".
    """

    def __init__(self) -> None:
        """Initialize RealIssueDevelopment."""

    def create_development_branch(
        self,
        repo_root: Path,
        issue_number: int,
        *,
        base_branch: str | None = None,
    ) -> DevelopmentBranch:
        """Create a development branch linked to an issue via gh issue develop.

        If a development branch already exists for the issue, returns that
        branch with already_existed=True.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, or command error).
        """
        # Check for existing linked branch first
        existing = self.get_linked_branch(repo_root, issue_number)
        if existing is not None:
            return DevelopmentBranch(
                branch_name=existing,
                issue_number=issue_number,
                already_existed=True,
            )

        # Create via gh issue develop
        cmd = ["gh", "issue", "develop", str(issue_number)]
        if base_branch is not None:
            cmd.extend(["--base", base_branch])

        stdout = execute_gh_command(cmd, repo_root)
        branch_name = stdout.strip()

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
        cmd = ["gh", "issue", "develop", "--list", str(issue_number)]
        stdout = execute_gh_command(cmd, repo_root)

        # Parse output - gh issue develop --list outputs branch names, one per line
        # If no branches are linked, output is empty
        lines = stdout.strip().split("\n") if stdout.strip() else []

        if not lines:
            return None

        # Return the first linked branch (there may be multiple)
        return lines[0]
