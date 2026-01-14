"""Schema implementations for metadata blocks."""

from dataclasses import dataclass
from typing import Any

from erk_shared.github.metadata.types import MetadataBlockSchema


@dataclass(frozen=True)
class ImplementationStatusSchema(MetadataBlockSchema):
    """Schema for erk-implementation-status blocks (completion status)."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate erk-implementation-status data structure."""
        required_fields = {
            "status",
            "timestamp",
        }

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate status values
        valid_statuses = {"pending", "in_progress", "complete", "failed"}
        if data["status"] not in valid_statuses:
            raise ValueError(
                f"Invalid status '{data['status']}'. "
                f"Must be one of: {', '.join(sorted(valid_statuses))}"
            )

    def get_key(self) -> str:
        return "erk-implementation-status"


@dataclass(frozen=True)
class WorktreeCreationSchema(MetadataBlockSchema):
    """Schema for erk-worktree-creation blocks."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate erk-worktree-creation data structure."""
        required_fields = {"worktree_name", "branch_name", "timestamp"}
        optional_fields = {"issue_number", "plan_file"}

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate required string fields
        for field in required_fields:
            if not isinstance(data[field], str):
                raise ValueError(f"{field} must be a string")
            if len(data[field]) == 0:
                raise ValueError(f"{field} must not be empty")

        # Validate optional issue_number field
        if "issue_number" in data:
            if not isinstance(data["issue_number"], int):
                raise ValueError("issue_number must be an integer")
            if data["issue_number"] <= 0:
                raise ValueError("issue_number must be positive")

        # Validate optional plan_file field
        if "plan_file" in data:
            if not isinstance(data["plan_file"], str):
                raise ValueError("plan_file must be a string")
            if len(data["plan_file"]) == 0:
                raise ValueError("plan_file must not be empty")

        # Check for unexpected fields
        known_fields = required_fields | optional_fields
        unknown_fields = set(data.keys()) - known_fields
        if unknown_fields:
            raise ValueError(f"Unknown fields: {', '.join(sorted(unknown_fields))}")

    def get_key(self) -> str:
        return "erk-worktree-creation"


@dataclass(frozen=True)
class PlanSchema(MetadataBlockSchema):
    """Schema for erk-plan blocks."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate erk-plan data structure."""
        required_fields = {"issue_number", "worktree_name", "timestamp"}
        optional_fields = {"plan_file"}

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate required fields
        if not isinstance(data["issue_number"], int):
            raise ValueError("issue_number must be an integer")
        if data["issue_number"] <= 0:
            raise ValueError("issue_number must be positive")

        if not isinstance(data["worktree_name"], str):
            raise ValueError("worktree_name must be a string")
        if len(data["worktree_name"]) == 0:
            raise ValueError("worktree_name must not be empty")

        if not isinstance(data["timestamp"], str):
            raise ValueError("timestamp must be a string")
        if len(data["timestamp"]) == 0:
            raise ValueError("timestamp must not be empty")

        # Validate optional plan_file field
        if "plan_file" in data:
            if not isinstance(data["plan_file"], str):
                raise ValueError("plan_file must be a string")
            if len(data["plan_file"]) == 0:
                raise ValueError("plan_file must not be empty")

        # Check for unexpected fields
        known_fields = required_fields | optional_fields
        unknown_fields = set(data.keys()) - known_fields
        if unknown_fields:
            raise ValueError(f"Unknown fields: {', '.join(sorted(unknown_fields))}")

    def get_key(self) -> str:
        return "erk-plan"


