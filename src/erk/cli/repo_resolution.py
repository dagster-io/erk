"""Shared --repo infrastructure for CLI commands.

Provides helpers for resolving owner/repo from either a --repo flag
or local git context, and constructing RemoteGitHub instances.
"""

import functools

import click

from erk.cli.ensure import UserFacingCliError
from erk.core.context import ErkContext, NoRepoSentinel
from erk_shared.gateway.github.types import GitHubRepoId
from erk_shared.gateway.remote_github.abc import RemoteGitHub
from erk_shared.gateway.remote_github.real import RealRemoteGitHub


def resolve_owner_repo(
    ctx: ErkContext,
    *,
    target_repo: str | None,
) -> tuple[str, str]:
    """Resolve owner/repo from --repo flag or local git context.

    Args:
        ctx: ErkContext
        target_repo: Optional "owner/repo" string from --repo flag

    Returns:
        Tuple of (owner, repo_name)

    Raises:
        UserFacingCliError: If owner/repo cannot be determined
    """
    if target_repo is not None:
        if "/" not in target_repo or target_repo.count("/") != 1:
            raise UserFacingCliError(
                f"Invalid --repo format: '{target_repo}'\n"
                "Expected format: owner/repo (e.g., dagster-io/erk)",
                error_type="cli_error",
            )
        owner, repo_name = target_repo.split("/")
        return (owner, repo_name)

    if isinstance(ctx.repo, NoRepoSentinel) or ctx.repo.github is None:
        raise UserFacingCliError(
            "Cannot determine target repository.\n"
            "Use --repo owner/repo or run from inside a git repository.",
            error_type="cli_error",
        )
    return (ctx.repo.github.owner, ctx.repo.github.repo)


def get_remote_github(ctx: ErkContext) -> RemoteGitHub:
    """Get or construct a RemoteGitHub from context.

    Uses ctx.remote_github if provided (tests inject FakeRemoteGitHub here).
    Otherwise constructs RealRemoteGitHub from ctx.http_client.

    Args:
        ctx: ErkContext with http_client and time

    Returns:
        RemoteGitHub instance

    Raises:
        UserFacingCliError: If no http_client is available
    """
    if ctx.remote_github is not None:
        return ctx.remote_github

    if ctx.http_client is None:
        raise UserFacingCliError(
            "GitHub authentication required.\nRun 'gh auth login' to authenticate.",
            error_type="cli_error",
        )

    return RealRemoteGitHub(http_client=ctx.http_client, time=ctx.time)


repo_option = click.option(
    "--repo",
    "target_repo",
    type=str,
    default=None,
    help="Target repo (owner/repo) for remote operation without local git clone",
)


def resolved_repo_option(fn):  # noqa: ANN001, ANN201
    """Decorator that resolves --repo into a GitHubRepoId.

    Wraps a Click command handler to resolve the --repo flag
    (or local git context) into a GitHubRepoId before calling
    the handler. The handler receives ``repo_id: GitHubRepoId``
    instead of ``target_repo: str | None``.
    """

    @repo_option
    @functools.wraps(fn)
    def wrapper(*, target_repo: str | None, **kwargs):  # noqa: ANN003, ANN202
        ctx = click.get_current_context().obj
        owner, repo_name = resolve_owner_repo(ctx, target_repo=target_repo)
        return fn(repo_id=GitHubRepoId(owner=owner, repo=repo_name), **kwargs)

    return wrapper
