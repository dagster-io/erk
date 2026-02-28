"""A GitHub issue or PR with structured metadata and event log."""

from pathlib import Path

from erk_shared.entity_store.log import EntityLog
from erk_shared.entity_store.state import EntityState
from erk_shared.entity_store.types import EntityKind
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.issues.abc import GitHubIssues


class GitHubEntity:
    """A GitHub issue or PR with structured metadata and event log.

    Provides two APIs:
    - state: mutable KV metadata stored in the entity body
    - log: immutable append-only entries stored as comments
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
        self._state = EntityState(
            number=number,
            kind=kind,
            github=github,
            github_issues=github_issues,
            repo_root=repo_root,
        )
        self._log = EntityLog(
            number=number,
            github_issues=github_issues,
            repo_root=repo_root,
        )

    @property
    def number(self) -> int:
        return self._number

    @property
    def kind(self) -> EntityKind:
        return self._kind

    @property
    def state(self) -> EntityState:
        return self._state

    @property
    def log(self) -> EntityLog:
        return self._log
