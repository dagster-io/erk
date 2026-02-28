"""Immutable append-only log stored as comments.

Each entry is a GitHub comment containing a metadata block.
Entries are never modified after creation.
"""

from pathlib import Path
from typing import Any

from erk_shared.entity_store.types import LogEntry
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.metadata.core import (
    create_metadata_block,
    parse_metadata_blocks,
    render_content_block,
    render_erk_issue_event,
)
from erk_shared.gateway.github.metadata.types import MetadataBlockSchema


class EntityLog:
    """Immutable append-only log stored as comments.

    Each entry is a GitHub comment containing a metadata block.
    Entries are never modified after creation.
    """

    def __init__(
        self,
        *,
        number: int,
        github_issues: GitHubIssues,
        repo_root: Path,
    ) -> None:
        self._number = number
        self._github_issues = github_issues
        self._repo_root = repo_root

    def append(
        self,
        key: str,
        data: dict[str, Any],
        *,
        title: str,
        description: str,
        schema: MetadataBlockSchema | None,
    ) -> int:
        """Append a structured log entry. Returns comment ID."""
        block = create_metadata_block(key, data, schema=schema)
        comment_body = render_erk_issue_event(title, block, description)
        return self._github_issues.add_comment(self._repo_root, self._number, comment_body)

    def append_content(
        self,
        key: str,
        content: str,
        *,
        title: str,
    ) -> int:
        """Append a raw markdown content entry (e.g., plan-body, objective-body).
        Returns comment ID."""
        rendered = render_content_block(key, title, content)
        return self._github_issues.add_comment(self._repo_root, self._number, rendered)

    def entries(self, key: str) -> list[LogEntry]:
        """Get all log entries with a given key, in chronological order."""
        all_entries = self.all_entries()
        return [entry for entry in all_entries if entry.key == key]

    def latest(self, key: str) -> LogEntry | None:
        """Get the most recent entry with a given key."""
        matching = self.entries(key)
        if not matching:
            return None
        return matching[-1]

    def all_entries(self) -> list[LogEntry]:
        """Get all log entries across all keys."""
        comment_bodies = self._github_issues.get_issue_comments(self._repo_root, self._number)
        entries: list[LogEntry] = []
        # Use synthetic comment IDs based on position since get_issue_comments
        # returns strings, not IDs. This maintains chronological order.
        for index, comment_body in enumerate(comment_bodies):
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
