"""Mutable KV metadata stored in the entity body.

Each operation does a full read-modify-write cycle to GitHub.
Use entity_state_update() to batch multiple field changes in one round-trip.
"""

from dataclasses import dataclass
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


@dataclass(frozen=True)
class EntityState:
    """KV metadata stored in the entity body.

    Read operations are methods on the dataclass.
    Write operations are standalone functions below.
    """

    number: int
    kind: EntityKind
    github: GitHub
    github_issues: GitHubIssues
    repo_root: Path

    def _fetch_body(self) -> str:
        """Fetch the current body text from GitHub."""
        if self.kind is EntityKind.ISSUE:
            result = self.github_issues.get_issue(self.repo_root, self.number)
            if isinstance(result, IssueNotFound):
                msg = f"Issue #{self.number} not found"
                raise RuntimeError(msg)
            return result.body
        else:
            result = self.github.get_pr(self.repo_root, self.number)
            if isinstance(result, PRNotFound):
                msg = f"PR #{self.number} not found"
                raise RuntimeError(msg)
            return result.body

    def _push_body(self, body: str) -> None:
        """Write the updated body text to GitHub."""
        if self.kind is EntityKind.ISSUE:
            self.github_issues.update_issue_body(
                self.repo_root, self.number, BodyText(content=body)
            )
        else:
            self.github.update_pr_body(self.repo_root, self.number, body)

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


def entity_state_set(
    state: EntityState,
    key: str,
    data: dict[str, Any],
    *,
    schema: MetadataBlockSchema,
) -> EntityState:
    """Set an entire metadata block. Creates or replaces. Returns the state."""
    block = create_metadata_block(key, data, schema=schema)
    rendered = render_metadata_block(block)
    body = state._fetch_body()

    existing = find_metadata_block(body, key)
    if existing is not None:
        new_body = replace_metadata_block_in_body(body, key, rendered)
    else:
        new_body = (body.rstrip() + "\n\n" + rendered) if body.strip() else rendered

    state._push_body(new_body)
    return state


def entity_state_set_field(
    state: EntityState,
    key: str,
    field: str,
    value: Any,
    *,
    schema: MetadataBlockSchema,
) -> EntityState:
    """Update a single field in a metadata block (read-modify-write). Returns the state."""
    return entity_state_update(state, key, {field: value}, schema=schema)


def entity_state_update(
    state: EntityState,
    key: str,
    fields: dict[str, Any],
    *,
    schema: MetadataBlockSchema,
) -> EntityState:
    """Update multiple fields in one round-trip (read-modify-write). Returns the state."""
    body = state._fetch_body()
    existing = find_metadata_block(body, key)
    if existing is None:
        msg = f"Metadata block '{key}' not found in body"
        raise ValueError(msg)

    updated_data = dict(existing.data)
    updated_data.update(fields)

    block = create_metadata_block(key, updated_data, schema=schema)
    rendered = render_metadata_block(block)
    new_body = replace_metadata_block_in_body(body, key, rendered)
    state._push_body(new_body)
    return state