@dataclass(frozen=True)
class SubmissionQueuedSchema(MetadataBlockSchema):
    """Schema for submission-queued blocks (posted by erk plan submit)."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate submission-queued data structure."""
        required_fields = {
            "status",
            "queued_at",
            "submitted_by",
            "issue_number",
            "validation_results",
            "expected_workflow",
            "trigger_mechanism",
        }

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate status value
        if data["status"] != "queued":
            raise ValueError(f"Invalid status '{data['status']}'. Must be 'queued'")

        # Validate string fields
        if not isinstance(data["queued_at"], str):
            raise ValueError("queued_at must be a string")
        if len(data["queued_at"]) == 0:
            raise ValueError("queued_at must not be empty")

        if not isinstance(data["submitted_by"], str):
            raise ValueError("submitted_by must be a string")
        if len(data["submitted_by"]) == 0:
            raise ValueError("submitted_by must not be empty")

        if not isinstance(data["expected_workflow"], str):
            raise ValueError("expected_workflow must be a string")
        if len(data["expected_workflow"]) == 0:
            raise ValueError("expected_workflow must not be empty")

        if not isinstance(data["trigger_mechanism"], str):
            raise ValueError("trigger_mechanism must be a string")
        if len(data["trigger_mechanism"]) == 0:
            raise ValueError("trigger_mechanism must not be empty")

        # Validate issue_number
        if not isinstance(data["issue_number"], int):
            raise ValueError("issue_number must be an integer")
        if data["issue_number"] <= 0:
            raise ValueError("issue_number must be positive")

        # Validate validation_results is a dict
        if not isinstance(data["validation_results"], dict):
            raise ValueError("validation_results must be a dict")

    def get_key(self) -> str:
        return "submission-queued"


@dataclass(frozen=True)
class WorkflowStartedSchema(MetadataBlockSchema):
    """Schema for workflow-started blocks (posted by GitHub Actions)."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate workflow-started data structure."""
        required_fields = {
            "status",
            "started_at",
            "workflow_run_id",
            "workflow_run_url",
            "issue_number",
        }
        optional_fields = {"branch_name", "worktree_path"}

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate status value
        if data["status"] != "started":
            raise ValueError(f"Invalid status '{data['status']}'. Must be 'started'")

        # Validate string fields
        if not isinstance(data["started_at"], str):
            raise ValueError("started_at must be a string")
        if len(data["started_at"]) == 0:
            raise ValueError("started_at must not be empty")

        if not isinstance(data["workflow_run_id"], str):
            raise ValueError("workflow_run_id must be a string")
        if len(data["workflow_run_id"]) == 0:
            raise ValueError("workflow_run_id must not be empty")

        if not isinstance(data["workflow_run_url"], str):
            raise ValueError("workflow_run_url must be a string")
        if len(data["workflow_run_url"]) == 0:
            raise ValueError("workflow_run_url must not be empty")

        # Validate issue_number
        if not isinstance(data["issue_number"], int):
            raise ValueError("issue_number must be an integer")
        if data["issue_number"] <= 0:
            raise ValueError("issue_number must be positive")

        # Validate optional fields if present
        if "branch_name" in data:
            if not isinstance(data["branch_name"], str):
                raise ValueError("branch_name must be a string")
            if len(data["branch_name"]) == 0:
                raise ValueError("branch_name must not be empty")

        if "worktree_path" in data:
            if not isinstance(data["worktree_path"], str):
                raise ValueError("worktree_path must be a string")
            if len(data["worktree_path"]) == 0:
                raise ValueError("worktree_path must not be empty")

        # Check for unexpected fields
        known_fields = required_fields | optional_fields
        unknown_fields = set(data.keys()) - known_fields
        if unknown_fields:
            raise ValueError(f"Unknown fields: {', '.join(sorted(unknown_fields))}")

    def get_key(self) -> str:
        return "workflow-started"


