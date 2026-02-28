"""Immutable append-only log stored as comments.

Each entry is a GitHub comment containing a metadata block.
Entries are never modified after creation.
"""

from functools import cached_property
from pathlib import Path
from typing import Any

from erk_shared.entity_store.types import LogEntry
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.metadata.core import (
    create_metadata_block,
    parse_metadata_blocks,
    render_erk_issue_event,
)
from erk_shared.gateway.github.metadata.types import MetadataBlockSchema


def _render_content_block(key: str, title: str, content: str) -> str:
    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:{key} -->
<details open>
<summary><strong>{title}</strong></summary>

{content}

</details>
<!-- /erk:metadata-block:{key} -->"""


class EntityLog:
    """Immutable append-only log stored as comments.

    Pure data snapshot — holds only comment bodies.
    Use entity_log_append() / entity_log_append_content() for mutations.
    """

    def __init__(
        self,
        *,
        comment_bodies: list[str],
    ) -> None:
        self._comment_bodies = comment_bodies

    def entries(self, key: str) -> list[LogEntry]:
        """Get all log entries with a given key, in chronological order."""
        return [entry for entry in self.all_entries if entry.key == key]

    def latest(self, key: str) -> LogEntry | None:
        """Get the most recent entry with a given key."""
        matching = self.entries(key)
        if not matching:
            return None
        return matching[-1]

    @cached_property
    def all_entries(self) -> list[LogEntry]:
        """Get all log entries across all keys."""
        entries: list[LogEntry] = []
        # Use synthetic comment IDs based on position since comment_bodies
        # are strings, not IDs. This maintains chronological order.
        for index, comment_body in enumerate(self._comment_bodies):
            result = parse_metadata_blocks(comment_body)
            for block in result.blocks:
                entries.append(
                    LogEntry(
                        key=block.key,
                        data=block.data,
                        comment_id=index,
                    )
                )
        return entries


def entity_log_append(
    *,
    github_issues: GitHubIssues,
    repo_root: Path,
    number: int,
    key: str,
    data: dict[str, Any],
    title: str,
    description: str,
    schema: MetadataBlockSchema,
) -> int:
    """Append a structured log entry. Returns comment ID."""
    block = create_metadata_block(key, data, schema=schema)
    comment_body = render_erk_issue_event(title, block, description)
    return github_issues.add_comment(repo_root, number, comment_body)


def entity_log_append_content(
    *,
    github_issues: GitHubIssues,
    repo_root: Path,
    number: int,
    key: str,
    content: str,
    title: str,
) -> int:
    """Append a raw markdown content entry (e.g., plan-body, objective-body).
    Returns comment ID."""
    rendered = _render_content_block(key, title, content)
    return github_issues.add_comment(repo_root, number, rendered)
