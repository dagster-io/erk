#!/usr/bin/env python3
"""Configure git user identity from GitHub username.

This command sets git user.name and user.email configuration based on
a GitHub username. Eliminates duplicated git config commands in workflows.

Usage:
    erk kit exec erk configure-git-user --username "octocat"

Output:
    JSON object with success status

Exit Codes:
    0: Success (git user configured)
    1: Error (git command failed)

Examples:
    $ erk kit exec erk configure-git-user --username "octocat"
    {
      "success": true,
      "user_name": "octocat",
      "user_email": "octocat@users.noreply.github.com"
    }
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click
from erk_shared.git.abc import Git

from dot_agent_kit.context_helpers import require_cwd, require_git


@dataclass
class ConfigureSuccess:
    """Success result when git user is configured."""

    success: bool
    user_name: str
    user_email: str


@dataclass
class ConfigureError:
    """Error result when configuration fails."""

    success: bool
    error: Literal["git_config_failed", "invalid_username"]
    message: str


def _configure_git_user_impl(
    git: Git,
    cwd: Path,
    username: str,
) -> ConfigureSuccess | ConfigureError:
    """Configure git user identity.

    Args:
        git: Git interface for operations
        cwd: Current working directory (repository path)
        username: GitHub username to use

    Returns:
        ConfigureSuccess on success, ConfigureError on failure
    """
    if not username or not username.strip():
        return ConfigureError(
            success=False,
            error="invalid_username",
            message="Username cannot be empty",
        )

    username = username.strip()
    email = f"{username}@users.noreply.github.com"

    # Configure git user.name and user.email
    git.config_set(cwd, "user.name", username)
    git.config_set(cwd, "user.email", email)

    return ConfigureSuccess(
        success=True,
        user_name=username,
        user_email=email,
    )


@click.command(name="configure-git-user")
@click.option("--username", required=True, help="GitHub username for git identity")
@click.pass_context
def configure_git_user(ctx: click.Context, username: str) -> None:
    """Configure git user identity from GitHub username.

    Sets git user.name to the username and user.email to
    {username}@users.noreply.github.com pattern used by GitHub.
    """
    git = require_git(ctx)
    cwd = require_cwd(ctx)

    result = _configure_git_user_impl(git, cwd, username)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if failed
    if isinstance(result, ConfigureError):
        raise SystemExit(1)
