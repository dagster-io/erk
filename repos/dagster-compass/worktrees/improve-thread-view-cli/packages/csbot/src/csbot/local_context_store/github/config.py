from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import aiohttp
import jwt
import pygit2
import requests
import structlog
from github import Auth, Github

from csbot.utils.check_async_context import ensure_not_in_async_context

logger = structlog.get_logger(__name__)


class GithubAuthSource(ABC):
    @abstractmethod
    async def get_callbacks(self) -> pygit2.RemoteCallbacks:
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def get_callbacks_sync(self) -> pygit2.RemoteCallbacks:
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def get_token(self) -> str:
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def get_github_client(self) -> Github:
        raise NotImplementedError("Subclasses must implement this method")


@dataclass(frozen=True)
class PATGithubAuthSource(GithubAuthSource):
    """
    Immutable configuration for GitHub API operations.

    This data class encapsulates GitHub-specific configuration parameters
    needed for API operations, ensuring type safety and immutability.
    """

    token: str
    """GitHub API token for authentication"""

    _github_client: Github | None = None

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if not self.token:
            raise ValueError("GitHub token cannot be empty")

    async def get_callbacks(self) -> pygit2.RemoteCallbacks:
        return pygit2.RemoteCallbacks(credentials=pygit2.UserPass(self.token, ""))

    def get_callbacks_sync(self) -> pygit2.RemoteCallbacks:
        return pygit2.RemoteCallbacks(credentials=pygit2.UserPass(self.token, ""))

    def get_token(self) -> str:
        return self.token

    def get_github_client(self) -> Github:
        if self._github_client is None:
            object.__setattr__(self, "_github_client", Github(auth=Auth.Token(self.token)))
        assert self._github_client is not None  # Help type checker
        return self._github_client

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PATGithubAuthSource):
            return False
        return self.token == other.token


