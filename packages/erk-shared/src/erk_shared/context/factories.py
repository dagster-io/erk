"""Factory functions for creating ErkContext instances.

This module provides factory functions for creating production contexts
with real implementations. Used by CLI entry points.
"""

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from erk_shared.core.fakes import (
    FakeClaudeExecutor,
    FakeConfigStore,
    FakePlanListService,
    FakePlannerRegistry,
    FakeScriptWriter,
)

if TYPE_CHECKING:
    from erk_shared.context.context import ErkContext
    from erk_shared.git.abc import Git
    from erk_shared.github.types import RepoInfo


def get_repo_info(git: "Git", repo_root: Path) -> "RepoInfo | None":
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
        return None


def create_minimal_context(*, debug: bool, cwd: Path | None = None) -> "ErkContext":
    """Create production context with real implementations for erk-kits.

    This factory creates a minimal context suitable for erk-kits commands.
    It uses real implementations for GitHub, git, and session store, but uses
    fake implementations for erk-specific services (ClaudeExecutor, etc.) that
    erk-kits doesn't need.

    Detects repository root using git rev-parse. Returns context with
    NoRepoSentinel if not in a git repository.

    Args:
        debug: If True, enable debug mode (full stack traces in error handling)
        cwd: Current working directory (defaults to Path.cwd())

    Returns:
        ErkContext with real GitHub integrations and detected repo context

    Example:
        >>> ctx = create_minimal_context(debug=False)
        >>> issue_number = ctx.issues.create_issue(ctx.repo_root, title, body, labels)
    """
    from erk_shared.context.context import ErkContext
    from erk_shared.context.types import LoadedConfig, NoRepoSentinel, RepoContext
    from erk_shared.extraction.claude_code_session_store import RealClaudeCodeSessionStore
    from erk_shared.gateway.completion import FakeCompletion
    from erk_shared.gateway.feedback import SuppressedFeedback
    from erk_shared.gateway.graphite.fake import FakeGraphite
    from erk_shared.gateway.shell import FakeShell
    from erk_shared.gateway.time.fake import FakeTime
    from erk_shared.gateway.time.real import RealTime
    from erk_shared.gateway.wt_stack.wt_stack import WtStack
    from erk_shared.git.real import RealGit
    from erk_shared.github.issues import RealGitHubIssues
    from erk_shared.github.real import RealGitHub
    from erk_shared.github_admin.fake import FakeGitHubAdmin
    from erk_shared.plan_store.github import GitHubPlanStore
    from erk_shared.prompt_executor.real import RealPromptExecutor

    resolved_cwd = cwd if cwd is not None else Path.cwd()

    # Detect repo root using git rev-parse
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )

    # Create git instance
    git = RealGit()

    if result.returncode != 0:
        # Not in a git repository
        repo: RepoContext | NoRepoSentinel = NoRepoSentinel()
        repo_info = None
    else:
        repo_root = Path(result.stdout.strip())
        repo_info = get_repo_info(git, repo_root)
        repo = RepoContext(
            root=repo_root,
            repo_name=repo_root.name,
            repo_dir=Path.home() / ".erk" / "repos" / repo_root.name,
            worktrees_dir=Path.home() / ".erk" / "repos" / repo_root.name / "worktrees",
        )

    # Use fake implementations for erk-specific services that erk-kits doesn't need
    fake_graphite = FakeGraphite()
    wt_stack_repo_root = repo.root if not isinstance(repo, NoRepoSentinel) else resolved_cwd
    github_issues = RealGitHubIssues()
    time = RealTime()
    fake_time = FakeTime()
    return ErkContext(
        git=git,
        github=RealGitHub(time=time, repo_info=repo_info),
        github_admin=FakeGitHubAdmin(),
        issues=github_issues,
        session_store=RealClaudeCodeSessionStore(),
        prompt_executor=RealPromptExecutor(time),
        graphite=fake_graphite,
        wt_stack=WtStack(git, wt_stack_repo_root, fake_graphite),
        time=fake_time,
        plan_store=GitHubPlanStore(github_issues, fake_time),
        shell=FakeShell(),
        completion=FakeCompletion(),
        feedback=SuppressedFeedback(),
        claude_executor=FakeClaudeExecutor(),
        config_store=FakeConfigStore(),
        script_writer=FakeScriptWriter(),
        planner_registry=FakePlannerRegistry(),
        plan_list_service=FakePlanListService(),
        cwd=resolved_cwd,
        repo=repo,
        repo_info=repo_info,
        global_config=None,
        local_config=LoadedConfig(env={}, post_create_commands=[], post_create_shell=None),
        dry_run=False,
        debug=debug,
    )
