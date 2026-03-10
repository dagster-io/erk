"""Fake implementation of git configuration operations for testing."""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.git.config_ops.abc import GitConfigOps


@dataclass(frozen=True)
class ConfigSetRecord:
    """Record of a config_set operation."""

    cwd: Path
    key: str
    value: str
    scope: str


class FakeGitConfigOps(GitConfigOps):
    """In-memory fake implementation for testing.

    Constructor Injection: pre-configured state passed via constructor.
    Mutation Tracking: tracks config_set calls for test assertions.
    """

    def __init__(
        self,
        *,
        user_names: dict[Path, str | None] | None = None,
        config_values: dict[tuple[Path, str], str] | None = None,
        git_user_name: str | None = None,
    ) -> None:
        """Create FakeGitConfigOps with pre-configured state.

        Args:
            user_names: Mapping of cwd -> user.name value
            config_values: Mapping of (cwd, key) -> config value
            git_user_name: Default git user.name value to return
        """
        self._user_names = user_names if user_names is not None else {}
        self._config_values = config_values if config_values is not None else {}
        self._git_user_name = git_user_name

        # Mutation tracking
        self._config_sets: list[ConfigSetRecord] = []

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str) -> None:
        """Set a git configuration value."""
        self._config_sets.append(ConfigSetRecord(cwd=cwd, key=key, value=value, scope=scope))
        self._config_values[(cwd, key)] = value
        # Special handling for user.name
        if key == "user.name":
            self._user_names[cwd] = value

    # ============================================================================
    # Query Operations
    # ============================================================================

    def get_git_user_name(self, cwd: Path) -> str | None:
        """Get the configured git user.name."""
        if cwd in self._user_names:
            return self._user_names[cwd]
        # Walk up to find a configured value
        for path in list(cwd.parents):
            if path in self._user_names:
                return self._user_names[path]
        # Fall back to default
        return self._git_user_name

    # ============================================================================
    # Mutation Tracking Properties
    # ============================================================================

    @property
    def config_sets(self) -> list[ConfigSetRecord]:
        """Read-only access to config_set operations for test assertions."""
        return list(self._config_sets)

    # ============================================================================
    # Link Mutation Tracking (for integration with FakeGit)
    # ============================================================================

    def link_mutation_tracking(
        self,
        *,
        config_sets: list[ConfigSetRecord],
    ) -> None:
        """Link this fake's mutation tracking to FakeGit's tracking lists.

        Args:
            config_sets: FakeGit's _config_sets list
        """
        self._config_sets = config_sets

    def link_state(
        self,
        *,
        user_names: dict[Path, str | None],
        config_values: dict[tuple[Path, str], str],
        git_user_name: str | None,
    ) -> None:
        """Link this fake's state to FakeGit's state.

        Args:
            user_names: FakeGit's user names mapping
            config_values: FakeGit's config values mapping
            git_user_name: Default git user.name value
        """
        self._user_names = user_names
        self._config_values = config_values
        self._git_user_name = git_user_name
