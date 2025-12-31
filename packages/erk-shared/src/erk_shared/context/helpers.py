"""Helper functions for accessing context dependencies with LBYL checks.

This module provides getter functions that encapsulate the "Look Before You Leap"
pattern for accessing dependencies from the ErkContext. These functions:

1. Check that context is initialized
2. Return the typed dependency
3. Exit with clear error message if context is missing

This eliminates code duplication across kit CLI commands.
"""

from __future__ import annotations

from pathlib import Path

import click

from erk_shared.context.types import LoadedConfig, NoRepoSentinel
from erk_shared.extraction.claude_code_session_store import ClaudeCodeSessionStore
from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.github.issues import GitHubIssues
from erk_shared.prompt_executor import PromptExecutor


def require_issues(ctx: click.Context) -> GitHubIssues:
    """Get GitHub Issues from context, exiting with error if not initialized.

    Uses LBYL pattern to check context before accessing. If context is not
    initialized (ctx.obj is None), prints error to stderr and exits with code 1.

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
        ...     issues = require_issues(ctx)
        ...     issues.add_comment(repo_root, issue_number, body)
    """
    from erk_shared.context.context import ErkContext

    if ctx.obj is None:
        click.echo("Error: Context not initialized", err=True)
        raise SystemExit(1)

    if not isinstance(ctx.obj, ErkContext):
        click.echo("Error: Context must be ErkContext", err=True)
        raise SystemExit(1)

    return ctx.obj.issues


def require_repo_root(ctx: click.Context) -> Path:
    """Get repo root from context, exiting with error if not initialized.

    Uses LBYL pattern to check context before accessing.

    Args:
        ctx: Click context (must have ErkContext in ctx.obj)

    Returns:
        Path to repository root

    Raises:
        SystemExit: If context not initialized (exits with code 1)

    Example:
        >>> @click.command()
        >>> @click.pass_context
        >>> def my_command(ctx: click.Context) -> None:
        ...     repo_root = require_repo_root(ctx)
        ...     issues = require_issues(ctx)
        ...     issues.create_issue(repo_root, title, body, labels)
    """
    from erk_shared.context.context import ErkContext

    if ctx.obj is None:
        click.echo("Error: Context not initialized", err=True)
        raise SystemExit(1)

    if not isinstance(ctx.obj, ErkContext):
        click.echo("Error: Context must be ErkContext", err=True)
        raise SystemExit(1)

    repo = ctx.obj.repo
    if isinstance(repo, NoRepoSentinel):
        click.echo("Error: Not in a git repository", err=True)
        raise SystemExit(1)

    return repo.root


def require_project_root(ctx: click.Context) -> Path:
    """Get project root from context, which is always the repo root.

    Simplified: With the project system removed, project root is always repo root.

    Args:
        ctx: Click context (must have ErkContext in ctx.obj)

    Returns:
        Path to repo root (always, since project system is removed)

    Raises:
        SystemExit: If context not initialized (exits with code 1)

    Example:
        >>> @click.command()
        >>> @click.pass_context
        >>> def my_command(ctx: click.Context) -> None:
        ...     project_root = require_project_root(ctx)
        ...     docs_dir = project_root / "docs" / "agent"
    """
    # With project system removed, project root is always repo root
    return require_repo_root(ctx)


def require_git(ctx: click.Context) -> Git:
    """Get Git from context, exiting with error if not initialized.

    Uses LBYL pattern to check context before accessing.

    Args:
        ctx: Click context (must have ErkContext in ctx.obj)

    Returns:
        Git instance from context

    Raises:
        SystemExit: If context not initialized (exits with code 1)

    Example:
        >>> @click.command()
        >>> @click.pass_context
        >>> def my_command(ctx: click.Context) -> None:
        ...     git = require_git(ctx)
        ...     cwd = require_cwd(ctx)
        ...     branch = git.get_current_branch(cwd)
    """
    if ctx.obj is None:
        click.echo("Error: Context not initialized", err=True)
        raise SystemExit(1)

    return ctx.obj.git


def require_github(ctx: click.Context) -> GitHub:
    """Get GitHub from context, exiting with error if not initialized.

    Uses LBYL pattern to check context before accessing.

    Args:
        ctx: Click context (must have ErkContext in ctx.obj)

    Returns:
        GitHub instance from context

    Raises:
        SystemExit: If context not initialized (exits with code 1)

    Example:
        >>> @click.command()
        >>> @click.pass_context
        >>> def my_command(ctx: click.Context) -> None:
        ...     github = require_github(ctx)
        ...     repo_root = require_repo_root(ctx)
        ...     pr_info = github.get_pr_status(repo_root, "main", debug=False)
    """
    if ctx.obj is None:
        click.echo("Error: Context not initialized", err=True)
        raise SystemExit(1)

    return ctx.obj.github


