"""Centralized test environment helpers for simulating erk scenarios.

This module provides helpers for setting up realistic erk test environments
with Click's CliRunner. It provides two patterns:

1. erk_isolated_fs_env(): Filesystem-based (uses isolated_filesystem(),
   creates real directories)
2. erk_inmem_env(): In-memory (uses fakes only, no filesystem I/O)

Key Components:
    - ErkIsolatedFsEnv: Helper class for filesystem-based testing
    - ErkInMemEnv: Helper class for in-memory testing
    - erk_isolated_fs_env(): Context manager for filesystem-based tests
    - erk_inmem_env(): Context manager for in-memory tests

Usage Pattern:

    Before (raw isolated_filesystem pattern - 20-30 lines per test):
    ```python
    def test_something() -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            cwd = Path.cwd()
            git_dir = cwd / ".git"
            git_dir.mkdir()
            erk_root = cwd / "erks"
            erk_root.mkdir()

            git = FakeGit(git_common_dirs={cwd: git_dir})
            global_config = GlobalConfig.test(...)
            test_ctx = context_for_test(cwd=cwd, ...)

            result = runner.invoke(cli, ["command"], obj=test_ctx)
    ```

    After (using erk_isolated_fs_env - ~10 lines per test):
    ```python
    def test_something() -> None:
        runner = CliRunner()
        with erk_isolated_fs_env(runner) as env:
            git = FakeGit(git_common_dirs={env.cwd: env.git_dir})
            global_config = GlobalConfig.test(...)
            script_writer=env.script_writer,
            test_ctx = context_for_test(cwd=env.cwd, ...)

            result = runner.invoke(cli, ["command"], obj=test_ctx)
    ```

Advanced Usage (complex worktree scenarios):
    ```python
    def test_multi_worktree_scenario() -> None:
        runner = CliRunner()
        with erk_isolated_fs_env(runner) as env:
            # Create linked worktrees
            env.create_linked_worktree("feat-1", "feat-1", chdir=False)
            env.create_linked_worktree("feat-2", "feat-2", chdir=True)

            # Build ops from branch metadata
            git, graphite = env.build_ops_from_branches(
                {
                    "main": BranchMetadata.trunk("main", children=["feat-1"]),
                    "feat-1": BranchMetadata.branch("feat-1", "main", children=["feat-2"]),
                    "feat-2": BranchMetadata.branch("feat-2", "feat-1"),
                },
                current_branch="feat-2",
            )

            script_writer=env.script_writer,
            test_ctx = context_for_test(cwd=env.cwd, git=git, ...)
    ```

Directory Structure Created:
    base/
      ├── repo/         (root worktree with .git/)
      └── erks/   (parallel to repo, initially empty)

Note: This helper is specifically for CliRunner tests. For pytest's tmp_path fixture,
use alternative patterns or integration tests instead.
"""

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from click.testing import CliRunner

from erk.core.context import ErkContext, context_for_test
from erk.core.repo_discovery import RepoContext
from erk.core.script_writer import RealScriptWriter
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.git.abc import Git, WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import GitHubRepoId
from tests.fakes.script_writer import FakeScriptWriter
from tests.fakes.shell import FakeShell