@dataclass
class GitHubAppAuthSource(GithubAuthSource):
    """
    Immutable configuration for GitHub API operations.

    This data class encapsulates GitHub-specific configuration parameters
    needed for API operations, ensuring type safety and immutability.
    """

    app_id: int
    installation_id: int
    private_key_path: str

    _cached_token: str | None = None
    _token_expires_at: int | None = None
    _github_client: Github | None = None

    def _generate_github_app_jwt(self) -> str:
        """Generate a JWT token for GitHub App authentication."""
        if not self.private_key_path or not self.app_id:
            raise ValueError("GitHub App credentials are incomplete")

        # Read the private key file
        try:
            with open(self.private_key_path) as key_file:
                private_key = key_file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Private key file not found: {self.private_key_path}")
        except Exception as e:
            raise ValueError(f"Failed to read private key file: {e}")

        # Generate JWT payload
        now = int(time.time())
        payload = {
            "iat": now - 60,  # Issued at time (1 minute in the past to account for clock drift)
            "exp": now + 600,  # Expires in 10 minutes (max allowed by GitHub)
            "iss": self.app_id,  # GitHub App ID
        }

        # Generate JWT token
        try:
            token = jwt.encode(payload, private_key, algorithm="RS256")
            return token
        except Exception as e:
            raise ValueError(f"Failed to generate JWT token: {e}")

    def get_installation_access_token_sync(self, jwt_token: str) -> str:
        """Exchange JWT token for an installation access token."""
        if not self.installation_id:
            raise ValueError("Installation ID is required for GitHub App authentication")

        url = f"https://api.github.com/app/installations/{self.installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        request = requests.post(url, headers=headers)
        request.raise_for_status()
        data = request.json()
        access_token = data.get("token")
        if not access_token:
            raise ValueError("No access token returned from GitHub API")
        return access_token

    async def _get_installation_access_token(self, jwt_token: str) -> str:
        """Exchange JWT token for an installation access token."""
        if not self.installation_id:
            raise ValueError("Installation ID is required for GitHub App authentication")

        url = f"https://api.github.com/app/installations/{self.installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()

                    access_token = data.get("token")
                    if not access_token:
                        raise ValueError("No access token returned from GitHub API")

                    return access_token
        except aiohttp.ClientError as e:
            raise ValueError(f"Failed to get installation access token: {e}")
        except KeyError:
            raise ValueError("Invalid response format from GitHub API")

    def get_auth_token_sync(self) -> str:
        now = int(time.time())
        if self._cached_token and self._token_expires_at and now < self._token_expires_at - 300:
            return self._cached_token
        logger.info("No valid GitHub App installation access token found, generating new one")
        jwt_token = self._generate_github_app_jwt()
        access_token = self.get_installation_access_token_sync(jwt_token)
        self._cached_token = access_token
        self._token_expires_at = now + 3300  # 50 minutes from now
        return access_token

    async def get_auth_token(self) -> str:
        """Get the authentication token, handling both PAT and GitHub App."""

        # Check if we have a cached token that's still valid
        now = int(time.time())
        if (
            self._cached_token and self._token_expires_at and now < self._token_expires_at - 300
        ):  # Refresh 5 minutes before expiry
            return self._cached_token

        logger.info("No valid GitHub App installation access token found, generating new one")

        # Generate JWT token and exchange for installation access token
        jwt_token = self._generate_github_app_jwt()
        access_token = await self._get_installation_access_token(jwt_token)

        # Cache the token for 1 hour (GitHub App installation tokens are valid for 1 hour)
        self._cached_token = access_token
        self._token_expires_at = now + 3300  # 50 minutes from now

        return access_token

    async def get_callbacks(self) -> pygit2.RemoteCallbacks:
        token = await self.get_auth_token()
        return pygit2.RemoteCallbacks(credentials=pygit2.UserPass("x-access-token", token))

    def get_callbacks_sync(self) -> pygit2.RemoteCallbacks:
        ensure_not_in_async_context()
        token = self.get_auth_token_sync()
        return pygit2.RemoteCallbacks(credentials=pygit2.UserPass("x-access-token", token))

    def get_token(self) -> str:
        return self.get_auth_token_sync()

    def get_github_client(self) -> Github:
        if self._github_client is None:
            with open(self.private_key_path) as key_file:
                private_key = key_file.read()
            client = Github(
                auth=Auth.AppInstallationAuth(
                    app_auth=Auth.AppAuth(self.app_id, private_key=private_key),
                    installation_id=self.installation_id,
                )
            )
            object.__setattr__(self, "_github_client", client)
        assert self._github_client is not None  # Help type checker
        return self._github_client

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GitHubAppAuthSource):
            return False
        return (
            self.app_id == other.app_id
            and self.installation_id == other.installation_id
            and self.private_key_path == other.private_key_path
        )


@dataclass(frozen=True)
class GithubConfig:
    """
    Immutable configuration for GitHub API operations.

    This data class encapsulates GitHub-specific configuration parameters
    needed for API operations, ensuring type safety and immutability.
    """

    auth_source: GithubAuthSource

    repo_name: str
    """Repository name in format 'owner/repo'"""

    @staticmethod
    def pat(token: str, repo_name: str) -> GithubConfig:
        return GithubConfig(auth_source=PATGithubAuthSource(token=token), repo_name=repo_name)

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if not self.auth_source:
            raise ValueError("GitHub token producer cannot be empty")

        if not self.repo_name:
            raise ValueError("Repository name cannot be empty")

        if "/" not in self.repo_name or self.repo_name.count("/") != 1:
            raise ValueError("Repository name must be in format 'owner/repo'")

        # Validate repo name doesn't have invalid characters
        parts = self.repo_name.split("/")
        owner, repo = parts[0], parts[1]

        if not owner or not repo:
            raise ValueError("Both owner and repository name must be non-empty")

    @property
    def owner(self) -> str:
        """Get the repository owner."""
        return self.repo_name.split("/")[0]

    @property
    def repository(self) -> str:
        """Get the repository name (without owner)."""
        return self.repo_name.split("/")[1]

    def base_repo_url(self) -> str:
        """Get the base repository URL."""
        return f"https://github.com/{self.repo_name}.git"
