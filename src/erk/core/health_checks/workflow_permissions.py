"""Check if GitHub Actions workflows can create PRs."""

from pathlib import Path

from erk.core.context import ErkContext
from erk.core.health_checks.models import CheckResult
from erk_shared.gateway.github_admin.abc import GitHubAdmin


def check_workflow_permissions(ctx: ErkContext, repo_root: Path, admin: GitHubAdmin) -> CheckResult:
    """Check if GitHub Actions workflows can create PRs.

    This is an info-level check - it always passes, but shows whether
    PR creation is enabled for workflows. This is required for erk's
    remote implementation feature.

    Args:
        ctx: ErkContext for repository access
        repo_root: Path to the repository root
        admin: GitHubAdmin implementation for API calls

    Returns:
        CheckResult with info about workflow permission status
    """
    # Need GitHub identity to check permissions
    try:
        remote_url = ctx.git.remote.get_remote_url(repo_root, "origin")
    except ValueError:
        return CheckResult(
            name="workflow-permissions",
            passed=True,  # Info level
            message="No origin remote configured",
        )

    # Parse GitHub owner/repo from remote URL
    from erk_shared.gateway.github.parsing import parse_git_remote_url
    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    try:
        owner_repo = parse_git_remote_url(remote_url)
    except ValueError:
        return CheckResult(
            name="workflow-permissions",
            passed=True,  # Info level
            message="Not a GitHub repository",
        )

    repo_id = GitHubRepoId(owner=owner_repo[0], repo=owner_repo[1])
    location = GitHubRepoLocation(root=repo_root, repo_id=repo_id)

    try:
        perms = admin.get_workflow_permissions(location)
        enabled = perms.get("can_approve_pull_request_reviews", False)

        if enabled:
            return CheckResult(
                name="workflow-permissions",
                passed=True,
                message="Workflows can create PRs",
            )
        else:
            return CheckResult(
                name="workflow-permissions",
                passed=True,  # Info level - always passes
                message="Workflows cannot create PRs",
                details="Run 'erk admin github-pr-setting --enable' to allow",
            )
    except Exception:
        return CheckResult(
            name="workflow-permissions",
            passed=True,  # Info level - don't fail on API errors
            message="Could not check workflow permissions",
        )
