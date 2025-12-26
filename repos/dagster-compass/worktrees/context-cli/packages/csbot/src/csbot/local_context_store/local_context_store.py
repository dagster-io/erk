"""Local context store pool implementation.

This module provides the LocalContextStorePool for managing local representations
of context stores with persistent caching for reads and isolated temporary
instances for writes, relying on filesystem caching for performance optimization.
"""

import asyncio
import fcntl
import logging
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from csbot.contextengine.contextstore_protocol import ContextStore
from csbot.contextengine.loader import load_context_store
from csbot.utils.check_async_context import ensure_not_in_async_context
from csbot.utils.time import DatetimeNow, system_datetime_now

from .git.file_tree import create_git_commit_file_tree
from .git.repository_operations import (
    SHALLOW_CLONE_DEPTH,
    clean_and_update_repository,
    clone_repository,
)
from .isolated_copy import IsolatedContextStoreCopy

if TYPE_CHECKING:
    from collections.abc import Generator

    from csbot.local_context_store.git.file_tree import FileTree
    from csbot.local_context_store.github.config import GithubConfig

logger = logging.getLogger(__name__)


def _get_context_store_refresh_minutes() -> float:
    """Get context store refresh interval in minutes from env var."""
    env_value = os.getenv("CONTEXT_STORE_REFRESH_MINUTES", "1")
    try:
        minutes = float(env_value)
        if minutes <= 0:
            logger.warning(
                f"Invalid CONTEXT_STORE_REFRESH_MINUTES value '{env_value}' (must be > 0), using default 1"
            )
            return 1.0
        return minutes
    except ValueError:
        logger.warning(
            f"Invalid CONTEXT_STORE_REFRESH_MINUTES value '{env_value}' (not a number), using default 1"
        )
        return 1.0


CONTEXT_STORE_REFRESH_MINUTES = _get_context_store_refresh_minutes()


@dataclass(frozen=True)
class RepoConfig:
    github_config: "GithubConfig"
    base_path: Path

    @property
    def repo_path(self) -> Path:
        return self.base_path / self.github_config.repository

    @property
    def lock_file_path(self) -> Path:
        return self.base_path / f"{self.github_config.repository}.lock"


class SharedRepo:
    """Manages repository refresh timing and locking.

    Encapsulates the logic for determining when to refresh a repository
    and handles fcntl-based locking for concurrent access coordination.
    """

    def __init__(
        self,
        repo_config: RepoConfig,
        datetime_now: DatetimeNow = system_datetime_now,
    ):
        """Initialize the RefreshManager.

        Args:
            repo_config: Repository configuration containing GitHub config and base path
            datetime_now: Callable for getting current datetime
        """
        self.repo_config = repo_config
        self.datetime_now = datetime_now
        # Force refresh on first access
        self.last_refresh_time = datetime.min

    @property
    def repo_path(self) -> Path:
        """Get the full path to the local repository directory."""
        return self.repo_config.repo_path

    @property
    def lock_file(self) -> Path:
        """Get the path to the repository lock file."""
        return self.repo_config.lock_file_path

    def refresh_if_needed(self):
        """Context manager that refreshes repository if needed, with locking.

        Yields after ensuring repository is up to date.
        """
        with self._fcntl_lock():
            if self._should_refresh():
                ensure_github_repository(self.repo_config)
                self.last_refresh_time = self.datetime_now()
            elif not self.repo_config.repo_path.exists():
                # Still ensure repo exists locally (lightweight check)
                ensure_github_repository(self.repo_config)
                self.last_refresh_time = self.datetime_now()

    def force_refresh(self) -> None:
        """Force a refresh with locking."""
        with self._fcntl_lock():
            ensure_github_repository(self.repo_config)
            clean_and_update_repository(
                self.repo_config.repo_path, github_config=self.repo_config.github_config
            )
            self.last_refresh_time = self.datetime_now()

    def _should_refresh(self) -> bool:
        """Check if repository should be refreshed based on time limit (CONTEXT_STORE_REFRESH_MINUTES env var)."""
        time_since_refresh = self.datetime_now() - self.last_refresh_time
        return time_since_refresh > timedelta(minutes=CONTEXT_STORE_REFRESH_MINUTES)

    @contextmanager
    def _fcntl_lock(self):
        """Helper for fcntl-based file locking."""
        self.repo_config.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
        # Use append mode to avoid truncating lock file, preventing race condition
        # where process crashes between open() and flock() could leave corrupted lock file
        with open(self.repo_config.lock_file_path, "a") as lock_fd:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)


