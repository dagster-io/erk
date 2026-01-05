"""Fake Linear implementation for validating PlanBackend ABC design.

This module provides a fake Linear backend to validate that the PlanBackend
ABC correctly abstracts over backends with fundamentally different data models.

Key differences from GitHub that this fake models:
- Plan IDs are UUID strings (not integers)
- 5-state workflow (backlog, todo, in_progress, done, canceled)
- Single assignee (not list)
- Comment IDs are UUID strings (not integers)
- Metadata stored in custom_fields (not YAML in body)

Sources:
- docs/learned/integrations/linear-primitives.md (Linear API and GraphQL schema)
- docs/learned/integrations/linear-erk-mapping.md (erk-to-Linear concept mapping)
- Linear GraphQL schema: https://github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql

ABC Abstraction Validation Results:
========================================

✅ WORKS WELL:
- `plan_id: str` works for both GitHub integers-as-strings and Linear UUIDs
- `PlanState.OPEN/CLOSED` maps cleanly to Linear's 5 states
- `list[str]` for assignees handles Linear's single assignee (0 or 1 items)
- Comment ID as str works for both GitHub int-as-str and Linear UUID
- `Mapping[str, object]` for metadata is sufficiently flexible
- `tuple[str, ...]` for labels in create_plan() is clean
- `repo_root: Path` parameter is ignored by Linear (but harmless)

⚠️ DISCOVERED QUIRKS (not blocking):
- Title may be modified by backends (GitHub appends [erk-plan] suffix)
  → Tests should check title CONTAINS original, not exact match
- Plan ID validation differs (GitHub requires numeric, Linear accepts any string)
  → Backends handle validation internally; ABC doesn't constrain format
- Metadata update behavior differs (GitHub has whitelist, Linear accepts all)
  → ABC doesn't specify field restrictions; that's backend policy

🎯 CONCLUSION:
The PlanBackend ABC successfully abstracts over fundamentally different backends.
No changes to the ABC are required to support Linear-style backends.
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from erk_shared.plan_store.backend import PlanBackend
from erk_shared.plan_store.types import CreatePlanResult, Plan, PlanQuery, PlanState

# Linear uses a 5-state workflow
LinearState = Literal["backlog", "todo", "in_progress", "done", "canceled"]


@dataclass(frozen=True)
class LinearIssue:
    """Internal representation of a Linear issue.

    Models Linear's key differences from GitHub Issues:
    - id: UUID string (not integer like GitHub)
    - state: 5 states (not just OPEN/CLOSED)
    - assignee: Single user or None (not list)
    """

    id: str  # UUID
    title: str
    description: str
    state: LinearState
    url: str
    labels: tuple[str, ...]  # Immutable
    assignee: str | None  # Single assignee (not list like GitHub)
    created_at: datetime
    updated_at: datetime
    custom_fields: dict[str, object]  # Metadata storage


@dataclass(frozen=True)
class LinearComment:
    """Internal representation of a Linear comment."""

    id: str  # UUID
    body: str
    created_at: datetime


class FakeLinearPlanBackend(PlanBackend):
    """Fake Linear implementation for testing ABC interface design.

    This fake validates that the PlanBackend ABC works for a backend with
    fundamentally different characteristics:

    1. UUID-based IDs (not integers like GitHub)
    2. 5-state workflow mapped to OPEN/CLOSED
    3. Single assignee instead of list
    4. Metadata in custom_fields instead of YAML
    """

    def __init__(
        self,
        *,
        issues: dict[str, LinearIssue] | None = None,
        comments: dict[str, list[LinearComment]] | None = None,
        id_prefix: str = "LIN",
    ) -> None:
        """Initialize fake with optional pre-configured state.

        Args:
            issues: Pre-configured issues keyed by UUID
            comments: Pre-configured comments keyed by issue UUID
            id_prefix: Prefix for generated IDs (default: "LIN")
        """
        # Internal state (mutable)
        self._issues: dict[str, LinearIssue] = dict(issues) if issues else {}
        self._comments: dict[str, list[LinearComment]] = (
            {k: list(v) for k, v in comments.items()} if comments else {}
        )
        self._id_prefix = id_prefix
        self._id_counter = 1

        # Mutation tracking (for test assertions)
        self._created_plans: list[tuple[str, str, tuple[str, ...]]] = []
        self._updated_metadata: list[tuple[str, Mapping[str, object]]] = []
        self._added_comments: list[tuple[str, str, str]] = []  # (plan_id, body, comment_id)
        self._closed_plans: list[str] = []

    # -------------------------------------------------------------------------
    # Read operations (from PlanBackend ABC)
    # -------------------------------------------------------------------------

    def get_plan(self, repo_root: Path, plan_id: str) -> Plan:
        """Fetch a plan by UUID identifier.

        Args:
            repo_root: Repository root directory (ignored for fake)
            plan_id: Linear UUID string

        Returns:
            Plan with converted data

        Raises:
            RuntimeError: If plan not found
        """
        if plan_id not in self._issues:
            msg = f"Linear issue {plan_id} not found"
            raise RuntimeError(msg)

        issue = self._issues[plan_id]
        return self._convert_to_plan(issue)

    def list_plans(self, repo_root: Path, query: PlanQuery) -> list[Plan]:
        """Query plans by criteria.

        Args:
            repo_root: Repository root directory (ignored for fake)
            query: Filter criteria (labels, state, limit)

        Returns:
            List of Plan matching the criteria
        """
        results: list[Plan] = []

        for issue in self._issues.values():
            # Filter by state
            if query.state is not None:
                issue_plan_state = self._map_linear_state_to_plan_state(issue.state)
                if issue_plan_state != query.state:
                    continue

            # Filter by labels (AND logic - all must match)
            if query.labels is not None:
                issue_labels_set = set(issue.labels)
                if not all(lbl in issue_labels_set for lbl in query.labels):
                    continue

            results.append(self._convert_to_plan(issue))

            # Apply limit
            if query.limit is not None and len(results) >= query.limit:
                break

        return results

    def get_provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "linear"
        """
        return "linear"

    def close_plan(self, repo_root: Path, plan_id: str) -> None:
        """Close a plan by setting state to 'done'.

        Args:
            repo_root: Repository root directory (ignored for fake)
            plan_id: Linear UUID string

        Raises:
            RuntimeError: If plan not found
        """
        if plan_id not in self._issues:
            msg = f"Linear issue {plan_id} not found"
            raise RuntimeError(msg)

        old_issue = self._issues[plan_id]

        # Create updated issue with 'done' state
        self._issues[plan_id] = LinearIssue(
            id=old_issue.id,
            title=old_issue.title,
            description=old_issue.description,
            state="done",
            url=old_issue.url,
            labels=old_issue.labels,
            assignee=old_issue.assignee,
            created_at=old_issue.created_at,
            updated_at=datetime.now(UTC),
            custom_fields=old_issue.custom_fields,
        )
        self._closed_plans.append(plan_id)

    # -------------------------------------------------------------------------
    # Write operations (from PlanBackend ABC)
    # -------------------------------------------------------------------------

    def create_plan(
        self,
        repo_root: Path,
        title: str,
        content: str,
        labels: tuple[str, ...],
        metadata: Mapping[str, object],
    ) -> CreatePlanResult:
        """Create a new plan.

        Args:
            repo_root: Repository root directory (ignored for fake)
            title: Plan title
            content: Plan body/description
            labels: Labels to apply
            metadata: Provider-specific metadata (stored in custom_fields)

        Returns:
            CreatePlanResult with UUID plan_id and url
        """
        # Generate UUID-based ID with hex suffix guaranteed to have letters
        hex_id = uuid.uuid4().hex[:8]
        # Ensure at least one non-digit character by appending 'a' if all digits
        if hex_id.isdigit():
            hex_id = hex_id[:7] + "a"
        plan_id = f"{self._id_prefix}-{hex_id}"
        self._id_counter += 1

        now = datetime.now(UTC)

        # Create Linear issue
        issue = LinearIssue(
            id=plan_id,
            title=title,
            description=content,
            state="todo",  # New plans start in 'todo' state
            url=f"https://linear.app/team/issue/{plan_id}",
            labels=labels,
            assignee=None,
            created_at=now,
            updated_at=now,
            custom_fields=dict(metadata),
        )

        self._issues[plan_id] = issue
        self._created_plans.append((title, content, labels))

        return CreatePlanResult(
            plan_id=plan_id,
            url=issue.url,
        )

    def update_metadata(
        self,
        repo_root: Path,
        plan_id: str,
        metadata: Mapping[str, object],
    ) -> None:
        """Update plan metadata in custom_fields.

        Args:
            repo_root: Repository root directory (ignored for fake)
            plan_id: Linear UUID string
            metadata: New metadata to merge into custom_fields

        Raises:
            RuntimeError: If plan not found
        """
        if plan_id not in self._issues:
            msg = f"Linear issue {plan_id} not found"
            raise RuntimeError(msg)

        old_issue = self._issues[plan_id]

        # Merge metadata into custom_fields
        new_custom_fields = dict(old_issue.custom_fields)
        for key, value in metadata.items():
            new_custom_fields[key] = value

        # Create updated issue
        self._issues[plan_id] = LinearIssue(
            id=old_issue.id,
            title=old_issue.title,
            description=old_issue.description,
            state=old_issue.state,
            url=old_issue.url,
            labels=old_issue.labels,
            assignee=old_issue.assignee,
            created_at=old_issue.created_at,
            updated_at=datetime.now(UTC),
            custom_fields=new_custom_fields,
        )
        self._updated_metadata.append((plan_id, metadata))

    def add_comment(
        self,
        repo_root: Path,
        plan_id: str,
        body: str,
    ) -> str:
        """Add a comment to a plan.

        Args:
            repo_root: Repository root directory (ignored for fake)
            plan_id: Linear UUID string
            body: Comment body text

        Returns:
            Comment ID as UUID string

        Raises:
            RuntimeError: If plan not found
        """
        if plan_id not in self._issues:
            msg = f"Linear issue {plan_id} not found"
            raise RuntimeError(msg)

        # Generate UUID for comment
        comment_id = f"comment-{uuid.uuid4().hex[:8]}"

        comment = LinearComment(
            id=comment_id,
            body=body,
            created_at=datetime.now(UTC),
        )

        if plan_id not in self._comments:
            self._comments[plan_id] = []
        self._comments[plan_id].append(comment)

        self._added_comments.append((plan_id, body, comment_id))

        return comment_id

    # -------------------------------------------------------------------------
    # Read-only properties for test assertions
    # -------------------------------------------------------------------------

    @property
    def created_plans(self) -> list[tuple[str, str, tuple[str, ...]]]:
        """Read-only access to created plans for test assertions.

        Returns list of (title, content, labels) tuples.
        """
        return list(self._created_plans)

    @property
    def updated_metadata(self) -> list[tuple[str, Mapping[str, object]]]:
        """Read-only access to metadata updates for test assertions.

        Returns list of (plan_id, metadata) tuples.
        """
        return list(self._updated_metadata)

    @property
    def added_comments(self) -> list[tuple[str, str, str]]:
        """Read-only access to added comments for test assertions.

        Returns list of (plan_id, body, comment_id) tuples.
        """
        return list(self._added_comments)

    @property
    def closed_plans(self) -> list[str]:
        """Read-only access to closed plans for test assertions.

        Returns list of plan_ids.
        """
        return list(self._closed_plans)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _map_linear_state_to_plan_state(self, linear_state: LinearState) -> PlanState:
        """Map Linear's 5 states to erk's 2 states.

        OPEN: backlog, todo, in_progress
        CLOSED: done, canceled
        """
        closed_states: set[LinearState] = {"done", "canceled"}
        if linear_state in closed_states:
            return PlanState.CLOSED
        return PlanState.OPEN

    def _convert_to_plan(self, issue: LinearIssue) -> Plan:
        """Convert LinearIssue to provider-agnostic Plan.

        Key adaptations:
        - Single assignee becomes list with 0 or 1 items
        - 5-state maps to OPEN/CLOSED
        - custom_fields becomes metadata
        """
        # Convert single assignee to list
        assignees: list[str] = []
        if issue.assignee is not None:
            assignees = [issue.assignee]

        return Plan(
            plan_identifier=issue.id,
            title=issue.title,
            body=issue.description,
            state=self._map_linear_state_to_plan_state(issue.state),
            url=issue.url,
            labels=list(issue.labels),
            assignees=assignees,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
            metadata=dict(issue.custom_fields),
        )
