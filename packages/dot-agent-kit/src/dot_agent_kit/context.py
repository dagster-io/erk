"""Application context with dependency injection.

This module provides the canonical context for dot-agent-kit.

The DotAgentContext is now an alias for erk_shared.context.ErkContext, providing
a unified context for both erk and dot-agent-kit operations.

Migration Notes:
- DotAgentContext.github_issues -> ctx.issues (renamed for consistency)
- DotAgentContext.repo_root -> ctx.repo_root (preserved as property)
- All other fields remain the same
"""

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import click
from erk_shared.context import ErkContext
from erk_shared.extraction.claude_code_session_store import ClaudeCodeSessionStore
from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.github.issues import GitHubIssues
from erk_shared.prompt_executor import PromptExecutor

if TYPE_CHECKING:
    from erk_shared.github.types import RepoInfo


def for_test(
    github_issues: GitHubIssues | None = None,
    git: Git | None = None,
    github: GitHub | None = None,
    session_store: ClaudeCodeSessionStore | None = None,
    prompt_executor: PromptExecutor | None = None,
    debug: bool = False,
    repo_root: Path | None = None,
    cwd: Path | None = None,
) -> ErkContext:
    """Create test context with optional pre-configured implementations.

    Provides full control over all context parameters with sensible test defaults
    for any unspecified values. Uses fakes by default to avoid subprocess calls.

    This is the factory function for creating test contexts in dot-agent-kit tests.
    It creates an ErkContext with fake implementations for erk-specific services.

    Args:
        github_issues: Optional GitHubIssues implementation. If None, creates FakeGitHubIssues.
        git: Optional Git implementation. If None, creates FakeGit.
        github: Optional GitHub implementation. If None, creates FakeGitHub.
        session_store: Optional SessionStore. If None, creates FakeClaudeCodeSessionStore.
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
        >>> ctx = for_test(github_issues=github, git=git_ops, debug=True)
    """
    from erk_shared.context.types import LoadedConfig, RepoContext
    from erk_shared.extraction.claude_code_session_store import FakeClaudeCodeSessionStore
    from erk_shared.git.fake import FakeGit
    from erk_shared.github.fake import FakeGitHub
    from erk_shared.github.issues import FakeGitHubIssues
    from erk_shared.integrations.completion import FakeCompletion
    from erk_shared.integrations.feedback import FakeUserFeedback
    from erk_shared.integrations.graphite.fake import FakeGraphite
    from erk_shared.integrations.shell import FakeShell
    from erk_shared.integrations.time.fake import FakeTime
    from erk_shared.objectives.storage import FakeObjectiveStore
    from erk_shared.plan_store.fake import FakePlanStore
    from erk_shared.prompt_executor.fake import FakePromptExecutor

    # Resolve defaults
    resolved_issues: GitHubIssues = (
        github_issues if github_issues is not None else FakeGitHubIssues()
    )
    resolved_git: Git = git if git is not None else FakeGit()
    resolved_github: GitHub = github if github is not None else FakeGitHub()
    resolved_session_store: ClaudeCodeSessionStore = (
        session_store if session_store is not None else FakeClaudeCodeSessionStore()
    )
    resolved_prompt_executor: PromptExecutor = (
        prompt_executor if prompt_executor is not None else FakePromptExecutor()
    )
    resolved_repo_root: Path = repo_root if repo_root is not None else Path("/fake/repo")
    resolved_cwd: Path = cwd if cwd is not None else Path("/fake/worktree")

    # Create repo context
    repo = RepoContext(
        root=resolved_repo_root,
        repo_name=resolved_repo_root.name,
        repo_dir=Path("/fake/erk/repos") / resolved_repo_root.name,
        worktrees_dir=Path("/fake/erk/repos") / resolved_repo_root.name / "worktrees",
    )

    # Create stub implementations for erk-specific services
    class FakeClaudeExecutor:
        pass

    class FakeConfigStore:
        pass

    class FakeScriptWriter:
        pass

    class FakePlannerRegistry:
        pass

    class FakePlanListService:
        pass

    return ErkContext(
        git=resolved_git,
        github=resolved_github,
        issues=resolved_issues,
        session_store=resolved_session_store,
        prompt_executor=resolved_prompt_executor,
        graphite=FakeGraphite(),
        time=FakeTime(),
        plan_store=FakePlanStore(),
        objectives=FakeObjectiveStore(),
        shell=FakeShell(),
        completion=FakeCompletion(),
        feedback=FakeUserFeedback(),
        claude_executor=FakeClaudeExecutor(),
        config_store=FakeConfigStore(),
        script_writer=FakeScriptWriter(),
        planner_registry=FakePlannerRegistry(),
        plan_list_service=FakePlanListService(),
        cwd=resolved_cwd,
        repo=repo,
        project=None,
        repo_info=None,
        global_config=None,
        local_config=LoadedConfig(env={}, post_create_commands=[], post_create_shell=None),
        dry_run=False,
        debug=debug,
    )


class _DotAgentContextWrapper:
    """Wrapper class that provides for_test() static method for backward compatibility.

    This allows existing code using DotAgentContext.for_test(...) to continue working.
    The actual context returned is ErkContext.
    """

    # Make for_test accessible as a static method
    for_test = staticmethod(for_test)

    def __new__(cls, *args, **kwargs):  # noqa: ANN002, ANN003, ANN204
        # When used as a constructor, return an ErkContext
        return ErkContext(*args, **kwargs)


