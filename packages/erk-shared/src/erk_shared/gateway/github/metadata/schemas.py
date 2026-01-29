"""Schema implementations for metadata blocks."""

from dataclasses import dataclass
from typing import Any, Literal

from erk_shared.gateway.github.metadata.types import MetadataBlockSchema


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
    "branch_name",
    "plan_comment_id",
    "last_dispatched_run_id",
    "last_dispatched_node_id",
    "last_dispatched_at",
    "last_local_impl_at",
    "last_local_impl_event",
    "last_local_impl_session",
    "last_local_impl_user",
    "last_remote_impl_at",
    "last_remote_impl_run_id",
    "last_remote_impl_session_id",
    "source_repo",
    "objective_issue",
    "created_from_session",
    "created_from_workflow_run_url",
    "last_learn_session",
    "last_learn_at",
    "learn_status",
    "learn_run_id",
    "last_session_gist_url",
    "last_session_gist_id",
    "last_session_id",
    "last_session_at",
    "last_session_source",
    "learn_plan_issue",
    "learn_plan_pr",
    "learned_from_issue",
    "review_pr",
    "last_review_pr",
]
"""Union type of all valid plan-header field names."""

# Required fields
SCHEMA_VERSION: Literal["schema_version"] = "schema_version"
CREATED_AT: Literal["created_at"] = "created_at"
CREATED_BY: Literal["created_by"] = "created_by"

# Optional fields
WORKTREE_NAME: Literal["worktree_name"] = "worktree_name"
BRANCH_NAME: Literal["branch_name"] = "branch_name"
PLAN_COMMENT_ID: Literal["plan_comment_id"] = "plan_comment_id"
LAST_DISPATCHED_RUN_ID: Literal["last_dispatched_run_id"] = "last_dispatched_run_id"
LAST_DISPATCHED_NODE_ID: Literal["last_dispatched_node_id"] = "last_dispatched_node_id"
LAST_DISPATCHED_AT: Literal["last_dispatched_at"] = "last_dispatched_at"
LAST_LOCAL_IMPL_AT: Literal["last_local_impl_at"] = "last_local_impl_at"
LAST_LOCAL_IMPL_EVENT: Literal["last_local_impl_event"] = "last_local_impl_event"
LAST_LOCAL_IMPL_SESSION: Literal["last_local_impl_session"] = "last_local_impl_session"
LAST_LOCAL_IMPL_USER: Literal["last_local_impl_user"] = "last_local_impl_user"
LAST_REMOTE_IMPL_AT: Literal["last_remote_impl_at"] = "last_remote_impl_at"
LAST_REMOTE_IMPL_RUN_ID: Literal["last_remote_impl_run_id"] = "last_remote_impl_run_id"
LAST_REMOTE_IMPL_SESSION_ID: Literal["last_remote_impl_session_id"] = "last_remote_impl_session_id"
SOURCE_REPO: Literal["source_repo"] = "source_repo"
OBJECTIVE_ISSUE: Literal["objective_issue"] = "objective_issue"
CREATED_FROM_SESSION: Literal["created_from_session"] = "created_from_session"
CREATED_FROM_WORKFLOW_RUN_URL: Literal["created_from_workflow_run_url"] = (
    "created_from_workflow_run_url"
)
LAST_LEARN_SESSION: Literal["last_learn_session"] = "last_learn_session"
LAST_LEARN_AT: Literal["last_learn_at"] = "last_learn_at"
LEARN_STATUS: Literal["learn_status"] = "learn_status"
LEARN_RUN_ID: Literal["learn_run_id"] = "learn_run_id"

# Session gist fields (unified for local and remote)
LAST_SESSION_GIST_URL: Literal["last_session_gist_url"] = "last_session_gist_url"
LAST_SESSION_GIST_ID: Literal["last_session_gist_id"] = "last_session_gist_id"
LAST_SESSION_ID: Literal["last_session_id"] = "last_session_id"
LAST_SESSION_AT: Literal["last_session_at"] = "last_session_at"
LAST_SESSION_SOURCE: Literal["last_session_source"] = "last_session_source"

