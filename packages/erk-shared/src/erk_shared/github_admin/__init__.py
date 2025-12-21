"""GitHub Admin operations for workflow and authentication.

This package provides the ABC and types for GitHub Actions admin operations.
"""

from erk_shared.github_admin.abc import AuthStatus as AuthStatus
from erk_shared.github_admin.abc import GitHubAdmin as GitHubAdmin
from erk_shared.github_admin.fake import FakeGitHubAdmin as FakeGitHubAdmin
