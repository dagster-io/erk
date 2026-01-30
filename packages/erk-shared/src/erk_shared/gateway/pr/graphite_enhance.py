"""Graphite enhancement utilities for PR submission.

Provides a quick check to determine if Graphite enhancement should proceed.
The actual enhancement logic lives in the submit pipeline.
"""

from pathlib import Path
from typing import NamedTuple

from erk_shared.context.context import ErkContext


class GraphiteCheckResult(NamedTuple):
    """Result of checking if Graphite enhancement should proceed.

    Attributes:
        should_enhance: Whether Graphite enhancement should proceed
        reason: The reason code - one of:
            - "tracked": Branch is tracked and Graphite is authenticated
            - "not_authenticated": Graphite is not authenticated
            - "not_tracked": Branch is not tracked by Graphite
            - "no_branch": Not on a branch (detached HEAD)
    """

    should_enhance: bool
    reason: str


def should_enhance_with_graphite(
    ctx: ErkContext,
    cwd: Path,
) -> GraphiteCheckResult:
    """Check if a PR should be enhanced with Graphite.

    This is a quick check to determine if Graphite enhancement would succeed.
    Use this for UI purposes (showing whether --no-graphite matters).

    Args:
        ctx: ErkContext
        cwd: Working directory

    Returns:
        GraphiteCheckResult with should_enhance and reason fields:
        - (True, "tracked") - Branch is tracked and Graphite is authenticated
        - (False, "not_authenticated") - Graphite is not authenticated
        - (False, "not_tracked") - Branch is not tracked by Graphite
        - (False, "no_branch") - Not on a branch (detached HEAD)
    """
    # Check Graphite auth
    is_authed, _, _ = ctx.graphite.check_auth_status()
    if not is_authed:
        return GraphiteCheckResult(should_enhance=False, reason="not_authenticated")

    # Check if branch is tracked
    repo_root = ctx.git.repo.get_repository_root(cwd)
    branch_name = ctx.git.branch.get_current_branch(cwd)
    if branch_name is None:
        return GraphiteCheckResult(should_enhance=False, reason="no_branch")

    all_branches = ctx.graphite.get_all_branches(ctx.git, repo_root)
    if branch_name not in all_branches:
        return GraphiteCheckResult(should_enhance=False, reason="not_tracked")

    return GraphiteCheckResult(should_enhance=True, reason="tracked")
