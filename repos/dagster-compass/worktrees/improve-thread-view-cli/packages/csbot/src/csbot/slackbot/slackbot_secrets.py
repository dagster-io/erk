import abc
import re
from functools import partial
from pathlib import Path
from typing import Any

import backoff
import httpx
import structlog

from csbot.utils.secrets import decrypt_string, encrypt_string

logger = structlog.getLogger(__name__)


def backoff_hdlr(details: Any):
    logger.warn("Backing off {wait:0.1f} seconds after {tries} tries".format(**details))


class RenderRateLimitedException(BaseException):
    pass


class SecretStore(abc.ABC):
    """Abstract base class for secret stores."""

    @abc.abstractmethod
    async def get_secret_contents(self, org_id: int, key: str) -> str:
        pass

    @abc.abstractmethod
    async def store_secret(self, org_id: int, key: str, contents: str) -> Path:
        pass


class NoopSecretStore(SecretStore):
    async def get_secret_contents(self, org_id: int, key: str) -> str:
        raise NotImplementedError("get_secret_contents not implemented")

    async def store_secret(self, org_id: int, key: str, contents: str) -> Path:
        raise Exception()


class LocalFileSecretStore(SecretStore):
    async def get_secret_contents(self, org_id: int, key: str) -> str:
        if not Path(f"/tmp/secrets/org_{org_id}_{key}").exists():
            raise FileNotFoundError(f"Secret {key} not found for organization {org_id}")
        return Path(f"/tmp/secrets/org_{org_id}_{key}").read_text()

    async def store_secret(self, org_id: int, key: str, contents: str) -> Path:
        Path("/tmp/secrets").mkdir(parents=True, exist_ok=True)
        path = Path(f"/tmp/secrets/org_{org_id}_{key}")
        path.write_text(contents)
        return path


class RenderSecretStore(SecretStore):
    def __init__(self, service_id: str, api_key: str):
        self.service_id = service_id
        self.api_key = api_key
        self._local_secret_cache: dict[str, str] = {}

    def _get_namespaced_file_name(self, org_id: int, key: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "_", f"org_{org_id}__{key}")

    async def get_secret_contents(self, org_id: int, key: str) -> str:
        return await self._get_secret_contents(org_id, key)

    @backoff.on_exception(
        partial(backoff.expo, 2, 7, max_value=30),
        exception=RenderRateLimitedException,
        max_time=60,
        on_backoff=backoff_hdlr,
    )
    async def _get_secret_contents(self, org_id: int, key: str) -> str:
        namespaced_file_name = self._get_namespaced_file_name(org_id, key)

        if namespaced_file_name in self._local_secret_cache:
            return self._local_secret_cache[namespaced_file_name]

        else:
            url = f"https://api.render.com/v1/services/{self.service_id}/secret-files/{namespaced_file_name}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=30)
                if response.status_code == 429:
                    raise RenderRateLimitedException
                response.raise_for_status()
                return decrypt_string(response.json()["content"])

    @backoff.on_exception(
        partial(backoff.expo, 2, 7, max_value=30),
        exception=RenderRateLimitedException,
        max_time=60,
        on_backoff=backoff_hdlr,
    )
    async def store_secret(self, org_id: int, key: str, contents: str) -> Path:
        """Upload a file to Render service for a specific organization and store locally so the
        service doesn't need to be restarted.

        Args:
            org_id: Organization identifier for namespacing
            key: The name to give the secret in Render
            contents: The file contents as a string (will be encrypted)

        Returns:
            The namespaced filename that was uploaded

        Raises:
            ValueError: If configuration is missing or encryption fails
            RuntimeError: If upload to Render fails
        """

        # Encrypt the file contents before upload
        try:
            encrypted_contents = encrypt_string(contents)
        except ValueError as e:
            raise ValueError("Failed to encrypt file contents") from e

        # Create namespaced filename with org_id prefix
        namespaced_file_name = self._get_namespaced_file_name(org_id, key)

        self._local_secret_cache[namespaced_file_name] = contents

        # Upload to Render
        url = f"https://api.render.com/v1/services/{self.service_id}/secret-files/{namespaced_file_name}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {"content": encrypted_contents}

        async with httpx.AsyncClient() as client:
            response = await client.put(url, json=data, headers=headers, timeout=30)
            if response.status_code == 429:
                raise RenderRateLimitedException
            response.raise_for_status()

        return Path("/etc/secrets") / namespaced_file_name


def is_on_tmpfs(path: Path) -> bool:
    # Resolve to an absolute path
    abs_path = str(path.absolute())

    # Read mounts
    with open("/proc/mounts") as f:
        mounts = [line.split() for line in f]

    # Find the longest mount-point prefix for our path
    best = (0, None)  # (length, fs_type)
    for device, mnt_point, fs_type, *_ in mounts:
        if abs_path.startswith(mnt_point.rstrip("/")) and len(mnt_point) > best[0]:
            best = (len(mnt_point), fs_type)

    # If the best match is tmpfs, we’re on tmpfs
    return best[1] == "tmpfs"
