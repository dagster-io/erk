"""GitHub Admin operations for workflow and authentication.

This package provides the ABC and types for GitHub Actions admin operations.
"""

from erk_shared.github_admin.abc import AuthStatus, GitHubAdmin
from erk_shared.github_admin.fake import FakeGitHubAdmin

__all__ = ["AuthStatus", "GitHubAdmin", "FakeGitHubAdmin"]