def require_cwd(ctx: click.Context) -> Path:
    """Get current working directory from context, exiting with error if not initialized.

    Uses LBYL pattern to check context before accessing.

    Args:
        ctx: Click context (must have ErkContext in ctx.obj)

    Returns:
        Path to current working directory (worktree path)

    Raises:
        SystemExit: If context not initialized (exits with code 1)

    Example:
        >>> @click.command()
        >>> @click.pass_context
        >>> def my_command(ctx: click.Context) -> None:
        ...     cwd = require_cwd(ctx)
        ...     git = require_git(ctx)
        ...     branch = git.get_current_branch(cwd)
    """
    if ctx.obj is None:
        click.echo("Error: Context not initialized", err=True)
        raise SystemExit(1)

    return ctx.obj.cwd


def require_session_store(ctx: click.Context) -> ClaudeCodeSessionStore:
    """Get SessionStore from context, exiting with error if not initialized.

    Uses LBYL pattern to check context before accessing.

    Args:
        ctx: Click context (must have ErkContext in ctx.obj)

    Returns:
        SessionStore instance from context

    Raises:
        SystemExit: If context not initialized (exits with code 1)

    Example:
        >>> @click.command()
        >>> @click.pass_context
        >>> def my_command(ctx: click.Context) -> None:
        ...     store = require_session_store(ctx)
        ...     sessions = store.find_sessions(cwd)
    """
    if ctx.obj is None:
        click.echo("Error: Context not initialized", err=True)
        raise SystemExit(1)

    return ctx.obj.session_store


def get_current_branch(ctx: click.Context) -> str | None:
    """Get current git branch from context.

    Convenience method that combines require_cwd and require_git to get
    the current branch name. Returns None if branch cannot be determined.

    Args:
        ctx: Click context (must have ErkContext in ctx.obj)

    Returns:
        Current branch name as string, or None if not determinable

    Raises:
        SystemExit: If context not initialized (exits with code 1)

    Example:
        >>> @click.command()
        >>> @click.pass_context
        >>> def my_command(ctx: click.Context) -> None:
        ...     branch = get_current_branch(ctx)
        ...     if branch is None:
        ...         # handle error
        ...     pr = github.get_pr_for_branch(repo_root, branch)
    """
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    return git.get_current_branch(cwd)


def require_prompt_executor(ctx: click.Context) -> PromptExecutor:
    """Get PromptExecutor from context, exiting with error if not initialized.

    Uses LBYL pattern to check context before accessing.

    Args:
        ctx: Click context (must have ErkContext in ctx.obj)

    Returns:
        PromptExecutor instance from context

    Raises:
        SystemExit: If context not initialized (exits with code 1)

    Example:
        >>> @click.command()
        >>> @click.pass_context
        >>> def my_command(ctx: click.Context) -> None:
        ...     executor = require_prompt_executor(ctx)
        ...     result = executor.execute_prompt("Generate summary", model="haiku")
    """
    if ctx.obj is None:
        click.echo("Error: Context not initialized", err=True)
        raise SystemExit(1)

    return ctx.obj.prompt_executor


def require_local_config(ctx: click.Context) -> LoadedConfig:
    """Get local config from context, exiting with error if not initialized.

    Uses LBYL pattern to check context before accessing.

    Args:
        ctx: Click context (must have ErkContext in ctx.obj)

    Returns:
        LoadedConfig instance from context

    Raises:
        SystemExit: If context not initialized (exits with code 1)

    Example:
        >>> @click.command()
        >>> @click.pass_context
        >>> def my_command(ctx: click.Context) -> None:
        ...     config = require_local_config(ctx)
        ...     plans_repo = config.plans_repo
    """
    if ctx.obj is None:
        click.echo("Error: Context not initialized", err=True)
        raise SystemExit(1)

    return ctx.obj.local_config


def get_repo_identifier(ctx: click.Context) -> str | None:
    """Get the GitHub repo identifier (owner/repo) from context.

    Convenience method that returns the repo identity in "owner/repo" format,
    or None if not in a GitHub-connected repository.

    Args:
        ctx: Click context (must have ErkContext in ctx.obj)

    Returns:
        Repo identifier as "owner/repo" string, or None if not available

    Raises:
        SystemExit: If context not initialized (exits with code 1)

    Example:
        >>> @click.command()
        >>> @click.pass_context
        >>> def my_command(ctx: click.Context) -> None:
        ...     repo_id = get_repo_identifier(ctx)
        ...     if repo_id:
        ...         print(f"Working in {repo_id}")
    """
    if ctx.obj is None:
        click.echo("Error: Context not initialized", err=True)
        raise SystemExit(1)

    repo = ctx.obj.repo
    if isinstance(repo, NoRepoSentinel):
        return None

    if repo.github is None:
        return None

    return f"{repo.github.owner}/{repo.github.repo}"
