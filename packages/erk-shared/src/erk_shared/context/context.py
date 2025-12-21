"""Unified context for erk and erk-kits operations.

This module provides ErkContext - the unified context that holds all dependencies
for erk and erk-kits operations.

The ABCs for erk-specific services (ClaudeExecutor, ConfigStore, ScriptWriter,
PlannerRegistry, PlanListService) are defined in erk_shared.core, enabling
proper type hints without circular imports. Real implementations remain in erk.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.context.types import (
    GlobalConfig,
    LoadedConfig,
    NoRepoSentinel,
    RepoContext,
)
from erk_shared.core.claude_executor import ClaudeExecutor
from erk_shared.core.config_store import ConfigStore
from erk_shared.core.plan_list_service import PlanListService
from erk_shared.core.planner_registry import PlannerRegistry
from erk_shared.core.script_writer import ScriptWriter
from erk_shared.extraction.claude_code_session_store import ClaudeCodeSessionStore
from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.github.issues import GitHubIssues
from erk_shared.github.types import RepoInfo
from erk_shared.github_admin.abc import GitHubAdmin
from erk_shared.integrations.completion import Completion
from erk_shared.integrations.feedback import UserFeedback
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.shell import Shell
from erk_shared.integrations.time.abc import Time
from erk_shared.integrations.wt_stack.wt_stack import WtStack
from erk_shared.objectives.storage import ObjectiveStore
from erk_shared.plan_store.store import PlanStore
from erk_shared.project_discovery import ProjectContext
from erk_shared.prompt_executor import PromptExecutor


@dataclass(frozen=True)
class ErkContext:
    """Immutable context holding all dependencies for erk and erk-kits operations.

    Created at CLI entry point and threaded through the application via Click's
    context system. Frozen to prevent accidental modification at runtime.

    This unified context replaces both the old ErkContext (from erk.core.context)
    and DotAgentContext (from erk_kits.context).

    Note:
    - global_config may be None only during init command before config is created.
      All other commands should have a valid GlobalConfig.

    DotAgentContext Compatibility:
    - github_issues -> issues (renamed for consistency)
    - repo_root property -> repo.root (access via repo property or require_repo_root helper)
    - debug field -> debug (preserved)
    """

    # Gateway integrations (from erk_shared)
    git: Git
    github: GitHub
    github_admin: GitHubAdmin  # GitHub Actions admin operations
    issues: GitHubIssues  # Note: ErkContext naming (was github_issues in DotAgentContext)
    graphite: Graphite
    wt_stack: WtStack  # Unified worktree+stack operations (Graphite optional)
    time: Time
    session_store: ClaudeCodeSessionStore
    plan_store: PlanStore
    objectives: ObjectiveStore
    prompt_executor: PromptExecutor  # From DotAgentContext

    # Shell/CLI integrations (moved to erk_shared)
    shell: Shell
    completion: Completion
    feedback: UserFeedback

    # Erk-specific services (ABCs now in erk_shared.core for proper type hints)
    claude_executor: ClaudeExecutor
    config_store: ConfigStore
    script_writer: ScriptWriter
    planner_registry: PlannerRegistry
    plan_list_service: PlanListService

    # Paths
    cwd: Path  # Current working directory at CLI invocation

    # Repository context
    repo: RepoContext | NoRepoSentinel
    project: ProjectContext | None  # None if not in a project subdirectory
    repo_info: RepoInfo | None  # None when not in a GitHub repo

    # Configuration
    global_config: GlobalConfig | None
    local_config: LoadedConfig

    # Mode flags
    dry_run: bool
    debug: bool  # From DotAgentContext

    @property
    def repo_root(self) -> Path:
        """DotAgentContext compatibility - get repo root from repo.

        Raises:
            RuntimeError: If not in a git repository
        """
        if isinstance(self.repo, NoRepoSentinel):
            raise RuntimeError("Not in a git repository")
        return self.repo.root

    @property
    def trunk_branch(self) -> str | None:
        """Get the trunk branch name from git detection.

        Returns None if not in a repository, otherwise uses git to detect trunk.
        """
        if isinstance(self.repo, NoRepoSentinel):
            return None
        return self.git.detect_trunk_branch(self.repo.root)

    @property
    def github_issues(self) -> GitHubIssues:
        """DotAgentContext compatibility - alias for issues field.

        Deprecated: Use ctx.issues instead. This property is provided for
        backward compatibility with code written for the old DotAgentContext.
        """
        return self.issues

    @staticmethod
    def for_test(
        github_issues: GitHubIssues | None = None,
        git: Git | None = None,
        github: GitHub | None = None,
        session_store: ClaudeCodeSessionStore | None = None,
        prompt_executor: PromptExecutor | None = None,
        debug: bool = False,
        repo_root: Path | None = None,
        cwd: Path | None = None,
    ) -> "ErkContext":
        """Create test context with optional pre-configured implementations.

        Provides full control over all context parameters with sensible test defaults
        for any unspecified values. Uses fakes by default to avoid subprocess calls.

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
            >>> ctx = ErkContext.for_test(github_issues=github, git=git_ops, debug=True)
        """
        from erk_shared.context.testing import context_for_test

        return context_for_test(
            github_issues=github_issues,
            git=git,
            github=github,
            session_store=session_store,
            prompt_executor=prompt_executor,
            debug=debug,
            repo_root=repo_root,
            cwd=cwd,
        )