@dataclass(frozen=True)
class PlanRetrySchema(MetadataBlockSchema):
    """Schema for plan-retry blocks (posted by erk plan retry)."""

    def validate(self, data: dict[str, Any]) -> None:
        """Validate plan-retry data structure."""
        required_fields = {
            "retry_timestamp",
            "triggered_by",
            "retry_count",
        }
        optional_fields = {"previous_retry_timestamp"}

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate string fields
        if not isinstance(data["retry_timestamp"], str):
            raise ValueError("retry_timestamp must be a string")
        if len(data["retry_timestamp"]) == 0:
            raise ValueError("retry_timestamp must not be empty")

        if not isinstance(data["triggered_by"], str):
            raise ValueError("triggered_by must be a string")
        if len(data["triggered_by"]) == 0:
            raise ValueError("triggered_by must not be empty")

        # Validate retry_count
        if not isinstance(data["retry_count"], int):
            raise ValueError("retry_count must be an integer")
        if data["retry_count"] < 1:
            raise ValueError("retry_count must be at least 1")

        # Validate optional fields
        if "previous_retry_timestamp" in data:
            if not isinstance(data["previous_retry_timestamp"], str):
                raise ValueError("previous_retry_timestamp must be a string")
            if len(data["previous_retry_timestamp"]) == 0:
                raise ValueError("previous_retry_timestamp must not be empty")

        # Check for unexpected fields
        known_fields = required_fields | optional_fields
        unknown_fields = set(data.keys()) - known_fields
        if unknown_fields:
            raise ValueError(f"Unknown fields: {', '.join(sorted(unknown_fields))}")

    def get_key(self) -> str:
        return "plan-retry"


@dataclass(frozen=True)
class PlanHeaderFields:
    """Field name constants for plan-header metadata blocks.

    Use these constants instead of hardcoded strings when accessing
    plan-header data dictionaries.
    """

    # Required fields
    SCHEMA_VERSION: str = "schema_version"
    CREATED_AT: str = "created_at"
    CREATED_BY: str = "created_by"

    # Optional fields
    WORKTREE_NAME: str = "worktree_name"
    PLAN_COMMENT_ID: str = "plan_comment_id"
    LAST_DISPATCHED_RUN_ID: str = "last_dispatched_run_id"
    LAST_DISPATCHED_NODE_ID: str = "last_dispatched_node_id"
    LAST_DISPATCHED_AT: str = "last_dispatched_at"
    LAST_LOCAL_IMPL_AT: str = "last_local_impl_at"
    LAST_LOCAL_IMPL_EVENT: str = "last_local_impl_event"
    LAST_LOCAL_IMPL_SESSION: str = "last_local_impl_session"
    LAST_LOCAL_IMPL_USER: str = "last_local_impl_user"
    LAST_REMOTE_IMPL_AT: str = "last_remote_impl_at"
    SOURCE_REPO: str = "source_repo"
    OBJECTIVE_ISSUE: str = "objective_issue"
    CREATED_FROM_SESSION: str = "created_from_session"
    LAST_LEARN_SESSION: str = "last_learn_session"
    LAST_LEARN_AT: str = "last_learn_at"


# Singleton instance for import
PLAN_HEADER_FIELDS = PlanHeaderFields()


