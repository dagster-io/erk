"""Compatibility wrapper for require_github_issues.

This module provides the require_github_issues function which is a compatibility
wrapper for the old name. New code should import directly from
erk_shared.context.helpers.

DEPRECATED: Import helpers directly from erk_shared.context.helpers instead:
    from erk_shared.context.helpers import require_git, require_cwd, require_issues
"""

import click

from erk_shared.context.helpers import require_issues
from erk_shared.github.issues import GitHubIssues


def require_github_issues(ctx: click.Context) -> GitHubIssues:
    """Get GitHub Issues from context (DEPRECATED - use require_issues).

    Compatibility wrapper. The context field is now named 'issues'
    instead of 'github_issues'. New code should import and use
    require_issues() from erk_shared.context.helpers directly.

    Args:
        ctx: Click context (must have ErkContext in ctx.obj)

    Returns:
        GitHubIssues instance from context

    Raises:
        SystemExit: If context not initialized (exits with code 1)
    """
    return require_issues(ctx)
