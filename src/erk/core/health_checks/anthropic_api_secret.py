"""Check if Anthropic API authentication secrets exist in the repository."""

from pathlib import Path

from erk.core.context import ErkContext
from erk.core.health_checks.models import CheckResult
from erk_shared.gateway.github_admin.abc import GitHubAdmin


def check_anthropic_api_secret(ctx: ErkContext, repo_root: Path, admin: GitHubAdmin) -> CheckResult:
    """Check if Anthropic API authentication secrets exist in the repository.

    Claude Code can authenticate via:
    - ANTHROPIC_API_KEY: Direct API key (takes precedence)
    - CLAUDE_CODE_OAUTH_TOKEN: OAuth token for Claude Max subscribers

    This is an info-level check - it always passes, but informs users
    whether authentication secrets are configured for GitHub Actions workflows.

    Args:
        ctx: ErkContext for repository access
        repo_root: Path to the repository root
        admin: GitHubAdmin implementation for API calls

    Returns:
        CheckResult with info about authentication secret status
    """
    api_key_secret = "ANTHROPIC_API_KEY"
    oauth_token_secret = "CLAUDE_CODE_OAUTH_TOKEN"

    # Need GitHub identity to check secrets
    try:
        remote_url = ctx.git.remote.get_remote_url(repo_root, "origin")
    except ValueError:
        return CheckResult(
            name="anthropic-api-secret",
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
            name="anthropic-api-secret",
            passed=True,  # Info level
            message="Not a GitHub repository",
            info=True,
        )

    repo_id = GitHubRepoId(owner=owner_repo[0], repo=owner_repo[1])
    location = GitHubRepoLocation(root=repo_root, repo_id=repo_id)

    api_key_exists = admin.secret_exists(location, api_key_secret)
    oauth_token_exists = admin.secret_exists(location, oauth_token_secret)

    # Handle API errors (None return means error)
    if api_key_exists is None and oauth_token_exists is None:
        return CheckResult(
            name="anthropic-api-secret",
            passed=True,  # Info level - don't fail on API errors
            message="Could not check secret status",
            info=True,
        )

    # Both secrets exist
    if api_key_exists is True and oauth_token_exists is True:
        return CheckResult(
            name="anthropic-api-secret",
            passed=True,
            message=f"Both {api_key_secret} and {oauth_token_secret} configured",
            details=f"{api_key_secret} takes precedence",
        )

    # Only API key exists
    if api_key_exists is True:
        return CheckResult(
            name="anthropic-api-secret",
            passed=True,
            message=f"{api_key_secret} configured",
        )

    # Only OAuth token exists
    if oauth_token_exists is True:
        return CheckResult(
            name="anthropic-api-secret",
            passed=True,
            message=f"{oauth_token_secret} configured",
        )

    # Neither secret is configured
    remediation = (
        "To run Claude in GitHub Actions, configure one of:\n"
        f"  - {api_key_secret}: Settings > Secrets > Actions > New repository secret\n"
        f"  - {oauth_token_secret}: For Claude Max subscribers (OAuth flow)\n"
        f"{api_key_secret} takes precedence if both are set."
    )
    return CheckResult(
        name="anthropic-api-secret",
        passed=True,  # Info level - always passes
        message="No Anthropic authentication secret configured",
        details="Required for Claude in GitHub Actions",
        info=True,
        remediation=remediation,
    )
