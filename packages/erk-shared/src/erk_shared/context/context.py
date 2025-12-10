"""Unified context for erk and dot-agent-kit operations.

This module provides ErkContext - the unified context that holds all dependencies
for erk and dot-agent-kit operations.

Note: Factory methods (minimal, for_test, etc.) are NOT defined here because they
require erk-specific ABCs (ClaudeExecutor, etc.) and test fakes. Those factories
are defined in erk.core.context to avoid circular imports.

Use ErkContext directly for type hints, and use the factories from erk.core.context
for instantiation.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from erk_shared.context.types import (
    GlobalConfig,
    LoadedConfig,
    NoRepoSentinel,
    RepoContext,
)
from erk_shared.extraction.claude_code_session_store import ClaudeCodeSessionStore
from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.github.issues import GitHubIssues
from erk_shared.github.types import RepoInfo
from erk_shared.integrations.completion import Completion
from erk_shared.integrations.feedback import UserFeedback
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.shell import Shell
from erk_shared.integrations.time.abc import Time
from erk_shared.objectives.storage import ObjectiveStore
from erk_shared.plan_store.store import PlanStore
from erk_shared.project_discovery import ProjectContext
from erk_shared.prompt_executor import PromptExecutor

if TYPE_CHECKING:
    # These ABCs stay in erk package due to their dependencies.
    # Imported only for documentation - actual type hints use Any to avoid import cycles.
    from erk.core.claude_executor import ClaudeExecutor as ClaudeExecutor
    from erk.core.config_store import ConfigStore as ConfigStore
    from erk.core.planner.registry_abc import PlannerRegistry as PlannerRegistry
    from erk.core.script_writer import ScriptWriter as ScriptWriter
    from erk.core.services.plan_list_service import PlanListService as PlanListService


@dataclass(frozen=True)
class ErkContext:
    """Immutable context holding all dependencies for erk and dot-agent-kit operations.

    Created at CLI entry point and threaded through the application via Click's
    context system. Frozen to prevent accidental modification at runtime.

    This unified context replaces both the old ErkContext (from erk.core.context)
    and DotAgentContext (from dot_agent_kit.context).

    Note:
    - global_config may be None only during init command before config is created.
      All other commands should have a valid GlobalConfig.
    - Factory methods (minimal, for_test) are in erk.core.context, not here.

    DotAgentContext Compatibility:
    - github_issues -> issues (renamed for consistency)
    - repo_root property -> repo.root (access via repo property or require_repo_root helper)
    - debug field -> debug (preserved)
    """

    # Gateway integrations (from erk_shared)
    git: Git
    github: GitHub
    issues: GitHubIssues  # Note: ErkContext naming (was github_issues in DotAgentContext)
    graphite: Graphite
    time: Time
    session_store: ClaudeCodeSessionStore
    plan_store: PlanStore
    objectives: ObjectiveStore
    prompt_executor: PromptExecutor  # From DotAgentContext

    # Shell/CLI integrations (moved to erk_shared)
    shell: Shell
    completion: Completion
    feedback: UserFeedback

    # Erk-specific (ABCs stay in erk, injected as Any to avoid import cycle)
    # Type hints are provided for static analysis via TYPE_CHECKING
    claude_executor: Any  # ClaudeExecutor at runtime
    config_store: Any  # ConfigStore at runtime
    script_writer: Any  # ScriptWriter at runtime
    planner_registry: Any  # PlannerRegistry at runtime
    plan_list_service: Any  # PlanListService at runtime

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
