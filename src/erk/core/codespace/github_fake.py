"""In-memory fake implementation of CodespaceGitHub for testing."""

from datetime import datetime

from erk.core.codespace.github_abc import CodespaceGitHub
from erk.core.codespace.types import GitHubCodespaceInfo


class FakeCodespaceGitHub(CodespaceGitHub):
    """Test implementation that simulates GitHub codespace operations.

    Use constructor injection to set up codespaces and control behavior.

    Example:
        >>> github = FakeCodespaceGitHub(
        ...     codespaces=[
        ...         GitHubCodespaceInfo(
        ...             name="schrockn-abc123",
        ...             state="Available",
        ...             repository="schrockn/erk",
        ...             branch="main",
        ...             machine_type="standardLinux32gb",
        ...             created_at=datetime.now(),
        ...         )
        ...     ]
        ... )
    """

    def __init__(
        self,
        codespaces: list[GitHubCodespaceInfo] | None = None,
        create_should_fail: bool = False,
        ssh_exit_code: int = 0,
    ) -> None:
        """Initialize fake GitHub codespace operations.

        Args:
            codespaces: Initial codespaces to return from list
            create_should_fail: If True, create_codespace raises RuntimeError
            ssh_exit_code: Exit code to return from ssh_interactive
        """
        self._codespaces = {cs.name: cs for cs in (codespaces or [])}
        self._create_should_fail = create_should_fail
        self._ssh_exit_code = ssh_exit_code
        self._ssh_connections: list[str] = []
        self._created_codespaces: list[GitHubCodespaceInfo] = []

    def list_codespaces(self) -> list[GitHubCodespaceInfo]:
        """List all simulated codespaces."""
        return list(self._codespaces.values())

    def get_codespace(self, gh_name: str) -> GitHubCodespaceInfo | None:
        """Get codespace by name."""
        return self._codespaces.get(gh_name)

    def create_codespace(
        self,
        repo: str,
        branch: str,
        machine_type: str = "standardLinux32gb",
    ) -> GitHubCodespaceInfo:
        """Simulate codespace creation."""
        if self._create_should_fail:
            raise RuntimeError("Simulated codespace creation failure")

        # Generate a fake name
        import hashlib

        hash_input = f"{repo}-{branch}-{datetime.now().isoformat()}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        name = f"fake-codespace-{short_hash}"

        info = GitHubCodespaceInfo(
            name=name,
            state="Available",  # Start as available in tests
            repository=repo,
            branch=branch,
            machine_type=machine_type,
            created_at=datetime.now(),
        )

        self._codespaces[name] = info
        self._created_codespaces.append(info)
        return info

    def wait_for_available(
        self,
        gh_name: str,
        timeout_seconds: int = 300,
    ) -> bool:
        """Simulate waiting for codespace (always succeeds if codespace exists)."""
        return gh_name in self._codespaces

    def ssh_interactive(self, gh_name: str) -> int:
        """Simulate interactive SSH session."""
        self._ssh_connections.append(gh_name)
        return self._ssh_exit_code

    def ssh_replace(self, gh_name: str) -> None:
        """Track SSH call (doesn't actually replace process in tests)."""
        self._ssh_connections.append(gh_name)

    # Read-only properties for test assertions

    @property
    def ssh_connections(self) -> list[str]:
        """Read-only access to SSH connection history for test assertions."""
        return self._ssh_connections.copy()

    @property
    def created_codespaces(self) -> list[GitHubCodespaceInfo]:
        """Read-only access to created codespaces for test assertions."""
        return self._created_codespaces.copy()

    # Test helpers for manipulating state

    def add_codespace(self, codespace: GitHubCodespaceInfo) -> None:
        """Add a codespace to the simulated GitHub state."""
        self._codespaces[codespace.name] = codespace

    def remove_codespace(self, gh_name: str) -> None:
        """Remove a codespace from the simulated GitHub state."""
        if gh_name in self._codespaces:
            del self._codespaces[gh_name]

    def set_codespace_state(self, gh_name: str, state: str) -> None:
        """Update a codespace's state."""
        if gh_name in self._codespaces:
            old = self._codespaces[gh_name]
            self._codespaces[gh_name] = GitHubCodespaceInfo(
                name=old.name,
                state=state,
                repository=old.repository,
                branch=old.branch,
                machine_type=old.machine_type,
                created_at=old.created_at,
            )
