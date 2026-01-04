#!/usr/bin/env python3
"""Configure git user identity from GitHub username.

This command sets git user.name and user.email configuration based on the
authenticated GitHub username. Useful in CI environments where git identity
needs to be configured before committing.

This replaces bash-based git config in GitHub Actions workflows:
```bash
gh_user=$(gh api user --jq '.login')
git config --local user.name "${gh_user}"
git config --local user.email "${gh_user}@users.noreply.github.com"
```

Usage:
    erk configure-git-user

Output:
    JSON object with success status and configured values

Exit Codes:
    0: Success (git user configured)
    1: Error (not authenticated or git config failed)

Examples:
    $ erk configure-git-user
    {
      "success": true,
      "username": "octocat",
      "email": "octocat@users.noreply.github.com"
    }

    $ erk configure-git-user  # when not authenticated
    {
      "success": false,
      "error": "not_authenticated",
      "message": "GitHub CLI is not authenticated. Run 'gh auth login' first."
    }
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click

from erk_shared.context.helpers import require_cwd, require_git, require_github
from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub


@dataclass(frozen=True)
class ConfiguredUser:
    """Success result with configured user identity."""

    success: bool
    username: str
    email: str


@dataclass(frozen=True)
class ConfigurationError:
    """Error result when user identity cannot be configured."""

    success: bool
    error: Literal["not-authenticated", "config-failed"]
    message: str


def _configure_git_user_impl(
    git: Git, github: GitHub, cwd: Path
) -> ConfiguredUser | ConfigurationError:
    """Configure git user identity from GitHub username.

    Gets the authenticated GitHub username and sets git user.name and user.email
    configuration in the local repository.

    Args:
        git: Git interface for operations
        github: GitHub interface for getting username
        cwd: Current working directory

    Returns:
        ConfiguredUser on success, ConfigurationError if not authenticated or config fails
    """
    # Check GitHub authentication and get username
    is_authenticated, username, _hostname = github.check_auth_status()

    if not is_authenticated or username is None:
        return ConfigurationError(
            success=False,
            error="not-authenticated",
            message="GitHub CLI is not authenticated. Run 'gh auth login' first.",
        )

    # Build email from username (GitHub noreply format)
    email = f"{username}@users.noreply.github.com"

    # Set git config
    git.config_set(cwd, "user.name", username, scope="local")
    git.config_set(cwd, "user.email", email, scope="local")

    return ConfiguredUser(success=True, username=username, email=email)


@click.command(name="configure-git-user")
@click.pass_context
def configure_git_user(ctx: click.Context) -> None:
    """Configure git user identity from GitHub username.

    Sets git user.name and user.email based on the authenticated GitHub CLI user.
    Uses GitHub's noreply email format for privacy.
    """
    git = require_git(ctx)
    github = require_github(ctx)
    cwd = require_cwd(ctx)

    result = _configure_git_user_impl(git, github, cwd)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if configuration failed
    if isinstance(result, ConfigurationError):
        raise SystemExit(1)