class ErkIsolatedFsEnv:
    """Helper for managing simulated erk test environment.

    This class provides utilities for:
    - Managing root and linked worktrees
    - Building FakeGit and FakeGraphite from branch metadata
    - Creating realistic git directory structures

    Attributes:
        cwd: Current working directory (initially root_worktree)
        git_dir: Path to .git directory (root_worktree / ".git")
        root_worktree: Path to root worktree (has .git/ directory)
        erk_root: Path to erks directory (parallel to root)
        script_writer: RealScriptWriter for creating actual temp files
        repo: RepoContext computed from root_worktree and erk_root
    """

    def __init__(self, root_worktree: Path, erk_root: Path) -> None:
        """Initialize test environment.

        Args:
            root_worktree: Path to root worktree (has .git/ directory)
            erk_root: Path to erks directory (parallel to root)
        """
        self.root_worktree = root_worktree
        self.erk_root = erk_root
        self.script_writer = RealScriptWriter()
        self._linked_worktrees: dict[str, Path] = {}  # Track branch -> worktree path
        # Match production path structure: erk_root / "repos" / repo_name
        repo_dir = erk_root / "repos" / root_worktree.name
        self._repo = RepoContext(
            root=root_worktree,
            repo_name=root_worktree.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
            github=GitHubRepoId(owner="owner", repo="repo"),
        )

    @property
    def cwd(self) -> Path:
        """Current working directory (convenience property)."""
        return self.root_worktree

    @property
    def git_dir(self) -> Path:
        """Path to .git directory (convenience property)."""
        return self.root_worktree / ".git"

    @property
    def repo(self) -> RepoContext:
        """RepoContext constructed from root worktree paths."""
        return self._repo

    def setup_repo_structure(self, create_config: bool = True) -> Path:
        """Create standard erk repo directory structure with worktrees folder.

        Creates:
            {erk_root}/repos/{cwd.name}/
            {erk_root}/repos/{cwd.name}/worktrees/
            {erk_root}/repos/{cwd.name}/config.toml (if create_config=True)

        Args:
            create_config: Whether to create empty config.toml file

        Returns:
            Path to repo directory ({erk_root}/repos/{cwd.name})

        Example:
            >>> with erk_isolated_fs_env(runner) as env:
            ...     repo_dir = env.setup_repo_structure()
            ...     # repo_dir = env.erk_root / "repos" / env.cwd.name
            ...     # Already has worktrees/ subdirectory created
        """
        repo_dir = self.erk_root / "repos" / self.cwd.name
        repo_dir.mkdir(parents=True, exist_ok=True)

        worktrees_dir = repo_dir / "worktrees"
        worktrees_dir.mkdir(parents=True, exist_ok=True)

        if create_config:
            config_toml = repo_dir / "config.toml"
            config_toml.write_text("", encoding="utf-8")

        return repo_dir

    def build_worktrees(
        self,
        root_branch: str = "main",
        linked_branches: list[str] | None = None,
        *,
        repo_dir: Path | None = None,
    ) -> dict[Path, list[WorktreeInfo]]:
        """Build standard worktree configuration for test scenarios.

        Creates a worktree list with:
        - Root worktree at self.cwd with specified branch
        - Linked worktrees in repo_dir/{branch} for each linked branch

        Args:
            root_branch: Branch name for root worktree (default: "main")
            linked_branches: List of linked worktree branches (default: [])
            repo_dir: Base directory for linked worktrees (default: auto-calculated)

        Returns:
            Dict mapping repo root to list of WorktreeInfo instances

        Example:
            >>> # Before (10-15 lines):
            >>> worktrees = {
            ...     env.cwd: [
            ...         WorktreeInfo(path=env.cwd, branch="main", is_root=True),
            ...         WorktreeInfo(
            ...             path=repo_dir / "worktrees" / "feat-1", branch="feat-1", is_root=False
            ...         ),
            ...         WorktreeInfo(
            ...             path=repo_dir / "worktrees" / "feat-2", branch="feat-2", is_root=False
            ...         ),
            ...     ]
            ... }
            >>> # After (1 line):
            >>> worktrees = env.build_worktrees("main", ["feat-1", "feat-2"])
        """
        if repo_dir is None:
            repo_dir = self.erk_root / "repos" / self.cwd.name

        worktrees = [WorktreeInfo(path=self.cwd, branch=root_branch, is_root=True)]

        for branch in linked_branches or []:
            worktrees.append(
                WorktreeInfo(
                    path=repo_dir / "worktrees" / branch,
                    branch=branch,
                    is_root=False,
                )
            )

        return {self.cwd: worktrees}

    def create_linked_worktree(self, name: str, branch: str, *, chdir: bool) -> Path:
        """Create a linked worktree in erks directory.

        Args:
            name: Name for the worktree directory
            branch: Branch name for the worktree
            chdir: Whether to change working directory to the new worktree (required)

        Returns:
            Path to the created linked worktree

        Example:
            ```python
            # Create but stay in root worktree
            wt1 = env.create_linked_worktree("feat-1", "feat-1", chdir=False)

            # Create and switch to it
            wt2 = env.create_linked_worktree("feat-2", "feat-2", chdir=True)
            assert Path.cwd() == wt2
            ```
        """
        # Create linked worktree directory
        linked_wt = self.erk_root / "repo" / name
        linked_wt.mkdir(parents=True)

        # Create .git file pointing to root worktree
        git_file = linked_wt / ".git"
        git_file.write_text(
            f"gitdir: {self.root_worktree / '.git' / 'worktrees' / name}\n",
            encoding="utf-8",
        )

        # Create worktree metadata in root's .git/worktrees/
        worktree_meta_dir = self.root_worktree / ".git" / "worktrees" / name
        worktree_meta_dir.mkdir(parents=True)

        # Change directory if requested
        if chdir:
            os.chdir(linked_wt)

        # Track the mapping for build_ops_from_branches()
        self._linked_worktrees[branch] = linked_wt

        return linked_wt

    def build_ops_from_branches(
        self,
        branches: dict[str, BranchMetadata],
        *,
        current_branch: str | None = None,
        current_worktree: Path | None = None,
    ) -> tuple[FakeGit, FakeGraphite]:
        """Build both FakeGit and FakeGraphite from branch metadata.

        Automatically:
        - Maps branches to worktrees (root + any created linked worktrees)
        - Computes stacks dict from parent/child relationships
        - Configures git_common_dirs for all worktrees
        - Sets current branch in specified worktree

        Args:
            branches: Branch metadata with parent/child relationships
            current_branch: Which branch is checked out (defaults to root's branch)
            current_worktree: Where current_branch is (defaults to root_worktree)

        Returns:
            Tuple of (FakeGit, FakeGraphite) configured for testing

        Example:
            ```python
            env.create_linked_worktree("feat-1", "feat-1", chdir=False)
            env.create_linked_worktree("feat-2", "feat-2", chdir=True)

            git, graphite = env.build_ops_from_branches(
                {
                    "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                    "feat-1": BranchMetadata.branch(
                        "feat-1", "main", children=["feat-2"], commit_sha="def456"
                    ),
                    "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
                },
                current_branch="feat-2",
            )
            # Now git and graphite are configured with full stack relationships
            ```
        """
        current_worktree = current_worktree or self.root_worktree

        # Find trunk branch (for root worktree)
        trunk_branch = None
        for name, meta in branches.items():
            if meta.is_trunk:
                trunk_branch = name
                break

        if trunk_branch is None:
            trunk_branch = "main"  # Fallback

        # Build worktrees list
        worktrees_list = [WorktreeInfo(path=self.root_worktree, branch=trunk_branch, is_root=True)]

        # Add linked worktrees created via create_linked_worktree()
        for branch, path in self._linked_worktrees.items():
            worktrees_list.append(WorktreeInfo(path=path, branch=branch, is_root=False))

        # Build current_branches mapping
        current_branches_map = {}
        for wt in worktrees_list:
            if wt.path == current_worktree:
                # This worktree has the current branch
                current_branches_map[wt.path] = current_branch if current_branch else wt.branch
            else:
                # Other worktrees stay on their own branch
                current_branches_map[wt.path] = wt.branch

        # Build git_common_dirs mapping (all point to root's .git)
        git_common_dirs_map = {wt.path: self.root_worktree / ".git" for wt in worktrees_list}

        # Build stacks from branches (auto-compute from parent/child)
        stacks = {}
        for branch_name in branches:
            if not branches[branch_name].is_trunk:
                stacks[branch_name] = self._build_stack_path(branches, branch_name)

        git = FakeGit(
            worktrees={self.root_worktree: worktrees_list},
            current_branches=current_branches_map,
            git_common_dirs=git_common_dirs_map,
        )

        graphite = FakeGraphite(
            branches=branches,
            stacks=stacks,
        )

        return git, graphite

    def build_context(
        self,
        *,
        current_branch: str | None = None,
        trunk_branch: str = "main",
        use_graphite: bool = False,
        git: Git | None = None,
        graphite: FakeGraphite | None = None,
        github: FakeGitHub | None = None,
        shell: FakeShell | None = None,
        repo: RepoContext | None = None,
        dry_run: bool = False,
        **kwargs,
    ) -> ErkContext:
        """Build ErkContext with smart defaults for test scenarios.

        This helper eliminates boilerplate by providing default ops and config
        for tests that don't need custom setup. Custom values can be provided
        via keyword arguments.

        Args:
            current_branch: If provided, auto-configures FakeGit.current_branches
            trunk_branch: Default branch name (default: "main")
            use_graphite: Enable Graphite integration (default: False)
            git: Custom FakeGit instance (overrides smart defaults)
            graphite: Custom FakeGraphite instance
            github: Custom FakeGitHub instance
            shell: Custom FakeShell instance
            repo: Custom RepoContext (default: None)
            dry_run: Whether to wrap with DryRunGit
            **kwargs: Additional context_for_test() parameters

        Returns:
            ErkContext configured for testing

        Example:
            ```python
            with erk_isolated_fs_env(runner) as env:
                # Simple case - use all defaults
                ctx = env.build_context()

                # Before (5 lines):
                git_ops = FakeGit(
                    git_common_dirs={env.cwd: env.git_dir},
                    default_branches={env.cwd: "main"},
                    current_branches={env.cwd: "feature-1"},
                )
                ctx = context_for_test(..., git=git_ops, ...)

                # After (1 line):
                ctx = env.build_context(current_branch="feature-1")

                # Custom git ops with branches
                git, graphite = env.build_ops_from_branches(...)
                ctx = env.build_context(git=git, graphite=graphite)

                # Enable Graphite with custom config
                ctx = env.build_context(use_graphite=True)
            ```
        """
        # Determine repo to use (either provided or default)
        if repo is None:
            repo = self._repo

        # Smart FakeGit configuration
        if git is None:
            git = FakeGit(
                git_common_dirs={self.cwd: self.git_dir},
                default_branches={self.cwd: trunk_branch},
                current_branches={self.cwd: current_branch} if current_branch else {},
                existing_paths={
                    self.cwd,
                    self.git_dir,
                    self.erk_root,
                    repo.root,
                    repo.repo_dir,
                },
                remote_urls={(self.cwd, "origin"): "https://github.com/owner/repo.git"},
            )
        else:
            from erk_shared.git.dry_run import DryRunGit

            unwrapped_ops = git._wrapped if isinstance(git, DryRunGit) else git

            # Add core paths to existing_paths if they're actually git repos
            # Only add paths that are in git_common_dirs (actual repos)
            has_existing = hasattr(unwrapped_ops, "_existing_paths")
            has_git_common = hasattr(unwrapped_ops, "_git_common_dirs")
            has_worktrees = hasattr(unwrapped_ops, "_worktrees")
            if has_existing and has_git_common:
                # Determine which cwd to use (custom or default)
                effective_cwd = kwargs.get("cwd", self.cwd)

                # Collect core paths - always include cwd and erk_root
                core_paths = {
                    self.cwd,
                    effective_cwd,
                    self.erk_root,
                    repo.repo_dir,
                }

                # Only add git_dir and repo.root if this is actually a git repo
                # (i.e., git_common_dirs is not empty)
                if unwrapped_ops._git_common_dirs:
                    core_paths.update({self.git_dir, repo.root})

                # Also add all worktree paths from git
                if has_worktrees:
                    for worktree_list in unwrapped_ops._worktrees.values():
                        for wt_info in worktree_list:
                            core_paths.add(wt_info.path)

                unwrapped_ops._existing_paths.update(core_paths)

        # Wrap with DryRunGit for dry-run mode (only if not already wrapped)
        if dry_run:
            from erk_shared.git.dry_run import DryRunGit

            if not isinstance(git, DryRunGit):
                git = DryRunGit(git)

        # Smart integration defaults
        # When use_graphite=False, use GraphiteDisabled sentinel to match production
        # behavior. This ensures ErkContext.branch_manager returns GitBranchManager
        # and branch operations use FakeGit.delete_branch (tracked in deleted_branches).
        if graphite is None:
            if use_graphite:
                graphite = FakeGraphite()
            else:
                from erk_shared.gateway.graphite.disabled import (
                    GraphiteDisabled,
                    GraphiteDisabledReason,
                )

                graphite = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)

        if github is None:
            github = FakeGitHub()

        if shell is None:
            shell = FakeShell()

        # Create global config if not provided in kwargs
        if "global_config" in kwargs:
            # Use the provided global_config (might be None for init tests)
            global_config = kwargs.pop("global_config")
        else:
            # Create default global config
            global_config = GlobalConfig.test(
                self.erk_root,
                use_graphite=use_graphite,
                shell_setup_complete=False,
            )

        # Build and return context
        # Default cwd and script_writer to env values unless overridden in kwargs
        if "cwd" not in kwargs:
            kwargs["cwd"] = self.cwd
        if "script_writer" not in kwargs:
            kwargs["script_writer"] = self.script_writer

        # Filter out erk_root - it's already set in global_config above
        # Tests shouldn't override it via kwargs
        if "erk_root" in kwargs:
            kwargs.pop("erk_root")

        # Filter out trunk_branch - it's now a computed property based on git
        if "trunk_branch" in kwargs:
            kwargs.pop("trunk_branch")

        return context_for_test(
            git=git,
            graphite=graphite,
            github=github,
            shell=shell,
            global_config=global_config,
            repo=repo,
            dry_run=dry_run,
            **kwargs,
        )

    def _build_stack_path(
        self,
        branches: dict[str, BranchMetadata],
        leaf: str,
    ) -> list[str]:
        """Build stack path from trunk to leaf.

        Args:
            branches: All branch metadata
            leaf: Leaf branch name

        Returns:
            List of branch names from trunk to leaf (inclusive)
        """
        stack = []
        current = leaf

        # Walk up to trunk
        while current in branches:
            stack.insert(0, current)
            parent = branches[current].parent

            if parent is None:
                # Reached trunk
                break

            if parent not in branches:
                # Parent not in branches dict, stop
                break

            current = parent

        return stack


