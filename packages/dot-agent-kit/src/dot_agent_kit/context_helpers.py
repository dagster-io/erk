"""Helper functions for accessing context dependencies with LBYL checks.

This module provides getter functions that encapsulate the "Look Before You Leap"
pattern for accessing dependencies from ErkContext. These functions:

1. Check that context is initialized
2. Return the typed dependency
3. Exit with clear error message if context is missing

This eliminates code duplication across kit CLI commands.

Note: These helpers are now thin wrappers around erk_shared.context.helpers.
The implementations have been moved to erk_shared for sharing with the erk package.
"""

import click
from erk_shared.context.helpers import get_current_branch as get_current_branch
from erk_shared.context.helpers import require_cwd as require_cwd
from erk_shared.context.helpers import require_git as require_git
from erk_shared.context.helpers import require_github as require_github
from erk_shared.context.helpers import require_issues as _require_issues
from erk_shared.context.helpers import require_project_root as require_project_root
from erk_shared.context.helpers import require_prompt_executor as require_prompt_executor
from erk_shared.context.helpers import require_repo_root as require_repo_root
from erk_shared.context.helpers import require_session_store as require_session_store
from erk_shared.github.issues import GitHubIssues


def require_github_issues(ctx: click.Context) -> GitHubIssues:
    """Get GitHub Issues from context, exiting with error if not initialized.

    Uses LBYL pattern to check context before accessing. If context is not
    initialized (ctx.obj is None), prints error to stderr and exits with code 1.

    Note: This is a compatibility wrapper. The context field is now named 'issues'
    instead of 'github_issues'. New code should use require_issues() directly,
    which is re-exported from erk_shared.context.helpers.

    Args:
        ctx: Click context (must have ErkContext in ctx.obj)

    Returns:
        GitHubIssues instance from context

    Raises:
        SystemExit: If context not initialized (exits with code 1)

    Example:
        >>> @click.command()
        >>> @click.pass_context
        >>> def my_command(ctx: click.Context) -> None:
        ...     github = require_github_issues(ctx)
        ...     github.add_comment(repo_root, issue_number, body)
    """
    return _require_issues(ctx)


# Re-export require_issues for code that prefers the new name
require_issues = _require_issues
