"""Mutable KV metadata stored in the entity body.

Each operation does a full read-modify-write cycle to GitHub.
Use update() to batch multiple field changes in one round-trip.
"""

from pathlib import Path
from typing import Any

from erk_shared.entity_store.types import EntityKind
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    create_metadata_block,
    find_metadata_block,
    render_metadata_block,
    replace_metadata_block_in_body,
)
from erk_shared.gateway.github.metadata.types import MetadataBlockSchema
from erk_shared.gateway.github.types import BodyText, PRNotFound


class EntityState:
    """Mutable KV metadata stored in the entity body.

    Each operation does a full read-modify-write cycle to GitHub.
    Use update() to batch multiple field changes in one round-trip.
    """

    def __init__(
        self,
        *,
        number: int,
        kind: EntityKind,
        github: GitHub,
        github_issues: GitHubIssues,
        repo_root: Path,
    ) -> None:
        self._number = number
        self._kind = kind
        self._github = github
        self._github_issues = github_issues
        self._repo_root = repo_root

    def _fetch_body(self) -> str:
        """Fetch the current body text from GitHub."""
        if self._kind is EntityKind.ISSUE:
            result = self._github_issues.get_issue(self._repo_root, self._number)
            if isinstance(result, IssueNotFound):
                msg = f"Issue #{self._number} not found"
                raise RuntimeError(msg)
            return result.body
        else:
            result = self._github.get_pr(self._repo_root, self._number)
            if isinstance(result, PRNotFound):
                msg = f"PR #{self._number} not found"
                raise RuntimeError(msg)
            return result.body

    def _push_body(self, body: str) -> None:
        """Write the updated body text to GitHub."""
        if self._kind is EntityKind.ISSUE:
            self._github_issues.update_issue_body(
                self._repo_root, self._number, BodyText(content=body)
            )
        else:
            self._github.update_pr_body(self._repo_root, self._number, body)

    def get(self, key: str) -> dict[str, Any] | None:
        """Get a metadata block by key. Returns None if not found."""
        body = self._fetch_body()
        block = find_metadata_block(body, key)
        if block is None:
            return None
        return block.data

    def get_field(self, key: str, field: str) -> Any | None:
        """Get a single field from a metadata block."""
        data = self.get(key)
        if data is None:
            return None
        return data.get(field)

    def has(self, key: str) -> bool:
        """Check if a metadata block exists in the body."""
        body = self._fetch_body()
        return find_metadata_block(body, key) is not None

    def set(
        self,
        key: str,
        data: dict[str, Any],
        *,
        schema: MetadataBlockSchema | None,
    ) -> None:
        """Set an entire metadata block. Creates or replaces."""
        block = create_metadata_block(key, data, schema=schema)
        rendered = render_metadata_block(block)
        body = self._fetch_body()

        # Try to replace existing block, otherwise append
        existing = find_metadata_block(body, key)
        if existing is not None:
            new_body = replace_metadata_block_in_body(body, key, rendered)
        else:
            new_body = body.rstrip() + "\n\n" + rendered if body.strip() else rendered

        self._push_body(new_body)

    def set_field(self, key: str, field: str, value: Any) -> None:
        """Update a single field in a metadata block (read-modify-write)."""
        self.update(key, {field: value})

    def update(self, key: str, fields: dict[str, Any]) -> None:
        """Update multiple fields in one round-trip (read-modify-write)."""
        body = self._fetch_body()
        existing = find_metadata_block(body, key)
        if existing is None:
            msg = f"Metadata block '{key}' not found in body"
            raise ValueError(msg)

        updated_data = dict(existing.data)
        updated_data.update(fields)

        block = create_metadata_block(key, updated_data, schema=None)
        rendered = render_metadata_block(block)
        new_body = replace_metadata_block_in_body(body, key, rendered)
        self._push_body(new_body)