@dataclass
class LocalContextStore:
    """Local context store pool for managing context store instances.

    Manages local representations of context stores on a bot server node with
    persistent caching for reads and isolated temporary instances for writes,
    relying on filesystem caching for performance optimization.
    """

    shared_repo: SharedRepo

    @property
    def github_config(self) -> "GithubConfig":
        """Get the GitHub configuration."""
        return self.shared_repo.repo_config.github_config

    @property
    def base_path(self) -> Path:
        """Get the base path for repositories."""
        return self.shared_repo.repo_config.base_path

    @contextmanager
    def latest_file_tree(self) -> "Generator[FileTree]":
        """Get file tree for latest commit from cached context store.

        - Uses persistent cached context store
        - Locks to update the repository but emits the FileTree which can be used lock-free

        Yields:
            FileTree: File tree interface for reading files from latest commit
        """
        self.shared_repo.refresh_if_needed()

        with create_git_commit_file_tree(
            self.shared_repo.repo_config.repo_path,
            self.shared_repo.repo_config.github_config.repo_name,
        ) as tree:
            yield tree

    def update_to_latest(self) -> None:
        """Update context store to latest state with locking.

        - Uses persistent cached context store
        - fcntl locking for write operations
        - Coordinates concurrent access
        """
        self.shared_repo.force_refresh()

    @contextmanager
    def isolated_copy(self) -> "Generator[IsolatedContextStoreCopy]":
        """Get isolated context store for PR creation.

        - Creates fresh clone in temporary directory
        - No locking needed (isolated)
        - Automatically cleaned up when context exits

        Yields:
            IsolatedContextStore: Context store handle for PR workflow operations
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_repo_path = Path(temp_dir) / "repo"
            setup_fresh_github_repository(
                self.shared_repo.repo_config.github_config, temp_repo_path
            )
            yield IsolatedContextStoreCopy(
                temp_repo_path, self.shared_repo.repo_config.github_config
            )


def create_local_context_store(
    github_config: "GithubConfig", base_path: Path | None = None
) -> LocalContextStore:
    """Create a local context store pool instance.

    Args:
        github_config: GitHub configuration
        base_path: Base path for context stores (defaults to ~/.compass/repos)
    """
    return LocalContextStore(
        shared_repo=SharedRepo(
            repo_config=RepoConfig(
                github_config=github_config,
                base_path=base_path or (Path.home() / ".compass" / "repos"),
            )
        )
    )


def ensure_github_repository(repo_config: RepoConfig) -> Path:
    """Ensure repository exists and is up to date.

    Args:
        repo_config: Repository configuration containing GitHub config and base path

    Returns:
        Path to the ready repository
    """
    repo_path = repo_config.repo_path
    setup_fresh_github_repository(repo_config.github_config, repo_path)
    return repo_path


def setup_fresh_github_repository(github_config: "GithubConfig", repo_path: Path) -> None:
    """Setup a fresh repository clone without locking.

    This is used for write operations that need isolated fresh clones.
    Since these are in temporary directories, no locking is needed.

    Args:
        github_config: GitHub configuration
        repo_path: Path to setup the repository at
    """
    ensure_not_in_async_context()

    repo_path.parent.mkdir(parents=True, exist_ok=True)

    if not repo_path.exists():
        clone_repository(repo_path, git_config=github_config, depth=SHALLOW_CLONE_DEPTH)
    else:
        clean_and_update_repository(local_repo_path=repo_path, github_config=github_config)


class LocalBackedGithubContextStoreManager:
    """Manages context store operations backed by local git with GitHub integration.

    Provides both read and write access to a context store backed by a local git
    repository that syncs with GitHub.
    """

    def __init__(
        self,
        local_context_store: LocalContextStore,
        github_monitor: "SlackbotGithubMonitor",
    ):
        self._local_context_store = local_context_store
        self._github_monitor = github_monitor

    async def get_context_store(self) -> ContextStore:
        """Get the current ContextStore state.

        Loads the ContextStore from the latest file tree in a thread to avoid
        blocking the async event loop.

        Returns:
            ContextStore: The current context store state
        """
        return await asyncio.to_thread(self._load_context_store_sync)

    def _load_context_store_sync(self) -> ContextStore:
        """Synchronously load ContextStore from the file tree.

        Returns:
            ContextStore: The loaded context store
        """
        with self._local_context_store.latest_file_tree() as tree:
            return load_context_store(tree)

    async def mutate(
        self, title: str, body: str, commit: bool, before: ContextStore, after: ContextStore
    ) -> str:
        """Mutate the context store by creating a GitHub PR.

        Returns:
            PR URL or commit URL
        """
        from csbot.contextengine.serializer import serialize_context_store
        from csbot.local_context_store.github.context import with_pull_request_context

        def mutate_sync():
            with with_pull_request_context(
                self._local_context_store,
                title,
                body,
                automerge=commit,
            ) as pr:
                # TODO (maybe) verify that `before` is still == to the filesystem context store
                serialize_context_store(after, pr.repo_path)

            if not pr.pr_url:
                raise RuntimeError("PR URL not set after creating pull request")
            return pr.pr_url

        pr_url = await asyncio.to_thread(mutate_sync)

        await asyncio.sleep(2)
        await self._github_monitor.tick()

        return pr_url


if TYPE_CHECKING:
    from csbot.contextengine.protocol import ContextStoreManager
    from csbot.slackbot.slackbot_github_monitor import SlackbotGithubMonitor

    _manager: ContextStoreManager = LocalBackedGithubContextStoreManager(...)  # type: ignore[abstract]