# DotAgentContext is now a wrapper that provides backward compatibility
# It supports both DotAgentContext.for_test(...) and DotAgentContext(...)
DotAgentContext = _DotAgentContextWrapper


def get_repo_info(git: Git, repo_root: Path) -> "RepoInfo | None":
    """Detect repository info from git remote URL.

    Parses the origin remote URL to extract owner/name for GitHub API calls.
    Returns None if no origin remote is configured or URL cannot be parsed.

    Args:
        git: Git interface for operations
        repo_root: Repository root path

    Returns:
        RepoInfo with owner/name, or None if not determinable
    """
    from erk_shared.github.parsing import parse_git_remote_url
    from erk_shared.github.types import RepoInfo

    try:
        remote_url = git.get_remote_url(repo_root)
        owner, name = parse_git_remote_url(remote_url)
        return RepoInfo(owner=owner, name=name)
    except ValueError:
        # No origin remote configured or URL cannot be parsed
        return None


def create_context(*, debug: bool) -> ErkContext:
    """Create production context with real implementations for dot-agent-kit.

    This is the canonical factory for creating the application context.
    Called once at CLI entry point to create the context for the entire
    command execution.

    Detects repository root using git rev-parse. Exits with error if not in a git repository.

    Note: This creates a minimal context for dot-agent-kit commands. If you need the full
    ErkContext with all erk-specific features, use erk.core.context.create_context() instead.

    Args:
        debug: If True, enable debug mode (full stack traces in error handling)

    Returns:
        ErkContext with real GitHub integrations and detected repo_root

    Example:
        >>> ctx = create_context(debug=False)
        >>> issue_number = ctx.issues.create_issue(ctx.repo_root, title, body, labels)
    """
    from erk_shared.context.types import LoadedConfig, RepoContext
    from erk_shared.extraction.claude_code_session_store import RealClaudeCodeSessionStore
    from erk_shared.git.real import RealGit
    from erk_shared.github.issues import RealGitHubIssues
    from erk_shared.github.real import RealGitHub
    from erk_shared.integrations.completion import FakeCompletion
    from erk_shared.integrations.feedback import SuppressedFeedback
    from erk_shared.integrations.graphite.fake import FakeGraphite
    from erk_shared.integrations.shell import FakeShell
    from erk_shared.integrations.time.fake import FakeTime
    from erk_shared.integrations.time.real import RealTime
    from erk_shared.objectives.storage import FakeObjectiveStore
    from erk_shared.plan_store.fake import FakePlanStore
    from erk_shared.prompt_executor.real import RealPromptExecutor

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

    # Create git instance and detect repo_info
    git = RealGit()
    repo_info = get_repo_info(git, repo_root)

    # Create minimal repo context for dot-agent-kit
    repo = RepoContext(
        root=repo_root,
        repo_name=repo_root.name,
        repo_dir=Path.home() / ".erk" / "repos" / repo_root.name,
        worktrees_dir=Path.home() / ".erk" / "repos" / repo_root.name / "worktrees",
    )

    # Create fake implementations for erk-specific services that dot-agent-kit doesn't need
    # This allows dot-agent-kit to work without the full erk package
    class FakeClaudeExecutor:
        """Fake implementation for dot-agent-kit (not needed)."""

        def execute_interactive(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            raise NotImplementedError("ClaudeExecutor not available in dot-agent-kit context")

        def execute_interactive_command(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            raise NotImplementedError("ClaudeExecutor not available in dot-agent-kit context")

    class FakeConfigStore:
        """Fake implementation for dot-agent-kit (not needed)."""

        def exists(self) -> bool:
            return False

        def load(self):  # noqa: ANN201
            raise NotImplementedError("ConfigStore not available in dot-agent-kit context")

        def save(self, config) -> None:  # noqa: ANN001
            raise NotImplementedError("ConfigStore not available in dot-agent-kit context")

        def path(self) -> Path:
            return Path("/fake/config")

    class FakeScriptWriter:
        """Fake implementation for dot-agent-kit (not needed)."""

        pass

    class FakePlannerRegistry:
        """Fake implementation for dot-agent-kit (not needed)."""

        pass

    class FakePlanListService:
        """Fake implementation for dot-agent-kit (not needed)."""

        pass

    return ErkContext(
        # Core integrations that dot-agent-kit uses
        git=git,
        github=RealGitHub(time=RealTime(), repo_info=repo_info),
        issues=RealGitHubIssues(),
        session_store=RealClaudeCodeSessionStore(),
        prompt_executor=RealPromptExecutor(),
        # Fakes for erk-specific integrations
        graphite=FakeGraphite(),
        time=FakeTime(),
        plan_store=FakePlanStore(),
        objectives=FakeObjectiveStore(),
        shell=FakeShell(),
        completion=FakeCompletion(),
        feedback=SuppressedFeedback(),
        claude_executor=FakeClaudeExecutor(),
        config_store=FakeConfigStore(),
        script_writer=FakeScriptWriter(),
        planner_registry=FakePlannerRegistry(),
        plan_list_service=FakePlanListService(),
        # Context values
        cwd=cwd,
        repo=repo,
        project=None,
        repo_info=repo_info,
        global_config=None,
        local_config=LoadedConfig(env={}, post_create_commands=[], post_create_shell=None),
        dry_run=False,
        debug=debug,
    )
