"""A GitHub issue or PR with structured metadata and event log."""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.entity_store.log import EntityLog
from erk_shared.entity_store.state import EntityState, fetch_entity_body
from erk_shared.entity_store.types import EntityKind
from erk_shared.gateway.github.abc import LocalGitHub
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
        github: LocalGitHub,
        github_issues: GitHubIssues,
        repo_root: Path,
    ) -> "GitHubEntity":
        """Build a GitHubEntity by fetching state body and comment bodies."""
        body = fetch_entity_body(
            number=number,
            kind=kind,
            github=github,
            github_issues=github_issues,
            repo_root=repo_root,
        )
        state = EntityState(
            number=number,
            kind=kind,
            body=body,
        )
        comment_bodies = github_issues.get_issue_comments(repo_root, number)
        log = EntityLog(comment_bodies=comment_bodies)
        return cls(number=number, kind=kind, state=state, log=log)