@contextmanager
def erk_isolated_fs_env(runner: CliRunner) -> Generator[ErkIsolatedFsEnv]:
    """Set up simulated erk environment with isolated filesystem.

    Creates realistic directory structure:
        base/
          ├── repo/         (root worktree with .git/)
          └── erks/   (parallel to repo, initially empty)

    Defaults to root worktree. Use env.create_linked_worktree() to create
    and optionally navigate to linked worktrees.

    IMPORTANT: This context manager handles runner.isolated_filesystem() internally.
    Do NOT nest this inside runner.isolated_filesystem() - that would create
    double indentation and is unnecessary.

    Args:
        runner: Click CliRunner instance

    Yields:
        SimulatedWorkstackEnv helper for managing test environment

    Example:
        ```python
        def test_something() -> None:
            runner = CliRunner()
            # Note: erk_isolated_fs_env() handles isolated_filesystem() internally
            with erk_isolated_fs_env(runner) as env:
                # env.cwd is available (root worktree)
                # env.git_dir is available (.git directory)
                # env.script_writer is available (RealScriptWriter for temp files)
                git = FakeGit(git_common_dirs={env.cwd: env.git_dir})
                test_ctx = context_for_test(
                    cwd=env.cwd,
                    script_writer=env.script_writer,
                    ...
                )
        ```
    """
    with runner.isolated_filesystem():
        base = Path.cwd()  # isolated_filesystem() creates temp dir and changes cwd to it

        # Create root worktree with .git directory
        root_worktree = base / "repo"
        root_worktree.mkdir()
        (root_worktree / ".git").mkdir()

        # Create erks directory
        erk_root = base / "erks"
        erk_root.mkdir()

        # Default to root worktree
        os.chdir(root_worktree)

        yield ErkIsolatedFsEnv(
            root_worktree=root_worktree,
            erk_root=erk_root,
        )


