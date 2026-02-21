"""Abstract interface for plan storage backends.

PlanBackend is a BACKEND, not a gateway. Backends compose gateways (like GitHubIssues)
and should NOT have fake implementations. To test code that uses a PlanBackend,
inject fake gateways into the real backend implementation.

Example:
    # Testing with fake gateway
    fake_issues = FakeGitHubIssues()
    backend = GitHubPlanBackend(fake_issues)  # Real backend, fake gateway
    result = backend.create_plan(...)

    # Assert on gateway mutations
    assert fake_issues.created_issues[0][0] == "expected title"

See: .claude/skills/fake-driven-testing/references/gateway-architecture.md
for the full gateway vs backend architecture.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Mapping
from pathlib import Path

from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_header_created_from_session,
    extract_plan_header_last_learn_session,
    extract_plan_header_last_session_id,
    extract_plan_header_last_session_source,
    extract_plan_header_local_impl_session,
    extract_plan_header_remote_impl_at,
    extract_plan_header_remote_impl_run_id,
    extract_plan_header_remote_impl_session_id,
    extract_plan_header_session_branch,
)
from erk_shared.learn.impl_events import (
    extract_implementation_sessions,
    extract_learn_sessions,
)
from erk_shared.plan_store.store import PlanStore
from erk_shared.plan_store.types import CreatePlanResult, Plan, PlanNotFound, PlanQuery
from erk_shared.sessions.discovery import SessionsForPlan

# ---------------------------------------------------------------------------
# Branch → Plan Resolution
# ---------------------------------------------------------------------------


class PlanBackend(PlanStore):
    """Abstract interface for plan storage operations.

    Extends PlanStore to add write operations while maintaining backward
    compatibility with code that only needs read operations.

    Implementations provide backend-specific storage for plans.
    Both read and write operations are supported.

    Read operations (inherited from PlanStore):
        get_plan: Fetch a plan by identifier
        list_plans: Query plans by criteria
        get_provider_name: Get the provider name
        close_plan: Close a plan
        get_metadata_field: Get a single metadata field value

    Write operations (added by PlanBackend):
        create_plan: Create a new plan
        update_metadata: Update plan metadata
        update_plan_content: Update plan content body
        add_comment: Add a comment to a plan
        post_event: Combined metadata update + optional comment
    """

    # Read operations (inherited from PlanStore, re-declared with updated param names)

    @abstractmethod
    def get_plan(self, repo_root: Path, plan_id: str) -> Plan | PlanNotFound:
        """Fetch a plan by identifier.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier (e.g., "42", "PROJ-123")

        Returns:
            Plan with all metadata, or PlanNotFound if the plan does not exist
        """
        ...

    @abstractmethod
    def list_plans(self, repo_root: Path, query: PlanQuery) -> list[Plan]:
        """Query plans by criteria.

        Args:
            repo_root: Repository root directory
            query: Filter criteria (labels, state, limit)

        Returns:
            List of Plan matching the criteria

        Raises:
            RuntimeError: If provider fails
        """
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the provider.

        Returns:
            Provider name (e.g., "github", "gitlab", "linear")
        """
        ...

    @abstractmethod
    def get_metadata_field(
        self,
        repo_root: Path,
        plan_id: str,
        field_name: str,
    ) -> object | PlanNotFound:
        """Get a single metadata field from a plan.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier
            field_name: Name of the metadata field to read

        Returns:
            Field value (may be None if unset), or PlanNotFound if plan doesn't exist
        """
        ...

    @abstractmethod
    def get_all_metadata_fields(
        self,
        repo_root: Path,
        plan_id: str,
    ) -> dict[str, object] | PlanNotFound:
        """Get all metadata fields from the plan-header block.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier

        Returns:
            Dictionary of all metadata fields, or PlanNotFound if plan doesn't exist.
            Returns empty dict if plan exists but has no metadata block.
        """
        ...

    @abstractmethod
    def get_comments(self, repo_root: Path, plan_id: str) -> list[str]:
        """Get all comments on a plan.

        Used by session discovery to find implementation and learn session IDs
        from impl-started/impl-ended/learn-invoked metadata blocks posted as comments.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier

        Returns:
            List of comment body strings, ordered oldest to newest.
            Returns empty list if plan has no comments.

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        ...

    # Session discovery (concrete — uses get_plan + get_comments)

    def find_sessions_for_plan(
        self,
        repo_root: Path,
        plan_id: str,
    ) -> SessionsForPlan:
        """Find all Claude Code sessions associated with a plan.

        Extracts session IDs from:
        1. created_from_session in plan-header (planning session)
        2. last_local_impl_session in plan-header (most recent impl session)
        3. impl-started/impl-ended comments (all implementation sessions)
        4. last_learn_session in plan-header (most recent learn session)
        5. learn-invoked comments (previous learn sessions)

        This is a concrete method that delegates to the abstract ``get_plan``
        and ``get_comments`` methods, so every backend gets it for free.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier

        Returns:
            SessionsForPlan with all discovered session IDs

        Raises:
            RuntimeError: If plan not found
        """
        plan = self.get_plan(repo_root, plan_id)
        if isinstance(plan, PlanNotFound):
            msg = f"Plan {plan_id} not found"
            raise RuntimeError(msg)

        body = plan.body
        planning_session_id = extract_plan_header_created_from_session(body)
        metadata_impl_session = extract_plan_header_local_impl_session(body)
        metadata_learn_session = extract_plan_header_last_learn_session(body)

        comments = self.get_comments(repo_root, plan_id)
        comment_impl_sessions = extract_implementation_sessions(comments)
        comment_learn_sessions = extract_learn_sessions(comments)

        # Combine implementation sessions: metadata first, then from comments
        implementation_session_ids: list[str] = []
        impl_seen: set[str] = set()
        if metadata_impl_session is not None:
            implementation_session_ids.append(metadata_impl_session)
            impl_seen.add(metadata_impl_session)
        for session_id in comment_impl_sessions:
            if session_id not in impl_seen:
                implementation_session_ids.append(session_id)
                impl_seen.add(session_id)

        # Combine learn sessions: metadata first, then from comments
        learn_session_ids: list[str] = []
        learn_seen: set[str] = set()
        if metadata_learn_session is not None:
            learn_session_ids.append(metadata_learn_session)
            learn_seen.add(metadata_learn_session)
        for session_id in comment_learn_sessions:
            if session_id not in learn_seen:
                learn_session_ids.append(session_id)
                learn_seen.add(session_id)

        return SessionsForPlan(
            planning_session_id=planning_session_id,
            implementation_session_ids=implementation_session_ids,
            learn_session_ids=learn_session_ids,
            last_remote_impl_at=extract_plan_header_remote_impl_at(body),
            last_remote_impl_run_id=extract_plan_header_remote_impl_run_id(body),
            last_remote_impl_session_id=extract_plan_header_remote_impl_session_id(body),
            last_session_branch=extract_plan_header_session_branch(body),
            last_session_id=extract_plan_header_last_session_id(body),
            last_session_source=extract_plan_header_last_session_source(body),
        )

    # Branch → Plan resolution

    @abstractmethod
    def get_plan_for_branch(self, repo_root: Path, branch_name: str) -> Plan | PlanNotFound:
        """Look up the plan associated with a branch.

        Resolves the branch name to a plan identifier and fetches the full plan.
        Returns PlanNotFound if the branch is not a plan branch or the plan
        doesn't exist.

        Args:
            repo_root: Repository root directory
            branch_name: Git branch name (e.g., "P123-fix-bug-01-15-1430")

        Returns:
            Plan if found, PlanNotFound otherwise
        """
        ...

    @abstractmethod
    def resolve_plan_id_for_branch(self, repo_root: Path, branch_name: str) -> str | None:
        """Resolve plan identifier for a branch without fetching the full plan.

        Lightweight resolution that does NOT verify the plan exists.
        Returns None if the branch is not associated with a plan.

        For GitHubPlanBackend this is a zero-cost regex operation.
        Future backends (e.g., DraftPRPlanBackend) may require an API call.

        Args:
            repo_root: Repository root directory
            branch_name: Git branch name

        Returns:
            Plan identifier string if branch is a plan branch, None otherwise
        """
        ...

    # Write operations

    @abstractmethod
    def create_plan(
        self,
        *,
        repo_root: Path,
        title: str,
        content: str,
        labels: tuple[str, ...],
        metadata: Mapping[str, object],
    ) -> CreatePlanResult:
        """Create a new plan.

        Args:
            repo_root: Repository root directory
            title: Plan title
            content: Plan body/description
            labels: Labels to apply (immutable tuple)
            metadata: Provider-specific metadata

        Returns:
            CreatePlanResult with plan_id and url

        Raises:
            RuntimeError: If provider fails
        """
        ...

    @abstractmethod
    def update_metadata(
        self,
        repo_root: Path,
        plan_id: str,
        metadata: Mapping[str, object],
    ) -> None:
        """Update plan metadata.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier
            metadata: New metadata to set

        Raises:
            PlanHeaderNotFoundError: If plan has no plan-header metadata block
            RuntimeError: If provider fails or plan not found
        """
        ...

    @abstractmethod
    def update_plan_content(
        self,
        repo_root: Path,
        plan_id: str,
        content: str,
    ) -> None:
        """Update the plan content body.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier
            content: New plan content

        Raises:
            RuntimeError: If plan not found or update fails
        """
        ...

    # close_plan is inherited from PlanStore

    @abstractmethod
    def update_plan_title(
        self,
        repo_root: Path,
        plan_id: str,
        title: str,
    ) -> None:
        """Update the title of a plan.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier (e.g., "42")
            title: New plan title

        Raises:
            RuntimeError: If plan not found or update fails
        """
        ...

    @abstractmethod
    def add_comment(
        self,
        repo_root: Path,
        plan_id: str,
        body: str,
    ) -> str:
        """Add a comment to a plan.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier
            body: Comment body text

        Returns:
            Comment ID as string

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        ...

    @abstractmethod
    def add_label(
        self,
        repo_root: Path,
        plan_id: str,
        label: str,
    ) -> None:
        """Add a label to a plan.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier
            label: Label to add

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        ...

    @abstractmethod
    def post_event(
        self,
        repo_root: Path,
        plan_id: str,
        *,
        metadata: Mapping[str, object],
        comment: str | None,
    ) -> None:
        """Post a combined event: metadata update + optional comment.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier
            metadata: Metadata fields to update
            comment: Optional comment body to post

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        ...
