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
        plan_type: Type discriminator - "standard" or "extraction"
        source_plan_issues: For extraction plans, list of issue numbers analyzed
        extraction_session_ids: For extraction plans, list of session IDs analyzed
        source_repo: For cross-repo plans, the repo where implementation happens (nullable)
        objective_issue: Parent objective issue number (nullable)
        created_from_session: Session ID that created this plan (nullable)
    """

    def validate(self, data: dict[str, Any]) -> None:
        """Validate plan-header data structure."""
        required_fields = {
            "schema_version",
            "created_at",
            "created_by",
        }
        optional_fields = {
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
            "plan_type",
            "source_plan_issues",
            "extraction_session_ids",
            "source_repo",
            "objective_issue",
            "created_from_session",
        }

        # Check required fields exist
        missing = required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

        # Validate schema_version
        if data["schema_version"] != "2":
            raise ValueError(f"Invalid schema_version '{data['schema_version']}'. Must be '2'")

        # Validate required string fields
        for field in ["created_at", "created_by"]:
            if not isinstance(data[field], str):
                raise ValueError(f"{field} must be a string")
            if len(data[field]) == 0:
                raise ValueError(f"{field} must not be empty")

        # Validate optional worktree_name field
        if "worktree_name" in data and data["worktree_name"] is not None:
            if not isinstance(data["worktree_name"], str):
                raise ValueError("worktree_name must be a string or null")
            if len(data["worktree_name"]) == 0:
                raise ValueError("worktree_name must not be empty when provided")

        # Validate optional plan_comment_id field
        if "plan_comment_id" in data and data["plan_comment_id"] is not None:
            if not isinstance(data["plan_comment_id"], int):
                raise ValueError("plan_comment_id must be an integer or null")
            if data["plan_comment_id"] <= 0:
                raise ValueError("plan_comment_id must be positive when provided")

        # Validate optional fields if present
        if "last_dispatched_run_id" in data:
            if data["last_dispatched_run_id"] is not None:
                if not isinstance(data["last_dispatched_run_id"], str):
                    raise ValueError("last_dispatched_run_id must be a string or null")

        if "last_dispatched_node_id" in data:
            if data["last_dispatched_node_id"] is not None:
                if not isinstance(data["last_dispatched_node_id"], str):
                    raise ValueError("last_dispatched_node_id must be a string or null")

        if "last_dispatched_at" in data:
            if data["last_dispatched_at"] is not None:
                if not isinstance(data["last_dispatched_at"], str):
                    raise ValueError("last_dispatched_at must be a string or null")

        if "last_local_impl_at" in data:
            if data["last_local_impl_at"] is not None:
                if not isinstance(data["last_local_impl_at"], str):
                    raise ValueError("last_local_impl_at must be a string or null")

        if "last_remote_impl_at" in data:
            if data["last_remote_impl_at"] is not None:
                if not isinstance(data["last_remote_impl_at"], str):
                    raise ValueError("last_remote_impl_at must be a string or null")

        # Validate last_local_impl_event
        if "last_local_impl_event" in data:
            if data["last_local_impl_event"] is not None:
                if not isinstance(data["last_local_impl_event"], str):
                    raise ValueError("last_local_impl_event must be a string or null")
                valid_events = {"started", "ended"}
                if data["last_local_impl_event"] not in valid_events:
                    event_value = data["last_local_impl_event"]
                    raise ValueError(
                        f"last_local_impl_event must be 'started' or 'ended', got '{event_value}'"
                    )

        # Validate last_local_impl_session
        if "last_local_impl_session" in data:
            if data["last_local_impl_session"] is not None:
                if not isinstance(data["last_local_impl_session"], str):
                    raise ValueError("last_local_impl_session must be a string or null")

        # Validate last_local_impl_user
        if "last_local_impl_user" in data:
            if data["last_local_impl_user"] is not None:
                if not isinstance(data["last_local_impl_user"], str):
                    raise ValueError("last_local_impl_user must be a string or null")

        # Validate plan_type field
        valid_plan_types = {"standard", "extraction"}
        if "plan_type" in data and data["plan_type"] is not None:
            if not isinstance(data["plan_type"], str):
                raise ValueError("plan_type must be a string or null")
            if data["plan_type"] not in valid_plan_types:
                raise ValueError(
                    f"Invalid plan_type '{data['plan_type']}'. "
                    f"Must be one of: {', '.join(sorted(valid_plan_types))}"
                )

        # Validate extraction mixin fields
        if "source_plan_issues" in data and data["source_plan_issues"] is not None:
            if not isinstance(data["source_plan_issues"], list):
                raise ValueError("source_plan_issues must be a list or null")
            for item in data["source_plan_issues"]:
                if not isinstance(item, int):
                    raise ValueError("source_plan_issues must contain only integers")
                if item <= 0:
                    raise ValueError("source_plan_issues must contain positive integers")

        if "extraction_session_ids" in data and data["extraction_session_ids"] is not None:
            if not isinstance(data["extraction_session_ids"], list):
                raise ValueError("extraction_session_ids must be a list or null")
            for item in data["extraction_session_ids"]:
                if not isinstance(item, str):
                    raise ValueError("extraction_session_ids must contain only strings")
                if len(item) == 0:
                    raise ValueError("extraction_session_ids must not contain empty strings")

        # Validate source_repo field - must be "owner/repo" format if present
        if "source_repo" in data and data["source_repo"] is not None:
            if not isinstance(data["source_repo"], str):
                raise ValueError("source_repo must be a string or null")
            if len(data["source_repo"]) == 0:
                raise ValueError("source_repo must not be empty when provided")
            # Validate owner/repo format
            if "/" not in data["source_repo"]:
                raise ValueError("source_repo must be in 'owner/repo' format")

        # Validate extraction mixin: when plan_type is "extraction", mixin fields should be present
        plan_type = data.get("plan_type")
        if plan_type == "extraction":
            if "source_plan_issues" not in data or data.get("source_plan_issues") is None:
                raise ValueError("source_plan_issues is required when plan_type is 'extraction'")
            if "extraction_session_ids" not in data or data.get("extraction_session_ids") is None:
                raise ValueError(
                    "extraction_session_ids is required when plan_type is 'extraction'"
                )

        # Validate optional objective_issue field
        if "objective_issue" in data and data["objective_issue"] is not None:
            if not isinstance(data["objective_issue"], int):
                raise ValueError("objective_issue must be an integer or null")
            if data["objective_issue"] <= 0:
                raise ValueError("objective_issue must be positive when provided")

        # Validate optional created_from_session field
        if "created_from_session" in data and data["created_from_session"] is not None:
            if not isinstance(data["created_from_session"], str):
                raise ValueError("created_from_session must be a string or null")
            if len(data["created_from_session"]) == 0:
                raise ValueError("created_from_session must not be empty when provided")

        # Check for unexpected fields
        known_fields = required_fields | optional_fields
        unknown_fields = set(data.keys()) - known_fields
        if unknown_fields:
            raise ValueError(f"Unknown fields: {', '.join(sorted(unknown_fields))}")

    def get_key(self) -> str:
        return "plan-header"


# Backward compatibility alias
PlanIssueSchema = PlanSchema