@dataclass(frozen=True)
class PlanHeaderSchema(MetadataBlockSchema):
    """Schema for plan-header blocks.

    Fields:
        schema_version: Internal version identifier ("2")
        created_at: ISO 8601 timestamp of plan creation
        created_by: GitHub username of plan creator
        worktree_name: Set when worktree is created (nullable)
        plan_comment_id: GitHub comment ID containing the plan content (nullable)
        last_dispatched_run_id: Updated by workflow, enables direct run lookup (nullable)
        last_dispatched_at: Updated by workflow (nullable)
        last_local_impl_at: Updated by local implementation, tracks last event timestamp (nullable)
        last_local_impl_event: Event type - "started" or "ended" (nullable)
        last_local_impl_session: Claude Code session ID from environment (nullable)
        last_local_impl_user: User who ran the implementation (nullable)
        last_remote_impl_at: Updated by GitHub Actions, tracks last remote run (nullable)
        source_repo: For cross-repo plans, the repo where implementation happens (nullable)
        objective_issue: Parent objective issue number (nullable)
        created_from_session: Session ID that created this plan (nullable)
        last_learn_session: Session ID that last invoked learn (nullable)
        last_learn_at: ISO 8601 timestamp of last learn invocation (nullable)
    """

    def validate(self, data: dict[str, Any]) -> None:
        """Validate plan-header data structure."""
        f = PLAN_HEADER_FIELDS
        required_fields = {
            f.SCHEMA_VERSION,
            f.CREATED_AT,
            f.CREATED_BY,
        }
        optional_fields = {
            f.WORKTREE_NAME,
            f.PLAN_COMMENT_ID,
            f.LAST_DISPATCHED_RUN_ID,
            f.LAST_DISPATCHED_NODE_ID,
            f.LAST_DISPATCHED_AT,
            f.LAST_LOCAL_IMPL_AT,
            f.LAST_LOCAL_IMPL_EVENT,
            f.LAST_LOCAL_IMPL_SESSION,
            f.LAST_LOCAL_IMPL_USER,
            f.LAST_REMOTE_IMPL_AT,
            f.SOURCE_REPO,
            f.OBJECTIVE_ISSUE,
            f.CREATED_FROM_SESSION,
            f.LAST_LEARN_SESSION,
            f.LAST_LEARN_AT,
        }

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate schema_version
        if data[f.SCHEMA_VERSION] != "2":
            raise ValueError(f"Invalid schema_version '{data[f.SCHEMA_VERSION]}'. Must be '2'")

        # Validate required string fields
        for field in [f.CREATED_AT, f.CREATED_BY]:
            if not isinstance(data[field], str):
                raise ValueError(f"{field} must be a string")
            if len(data[field]) == 0:
                raise ValueError(f"{field} must not be empty")

        # Validate optional worktree_name field
        if f.WORKTREE_NAME in data and data[f.WORKTREE_NAME] is not None:
            if not isinstance(data[f.WORKTREE_NAME], str):
                raise ValueError("worktree_name must be a string or null")
            if len(data[f.WORKTREE_NAME]) == 0:
                raise ValueError("worktree_name must not be empty when provided")

        # Validate optional plan_comment_id field
        if f.PLAN_COMMENT_ID in data and data[f.PLAN_COMMENT_ID] is not None:
            if not isinstance(data[f.PLAN_COMMENT_ID], int):
                raise ValueError("plan_comment_id must be an integer or null")
            if data[f.PLAN_COMMENT_ID] <= 0:
                raise ValueError("plan_comment_id must be positive when provided")

        # Validate optional fields if present
        if f.LAST_DISPATCHED_RUN_ID in data:
            if data[f.LAST_DISPATCHED_RUN_ID] is not None:
                if not isinstance(data[f.LAST_DISPATCHED_RUN_ID], str):
                    raise ValueError("last_dispatched_run_id must be a string or null")

        if f.LAST_DISPATCHED_NODE_ID in data:
            if data[f.LAST_DISPATCHED_NODE_ID] is not None:
                if not isinstance(data[f.LAST_DISPATCHED_NODE_ID], str):
                    raise ValueError("last_dispatched_node_id must be a string or null")

        if f.LAST_DISPATCHED_AT in data:
            if data[f.LAST_DISPATCHED_AT] is not None:
                if not isinstance(data[f.LAST_DISPATCHED_AT], str):
                    raise ValueError("last_dispatched_at must be a string or null")

        if f.LAST_LOCAL_IMPL_AT in data:
            if data[f.LAST_LOCAL_IMPL_AT] is not None:
                if not isinstance(data[f.LAST_LOCAL_IMPL_AT], str):
                    raise ValueError("last_local_impl_at must be a string or null")

        if f.LAST_REMOTE_IMPL_AT in data:
            if data[f.LAST_REMOTE_IMPL_AT] is not None:
                if not isinstance(data[f.LAST_REMOTE_IMPL_AT], str):
                    raise ValueError("last_remote_impl_at must be a string or null")

        # Validate last_local_impl_event
        if f.LAST_LOCAL_IMPL_EVENT in data:
            if data[f.LAST_LOCAL_IMPL_EVENT] is not None:
                if not isinstance(data[f.LAST_LOCAL_IMPL_EVENT], str):
                    raise ValueError("last_local_impl_event must be a string or null")
                valid_events = {"started", "ended"}
                if data[f.LAST_LOCAL_IMPL_EVENT] not in valid_events:
                    event_value = data[f.LAST_LOCAL_IMPL_EVENT]
                    raise ValueError(
                        f"last_local_impl_event must be 'started' or 'ended', got '{event_value}'"
                    )

        # Validate last_local_impl_session
        if f.LAST_LOCAL_IMPL_SESSION in data:
            if data[f.LAST_LOCAL_IMPL_SESSION] is not None:
                if not isinstance(data[f.LAST_LOCAL_IMPL_SESSION], str):
                    raise ValueError("last_local_impl_session must be a string or null")

        # Validate last_local_impl_user
        if f.LAST_LOCAL_IMPL_USER in data:
            if data[f.LAST_LOCAL_IMPL_USER] is not None:
                if not isinstance(data[f.LAST_LOCAL_IMPL_USER], str):
                    raise ValueError("last_local_impl_user must be a string or null")

        # Validate source_repo field - must be "owner/repo" format if present
        if f.SOURCE_REPO in data and data[f.SOURCE_REPO] is not None:
            if not isinstance(data[f.SOURCE_REPO], str):
                raise ValueError("source_repo must be a string or null")
            if len(data[f.SOURCE_REPO]) == 0:
                raise ValueError("source_repo must not be empty when provided")
            # Validate owner/repo format
            if "/" not in data[f.SOURCE_REPO]:
                raise ValueError("source_repo must be in 'owner/repo' format")

        # Validate optional objective_issue field
        if f.OBJECTIVE_ISSUE in data and data[f.OBJECTIVE_ISSUE] is not None:
            if not isinstance(data[f.OBJECTIVE_ISSUE], int):
                raise ValueError("objective_issue must be an integer or null")
            if data[f.OBJECTIVE_ISSUE] <= 0:
                raise ValueError("objective_issue must be positive when provided")

        # Validate optional created_from_session field
        if f.CREATED_FROM_SESSION in data and data[f.CREATED_FROM_SESSION] is not None:
            if not isinstance(data[f.CREATED_FROM_SESSION], str):
                raise ValueError("created_from_session must be a string or null")
            if len(data[f.CREATED_FROM_SESSION]) == 0:
                raise ValueError("created_from_session must not be empty when provided")

        # Validate optional last_learn_session field
        if f.LAST_LEARN_SESSION in data and data[f.LAST_LEARN_SESSION] is not None:
            if not isinstance(data[f.LAST_LEARN_SESSION], str):
                raise ValueError("last_learn_session must be a string or null")
            if len(data[f.LAST_LEARN_SESSION]) == 0:
                raise ValueError("last_learn_session must not be empty when provided")

        # Validate optional last_learn_at field
        if f.LAST_LEARN_AT in data and data[f.LAST_LEARN_AT] is not None:
            if not isinstance(data[f.LAST_LEARN_AT], str):
                raise ValueError("last_learn_at must be a string or null")
            if len(data[f.LAST_LEARN_AT]) == 0:
                raise ValueError("last_learn_at must not be empty when provided")

        # Check for unexpected fields
        known_fields = required_fields | optional_fields
        unknown_fields = set(data.keys()) - known_fields
        if unknown_fields:
            raise ValueError(f"Unknown fields: {', '.join(sorted(unknown_fields))}")

    def get_key(self) -> str:
        return "plan-header"


# Backward compatibility alias
PlanIssueSchema = PlanSchema
