"""Context types for erk and erk-kits.

This module provides the core data types used by ErkContext:
- RepoContext: Repository discovery result
- NoRepoSentinel: Sentinel for when not in a repository
- GlobalConfig: Global erk configuration
- LoadedConfig: Repository-level configuration
- InteractiveAgentConfig: Configuration for interactive agent launches (Claude or Codex)
- AgentBackend: Type for agent backend selection
- PermissionMode: Generic permission mode for both Claude and Codex
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal, Self

from erk_shared.gateway.github.types import GitHubRepoId

# Agent backend types
AgentBackend = Literal["claude", "codex"]

# Plan storage backend types
PlanBackendType = Literal["draft_pr", "github"]

# Claude CLI permission modes:
# - "default": Default mode with permission prompts
# - "acceptEdits": Accept edits without prompts (--permission-mode acceptEdits)
# - "plan": Plan mode for exploration and planning (--permission-mode plan)
# - "bypassPermissions": Bypass all permissions (--permission-mode bypassPermissions)
ClaudePermissionMode = Literal["default", "acceptEdits", "plan", "bypassPermissions"]

# Generic permission mode that maps to both Claude and Codex
# - "safe": Default mode with permission prompts (Claude "default", Codex "--sandbox read-only")
# - "edits": Accept edits without prompts (Claude "acceptEdits", Codex "--full-auto")
# - "plan": Plan mode for exploration (Claude "plan", Codex "--sandbox read-only")
# - "dangerous": Bypass all permissions (Claude skip permissions, Codex "--yolo")
PermissionMode = Literal["safe", "edits", "plan", "dangerous"]


@cache
def permission_mode_to_claude(permission_mode: PermissionMode) -> ClaudePermissionMode:
    """Map generic permission mode to Claude-specific permission mode."""
    lookup: dict[PermissionMode, ClaudePermissionMode] = {
        "safe": "default",
        "edits": "acceptEdits",
        "plan": "plan",
        "dangerous": "bypassPermissions",
    }
    if permission_mode in lookup:
        return lookup[permission_mode]
    raise ValueError(f"Unknown permission_mode: {permission_mode}")


@cache
def permission_mode_to_codex_exec(permission_mode: PermissionMode) -> list[str]:
    """Map generic permission mode to Codex CLI flags for exec (headless) mode.

    Codex exec mode: approval is hardcoded to Never, so only sandbox flags matter.
    See docs/learned/integrations/codex/codex-cli-reference.md for rationale.

    Args:
        permission_mode: Generic erk permission mode.

    Returns:
        List of CLI flag strings to pass to the codex command.
    """
    lookup: dict[PermissionMode, list[str]] = {
        "safe": ["--sandbox", "read-only"],
        "edits": ["--full-auto"],
        "plan": ["--sandbox", "read-only"],
        "dangerous": ["--yolo"],
    }
    if permission_mode in lookup:
        return lookup[permission_mode]
    raise ValueError(f"Unknown permission_mode: {permission_mode}")


@cache
def permission_mode_to_codex_tui(permission_mode: PermissionMode) -> list[str]:
    """Map generic permission mode to Codex CLI flags for TUI (interactive) mode.

    Codex TUI mode: both sandbox and approval flags are needed.
    See docs/learned/integrations/codex/codex-cli-reference.md for rationale.

    Args:
        permission_mode: Generic erk permission mode.

    Returns:
        List of CLI flag strings to pass to the codex command.
    """
    lookup: dict[PermissionMode, list[str]] = {
        "safe": ["--sandbox", "read-only", "-a", "untrusted"],
        "edits": ["--sandbox", "workspace-write", "-a", "on-request"],
        "plan": ["--sandbox", "read-only", "-a", "never"],
        "dangerous": ["--yolo"],
    }
    if permission_mode in lookup:
        return lookup[permission_mode]
    raise ValueError(f"Unknown permission_mode: {permission_mode}")


@dataclass(frozen=True)
class RepoContext:
    """Represents a git repo root and its managed worktrees directory.

    Attributes:
        root: The actual working tree root (where git commands run).
              For worktrees, this is the worktree directory.
              For main repos, this equals main_repo_root.
        repo_name: Name of the repository (derived from main_repo_root).
        repo_dir: Path to erk metadata directory (~/.erk/repos/<repo-name>).
        worktrees_dir: Path to worktrees directory (~/.erk/repos/<repo-name>/worktrees).
        main_repo_root: The main repository root (for consistent metadata paths).
                       For worktrees, this is the parent repo's root directory.
                       For main repos, this equals root.
                       Defaults to root for backwards compatibility.
        github: GitHub repository identity, if available.
    """

    root: Path
    repo_name: str
    repo_dir: Path  # ~/.erk/repos/<repo-name>
    worktrees_dir: Path  # ~/.erk/repos/<repo-name>/worktrees
    pool_json_path: Path  # ~/.erk/repos/<repo-name>/pool.json
    main_repo_root: Path | None = None  # Defaults to root for backwards compatibility
    github: GitHubRepoId | None = None  # None if not a GitHub repo or no remote

    def __post_init__(self) -> None:
        """Set main_repo_root to root if not provided."""
        if self.main_repo_root is None:
            # Use object.__setattr__ because dataclass is frozen
            object.__setattr__(self, "main_repo_root", self.root)


@dataclass(frozen=True)
class NoRepoSentinel:
    """Sentinel value indicating execution outside a git repository.

    Used when commands run outside git repositories (e.g., before init,
    in non-git directories). Commands that require repo context can check
    for this sentinel and fail fast.
    """

    message: str = "Not inside a git repository"


@dataclass(frozen=True)
class InteractiveAgentConfig:
    """Configuration for interactive agent CLI launches.

    All fields are optional in the config file. CLI flags always override
    config values. This is loaded from [interactive-agent] section in
    ~/.erk/config.toml (with backward compatibility for [interactive-claude]).

    Attributes:
        backend: Which agent backend to use (claude or codex)
        model: Model to use (e.g., "claude-opus-4-5" or "gpt-4")
        verbose: Whether to show verbose output
        permission_mode: Generic permission mode. See PermissionMode for options.
        dangerous: Whether to skip permission prompts
        allow_dangerous: Whether to enable allowing dangerous operations,
            which lets the user opt into skipping prompts during a session
    """

    backend: AgentBackend
    model: str | None
    verbose: bool
    permission_mode: PermissionMode
    dangerous: bool
    allow_dangerous: bool

    @staticmethod
    def default() -> InteractiveAgentConfig:
        """Create default configuration with sensible defaults."""
        return InteractiveAgentConfig(
            backend="claude",
            model=None,
            verbose=False,
            permission_mode="edits",
            dangerous=False,
            allow_dangerous=False,
        )

    def with_overrides(
        self: Self,
        *,
        permission_mode_override: PermissionMode | None,
        model_override: str | None,
        dangerous_override: bool | None,
        allow_dangerous_override: bool | None,
    ) -> InteractiveAgentConfig:
        """Create a new config with CLI overrides applied.

        CLI flags always override config values. Pass None to keep config value.

        Args:
            permission_mode_override: Override permission_mode if not None
            model_override: Override model if not None
            dangerous_override: Override dangerous if not None
            allow_dangerous_override: Override allow_dangerous if not None

        Returns:
            New InteractiveAgentConfig with overrides applied
        """
        new_permission_mode: PermissionMode = (
            permission_mode_override
            if permission_mode_override is not None
            else self.permission_mode
        )
        return InteractiveAgentConfig(
            backend=self.backend,
            model=model_override if model_override is not None else self.model,
            verbose=self.verbose,
            permission_mode=new_permission_mode,
            dangerous=dangerous_override if dangerous_override is not None else self.dangerous,
            allow_dangerous=(
                allow_dangerous_override
                if allow_dangerous_override is not None
                else self.allow_dangerous
            ),
        )


@dataclass(frozen=True)
class GlobalConfig:
    """Immutable global configuration data.

    Loaded once at CLI entry point and stored in ErkContext.
    All fields are read-only after construction.
    """

    erk_root: Path
    use_graphite: bool
    shell_setup_complete: bool
    github_planning: bool
    fix_conflicts_require_dangerous_flag: bool = True
    show_hidden_commands: bool = False
    prompt_learn_on_land: bool = True
    shell_integration: bool = False
    interactive_agent: InteractiveAgentConfig = InteractiveAgentConfig.default()

    @staticmethod
    def test(
        erk_root: Path,
        *,
        use_graphite: bool = True,
        shell_setup_complete: bool = True,
        github_planning: bool = True,
        fix_conflicts_require_dangerous_flag: bool = True,
        show_hidden_commands: bool = False,
        prompt_learn_on_land: bool = True,
        shell_integration: bool = False,
        interactive_agent: InteractiveAgentConfig | None = None,
    ) -> GlobalConfig:
        """Create a GlobalConfig with sensible test defaults."""
        return GlobalConfig(
            erk_root=erk_root,
            use_graphite=use_graphite,
            shell_setup_complete=shell_setup_complete,
            github_planning=github_planning,
            fix_conflicts_require_dangerous_flag=fix_conflicts_require_dangerous_flag,
            show_hidden_commands=show_hidden_commands,
            prompt_learn_on_land=prompt_learn_on_land,
            shell_integration=shell_integration,
            interactive_agent=(
                interactive_agent
                if interactive_agent is not None
                else InteractiveAgentConfig.default()
            ),
        )


@dataclass(frozen=True)
class LoadedConfig:
    """In-memory representation of merged repo + project config."""

    env: dict[str, str]
    post_create_commands: list[str]
    post_create_shell: str | None
    plans_repo: str | None
    pool_size: int | None  # None = use default
    pool_checkout_commands: list[str]  # Commands to run after pooled checkout
    pool_checkout_shell: str | None  # Shell to use for checkout commands
    # Overridable global keys (can be set at repo or local level to override global config)
    prompt_learn_on_land: bool | None  # None = not set at this level, use global

    @staticmethod
    def test(
        *,
        env: dict[str, str] | None = None,
        post_create_commands: list[str] | None = None,
        post_create_shell: str | None = None,
        plans_repo: str | None = None,
        pool_size: int | None = None,
        pool_checkout_commands: list[str] | None = None,
        pool_checkout_shell: str | None = None,
        prompt_learn_on_land: bool | None = None,
    ) -> LoadedConfig:
        """Create a LoadedConfig with sensible test defaults."""
        return LoadedConfig(
            env=env if env is not None else {},
            post_create_commands=post_create_commands if post_create_commands is not None else [],
            post_create_shell=post_create_shell,
            plans_repo=plans_repo,
            pool_size=pool_size,
            pool_checkout_commands=(
                pool_checkout_commands if pool_checkout_commands is not None else []
            ),
            pool_checkout_shell=pool_checkout_shell,
            prompt_learn_on_land=prompt_learn_on_land,
        )
