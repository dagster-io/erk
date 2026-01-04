"""Test factories for creating ErkContext instances.

This module provides factory functions for creating test contexts with
fake implementations. These are used by both erk and erk-kits tests.
"""

from pathlib import Path

from erk_shared.context.context import ErkContext
from erk_shared.context.types import LoadedConfig, RepoContext
from erk_shared.core.fakes import (
    FakeClaudeExecutor,
    FakePlanListService,
    FakePlannerRegistry,
    FakeScriptWriter,
)
from erk_shared.extraction.claude_installation import ClaudeInstallation
from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.github.issues import GitHubIssues
from erk_shared.prompt_executor import PromptExecutor


def context_for_test(
    github_issues: GitHubIssues | None = None,
    git: Git | None = None,
    github: GitHub | None = None,
    graphite: Graphite | None = None,
    claude_installation: ClaudeInstallation | None = None,
    prompt_executor: PromptExecutor | None = None,
    debug: bool = False,
    repo_root: Path | None = None,
    cwd: Path | None = None,
) -> ErkContext:
    """Create test context with optional pre-configured implementations.

    Provides full control over all context parameters with sensible test defaults
    for any unspecified values. Uses fakes by default to avoid subprocess calls.

    This is the factory function for creating test contexts in tests.
    It creates an ErkContext with fake implementations for all services.

    Args:
        github_issues: Optional GitHubIssues implementation. If None, creates FakeGitHubIssues.
        git: Optional Git implementation. If None, creates FakeGit.
        github: Optional GitHub implementation. If None, creates FakeGitHub.
        graphite: Optional Graphite implementation. If None, creates FakeGraphite.
        claude_installation: Optional ClaudeInstallation. If None, creates FakeClaudeInstallation.
        prompt_executor: Optional PromptExecutor. If None, creates FakePromptExecutor.
        debug: Whether to enable debug mode (default False).
        repo_root: Repository root path (defaults to Path("/fake/repo"))
        cwd: Current working directory (defaults to Path("/fake/worktree"))

    Returns:
        ErkContext configured with provided values and test defaults

    Example:
        >>> from erk_shared.github.issues import FakeGitHubIssues
        >>> from erk_shared.git.fake import FakeGit
        >>> github = FakeGitHubIssues()
        >>> git_ops = FakeGit()
        >>> ctx = context_for_test(github_issues=github, git=git_ops, debug=True)
    """
    from erk_shared.extraction.claude_installation import FakeClaudeInstallation
    from erk_shared.gateway.claude_settings.fake import FakeClaudeSettingsStore
    from erk_shared.gateway.completion import FakeCompletion
    from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
    from erk_shared.gateway.feedback import FakeUserFeedback
    from erk_shared.gateway.graphite.fake import FakeGraphite
    from erk_shared.gateway.shell import FakeShell
    from erk_shared.gateway.time.fake import FakeTime
    from erk_shared.git.fake import FakeGit
    from erk_shared.github.fake import FakeGitHub
    from erk_shared.github.issues import FakeGitHubIssues
    from erk_shared.github_admin.fake import FakeGitHubAdmin
    from erk_shared.plan_store.github import GitHubPlanStore
    from erk_shared.prompt_executor.fake import FakePromptExecutor

    # Resolve defaults
    resolved_issues: GitHubIssues = (
        github_issues if github_issues is not None else FakeGitHubIssues()
    )
    resolved_git: Git = git if git is not None else FakeGit()
    resolved_github: GitHub = github if github is not None else FakeGitHub()
    resolved_graphite: Graphite = graphite if graphite is not None else FakeGraphite()
    resolved_repo_root: Path = repo_root if repo_root is not None else Path("/fake/repo")
    resolved_claude_installation: ClaudeInstallation = (
        claude_installation
        if claude_installation is not None
        else FakeClaudeInstallation.for_test()
    )
    resolved_prompt_executor: PromptExecutor = (
        prompt_executor if prompt_executor is not None else FakePromptExecutor()
    )
    resolved_cwd: Path = cwd if cwd is not None else Path("/fake/worktree")

    # Create repo context
    repo_dir = Path("/fake/erk/repos") / resolved_repo_root.name
    repo = RepoContext(
        root=resolved_repo_root,
        repo_name=resolved_repo_root.name,
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )

    fake_time = FakeTime()
    return ErkContext(
        git=resolved_git,
        github=resolved_github,
        github_admin=FakeGitHubAdmin(),
        issues=resolved_issues,
        claude_installation=resolved_claude_installation,
        prompt_executor=resolved_prompt_executor,
        graphite=resolved_graphite,
        time=fake_time,
        erk_installation=FakeErkInstallation(),
        plan_store=GitHubPlanStore(resolved_issues, fake_time),
        claude_settings_store=FakeClaudeSettingsStore(),
        shell=FakeShell(),
        completion=FakeCompletion(),
        feedback=FakeUserFeedback(),
        claude_executor=FakeClaudeExecutor(),
        script_writer=FakeScriptWriter(),
        planner_registry=FakePlannerRegistry(),
        plan_list_service=FakePlanListService(),
        cwd=resolved_cwd,
        repo=repo,
        repo_info=None,
        global_config=None,
        local_config=LoadedConfig.test(),
        dry_run=False,
        debug=debug,
    )