# Learn plan tracking fields
LEARN_PLAN_ISSUE: Literal["learn_plan_issue"] = "learn_plan_issue"
LEARN_PLAN_PR: Literal["learn_plan_pr"] = "learn_plan_pr"
LEARNED_FROM_ISSUE: Literal["learned_from_issue"] = "learned_from_issue"

# Review PR tracking fields
REVIEW_PR: Literal["review_pr"] = "review_pr"
LAST_REVIEW_PR: Literal["last_review_pr"] = "last_review_pr"

# Valid values for learn_status field
LearnStatusValue = Literal[
    "not_started",
    "pending",
    "completed_no_plan",
    "completed_with_plan",
    "pending_review",
    "plan_completed",
]
"""Valid values for the learn_status plan header field.

Status progression:
- not_started: No learn workflow has been run yet
- pending: Learn workflow is in progress
- completed_no_plan: Learn completed, no plan was needed/created
- completed_with_plan: Learn completed and created a plan issue
- pending_review: Documentation PR created directly, awaiting review
- plan_completed: The learn plan was implemented and landed
"""

# Valid values for last_session_source field
SessionSourceValue = Literal["local", "remote"]
"""Valid values for the last_session_source plan header field."""


@dataclass(frozen=True)
class PlanHeaderSchema(MetadataBlockSchema):
    """Schema for plan-header blocks.

    Fields:
        schema_version: Internal version identifier ("2")
        created_at: ISO 8601 timestamp of plan creation
        created_by: GitHub username of plan creator
        worktree_name: Set when worktree is created (nullable)
        branch_name: Git branch name for this plan (nullable)
        plan_comment_id: GitHub comment ID containing the plan content (nullable)
        last_dispatched_run_id: Updated by workflow, enables direct run lookup (nullable)
        last_dispatched_at: Updated by workflow (nullable)
        last_local_impl_at: Updated by local implementation, tracks last event timestamp (nullable)
        last_local_impl_event: Event type - "started" or "ended" (nullable)
        last_local_impl_session: Claude Code session ID from environment (nullable)
        last_local_impl_user: User who ran the implementation (nullable)
        last_remote_impl_at: Updated by GitHub Actions, tracks last remote run (nullable)
        last_remote_impl_run_id: GitHub Actions run ID for remote implementation (nullable)
        last_remote_impl_session_id: Claude Code session ID for remote implementation (nullable)
        source_repo: For cross-repo plans, the repo where implementation happens (nullable)
        objective_issue: Parent objective issue number (nullable)
        created_from_session: Session ID that created this plan (nullable)
        created_from_workflow_run_url: Workflow run URL that created this plan (nullable)
        last_learn_session: Session ID that last invoked learn (nullable)
        last_learn_at: ISO 8601 timestamp of last learn invocation (nullable)
        learn_status: Learning workflow status (nullable)
        learn_plan_issue: Issue number of generated learn plan (nullable)
        learn_plan_pr: PR number that implemented the learn plan (nullable)
        learned_from_issue: Parent plan issue number (for learn plans only) (nullable)
        last_session_gist_url: URL of gist containing session JSONL (nullable)
        last_session_gist_id: ID of gist containing session JSONL (nullable)
        last_session_id: Claude Code session ID of uploaded session (nullable)
        last_session_at: ISO 8601 timestamp of session upload (nullable)
        last_session_source: "local" or "remote" indicating session origin (nullable)
        review_pr: PR number for plan review (nullable)
        last_review_pr: PR number of the last completed review (nullable)
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
            BRANCH_NAME,
            PLAN_COMMENT_ID,
            LAST_DISPATCHED_RUN_ID,
            LAST_DISPATCHED_NODE_ID,
            LAST_DISPATCHED_AT,
            LAST_LOCAL_IMPL_AT,
            LAST_LOCAL_IMPL_EVENT,
            LAST_LOCAL_IMPL_SESSION,
            LAST_LOCAL_IMPL_USER,
            LAST_REMOTE_IMPL_AT,
            LAST_REMOTE_IMPL_RUN_ID,
            LAST_REMOTE_IMPL_SESSION_ID,
            SOURCE_REPO,
            OBJECTIVE_ISSUE,
            CREATED_FROM_SESSION,
            CREATED_FROM_WORKFLOW_RUN_URL,
            LAST_LEARN_SESSION,
            LAST_LEARN_AT,
            LEARN_STATUS,
            LEARN_RUN_ID,
            LAST_SESSION_GIST_URL,
            LAST_SESSION_GIST_ID,
            LAST_SESSION_ID,
            LAST_SESSION_AT,
            LAST_SESSION_SOURCE,
            LEARN_PLAN_ISSUE,
            LEARN_PLAN_PR,
            LEARNED_FROM_ISSUE,
            REVIEW_PR,
            LAST_REVIEW_PR,
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

        # Validate optional branch_name field
        if BRANCH_NAME in data and data[BRANCH_NAME] is not None:
            if not isinstance(data[BRANCH_NAME], str):
                raise ValueError("branch_name must be a string or null")
            if len(data[BRANCH_NAME]) == 0:
                raise ValueError("branch_name must not be empty when provided")

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

        # Validate last_remote_impl_run_id
        if LAST_REMOTE_IMPL_RUN_ID in data:
            if data[LAST_REMOTE_IMPL_RUN_ID] is not None:
                if not isinstance(data[LAST_REMOTE_IMPL_RUN_ID], str):
                    raise ValueError("last_remote_impl_run_id must be a string or null")

        # Validate last_remote_impl_session_id
        if LAST_REMOTE_IMPL_SESSION_ID in data:
            if data[LAST_REMOTE_IMPL_SESSION_ID] is not None:
                if not isinstance(data[LAST_REMOTE_IMPL_SESSION_ID], str):
                    raise ValueError("last_remote_impl_session_id must be a string or null")

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

        # Validate optional created_from_workflow_run_url field
        if (
            CREATED_FROM_WORKFLOW_RUN_URL in data
            and data[CREATED_FROM_WORKFLOW_RUN_URL] is not None
        ):
            if not isinstance(data[CREATED_FROM_WORKFLOW_RUN_URL], str):
                raise ValueError("created_from_workflow_run_url must be a string or null")
            if len(data[CREATED_FROM_WORKFLOW_RUN_URL]) == 0:
                raise ValueError("created_from_workflow_run_url must not be empty when provided")

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

        # Validate optional learn_status field
        if LEARN_STATUS in data and data[LEARN_STATUS] is not None:
            if not isinstance(data[LEARN_STATUS], str):
                raise ValueError("learn_status must be a string or null")
            valid_statuses = {
                "not_started",
                "pending",
                "completed_no_plan",
                "completed_with_plan",
                "pending_review",
                "plan_completed",
            }
            if data[LEARN_STATUS] not in valid_statuses:
                status_value = data[LEARN_STATUS]
                valid_list = ", ".join(sorted(valid_statuses))
                raise ValueError(f"learn_status must be one of: {valid_list}. Got '{status_value}'")

        # Validate optional learn_run_id field
        if LEARN_RUN_ID in data and data[LEARN_RUN_ID] is not None:
            if not isinstance(data[LEARN_RUN_ID], str):
                raise ValueError("learn_run_id must be a string or null")
            if len(data[LEARN_RUN_ID]) == 0:
                raise ValueError("learn_run_id must not be empty when provided")

        # Validate optional last_session_gist_url field
        if LAST_SESSION_GIST_URL in data and data[LAST_SESSION_GIST_URL] is not None:
            if not isinstance(data[LAST_SESSION_GIST_URL], str):
                raise ValueError("last_session_gist_url must be a string or null")
            if len(data[LAST_SESSION_GIST_URL]) == 0:
                raise ValueError("last_session_gist_url must not be empty when provided")

        # Validate optional last_session_gist_id field
        if LAST_SESSION_GIST_ID in data and data[LAST_SESSION_GIST_ID] is not None:
            if not isinstance(data[LAST_SESSION_GIST_ID], str):
                raise ValueError("last_session_gist_id must be a string or null")
            if len(data[LAST_SESSION_GIST_ID]) == 0:
                raise ValueError("last_session_gist_id must not be empty when provided")

        # Validate optional last_session_id field
        if LAST_SESSION_ID in data and data[LAST_SESSION_ID] is not None:
            if not isinstance(data[LAST_SESSION_ID], str):
                raise ValueError("last_session_id must be a string or null")
            if len(data[LAST_SESSION_ID]) == 0:
                raise ValueError("last_session_id must not be empty when provided")

        # Validate optional last_session_at field
        if LAST_SESSION_AT in data and data[LAST_SESSION_AT] is not None:
            if not isinstance(data[LAST_SESSION_AT], str):
                raise ValueError("last_session_at must be a string or null")
            if len(data[LAST_SESSION_AT]) == 0:
                raise ValueError("last_session_at must not be empty when provided")

        # Validate optional last_session_source field
        if LAST_SESSION_SOURCE in data and data[LAST_SESSION_SOURCE] is not None:
            if not isinstance(data[LAST_SESSION_SOURCE], str):
                raise ValueError("last_session_source must be a string or null")
            valid_sources = {"local", "remote"}
            if data[LAST_SESSION_SOURCE] not in valid_sources:
                source_value = data[LAST_SESSION_SOURCE]
                raise ValueError(
                    f"last_session_source must be 'local' or 'remote', got '{source_value}'"
                )

        # Validate optional learn_plan_issue field
        if LEARN_PLAN_ISSUE in data and data[LEARN_PLAN_ISSUE] is not None:
            if not isinstance(data[LEARN_PLAN_ISSUE], int):
                raise ValueError("learn_plan_issue must be an integer or null")
            if data[LEARN_PLAN_ISSUE] <= 0:
                raise ValueError("learn_plan_issue must be positive when provided")

        # Validate optional learn_plan_pr field
        if LEARN_PLAN_PR in data and data[LEARN_PLAN_PR] is not None:
            if not isinstance(data[LEARN_PLAN_PR], int):
                raise ValueError("learn_plan_pr must be an integer or null")
            if data[LEARN_PLAN_PR] <= 0:
                raise ValueError("learn_plan_pr must be positive when provided")

        # Validate optional learned_from_issue field
        if LEARNED_FROM_ISSUE in data and data[LEARNED_FROM_ISSUE] is not None:
            if not isinstance(data[LEARNED_FROM_ISSUE], int):
                raise ValueError("learned_from_issue must be an integer or null")
            if data[LEARNED_FROM_ISSUE] <= 0:
                raise ValueError("learned_from_issue must be positive when provided")

        # Validate optional review_pr field
        if REVIEW_PR in data and data[REVIEW_PR] is not None:
            if not isinstance(data[REVIEW_PR], int):
                raise ValueError("review_pr must be an integer or null")
            if data[REVIEW_PR] <= 0:
                raise ValueError("review_pr must be positive when provided")

        # Validate optional last_review_pr field
        if LAST_REVIEW_PR in data and data[LAST_REVIEW_PR] is not None:
            if not isinstance(data[LAST_REVIEW_PR], int):
                raise ValueError("last_review_pr must be an integer or null")
            if data[LAST_REVIEW_PR] <= 0:
                raise ValueError("last_review_pr must be positive when provided")

        # Check for unexpected fields
        known_fields = required_fields | optional_fields
        unknown_fields = set(data.keys()) - known_fields
        if unknown_fields:
            raise ValueError(f"Unknown fields: {', '.join(sorted(unknown_fields))}")

    def get_key(self) -> str:
        return "plan-header"


# Backward compatibility alias
PlanIssueSchema = PlanSchema
