"""Draft PR implementation of plan storage.

Uses GitHub draft pull requests as the backing store for plans.
PR body contains the plan-header metadata block followed by plan content.
The "erk-plan" label identifies plan PRs vs regular draft PRs.
"""

from collections.abc import Mapping
from datetime import UTC
from pathlib import Path

from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.metadata.core import (
    find_metadata_block,
    render_metadata_block,
    replace_metadata_block_in_body,
)
from erk_shared.gateway.github.metadata.plan_header import (
    format_plan_header_body,
)
from erk_shared.gateway.github.metadata.schemas import (
    CREATED_FROM_SESSION,
    OBJECTIVE_ISSUE,
    SOURCE_REPO,
    PlanHeaderSchema,
)
from erk_shared.gateway.github.metadata.types import MetadataBlock
from erk_shared.gateway.github.pr_footer import build_pr_body_footer
from erk_shared.gateway.github.types import PRDetails, PRNotFound
from erk_shared.gateway.time.abc import Time
from erk_shared.gateway.time.real import RealTime
from erk_shared.plan_store.backend import PlanBackend
from erk_shared.plan_store.conversion import pr_details_to_plan
from erk_shared.plan_store.draft_pr_lifecycle import (
    PLAN_CONTENT_SEPARATOR,
    build_plan_stage_body,
    extract_metadata_prefix,
    extract_plan_content,
)
from erk_shared.plan_store.types import (
    CreatePlanResult,
    Plan,
    PlanHeaderNotFoundError,
    PlanNotFound,
    PlanQuery,
    PlanState,
)

_PLAN_LABEL = "erk-plan"


def _parse_objective_id(value: object) -> int | None:
    """Parse objective_id from metadata value.

    Args:
        value: Raw value from metadata (str, int, or None)

    Returns:
        Parsed integer or None

    Raises:
        ValueError: If value cannot be converted to int
    """
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise ValueError(f"objective_issue must be str or int, got {type(value).__name__}")