class ErkInMemEnv:
    """Helper for pure in-memory testing without filesystem I/O.

    Use this for tests that verify command logic without needing
    actual filesystem operations. This is faster and simpler than
    erk_isolated_fs_env() for tests that don't need real directories.

    Attributes:
        cwd: Sentinel path representing current working directory
        git_dir: Sentinel path representing .git directory
        erk_root: Sentinel path for erks directory
        script_writer: FakeScriptWriter for in-memory script verification
        repo: RepoContext computed from cwd and erk_root
    """

    def __init__(
        self,
        cwd: Path,
        git_dir: Path,
        erk_root: Path,
        script_writer: FakeScriptWriter,
    ) -> None:
        """Initialize pure test environment.

        Args:
            cwd: Sentinel path for current working directory
            git_dir: Sentinel path for .git directory
            erk_root: Sentinel path for erks directory
            script_writer: FakeScriptWriter instance for script verification
        """
        self.cwd = cwd
        self.git_dir = git_dir
        self.erk_root = erk_root
        self.script_writer = script_writer
        self._linked_worktrees: dict[str, Path] = {}  # Track branch -> worktree path
        repo_dir = erk_root / "repos" / cwd.name
        self._repo = RepoContext(
            root=cwd,
            repo_name=cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
            github=GitHubRepoId(owner="owner", repo="repo"),
        )

    @property
    def repo(self) -> RepoContext:
        """RepoContext constructed from sentinel paths."""
        return self._repo

    @property
    def root_worktree(self) -> Path:
        """Alias for cwd for compatibility with SimulatedWorkstackEnv."""
        return self.cwd

    def setup_repo_structure(self, create_config: bool = True) -> Path:
        """Create standard erk repo directory structure (in-memory sentinel paths).

        Creates sentinel paths for:
            {erk_root}/repos/{cwd.name}/
            {erk_root}/repos/{cwd.name}/worktrees/
            {erk_root}/repos/{cwd.name}/config.toml (if create_config=True)

        Note: In pure mode, this only creates sentinel paths. No actual directories
        are created on the filesystem. Paths returned are just Path objects that
        will be validated through FakeGit's existing_paths mechanism.

        Args:
            create_config: Whether to create config.toml file content in memory

        Returns:
            Path to repo directory ({erk_root}/repos/{cwd.name})

        Example:
            >>> with erk_inmem_env(runner) as env:
            ...     repo_dir = env.setup_repo_structure()
            ...     # repo_dir = env.erk_root / "repos" / env.cwd.name
            ...     # Returns sentinel path (no filesystem I/O)
        """
        repo_dir = self.erk_root / "repos" / self.cwd.name

        # In pure mode, just create the paths - no mkdir() or special tracking needed
        # FakeGit's existing_paths will handle path validation
        # SentinelPath.mkdir() is a no-op anyway
        # Note: worktrees_dir path (repo_dir / "worktrees") is implicitly available
        # but doesn't need to be created or tracked in pure mode

        if create_config:
            config_toml = repo_dir / "config.toml"
            # Store empty config content in memory
            config_toml.write_text("", encoding="utf-8")

        return repo_dir

    def build_worktrees(
        self,
        root_branch: str = "main",
        linked_branches: list[str] | None = None,
        *,
        repo_dir: Path | None = None,
    ) -> dict[Path, list[WorktreeInfo]]:
        """Build standard worktree configuration for test scenarios.

        Creates a worktree list with:
        - Root worktree at self.cwd with specified branch
        - Linked worktrees in repo_dir/{branch} for each linked branch

        Args:
            root_branch: Branch name for root worktree (default: "main")
            linked_branches: List of linked worktree branches (default: [])
            repo_dir: Base directory for linked worktrees (default: auto-calculated)

        Returns:
            Dict mapping repo root to list of WorktreeInfo instances

        Example:
            >>> # Before (10-15 lines):
            >>> worktrees = {
            ...     env.cwd: [
            ...         WorktreeInfo(path=env.cwd, branch="main", is_root=True),
            ...         WorktreeInfo(
            ...             path=repo_dir / "worktrees" / "feat-1", branch="feat-1", is_root=False
            ...         ),
            ...         WorktreeInfo(
            ...             path=repo_dir / "worktrees" / "feat-2", branch="feat-2", is_root=False
            ...         ),
            ...     ]
            ... }
            >>> # After (1 line):
            >>> worktrees = env.build_worktrees("main", ["feat-1", "feat-2"])
        """
        if repo_dir is None:
            repo_dir = self.erk_root / "repos" / self.cwd.name

        worktrees = [WorktreeInfo(path=self.cwd, branch=root_branch, is_root=True)]

        for branch in linked_branches or []:
            worktrees.append(
                WorktreeInfo(
                    path=repo_dir / "worktrees" / branch,
                    branch=branch,
                    is_root=False,
                )
            )

        return {self.cwd: worktrees}

    def build_context(
        self,
        *,
        current_branch: str | None = None,
        trunk_branch: str = "main",
        use_graphite: bool = False,
        git: Git | None = None,
        graphite: FakeGraphite | None = None,
        github: FakeGitHub | None = None,
        shell: FakeShell | None = None,
        repo: RepoContext | None = None,
        existing_paths: set[Path] | None = None,
        file_contents: dict[Path, str] | None = None,
        dry_run: bool = False,
        **kwargs,
    ) -> ErkContext:
        """Build ErkContext with smart defaults for test scenarios.

        This helper eliminates boilerplate by providing default ops and config
        for tests that don't need custom setup. Custom values can be provided
        via keyword arguments.

        Args:
            current_branch: If provided, auto-configures FakeGit.current_branches
            trunk_branch: Default branch name (default: "main")
            use_graphite: Enable Graphite integration (default: False)
            git: Custom FakeGit instance (overrides smart defaults)
            graphite: Custom FakeGraphite instance
            github: Custom FakeGitHub instance
            shell: Custom FakeShell instance
            repo: Custom RepoContext (default: None)
            existing_paths: Set of sentinel paths to treat as existing (pure mode only)
            file_contents: Mapping of sentinel paths to file content (pure mode only)
            dry_run: Whether to wrap with DryRunGit
            **kwargs: Additional context_for_test() parameters

        Returns:
            ErkContext configured for testing

        Example:
            ```python
            with erk_inmem_env(runner) as env:
                # Simple case - use all defaults
                ctx = env.build_context()

                # Before (5 lines):
                git_ops = FakeGit(
                    git_common_dirs={env.cwd: env.git_dir},
                    default_branches={env.cwd: "main"},
                    current_branches={env.cwd: "feature-1"},
                )
                ctx = context_for_test(..., git=git_ops, ...)

                # After (1 line):
                ctx = env.build_context(current_branch="feature-1")

                # Enable Graphite with custom config
                ctx = env.build_context(use_graphite=True)

                # With existing paths for pure mode testing
                ctx = env.build_context(
                    existing_paths={Path("/test/repo/.erk")},
                    file_contents={Path("/test/repo/.PLAN.md"): "plan content"},
                )
            ```
        """
        # Determine repo to use (either provided or default)
        if repo is None:
            repo = self._repo

        # Smart FakeGit configuration
        if git is None:
            # Automatically include core sentinel paths in existing_paths
            # so that repo discovery and other path checks work correctly
            # Include repo.root and repo.erks_dir so os.walk() and path checks succeed
            core_paths = {
                self.cwd,
                self.git_dir,
                self.erk_root,
                repo.root,
                repo.repo_dir,
            }
            all_existing = core_paths | (existing_paths or set())

            git = FakeGit(
                git_common_dirs={self.cwd: self.git_dir},
                default_branches={self.cwd: trunk_branch},
                current_branches={self.cwd: current_branch} if current_branch else {},
                existing_paths=all_existing,
                file_contents=file_contents or {},
                remote_urls={(self.cwd, "origin"): "https://github.com/owner/repo.git"},
            )
        else:
            from erk_shared.git.dry_run import DryRunGit

            unwrapped_ops = git._wrapped if isinstance(git, DryRunGit) else git
            worktree_paths = {
                wt.path for worktrees in unwrapped_ops._worktrees.values() for wt in worktrees
            }
            # Determine which cwd to use (custom or default)
            effective_cwd = kwargs.get("cwd", self.cwd)

            core_paths = {
                self.cwd,
                effective_cwd,
                self.git_dir,
                self.erk_root,
                repo.root,
                repo.repo_dir,
            }
            all_existing = core_paths | worktree_paths | (existing_paths or set())

            # Mutate existing ops instance instead of recreating
            # This preserves mutation tracking for test assertions
            unwrapped_ops._existing_paths.update(all_existing)
            if file_contents:
                unwrapped_ops._file_contents.update(file_contents)

        # Wrap with DryRunGit for dry-run mode (only if not already wrapped)
        if dry_run:
            from erk_shared.git.dry_run import DryRunGit

            if not isinstance(git, DryRunGit):
                git = DryRunGit(git)

        # Smart integration defaults
        # When use_graphite=False, use GraphiteDisabled sentinel to match production
        # behavior. This ensures ErkContext.branch_manager returns GitBranchManager
        # and branch operations use FakeGit.delete_branch (tracked in deleted_branches).
        if graphite is None:
            if use_graphite:
                graphite = FakeGraphite()
            else:
                from erk_shared.gateway.graphite.disabled import (
                    GraphiteDisabled,
                    GraphiteDisabledReason,
                )

                graphite = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)

        if github is None:
            github = FakeGitHub()

        if shell is None:
            shell = FakeShell()

        # Create global config if not provided in kwargs
        if "global_config" in kwargs:
            # Use the provided global_config (might be None for init tests)
            global_config = kwargs.pop("global_config")
        else:
            # Create default global config
            global_config = GlobalConfig.test(
                self.erk_root,
                use_graphite=use_graphite,
                shell_setup_complete=False,
            )

        # Build and return context
        # Default cwd and script_writer to env values unless overridden in kwargs
        if "cwd" not in kwargs:
            kwargs["cwd"] = self.cwd
        if "script_writer" not in kwargs:
            kwargs["script_writer"] = self.script_writer

        # Filter out erk_root - it's already set in global_config above
        # Tests shouldn't override it via kwargs
        if "erk_root" in kwargs:
            kwargs.pop("erk_root")

        # Filter out trunk_branch - it's now a computed property based on git
        if "trunk_branch" in kwargs:
            kwargs.pop("trunk_branch")

        return context_for_test(
            git=git,
            graphite=graphite,
            github=github,
            shell=shell,
            global_config=global_config,
            repo=repo,
            dry_run=dry_run,
            **kwargs,
        )

    def create_linked_worktree(self, name: str, branch: str, *, chdir: bool = False) -> Path:
        """Create a linked worktree (sentinel path only, no filesystem).

        Args:
            name: Worktree directory name
            branch: Branch to checkout in the worktree
            chdir: Ignored in pure mode (no actual directory change)

        Returns:
            Sentinel path for the worktree
        """
        # Create sentinel path (no mkdir needed)
        linked_wt = self.erk_root / self.cwd.name / name
        # Track it
        self._linked_worktrees[branch] = linked_wt
        return linked_wt

    def build_ops_from_branches(
        self,
        branches: dict[str, BranchMetadata],
        *,
        current_branch: str | None = None,
        current_worktree: Path | None = None,
    ) -> tuple[FakeGit, FakeGraphite]:
        """Build both FakeGit and FakeGraphite from branch metadata.

        Automatically:
        - Maps branches to worktrees (root + any created linked worktrees)
        - Computes stacks dict from parent/child relationships
        - Configures git_common_dirs for all worktrees
        - Sets current branch in specified worktree

        Args:
            branches: Branch metadata with parent/child relationships
            current_branch: Which branch is checked out (defaults to root's branch)
            current_worktree: Where current_branch is (defaults to root_worktree)

        Returns:
            Tuple of (FakeGit, FakeGraphite) configured for testing
        """
        current_worktree = current_worktree or self.root_worktree

        # Find trunk branch (for root worktree)
        trunk_branch = None
        for name, meta in branches.items():
            if meta.is_trunk:
                trunk_branch = name
                break

        if trunk_branch is None:
            trunk_branch = "main"  # Fallback

        # Build worktrees list
        worktrees_list = [WorktreeInfo(path=self.root_worktree, branch=trunk_branch, is_root=True)]

        # Add linked worktrees created via create_linked_worktree()
        for branch, path in self._linked_worktrees.items():
            worktrees_list.append(WorktreeInfo(path=path, branch=branch, is_root=False))

        # Build current_branches mapping
        current_branches_map = {}
        for wt in worktrees_list:
            if wt.path == current_worktree:
                # This worktree has the current branch
                current_branches_map[wt.path] = current_branch if current_branch else wt.branch
            else:
                # Other worktrees stay on their own branch
                current_branches_map[wt.path] = wt.branch

        # Build git_common_dirs mapping (all point to root's .git)
        git_common_dirs_map = {wt.path: self.root_worktree / ".git" for wt in worktrees_list}

        # Build stacks from branches (auto-compute from parent/child)
        stacks = {}
        for branch_name in branches:
            if not branches[branch_name].is_trunk:
                stacks[branch_name] = self._build_stack_path(branches, branch_name)

        # Collect all worktree paths as existing
        existing_paths = {wt.path for wt in worktrees_list} | {self.cwd, self.git_dir}

        git = FakeGit(
            worktrees={self.root_worktree: worktrees_list},
            current_branches=current_branches_map,
            git_common_dirs=git_common_dirs_map,
            existing_paths=existing_paths,
        )

        graphite = FakeGraphite(
            branches=branches,
            stacks=stacks,
        )

        return git, graphite

    def _build_stack_path(
        self,
        branches: dict[str, BranchMetadata],
        leaf: str,
    ) -> list[str]:
        """Build stack path from trunk to leaf.

        Args:
            branches: All branch metadata
            leaf: Leaf branch name

        Returns:
            List of branch names from trunk to leaf (inclusive)
        """
        stack = []
        current = leaf

        while current is not None:
            stack.insert(0, current)
            parent = branches[current].parent
            current = parent

        return stack


