"""Shared context builders for test scenarios.

This module provides reusable context builder functions to eliminate duplication
across test files. These builders encapsulate common patterns for setting up
ErkContext with appropriate fake implementations.
"""

from erk.core.context import ErkContext
from erk_shared.git.dry_run import DryRunGit
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.integrations.graphite.fake import FakeGraphite
from tests.fakes.shell import FakeShell
from tests.test_utils.env_helpers import ErkInMemEnv, ErkIsolatedFsEnv


def build_workspace_test_context(
    env: ErkInMemEnv | ErkIsolatedFsEnv,
    *,
    dry_run: bool = False,
    use_graphite: bool = False,
    current_branch: str | None = None,
    **kwargs,
) -> ErkContext:
    """Build ErkContext for workspace command tests (create, split, consolidate, delete).

    This builder provides a standard context configuration for workspace manipulation
    commands with sensible defaults and support for common testing scenarios.

    Args:
        env: Pure or isolated erk environment fixture
        dry_run: Whether to wrap git operations with DryRunGit (default: False)
        use_graphite: Whether to enable Graphite integration (default: False)
        current_branch: Current branch name for FakeGit configuration (default: None)
        **kwargs: Additional arguments passed to env.build_context()
                  (can include custom git, github, graphite, shell instances)

    Returns:
        ErkContext configured for workspace command testing

    Example:
        >>> with erk_inmem_env(runner) as env:
        ...     ctx = build_workspace_test_context(env, dry_run=True)
        ...     result = runner.invoke(cli, ["delete", "branch"], obj=ctx)
    """
    # Only create default git if not provided in kwargs
    if "git" not in kwargs:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        if dry_run:
            git_ops = DryRunGit(git_ops)
        kwargs["git"] = git_ops
    else:
        # Ensure custom git has remote_urls configured for repo discovery
        git_ops = kwargs["git"]
        unwrapped = git_ops._wrapped if isinstance(git_ops, DryRunGit) else git_ops
        if hasattr(unwrapped, "_remote_urls"):
            # Add default remote URL if not already set for env.cwd
            if (env.cwd, "origin") not in unwrapped._remote_urls:
                unwrapped._remote_urls[(env.cwd, "origin")] = "https://github.com/owner/repo.git"

    # Provide defaults for other integrations if not in kwargs
    if "github" not in kwargs:
        kwargs["github"] = FakeGitHub()
    if "graphite" not in kwargs:
        kwargs["graphite"] = FakeGraphite()
    if "shell" not in kwargs:
        kwargs["shell"] = FakeShell()

    return env.build_context(
        use_graphite=use_graphite,
        dry_run=dry_run,
        **kwargs,
    )


def build_graphite_test_context(
    env: ErkInMemEnv | ErkIsolatedFsEnv, *, dry_run: bool = False, **kwargs
) -> ErkContext:
    """Build ErkContext for Graphite-enabled command tests.

    Convenience wrapper around build_workspace_test_context() that enables
    Graphite integration by default.

    Args:
        env: Pure or isolated erk environment fixture
        dry_run: Whether to wrap git operations with DryRunGit (default: False)
        **kwargs: Additional arguments passed to env.build_context()

    Returns:
        ErkContext configured for Graphite command testing

    Example:
        >>> with erk_inmem_env(runner) as env:
        ...     ctx = build_graphite_test_context(env)
        ...     result = runner.invoke(cli, ["land-stack"], obj=ctx)
    """
    return build_workspace_test_context(env, dry_run=dry_run, use_graphite=True, **kwargs)


def build_navigation_test_context(
    env: ErkInMemEnv | ErkIsolatedFsEnv, *, current_branch: str | None = None, **kwargs
) -> ErkContext:
    """Build ErkContext for navigation command tests (up, down, goto).

    Convenience wrapper around build_workspace_test_context() for navigation
    commands that typically need to specify the current branch.

    Args:
        env: Pure or isolated erk environment fixture
        current_branch: Current branch name for FakeGit configuration (default: None)
        **kwargs: Additional arguments passed to env.build_context()

    Returns:
        ErkContext configured for navigation command testing

    Example:
        >>> with erk_inmem_env(runner) as env:
        ...     ctx = build_navigation_test_context(env, current_branch="feat-1")
        ...     result = runner.invoke(cli, ["up"], obj=ctx)
    """
    return build_workspace_test_context(env, current_branch=current_branch, **kwargs)
