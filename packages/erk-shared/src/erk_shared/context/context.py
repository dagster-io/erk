"""Unified context for erk and erk-kits operations.

This module provides ErkContext - the unified context that holds all dependencies
for erk and erk-kits operations.

The ABCs for erk-specific services (ClaudeExecutor, ConfigStore, ScriptWriter,
PlanListService) are defined in erk_shared.core, enabling
proper type hints without circular imports. Real implementations remain in erk.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from erk_shared.branch_manager.abc import BranchManager
from erk_shared.branch_manager.git import GitBranchManager
from erk_shared.branch_manager.graphite import GraphiteBranchManager
from erk_shared.context.types import (
    GlobalConfig,
    LoadedConfig,
    NoRepoSentinel,
    RepoContext,
)
from erk_shared.core.claude_executor import ClaudeExecutor
from erk_shared.core.codespace_registry import CodespaceRegistry
from erk_shared.core.plan_list_service import PlanListService
from erk_shared.core.script_writer import ScriptWriter
from erk_shared.gateway.codespace.abc import Codespace
from erk_shared.gateway.completion.abc import Completion
from erk_shared.gateway.console.abc import Console
from erk_shared.gateway.erk_installation.abc import ErkInstallation
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.types import RepoInfo
from erk_shared.gateway.github_admin.abc import GitHubAdmin
from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.gateway.graphite.branch_ops.abc import GraphiteBranchOps
from erk_shared.gateway.graphite.disabled import GraphiteDisabled
from erk_shared.gateway.graphite.dry_run import DryRunGraphite
from erk_shared.gateway.shell.abc import Shell
from erk_shared.gateway.time.abc import Time
from erk_shared.learn.extraction.claude_installation.abc import ClaudeInstallation
from erk_shared.plan_store.backend import PlanBackend
from erk_shared.plan_store.store import PlanStore
from erk_shared.prompt_executor.abc import PromptExecutor


@dataclass(frozen=True)
class ErkContext:
    """Immutable context holding all dependencies for erk and erk-kits operations.

    Created at CLI entry point and threaded through the application via Click's
    context system. Frozen to prevent accidental modification at runtime.

    This unified context combines functionality that was previously split across
    multiple context types (erk.core.context.ErkContext and erk_kits.context).

    Note:
    - global_config may be None only during init command before config is created.
      All other commands should have a valid GlobalConfig.

    Field naming conventions:
    - github_issues property -> issues (renamed for consistency)
    - repo_root property -> repo.root (access via repo property or require_repo_root helper)
    """

    # Gateway integrations (from erk_shared)
    git: Git
    git_branch_ops: GitBranchOps  # Sub-gateway for branch mutations
    github: GitHub  # Note: issues accessed via github.issues property
    github_admin: GitHubAdmin  # GitHub Actions admin operations
    graphite: Graphite
    graphite_branch_ops: GraphiteBranchOps | None  # None when Graphite disabled
    console: Console  # TTY detection, user feedback, and confirmation prompts
    time: Time
    erk_installation: ErkInstallation  # ~/.erk/ installation data (config, pool state)
    claude_installation: ClaudeInstallation  # ~/.claude/ installation data (sessions, settings)
    plan_store: PlanStore
    prompt_executor: PromptExecutor

    # Shell/CLI integrations (moved to erk_shared)
    shell: Shell
    completion: Completion
    codespace: Codespace

    # Erk-specific services (ABCs now in erk_shared.core for proper type hints)
    claude_executor: ClaudeExecutor
    erk_installation: ErkInstallation
    script_writer: ScriptWriter
    codespace_registry: CodespaceRegistry
    plan_list_service: PlanListService

    # Paths
    cwd: Path  # Current working directory at CLI invocation

    # Repository context
    repo: RepoContext | NoRepoSentinel
    repo_info: RepoInfo | None  # None when not in a GitHub repo

    # Configuration
    global_config: GlobalConfig | None
    local_config: LoadedConfig

    # Mode flags
    dry_run: bool
    debug: bool

    @property
    def repo_root(self) -> Path:
        """Convenience property - get repo root from repo.

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
    def issues(self) -> GitHubIssues:
        """Access to issue operations via the composed GitHub gateway.

        All issue operations should be accessed via ctx.github.issues directly,
        but this property is provided for backward compatibility.
        """
        return self.github.issues

    @property
    def github_issues(self) -> GitHubIssues:
        """DotAgentContext compatibility - alias for issues property.

        Deprecated: Use ctx.github.issues instead. This property is provided for
        backward compatibility with code written for the old DotAgentContext.
        """
        return self.github.issues

    @property
    def plan_backend(self) -> PlanBackend:
        """Access plan_store as PlanBackend (read/write interface).

        GitHubPlanStore now extends PlanBackend, so this property provides
        typed access to write operations (create_plan, update_metadata, add_comment)
        while plan_store remains for backward compatibility.
        """
        # GitHubPlanStore extends PlanBackend, so this cast is safe
        # At runtime, plan_store is always a GitHubPlanStore instance
        if not isinstance(self.plan_store, PlanBackend):
            raise RuntimeError(
                f"plan_store must be a PlanBackend, got {type(self.plan_store).__name__}"
            )
        return self.plan_store

    @property
    def branch_manager(self) -> BranchManager:
        """Get the appropriate BranchManager for branch operations.

        Returns GitBranchManager when Graphite is disabled,
        GraphiteBranchManager when Graphite is enabled.

        This provides a unified interface for branch operations that
        handles Graphite vs plain Git differences transparently.
        """
        # Check if Graphite is disabled (also handles DryRunGraphite wrapping GraphiteDisabled)
        graphite = self.graphite
        if isinstance(graphite, DryRunGraphite):
            graphite = graphite._wrapped
        if isinstance(graphite, GraphiteDisabled):
            return GitBranchManager(
                git=self.git,
                git_branch_ops=self.git_branch_ops,
                github=self.github,
            )
        if self.graphite_branch_ops is None:
            raise RuntimeError("graphite_branch_ops must be set when Graphite is enabled")
        return GraphiteBranchManager(
            git=self.git,
            git_branch_ops=self.git_branch_ops,
            graphite=self.graphite,
            graphite_branch_ops=self.graphite_branch_ops,
            github=self.github,
        )

    @staticmethod
    def for_test(
        *,
        github_issues: GitHubIssues | None = None,
        git: Git | None = None,
        github: GitHub | None = None,
        claude_installation: ClaudeInstallation | None = None,
        prompt_executor: PromptExecutor | None = None,
        claude_executor: ClaudeExecutor | None = None,
        debug: bool = False,
        repo_root: Path | None = None,
        cwd: Path | None = None,
        repo_info: RepoInfo | None = None,
    ) -> ErkContext:
        """Create test context with optional pre-configured implementations.

        Provides full control over all context parameters with sensible test defaults
        for any unspecified values. Uses fakes by default to avoid subprocess calls.

        Args:
            github_issues: Optional GitHubIssues implementation. If None, creates FakeGitHubIssues.
            git: Optional Git implementation. If None, creates FakeGit.
            github: Optional GitHub implementation. If None, creates FakeGitHub.
            claude_installation: ClaudeInstallation or None. Creates FakeClaudeInstallation if None.
            prompt_executor: Optional PromptExecutor. If None, creates FakePromptExecutor.
            claude_executor: Optional ClaudeExecutor. If None, creates FakeClaudeExecutor.
            debug: Whether to enable debug mode (default False).
            repo_root: Repository root path (defaults to Path("/fake/repo"))
            cwd: Current working directory (defaults to Path("/fake/worktree"))
            repo_info: Optional RepoInfo (owner/name). If None, repo_info will be None in context.

        Returns:
            ErkContext configured with provided values and test defaults

        Example:
            >>> from erk_shared.gateway.github.issues import FakeGitHubIssues
            >>> from erk_shared.gateway.git.fake import FakeGit
            >>> github = FakeGitHubIssues()
            >>> git_ops = FakeGit()
            >>> ctx = ErkContext.for_test(github_issues=github, git=git_ops, debug=True)
        """
        from erk_shared.context.testing import context_for_test

        return context_for_test(
            github_issues=github_issues,
            git=git,
            github=github,
            claude_installation=claude_installation,
            prompt_executor=prompt_executor,
            claude_executor=claude_executor,
            debug=debug,
            repo_root=repo_root,
            cwd=cwd,
            repo_info=repo_info,
        )
