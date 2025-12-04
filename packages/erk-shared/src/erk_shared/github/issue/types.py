"""Data types for GitHub issue operations.

Re-exports from erk_shared.github.issues.types for backwards compatibility,
plus issue-linked branch types.
"""

from dataclasses import dataclass

from erk_shared.github.issues.types import (
    CreateIssueResult as CreateIssueResult,
)
from erk_shared.github.issues.types import (
    IssueComment as IssueComment,
)
from erk_shared.github.issues.types import (
    IssueInfo as IssueInfo,
)


@dataclass(frozen=True)
class DevelopmentBranch:
    """Result of creating or getting an issue-linked development branch.

    Attributes:
        branch_name: The branch name (e.g., "123-my-feature")
        issue_number: The GitHub issue number this branch is linked to
        already_existed: True if the branch already existed, False if newly created
    """

    branch_name: str
    issue_number: int
    already_existed: bool
