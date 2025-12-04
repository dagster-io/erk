"""GitHub issues integration for erk plan storage.

This package provides an abstract interface and implementations for GitHub issue operations.
"""

from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.github.issues.dry_run import DryRunGitHubIssues
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.real import RealGitHubIssues
from erk_shared.github.issues.types import CreateIssueResult, IssueInfo

__all__ = [
    "CreateIssueResult",
    "DryRunGitHubIssues",
    "FakeGitHubIssues",
    "GitHubIssues",
    "IssueInfo",
    "RealGitHubIssues",
]
