"""Mutable KV metadata stored in the entity body.

Each write operation does a full read-modify-write cycle to GitHub.
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
    """KV metadata snapshot stored in the entity body.

    Pure data — holds the body text directly.
    Read operations are methods on the dataclass.
    Write operations are standalone functions below.
    """

    number: int
    kind: EntityKind
    body: str

    def get(self, key: str) -> dict[str, Any] | None:
        """Get a metadata block by key. Returns None if not found."""
        block = find_metadata_block(self.body, key)
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
        return find_metadata_block(self.body, key) is not None


def fetch_entity_body(
    *,
    number: int,
    kind: EntityKind,
    github: GitHub,
    github_issues: GitHubIssues,
    repo_root: Path,
) -> str:
    """Fetch the current body text from GitHub."""
    if kind is EntityKind.ISSUE:
        result = github_issues.get_issue(repo_root, number)
        if isinstance(result, IssueNotFound):
            msg = f"Issue #{number} not found"
            raise RuntimeError(msg)
        return result.body
    else:
        result = github.get_pr(repo_root, number)
        if isinstance(result, PRNotFound):
            msg = f"PR #{number} not found"
            raise RuntimeError(msg)
        return result.body


def push_entity_body(
    *,
    number: int,
    kind: EntityKind,
    body: str,
    github: GitHub,
    github_issues: GitHubIssues,
    repo_root: Path,
) -> None:
    """Write the updated body text to GitHub."""
    if kind is EntityKind.ISSUE:
        github_issues.update_issue_body(repo_root, number, BodyText(content=body))
    else:
        github.update_pr_body(repo_root, number, body)


def entity_state_set(
    state: EntityState,
    key: str,
    data: dict[str, Any],
    *,
    schema: MetadataBlockSchema,
    github: GitHub,
    github_issues: GitHubIssues,
    repo_root: Path,
) -> EntityState:
    """Set an entire metadata block. Creates or replaces. Returns new state."""
    block = create_metadata_block(key, data, schema=schema)
    rendered = render_metadata_block(block)
    body = state.body

    existing = find_metadata_block(body, key)
    if existing is not None:
        new_body = replace_metadata_block_in_body(body, key, rendered)
    else:
        new_body = (body.rstrip() + "\n\n" + rendered) if body.strip() else rendered

    push_entity_body(
        number=state.number,
        kind=state.kind,
        body=new_body,
        github=github,
        github_issues=github_issues,
        repo_root=repo_root,
    )
    return EntityState(number=state.number, kind=state.kind, body=new_body)


def entity_state_set_field(
    state: EntityState,
    key: str,
    field: str,
    value: Any,
    *,
    schema: MetadataBlockSchema,
    github: GitHub,
    github_issues: GitHubIssues,
    repo_root: Path,
) -> EntityState:
    """Update a single field in a metadata block (read-modify-write). Returns new state."""
    return entity_state_update(
        state,
        key,
        {field: value},
        schema=schema,
        github=github,
        github_issues=github_issues,
        repo_root=repo_root,
    )


def entity_state_update(
    state: EntityState,
    key: str,
    fields: dict[str, Any],
    *,
    schema: MetadataBlockSchema,
    github: GitHub,
    github_issues: GitHubIssues,
    repo_root: Path,
) -> EntityState:
    """Update multiple fields in one round-trip (read-modify-write). Returns new state."""
    body = state.body
    existing = find_metadata_block(body, key)
    if existing is None:
        msg = f"Metadata block '{key}' not found in body"
        raise ValueError(msg)

    updated_data = dict(existing.data)
    updated_data.update(fields)

    block = create_metadata_block(key, updated_data, schema=schema)
    rendered = render_metadata_block(block)
    new_body = replace_metadata_block_in_body(body, key, rendered)
    push_entity_body(
        number=state.number,
        kind=state.kind,
        body=new_body,
        github=github,
        github_issues=github_issues,
        repo_root=repo_root,
    )
    return EntityState(number=state.number, kind=state.kind, body=new_body)
