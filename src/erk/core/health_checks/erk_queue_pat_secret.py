"""Check if ERK_QUEUE_GH_PAT secret exists in the repository."""

from pathlib import Path

from erk.core.context import ErkContext
from erk.core.health_checks.models import CheckResult
from erk_shared.gateway.github_admin.abc import GitHubAdmin


def check_erk_queue_pat_secret(ctx: ErkContext, repo_root: Path, admin: GitHubAdmin) -> CheckResult:
    """Check if ERK_QUEUE_GH_PAT secret exists in the repository.

    This secret is required for erk's remote implementation queue feature.
    When a GitHub Actions workflow runs, it uses this PAT to authenticate
    when creating PRs on behalf of the user.

    This is an info-level check - it always passes, but informs users
    whether the secret is configured.

    Args:
        ctx: ErkContext for repository access
        repo_root: Path to the repository root
        admin: GitHubAdmin implementation for API calls

    Returns:
        CheckResult with info about secret status
    """
    secret_name = "ERK_QUEUE_GH_PAT"

    # Need GitHub identity to check secrets
    try:
        remote_url = ctx.git.remote.get_remote_url(repo_root, "origin")
    except ValueError:
        return CheckResult(
            name="erk-queue-pat-secret",
            passed=True,  # Info level
            message="No origin remote configured",
            info=True,
        )

    # Parse GitHub owner/repo from remote URL
    from erk_shared.gateway.github.parsing import parse_git_remote_url
    from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

    try:
        owner_repo = parse_git_remote_url(remote_url)
    except ValueError:
        return CheckResult(
            name="erk-queue-pat-secret",
            passed=True,  # Info level
            message="Not a GitHub repository",
            info=True,
        )

    repo_id = GitHubRepoId(owner=owner_repo[0], repo=owner_repo[1])
    location = GitHubRepoLocation(root=repo_root, repo_id=repo_id)

    secret_exists_result = admin.secret_exists(location, secret_name)

    if secret_exists_result is True:
        return CheckResult(
            name="erk-queue-pat-secret",
            passed=True,
            message=f"{secret_name} secret configured",
        )
    elif secret_exists_result is False:
        return CheckResult(
            name="erk-queue-pat-secret",
            passed=True,  # Info level - always passes
            message=f"{secret_name} secret not configured",
            details="Required for remote implementation queue",
            info=True,
        )
    else:
        # None means API error (permissions, rate limit, etc.)
        return CheckResult(
            name="erk-queue-pat-secret",
            passed=True,  # Info level - don't fail on API errors
            message="Could not check secret status",
            info=True,
        )
