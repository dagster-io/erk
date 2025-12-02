"""Application context with dependency injection.

This module provides the canonical context creation pattern for dot-agent-kit,
following the architecture established in erk's core/context.py.

The DotAgentContext dataclass holds all dependencies (GitHub integrations, config)
and is created once at CLI entry point, then threaded through the application.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

import click
from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.github.issues import GitHubIssues, RealGitHubIssues


@dataclass(frozen=True)
class DotAgentContext:
    """Immutable context holding all dependencies for dot-agent-kit operations.

    Created at CLI entry point via create_context() and threaded through
    the application via Click's context system. Frozen to prevent accidental
    modification at runtime.

    Attributes:
        github_issues: GitHub Issues integration for querying/commenting
        git: Git operations integration for branch/commit queries
        github: GitHub integration for PR operations
        debug: Debug flag for error handling (full stack traces)
        repo_root: Repository root directory (detected at CLI entry)
        cwd: Current working directory (worktree path)
    """

    github_issues: GitHubIssues
    git: Git
    github: GitHub
    debug: bool
    repo_root: Path
    cwd: Path

    @staticmethod
    def for_test(
        github_issues: GitHubIssues | None = None,
        git: Git | None = None,
        github: GitHub | None = None,
        debug: bool = False,
        repo_root: Path | None = None,
        cwd: Path | None = None,
    ) -> "DotAgentContext":
        """Create test context with optional pre-configured implementations.

        Provides full control over all context parameters with sensible test defaults
        for any unspecified values. Uses fakes by default to avoid subprocess calls.

        Args:
            github_issues: Optional GitHubIssues implementation. If None, creates FakeGitHubIssues.
            git: Optional Git implementation. If None, creates FakeGit.
            github: Optional GitHub implementation. If None, creates FakeGitHub.
            debug: Whether to enable debug mode (default False).
            repo_root: Repository root path (defaults to Path("/fake/repo"))
            cwd: Current working directory (defaults to Path("/fake/worktree"))

        Returns:
            DotAgentContext configured with provided values and test defaults

        Example:
            >>> from erk_shared.github.issues import FakeGitHubIssues
            >>> from erk_shared.git.fake import FakeGit
            >>> github = FakeGitHubIssues()
            >>> git_ops = FakeGit()
            >>> ctx = DotAgentContext.for_test(
            ...     github_issues=github, git=git_ops, debug=True
            ... )
        """
        from erk_shared.git.fake import FakeGit
        from erk_shared.github.fake import FakeGitHub
        from erk_shared.github.issues import FakeGitHubIssues

        # Provide defaults - ensures non-None values for type checker
        resolved_github_issues: GitHubIssues = (
            github_issues if github_issues is not None else FakeGitHubIssues()
        )
        resolved_git: Git = git if git is not None else FakeGit()
        resolved_github: GitHub = github if github is not None else FakeGitHub()
        resolved_repo_root: Path = repo_root if repo_root is not None else Path("/fake/repo")
        resolved_cwd: Path = cwd if cwd is not None else Path("/fake/worktree")

        return DotAgentContext(
            github_issues=resolved_github_issues,
            git=resolved_git,
            github=resolved_github,
            debug=debug,
            repo_root=resolved_repo_root,
            cwd=resolved_cwd,
        )


def create_context(*, debug: bool) -> DotAgentContext:
    """Create production context with real implementations.

    This is the canonical factory for creating the application context.
    Called once at CLI entry point to create the context for the entire
    command execution.

    Detects repository root using git rev-parse. Exits with error if not in a git repository.

    Args:
        debug: If True, enable debug mode (full stack traces in error handling)

    Returns:
        DotAgentContext with real GitHub integrations and detected repo_root

    Example:
        >>> ctx = create_context(debug=False)
        >>> issue_number = ctx.github_issues.create_issue(ctx.repo_root, title, body, labels)
    """
    from erk_shared.git.real import RealGit
    from erk_shared.github.real import RealGitHub
    from erk_shared.integrations.time.real import RealTime

    # Detect repo root using git rev-parse
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        click.echo("Error: Not in a git repository", err=True)
        raise SystemExit(1)

    repo_root = Path(result.stdout.strip())
    cwd = Path.cwd()

    return DotAgentContext(
        github_issues=RealGitHubIssues(),
        git=RealGit(),
        github=RealGitHub(time=RealTime()),
        debug=debug,
        repo_root=repo_root,
        cwd=cwd,
    )
