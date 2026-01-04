"""Context types for erk and erk-kits.

This module provides the core data types used by ErkContext:
- RepoContext: Repository discovery result
- NoRepoSentinel: Sentinel for when not in a repository
- GlobalConfig: Global erk configuration
- LoadedConfig: Repository-level configuration
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from erk_shared.github.types import GitHubRepoId


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
class GlobalConfig:
    """Immutable global configuration data.

    Loaded once at CLI entry point and stored in ErkContext.
    All fields are read-only after construction.
    """

    erk_root: Path
    use_graphite: bool
    shell_setup_complete: bool
    show_pr_info: bool
    github_planning: bool
    auto_restack_require_dangerous_flag: bool = True
    fix_conflicts_require_dangerous_flag: bool = True
    show_hidden_commands: bool = False

    @staticmethod
    def test(
        erk_root: Path,
        *,
        use_graphite: bool = True,
        shell_setup_complete: bool = True,
        show_pr_info: bool = True,
        github_planning: bool = True,
        auto_restack_require_dangerous_flag: bool = True,
        fix_conflicts_require_dangerous_flag: bool = True,
        show_hidden_commands: bool = False,
    ) -> GlobalConfig:
        """Create a GlobalConfig with sensible test defaults."""
        return GlobalConfig(
            erk_root=erk_root,
            use_graphite=use_graphite,
            shell_setup_complete=shell_setup_complete,
            show_pr_info=show_pr_info,
            github_planning=github_planning,
            auto_restack_require_dangerous_flag=auto_restack_require_dangerous_flag,
            fix_conflicts_require_dangerous_flag=fix_conflicts_require_dangerous_flag,
            show_hidden_commands=show_hidden_commands,
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
        )
