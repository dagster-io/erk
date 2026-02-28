"""A GitHub issue or PR with structured metadata and event log."""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.entity_store.log import EntityLog
from erk_shared.entity_store.state import EntityState
from erk_shared.entity_store.types import EntityKind
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.issues.abc import GitHubIssues


@dataclass(frozen=True)
class GitHubEntity:
    """A GitHub issue or PR with structured metadata and event log.

    Provides two APIs:
    - state: mutable KV metadata stored in the entity body
    - log: immutable append-only entries stored as comments
    """

    number: int
    kind: EntityKind
    state: EntityState
    log: EntityLog

    @classmethod
    def create(
        cls,
        *,
        number: int,
        kind: EntityKind,
        github: GitHub,
        github_issues: GitHubIssues,
        repo_root: Path,
    ) -> "GitHubEntity":
        """Build a GitHubEntity with its EntityState and EntityLog."""
        state = EntityState(
            number=number,
            kind=kind,
            github=github,
            github_issues=github_issues,
            repo_root=repo_root,
        )
        log = EntityLog(
            number=number,
            github_issues=github_issues,
            repo_root=repo_root,
        )
        return cls(
            number=number,
            kind=kind,
            state=state,
            log=log,
        )