class DraftPRPlanBackend(PlanBackend):
    """Draft PR implementation of plan storage.

    Uses GitHub draft pull requests as the backing store for plans.
    Composes the top-level GitHub ABC which already provides all needed
    PR methods (create_pr, get_pr, close_pr, etc.).

    PR body format:
        <!-- plan-header metadata block -->

        ---

        # Plan: Title

        Plan content here...
    """

    def __init__(
        self, github: GitHub, github_issues: GitHubIssues, time: Time | None = None
    ) -> None:
        """Initialize DraftPRPlanBackend with GitHub and issues gateways.

        Args:
            github: GitHub gateway implementation (real or fake)
            github_issues: GitHubIssues gateway for comment access. On GitHub,
                PR discussion comments share the same API as issue comments.
            time: Time abstraction for deterministic timestamps. Defaults to RealTime().
        """
        self._github = github
        self._github_issues = github_issues
        self._time = time if time is not None else RealTime()

    def get_provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "github-draft-pr"
        """
        return "github-draft-pr"

    def resolve_plan_id_for_branch(self, repo_root: Path, branch_name: str) -> str | None:
        """Resolve plan identifier for a branch by querying for a PR.

        Unlike GitHubPlanStore (zero-cost regex), this requires an API call
        to find the draft PR associated with the branch.

        Args:
            repo_root: Repository root directory
            branch_name: Git branch name

        Returns:
            PR number as string if a draft PR exists for the branch, None otherwise
        """
        result = self._github.get_pr_for_branch(repo_root, branch_name)
        if isinstance(result, PRNotFound):
            return None
        return str(result.number)

    def get_plan_for_branch(self, repo_root: Path, branch_name: str) -> Plan | PlanNotFound:
        """Look up the plan associated with a branch.

        Queries for a draft PR on the branch and converts to Plan.

        Args:
            repo_root: Repository root directory
            branch_name: Git branch name

        Returns:
            Plan if found, PlanNotFound if no draft PR exists for the branch
        """
        result = self._github.get_pr_for_branch(repo_root, branch_name)
        if isinstance(result, PRNotFound):
            return PlanNotFound(plan_id=branch_name)
        return self._convert_to_plan(result)

    def get_plan(self, repo_root: Path, plan_id: str) -> Plan | PlanNotFound:
        """Fetch plan from a draft PR by PR number.

        Args:
            repo_root: Repository root directory
            plan_id: PR number as string (e.g., "42")

        Returns:
            Plan with converted data, or PlanNotFound if PR does not exist
        """
        pr_number = int(plan_id)
        result = self._github.get_pr(repo_root, pr_number)
        if isinstance(result, PRNotFound):
            return PlanNotFound(plan_id=plan_id)
        return self._convert_to_plan(result)

    def get_comments(self, repo_root: Path, plan_id: str) -> list[str]:
        """Get all comments on a plan's draft PR.

        On GitHub, PR discussion comments share the same API as issue comments,
        so we delegate to GitHubIssues.get_issue_comments() with the PR number.

        Args:
            repo_root: Repository root directory
            plan_id: PR number as string

        Returns:
            List of comment body strings, ordered oldest to newest
        """
        pr_number = int(plan_id)
        return self._github_issues.get_issue_comments(repo_root, pr_number)

    def list_plans(self, repo_root: Path, query: PlanQuery) -> list[Plan]:
        """Query plans from draft PRs.

        Lists open PRs, filters to drafts with the erk-plan label,
        and converts each to a Plan.

        Args:
            repo_root: Repository root directory
            query: Filter criteria (labels, state, limit)

        Returns:
            List of Plan matching the criteria
        """
        # Map PlanState to PR list state
        if query.state == PlanState.CLOSED:
            pr_state = "closed"
        elif query.state == PlanState.OPEN:
            pr_state = "open"
        else:
            pr_state = "all"

        # Push label and draft filtering to list_prs
        all_labels = [_PLAN_LABEL]
        if query.labels is not None:
            all_labels.extend(query.labels)

        prs = self._github.list_prs(
            repo_root,
            state=pr_state,
            labels=all_labels,
            draft=True,
        )

        plans: list[Plan] = []
        for _branch, pr_info in prs.items():
            pr_details = self._github.get_pr(repo_root, pr_info.number)
            if isinstance(pr_details, PRNotFound):
                continue

            plans.append(self._convert_to_plan(pr_details))

            if query.limit is not None and len(plans) >= query.limit:
                break

        return plans

    def close_plan(self, repo_root: Path, plan_id: str) -> None:
        """Close a plan by closing its draft PR.

        Adds a comment before closing for audit trail.

        Args:
            repo_root: Repository root directory
            plan_id: PR number as string

        Raises:
            RuntimeError: If PR not found
        """
        pr_number = int(plan_id)
        result = self._github.get_pr(repo_root, pr_number)
        if isinstance(result, PRNotFound):
            msg = f"PR #{pr_number} not found"
            raise RuntimeError(msg)

        self._github.create_pr_comment(repo_root, pr_number, "Plan completed via erk plan close")
        self._github.close_pr(repo_root, pr_number)

    def create_plan(
        self,
        *,
        repo_root: Path,
        title: str,
        content: str,
        labels: tuple[str, ...],
        metadata: Mapping[str, object],
    ) -> CreatePlanResult:
        """Create a new plan as a draft PR.

        Requires "branch_name" in metadata since draft PRs need an existing
        pushed branch.

        Args:
            repo_root: Repository root directory
            title: Plan title
            content: Plan body/description
            labels: Labels to apply (immutable tuple)
            metadata: Provider-specific metadata. Required keys:
                - branch_name: str (branch for the draft PR)
              Optional keys:
                - source_repo: str | None
                - objective_issue: int | None
                - created_from_session: str | None

        Returns:
            CreatePlanResult with plan_id (PR number) and url

        Raises:
            RuntimeError: If branch_name not in metadata or creation fails
        """
        branch_name = metadata.get("branch_name")
        if branch_name is None or not isinstance(branch_name, str):
            raise RuntimeError("branch_name is required in metadata for DraftPRPlanBackend")

        # Get username for metadata
        auth_result = self._github.check_auth_status()
        username: str = (
            auth_result[1] if auth_result[0] and auth_result[1] is not None else "unknown"
        )

        # Build metadata body
        source_repo_raw = metadata.get(SOURCE_REPO)
        source_repo_str: str | None = str(source_repo_raw) if source_repo_raw is not None else None

        objective_issue_raw = metadata.get(OBJECTIVE_ISSUE)
        objective_id: int | None = _parse_objective_id(objective_issue_raw)

        created_from_session_raw = metadata.get(CREATED_FROM_SESSION)
        created_from_session_str: str | None = (
            str(created_from_session_raw) if created_from_session_raw is not None else None
        )

        created_at = self._time.now().replace(tzinfo=UTC).isoformat()
        metadata_body = format_plan_header_body(
            created_at=created_at,
            created_by=username,
            worktree_name=None,
            branch_name=branch_name,
            plan_comment_id=None,
            last_dispatched_run_id=None,
            last_dispatched_node_id=None,
            last_dispatched_at=None,
            last_local_impl_at=None,
            last_local_impl_event=None,
            last_local_impl_session=None,
            last_local_impl_user=None,
            last_remote_impl_at=None,
            last_remote_impl_run_id=None,
            last_remote_impl_session_id=None,
            source_repo=source_repo_str,
            objective_issue=objective_id,
            created_from_session=created_from_session_str,
            created_from_workflow_run_url=None,
            last_learn_session=None,
            last_learn_at=None,
            learn_status=None,
            learn_plan_issue=None,
            learn_plan_pr=None,
            learned_from_issue=None,
        )

        pr_body = build_plan_stage_body(metadata_body, content)

        trunk_branch_raw = metadata.get("trunk_branch")
        base = trunk_branch_raw if isinstance(trunk_branch_raw, str) else "master"

        pr_number = self._github.create_pr(
            repo_root,
            branch=branch_name,
            title=title,
            body=pr_body,
            base=base,
            draft=True,
        )

        # Append checkout footer now that we have the PR number.
        # No issue_number or plans_repo — draft PR IS the plan, so
        # "Closes #N" would be self-referential.
        footer = build_pr_body_footer(pr_number, issue_number=None, plans_repo=None)
        self._github.update_pr_body(repo_root, pr_number, pr_body + footer)

        # Add erk-plan label
        self._github.add_label_to_pr(repo_root, pr_number, _PLAN_LABEL)

        # Add any extra labels
        for label in labels:
            if label != _PLAN_LABEL:
                self._github.add_label_to_pr(repo_root, pr_number, label)

        # Get the PR URL from the created PR
        pr_result = self._github.get_pr(repo_root, pr_number)
        url = pr_result.url if not isinstance(pr_result, PRNotFound) else ""

        return CreatePlanResult(
            plan_id=str(pr_number),
            url=url,
        )

    def get_metadata_field(
        self,
        repo_root: Path,
        plan_id: str,
        field_name: str,
    ) -> object | PlanNotFound:
        """Get a single metadata field from the plan-header block in the PR body.

        Args:
            repo_root: Repository root directory
            plan_id: PR number as string
            field_name: Name of the metadata field to read

        Returns:
            Field value (may be None if unset), or PlanNotFound if PR doesn't exist
        """
        pr_number = int(plan_id)
        result = self._github.get_pr(repo_root, pr_number)
        if isinstance(result, PRNotFound):
            return PlanNotFound(plan_id=plan_id)

        block = find_metadata_block(result.body, "plan-header")
        if block is None:
            return None

        return block.data.get(field_name)

    def get_all_metadata_fields(
        self,
        repo_root: Path,
        plan_id: str,
    ) -> dict[str, object] | PlanNotFound:
        """Get all metadata fields from the plan-header block in the PR body.

        Args:
            repo_root: Repository root directory
            plan_id: PR number as string

        Returns:
            Dictionary of all metadata fields, or PlanNotFound if PR doesn't exist.
            Returns empty dict if PR exists but has no metadata block.
        """
        pr_number = int(plan_id)
        result = self._github.get_pr(repo_root, pr_number)
        if isinstance(result, PRNotFound):
            return PlanNotFound(plan_id=plan_id)

        block = find_metadata_block(result.body, "plan-header")
        if block is None:
            return {}

        return dict(block.data)

    def update_metadata(
        self,
        repo_root: Path,
        plan_id: str,
        metadata: Mapping[str, object],
    ) -> None:
        """Update plan metadata in the PR body.

        Fetches the current PR body, updates the plan-header metadata block,
        and updates the PR body.

        Args:
            repo_root: Repository root directory
            plan_id: PR number as string
            metadata: New metadata to set

        Raises:
            PlanHeaderNotFoundError: If PR body has no plan-header metadata block
            RuntimeError: If PR not found or update fails
        """
        pr_number = int(plan_id)
        result = self._github.get_pr(repo_root, pr_number)
        if isinstance(result, PRNotFound):
            msg = f"PR #{pr_number} not found"
            raise RuntimeError(msg)

        block = find_metadata_block(result.body, "plan-header")
        if block is None:
            raise PlanHeaderNotFoundError("plan-header block not found in PR body")

        current_data = dict(block.data)

        # Protect immutable fields
        immutable_fields = {"schema_version", "created_at", "created_by"}
        for key, value in metadata.items():
            if key not in immutable_fields:
                current_data[key] = value

        schema = PlanHeaderSchema()
        schema.validate(current_data)

        new_block = MetadataBlock(key="plan-header", data=current_data)
        new_block_content = render_metadata_block(new_block)

        updated_body = replace_metadata_block_in_body(result.body, "plan-header", new_block_content)
        self._github.update_pr_body(repo_root, pr_number, updated_body)

    def update_plan_content(
        self,
        repo_root: Path,
        plan_id: str,
        content: str,
    ) -> None:
        """Update the plan content in the PR body.

        Replaces everything after the metadata block separator with new content.

        Args:
            repo_root: Repository root directory
            plan_id: PR number as string
            content: New plan content

        Raises:
            RuntimeError: If PR not found
        """
        pr_number = int(plan_id)
        result = self._github.get_pr(repo_root, pr_number)
        if isinstance(result, PRNotFound):
            msg = f"PR #{pr_number} not found"
            raise RuntimeError(msg)

        # Preserve metadata prefix and replace plan content
        metadata_prefix = extract_metadata_prefix(result.body)
        if metadata_prefix:
            updated_body = build_plan_stage_body(
                metadata_prefix[: -len(PLAN_CONTENT_SEPARATOR)], content
            )
        else:
            # No separator found - just set the content
            updated_body = content

        self._github.update_pr_body(repo_root, pr_number, updated_body)

    def add_comment(
        self,
        repo_root: Path,
        plan_id: str,
        body: str,
    ) -> str:
        """Add a comment to the plan's draft PR.

        Args:
            repo_root: Repository root directory
            plan_id: PR number as string
            body: Comment body text

        Returns:
            Comment ID as string

        Raises:
            RuntimeError: If PR not found
        """
        pr_number = int(plan_id)
        result = self._github.get_pr(repo_root, pr_number)
        if isinstance(result, PRNotFound):
            msg = f"PR #{pr_number} not found"
            raise RuntimeError(msg)

        comment_id = self._github.create_pr_comment(repo_root, pr_number, body)
        return str(comment_id)

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
            plan_id: PR number as string
            metadata: Metadata fields to update
            comment: Optional comment body to post

        Raises:
            RuntimeError: If PR not found
        """
        if comment is not None:
            self.add_comment(repo_root, plan_id, comment)
        self.update_metadata(repo_root, plan_id, metadata)

    def _convert_to_plan(self, pr: PRDetails) -> Plan:
        """Convert PRDetails to Plan, extracting plan content from body.

        Args:
            pr: PRDetails from GitHub API

        Returns:
            Plan with plan content extracted from body
        """
        plan_body = extract_plan_content(pr.body)
        plan = pr_details_to_plan(pr, plan_body=plan_body)

        # If labels weren't in PRDetails, check via has_pr_label
        return plan
