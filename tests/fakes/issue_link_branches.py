"""Fake issue-linked branch operations for testing.

FakeIssueLinkBranches is an in-memory implementation that accepts pre-configured state
in its constructor. Construct instances directly with keyword arguments.
"""

from dataclasses import dataclass, field
from pathlib import Path

from erk_shared.github.issue_link_branches import DevelopmentBranch, IssueLinkBranches


@dataclass
class FakeIssueLinkBranches(IssueLinkBranches):
    """In-memory fake implementation of issue-linked branch operations.

    This class has NO public setup methods. All state is provided via constructor
    using keyword arguments with sensible defaults (empty dicts).

    Mutation tracking:
        - _created_branches: List of (issue_number, branch_name) tuples for created branches
    """

    # Pre-configured state: mapping of issue_number -> branch_name
    existing_branches: dict[int, str] = field(default_factory=dict)

    # Mutation tracking (private, read via property)
    _created_branches: list[tuple[int, str]] = field(default_factory=list)

    @property
    def created_branches(self) -> list[tuple[int, str]]:
        """Read-only access to created branches for assertions.

        Returns:
            List of (issue_number, branch_name) tuples
        """
        return list(self._created_branches)

    def create_development_branch(
        self,
        repo_root: Path,
        issue_number: int,
        *,
        base_branch: str | None = None,
    ) -> DevelopmentBranch:
        """Create a fake development branch linked to an issue.

        If a branch already exists for this issue in existing_branches,
        returns it with already_existed=True.

        Otherwise, creates a new branch named "{issue_number}-issue-branch",
        stores it in existing_branches, tracks in _created_branches, and
        returns with already_existed=False.
        """
        if issue_number in self.existing_branches:
            return DevelopmentBranch(
                branch_name=self.existing_branches[issue_number],
                issue_number=issue_number,
                already_existed=True,
            )

        branch_name = f"{issue_number}-issue-branch"
        self._created_branches.append((issue_number, branch_name))
        self.existing_branches[issue_number] = branch_name

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

        Returns the branch from existing_branches if present, None otherwise.
        """
        return self.existing_branches.get(issue_number)