@contextmanager
def erk_inmem_env(
    runner: CliRunner,
    *,
    branches: list[BranchMetadata] | None = None,
) -> Generator[ErkInMemEnv]:
    """Create pure in-memory test environment without filesystem I/O.

    This context manager provides a faster alternative to erk_isolated_fs_env()
    for tests that don't need actual filesystem operations. It uses sentinel paths
    and in-memory fakes exclusively.

    Sentinel paths throw errors if filesystem operations are attempted (.exists(),
    .resolve(), .mkdir(), etc.), enforcing that all checks go through fake operations
    for high test fidelity.

    Use this when:
    - Testing command logic that doesn't depend on real directories
    - Verifying script content without creating temp files
    - Running tests faster without filesystem overhead

    Use erk_isolated_fs_env() when:
    - Testing actual worktree creation/removal
    - Verifying git integration with real directories
    - Testing filesystem-dependent features

    Args:
        runner: Click CliRunner instance (not used, but kept for API consistency)
        branches: Optional branch metadata for initializing git state

    Yields:
        PureWorkstackEnv with sentinel paths and in-memory fakes

    Example:
        ```python
        def test_checkout_pure() -> None:
            runner = CliRunner()
            with erk_inmem_env(runner) as env:
                # No filesystem I/O, all operations in-memory
                git = FakeGit(git_common_dirs={env.cwd: env.git_dir})
                ctx = context_for_test(
                    cwd=env.cwd,
                    git=git,
                    script_writer=env.script_writer,
                )
                result = runner.invoke(cli, ["checkout", "feature", "--script"], obj=ctx)

                # Verify script content in-memory
                script_path = Path(result.stdout.strip())
                content = env.script_writer.get_script_content(script_path)
                assert content is not None
        ```
    """
    from tests.test_utils.paths import sentinel_path

    # Use sentinel paths that throw on filesystem operations
    cwd = sentinel_path("/test/repo")
    git_dir = sentinel_path("/test/repo/.git")
    erk_root = sentinel_path("/test/erks")

    # Create in-memory script writer
    script_writer = FakeScriptWriter()

    # No isolated_filesystem(), no os.chdir(), no mkdir()
    try:
        yield ErkInMemEnv(
            cwd=cwd,
            git_dir=git_dir,
            erk_root=erk_root,
            script_writer=script_writer,
        )
    finally:
        # Clear SentinelPath file storage for test isolation
        from tests.test_utils.paths import SentinelPath

        SentinelPath.clear_file_storage()
