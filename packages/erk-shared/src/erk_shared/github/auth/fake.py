"""Fake GitHub authentication operations for testing."""

from erk_shared.github.auth.abc import GitHubAuthGateway


class FakeGitHubAuthGateway(GitHubAuthGateway):
    """In-memory fake implementation of GitHub authentication operations.

    This class has NO public setup methods. All state is provided via constructor
    using keyword arguments with sensible defaults.
    """

    def __init__(
        self,
        *,
        authenticated: bool = True,
        username: str | None = "test-user",
        hostname: str | None = "github.com",
    ) -> None:
        """Create FakeGitHubAuthGateway with pre-configured state.

        Args:
            authenticated: Whether gh CLI is authenticated (default True for test convenience)
            username: Username returned by check_auth_status() and get_current_username()
            hostname: Hostname returned by check_auth_status()
        """
        self._authenticated = authenticated
        self._username = username
        self._hostname = hostname
        self._check_auth_status_calls: list[None] = []
        self._get_current_username_calls: list[None] = []

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Return pre-configured authentication status.

        Tracks calls for verification.

        Returns:
            Tuple of (is_authenticated, username, hostname)
        """
        self._check_auth_status_calls.append(None)

        if not self._authenticated:
            return (False, None, None)

        return (True, self._username, self._hostname)

    def get_current_username(self) -> str | None:
        """Return pre-configured username.

        Tracks calls for verification.

        Returns:
            Pre-configured username if authenticated, None otherwise
        """
        self._get_current_username_calls.append(None)

        if not self._authenticated:
            return None

        return self._username

    @property
    def check_auth_status_calls(self) -> list[None]:
        """Get the list of check_auth_status() calls that were made.

        Returns list of None values (one per call, no arguments tracked).
        """
        return self._check_auth_status_calls

    @property
    def get_current_username_calls(self) -> list[None]:
        """Get the list of get_current_username() calls that were made.

        Returns list of None values (one per call, no arguments tracked).
        """
        return self._get_current_username_calls
