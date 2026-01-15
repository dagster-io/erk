"""Schema implementations for metadata blocks."""

from dataclasses import dataclass
from typing import Any, Literal

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


# Plan-header field name constants with Literal types
# Use these constants instead of hardcoded strings when accessing plan-header data dictionaries.

PlanHeaderFieldName = Literal[
    "schema_version",
    "created_at",
    "created_by",
    "worktree_name",
    "plan_comment_id",
    "last_dispatched_run_id",
    "last_dispatched_node_id",
    "last_dispatched_at",
    "last_local_impl_at",
    "last_local_impl_event",
    "last_local_impl_session",
    "last_local_impl_user",
    "last_remote_impl_at",
    "source_repo",
    "objective_issue",
    "created_from_session",
    "last_learn_session",
    "last_learn_at",
]
"""Union type of all valid plan-header field names."""

# Required fields
SCHEMA_VERSION: Literal["schema_version"] = "schema_version"
CREATED_AT: Literal["created_at"] = "created_at"
CREATED_BY: Literal["created_by"] = "created_by"

# Optional fields
WORKTREE_NAME: Literal["worktree_name"] = "worktree_name"
PLAN_COMMENT_ID: Literal["plan_comment_id"] = "plan_comment_id"
LAST_DISPATCHED_RUN_ID: Literal["last_dispatched_run_id"] = "last_dispatched_run_id"
LAST_DISPATCHED_NODE_ID: Literal["last_dispatched_node_id"] = "last_dispatched_node_id"
LAST_DISPATCHED_AT: Literal["last_dispatched_at"] = "last_dispatched_at"
LAST_LOCAL_IMPL_AT: Literal["last_local_impl_at"] = "last_local_impl_at"
LAST_LOCAL_IMPL_EVENT: Literal["last_local_impl_event"] = "last_local_impl_event"
LAST_LOCAL_IMPL_SESSION: Literal["last_local_impl_session"] = "last_local_impl_session"
LAST_LOCAL_IMPL_USER: Literal["last_local_impl_user"] = "last_local_impl_user"
LAST_REMOTE_IMPL_AT: Literal["last_remote_impl_at"] = "last_remote_impl_at"
SOURCE_REPO: Literal["source_repo"] = "source_repo"
OBJECTIVE_ISSUE: Literal["objective_issue"] = "objective_issue"
CREATED_FROM_SESSION: Literal["created_from_session"] = "created_from_session"
LAST_LEARN_SESSION: Literal["last_learn_session"] = "last_learn_session"
LAST_LEARN_AT: Literal["last_learn_at"] = "last_learn_at"


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
        required_fields = {
            SCHEMA_VERSION,
            CREATED_AT,
            CREATED_BY,
        }
        optional_fields = {
            WORKTREE_NAME,
            PLAN_COMMENT_ID,
            LAST_DISPATCHED_RUN_ID,
            LAST_DISPATCHED_NODE_ID,
            LAST_DISPATCHED_AT,
            LAST_LOCAL_IMPL_AT,
            LAST_LOCAL_IMPL_EVENT,
            LAST_LOCAL_IMPL_SESSION,
            LAST_LOCAL_IMPL_USER,
            LAST_REMOTE_IMPL_AT,
            SOURCE_REPO,
            OBJECTIVE_ISSUE,
            CREATED_FROM_SESSION,
            LAST_LEARN_SESSION,
            LAST_LEARN_AT,
        }

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate schema_version
        if data[SCHEMA_VERSION] != "2":
            raise ValueError(f"Invalid schema_version '{data[SCHEMA_VERSION]}'. Must be '2'")

        # Validate required string fields
        for field in [CREATED_AT, CREATED_BY]:
            if not isinstance(data[field], str):
                raise ValueError(f"{field} must be a string")
            if len(data[field]) == 0:
                raise ValueError(f"{field} must not be empty")

        # Validate optional worktree_name field
        if WORKTREE_NAME in data and data[WORKTREE_NAME] is not None:
            if not isinstance(data[WORKTREE_NAME], str):
                raise ValueError("worktree_name must be a string or null")
            if len(data[WORKTREE_NAME]) == 0:
                raise ValueError("worktree_name must not be empty when provided")

        # Validate optional plan_comment_id field
        if PLAN_COMMENT_ID in data and data[PLAN_COMMENT_ID] is not None:
            if not isinstance(data[PLAN_COMMENT_ID], int):
                raise ValueError("plan_comment_id must be an integer or null")
            if data[PLAN_COMMENT_ID] <= 0:
                raise ValueError("plan_comment_id must be positive when provided")

        # Validate optional fields if present
        if LAST_DISPATCHED_RUN_ID in data:
            if data[LAST_DISPATCHED_RUN_ID] is not None:
                if not isinstance(data[LAST_DISPATCHED_RUN_ID], str):
                    raise ValueError("last_dispatched_run_id must be a string or null")

        if LAST_DISPATCHED_NODE_ID in data:
            if data[LAST_DISPATCHED_NODE_ID] is not None:
                if not isinstance(data[LAST_DISPATCHED_NODE_ID], str):
                    raise ValueError("last_dispatched_node_id must be a string or null")

        if LAST_DISPATCHED_AT in data:
            if data[LAST_DISPATCHED_AT] is not None:
                if not isinstance(data[LAST_DISPATCHED_AT], str):
                    raise ValueError("last_dispatched_at must be a string or null")

        if LAST_LOCAL_IMPL_AT in data:
            if data[LAST_LOCAL_IMPL_AT] is not None:
                if not isinstance(data[LAST_LOCAL_IMPL_AT], str):
                    raise ValueError("last_local_impl_at must be a string or null")

        if LAST_REMOTE_IMPL_AT in data:
            if data[LAST_REMOTE_IMPL_AT] is not None:
                if not isinstance(data[LAST_REMOTE_IMPL_AT], str):
                    raise ValueError("last_remote_impl_at must be a string or null")

        # Validate last_local_impl_event
        if LAST_LOCAL_IMPL_EVENT in data:
            if data[LAST_LOCAL_IMPL_EVENT] is not None:
                if not isinstance(data[LAST_LOCAL_IMPL_EVENT], str):
                    raise ValueError("last_local_impl_event must be a string or null")
                valid_events = {"started", "ended"}
                if data[LAST_LOCAL_IMPL_EVENT] not in valid_events:
                    event_value = data[LAST_LOCAL_IMPL_EVENT]
                    raise ValueError(
                        f"last_local_impl_event must be 'started' or 'ended', got '{event_value}'"
                    )

        # Validate last_local_impl_session
        if LAST_LOCAL_IMPL_SESSION in data:
            if data[LAST_LOCAL_IMPL_SESSION] is not None:
                if not isinstance(data[LAST_LOCAL_IMPL_SESSION], str):
                    raise ValueError("last_local_impl_session must be a string or null")

        # Validate last_local_impl_user
        if LAST_LOCAL_IMPL_USER in data:
            if data[LAST_LOCAL_IMPL_USER] is not None:
                if not isinstance(data[LAST_LOCAL_IMPL_USER], str):
                    raise ValueError("last_local_impl_user must be a string or null")

        # Validate source_repo field - must be "owner/repo" format if present
        if SOURCE_REPO in data and data[SOURCE_REPO] is not None:
            if not isinstance(data[SOURCE_REPO], str):
                raise ValueError("source_repo must be a string or null")
            if len(data[SOURCE_REPO]) == 0:
                raise ValueError("source_repo must not be empty when provided")
            # Validate owner/repo format
            if "/" not in data[SOURCE_REPO]:
                raise ValueError("source_repo must be in 'owner/repo' format")

        # Validate optional objective_issue field
        if OBJECTIVE_ISSUE in data and data[OBJECTIVE_ISSUE] is not None:
            if not isinstance(data[OBJECTIVE_ISSUE], int):
                raise ValueError("objective_issue must be an integer or null")
            if data[OBJECTIVE_ISSUE] <= 0:
                raise ValueError("objective_issue must be positive when provided")

        # Validate optional created_from_session field
        if CREATED_FROM_SESSION in data and data[CREATED_FROM_SESSION] is not None:
            if not isinstance(data[CREATED_FROM_SESSION], str):
                raise ValueError("created_from_session must be a string or null")
            if len(data[CREATED_FROM_SESSION]) == 0:
                raise ValueError("created_from_session must not be empty when provided")

        # Validate optional last_learn_session field
        if LAST_LEARN_SESSION in data and data[LAST_LEARN_SESSION] is not None:
            if not isinstance(data[LAST_LEARN_SESSION], str):
                raise ValueError("last_learn_session must be a string or null")
            if len(data[LAST_LEARN_SESSION]) == 0:
                raise ValueError("last_learn_session must not be empty when provided")

        # Validate optional last_learn_at field
        if LAST_LEARN_AT in data and data[LAST_LEARN_AT] is not None:
            if not isinstance(data[LAST_LEARN_AT], str):
                raise ValueError("last_learn_at must be a string or null")
            if len(data[LAST_LEARN_AT]) == 0:
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
