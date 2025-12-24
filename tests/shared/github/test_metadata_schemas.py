"""Unit tests for metadata block schema validators.

Layer 3 (Pure Unit Tests): Tests for schema validation logic with zero dependencies.
Tests all validator methods for all schema classes in metadata.py.
"""

import pytest

from erk_shared.github.metadata import (
    ImplementationStatusSchema,
    PlanHeaderSchema,
    PlanSchema,
    ProgressStatusSchema,
    StartStatusSchema,
    SubmissionQueuedSchema,
    WorkflowStartedSchema,
    WorktreeCreationSchema,
)


class TestImplementationStatusSchema:
    """Test ImplementationStatusSchema validation."""

    def test_valid_complete_status(self) -> None:
        """Valid completion status with all required fields."""
        schema = ImplementationStatusSchema()
        data = {
            "status": "complete",
            "completed_steps": 5,
            "total_steps": 5,
            "timestamp": "2024-01-15T10:30:00Z",
        }
        schema.validate(data)  # Should not raise

    def test_valid_in_progress_status(self) -> None:
        """Valid in-progress status."""
        schema = ImplementationStatusSchema()
        data = {
            "status": "in_progress",
            "completed_steps": 3,
            "total_steps": 5,
            "timestamp": "2024-01-15T10:30:00Z",
        }
        schema.validate(data)  # Should not raise

    def test_valid_with_optional_fields(self) -> None:
        """Valid status with optional fields."""
        schema = ImplementationStatusSchema()
        data = {
            "status": "complete",
            "completed_steps": 5,
            "total_steps": 5,
            "timestamp": "2024-01-15T10:30:00Z",
            "summary": "Implemented feature X",
            "branch_name": "feature/x",
            "pr_url": "https://github.com/org/repo/pull/123",
            "commit_sha": "abc123def456",
            "worktree_path": "/path/to/worktree",
            "status_history": [{"status": "queued", "timestamp": "2024-01-15T10:00:00Z"}],
        }
        schema.validate(data)  # Should not raise

    def test_missing_required_field(self) -> None:
        """Missing required field raises ValueError."""
        schema = ImplementationStatusSchema()
        data = {
            "status": "complete",
            "completed_steps": 5,
            # Missing total_steps
            "timestamp": "2024-01-15T10:30:00Z",
        }
        with pytest.raises(ValueError, match="Missing required fields: total_steps"):
            schema.validate(data)

    def test_invalid_status_value(self) -> None:
        """Invalid status value raises ValueError."""
        schema = ImplementationStatusSchema()
        data = {
            "status": "invalid_status",
            "completed_steps": 5,
            "total_steps": 5,
            "timestamp": "2024-01-15T10:30:00Z",
        }
        with pytest.raises(ValueError, match="Invalid status 'invalid_status'"):
            schema.validate(data)

    def test_non_integer_completed_steps(self) -> None:
        """Non-integer completed_steps raises ValueError."""
        schema = ImplementationStatusSchema()
        data = {
            "status": "complete",
            "completed_steps": "5",  # String instead of int
            "total_steps": 5,
            "timestamp": "2024-01-15T10:30:00Z",
        }
        with pytest.raises(ValueError, match="completed_steps must be an integer"):
            schema.validate(data)

    def test_negative_completed_steps(self) -> None:
        """Negative completed_steps raises ValueError."""
        schema = ImplementationStatusSchema()
        data = {
            "status": "complete",
            "completed_steps": -1,
            "total_steps": 5,
            "timestamp": "2024-01-15T10:30:00Z",
        }
        with pytest.raises(ValueError, match="completed_steps must be non-negative"):
            schema.validate(data)

    def test_total_steps_less_than_one(self) -> None:
        """total_steps less than 1 raises ValueError."""
        schema = ImplementationStatusSchema()
        data = {
            "status": "complete",
            "completed_steps": 0,
            "total_steps": 0,
            "timestamp": "2024-01-15T10:30:00Z",
        }
        with pytest.raises(ValueError, match="total_steps must be at least 1"):
            schema.validate(data)

    def test_completed_exceeds_total(self) -> None:
        """completed_steps exceeding total_steps raises ValueError."""
        schema = ImplementationStatusSchema()
        data = {
            "status": "complete",
            "completed_steps": 6,
            "total_steps": 5,
            "timestamp": "2024-01-15T10:30:00Z",
        }
        with pytest.raises(ValueError, match="completed_steps cannot exceed total_steps"):
            schema.validate(data)

    def test_get_key(self) -> None:
        """get_key returns correct key."""
        schema = ImplementationStatusSchema()
        assert schema.get_key() == "erk-implementation-status"


class TestProgressStatusSchema:
    """Test ProgressStatusSchema validation."""

    def test_valid_progress(self) -> None:
        """Valid progress status."""
        schema = ProgressStatusSchema()
        data = {
            "status": "in_progress",
            "completed_steps": 3,
            "total_steps": 5,
            "timestamp": "2024-01-15T10:30:00Z",
        }
        schema.validate(data)  # Should not raise

    def test_valid_with_step_description(self) -> None:
        """Valid progress with optional step_description."""
        schema = ProgressStatusSchema()
        data = {
            "status": "in_progress",
            "completed_steps": 3,
            "total_steps": 5,
            "timestamp": "2024-01-15T10:30:00Z",
            "step_description": "Implementing database layer",
        }
        schema.validate(data)  # Should not raise

    def test_missing_required_field(self) -> None:
        """Missing required field raises ValueError."""
        schema = ProgressStatusSchema()
        data = {
            "status": "in_progress",
            "completed_steps": 3,
            # Missing total_steps and timestamp
        }
        with pytest.raises(ValueError, match="Missing required fields"):
            schema.validate(data)


class TestStartStatusSchema:
    """Test StartStatusSchema validation."""

    def test_valid_start_status(self) -> None:
        """Valid start status with all required fields."""
        schema = StartStatusSchema()
        data = {
            "status": "starting",
            "total_steps": 5,
            "timestamp": "2024-01-15T10:30:00Z",
            "worktree": "feature-123",
            "branch": "feature/new-feature",
        }
        schema.validate(data)  # Should not raise

    def test_invalid_status_value(self) -> None:
        """Status must be 'starting'."""
        schema = StartStatusSchema()
        data = {
            "status": "complete",  # Wrong status
            "total_steps": 5,
            "timestamp": "2024-01-15T10:30:00Z",
            "worktree": "feature-123",
            "branch": "feature/new-feature",
        }
        with pytest.raises(ValueError, match="Invalid status 'complete'. Must be 'starting'"):
            schema.validate(data)

    def test_non_integer_total_steps(self) -> None:
        """total_steps must be integer."""
        schema = StartStatusSchema()
        data = {
            "status": "starting",
            "total_steps": "5",
            "timestamp": "2024-01-15T10:30:00Z",
            "worktree": "feature-123",
            "branch": "feature/new-feature",
        }
        with pytest.raises(ValueError, match="total_steps must be an integer"):
            schema.validate(data)

    def test_empty_timestamp(self) -> None:
        """Empty timestamp raises ValueError."""
        schema = StartStatusSchema()
        data = {
            "status": "starting",
            "total_steps": 5,
            "timestamp": "",
            "worktree": "feature-123",
            "branch": "feature/new-feature",
        }
        with pytest.raises(ValueError, match="timestamp must not be empty"):
            schema.validate(data)

    def test_empty_worktree(self) -> None:
        """Empty worktree raises ValueError."""
        schema = StartStatusSchema()
        data = {
            "status": "starting",
            "total_steps": 5,
            "timestamp": "2024-01-15T10:30:00Z",
            "worktree": "",
            "branch": "feature/new-feature",
        }
        with pytest.raises(ValueError, match="worktree must not be empty"):
            schema.validate(data)


class TestWorktreeCreationSchema:
    """Test WorktreeCreationSchema validation."""

    def test_valid_minimal(self) -> None:
        """Valid worktree creation with only required fields."""
        schema = WorktreeCreationSchema()
        data = {
            "worktree_name": "feature-123",
            "branch_name": "feature/new-feature",
            "timestamp": "2024-01-15T10:30:00Z",
        }
        schema.validate(data)  # Should not raise

    def test_valid_with_optional_fields(self) -> None:
        """Valid worktree creation with optional fields."""
        schema = WorktreeCreationSchema()
        data = {
            "worktree_name": "feature-123",
            "branch_name": "feature/new-feature",
            "timestamp": "2024-01-15T10:30:00Z",
            "issue_number": 123,
            "plan_file": ".impl/plan.md",
        }
        schema.validate(data)  # Should not raise

    def test_invalid_issue_number_type(self) -> None:
        """issue_number must be integer."""
        schema = WorktreeCreationSchema()
        data = {
            "worktree_name": "feature-123",
            "branch_name": "feature/new-feature",
            "timestamp": "2024-01-15T10:30:00Z",
            "issue_number": "123",
        }
        with pytest.raises(ValueError, match="issue_number must be an integer"):
            schema.validate(data)

    def test_negative_issue_number(self) -> None:
        """issue_number must be positive."""
        schema = WorktreeCreationSchema()
        data = {
            "worktree_name": "feature-123",
            "branch_name": "feature/new-feature",
            "timestamp": "2024-01-15T10:30:00Z",
            "issue_number": -1,
        }
        with pytest.raises(ValueError, match="issue_number must be positive"):
            schema.validate(data)

    def test_empty_plan_file(self) -> None:
        """Empty plan_file raises ValueError."""
        schema = WorktreeCreationSchema()
        data = {
            "worktree_name": "feature-123",
            "branch_name": "feature/new-feature",
            "timestamp": "2024-01-15T10:30:00Z",
            "plan_file": "",
        }
        with pytest.raises(ValueError, match="plan_file must not be empty"):
            schema.validate(data)

    def test_unknown_fields(self) -> None:
        """Unknown fields raise ValueError."""
        schema = WorktreeCreationSchema()
        data = {
            "worktree_name": "feature-123",
            "branch_name": "feature/new-feature",
            "timestamp": "2024-01-15T10:30:00Z",
            "unknown_field": "value",
        }
        with pytest.raises(ValueError, match="Unknown fields: unknown_field"):
            schema.validate(data)


class TestPlanSchema:
    """Test PlanSchema validation."""

    def test_valid_minimal(self) -> None:
        """Valid plan with only required fields."""
        schema = PlanSchema()
        data = {
            "issue_number": 123,
            "worktree_name": "feature-123",
            "timestamp": "2024-01-15T10:30:00Z",
        }
        schema.validate(data)  # Should not raise

    def test_valid_with_plan_file(self) -> None:
        """Valid plan with optional plan_file."""
        schema = PlanSchema()
        data = {
            "issue_number": 123,
            "worktree_name": "feature-123",
            "timestamp": "2024-01-15T10:30:00Z",
            "plan_file": ".impl/plan.md",
        }
        schema.validate(data)  # Should not raise

    def test_invalid_issue_number_type(self) -> None:
        """issue_number must be integer."""
        schema = PlanSchema()
        data = {
            "issue_number": "123",
            "worktree_name": "feature-123",
            "timestamp": "2024-01-15T10:30:00Z",
        }
        with pytest.raises(ValueError, match="issue_number must be an integer"):
            schema.validate(data)

    def test_zero_issue_number(self) -> None:
        """issue_number must be positive."""
        schema = PlanSchema()
        data = {
            "issue_number": 0,
            "worktree_name": "feature-123",
            "timestamp": "2024-01-15T10:30:00Z",
        }
        with pytest.raises(ValueError, match="issue_number must be positive"):
            schema.validate(data)

    def test_empty_worktree_name(self) -> None:
        """Empty worktree_name raises ValueError."""
        schema = PlanSchema()
        data = {
            "issue_number": 123,
            "worktree_name": "",
            "timestamp": "2024-01-15T10:30:00Z",
        }
        with pytest.raises(ValueError, match="worktree_name must not be empty"):
            schema.validate(data)


class TestSubmissionQueuedSchema:
    """Test SubmissionQueuedSchema validation."""

    def test_valid_submission_queued(self) -> None:
        """Valid submission queued status."""
        schema = SubmissionQueuedSchema()
        data = {
            "status": "queued",
            "queued_at": "2024-01-15T10:30:00Z",
            "submitted_by": "john.doe",
            "issue_number": 123,
            "validation_results": {"issue_is_open": True, "has_erk_plan_label": True},
            "expected_workflow": "implement-plan.yml",
            "trigger_mechanism": "label-based-webhook",
        }
        schema.validate(data)  # Should not raise

    def test_invalid_status(self) -> None:
        """Status must be 'queued'."""
        schema = SubmissionQueuedSchema()
        data = {
            "status": "started",
            "queued_at": "2024-01-15T10:30:00Z",
            "submitted_by": "john.doe",
            "issue_number": 123,
            "validation_results": {},
            "expected_workflow": "implement-plan.yml",
            "trigger_mechanism": "label-based-webhook",
        }
        with pytest.raises(ValueError, match="Invalid status 'started'. Must be 'queued'"):
            schema.validate(data)

    def test_empty_queued_at(self) -> None:
        """Empty queued_at raises ValueError."""
        schema = SubmissionQueuedSchema()
        data = {
            "status": "queued",
            "queued_at": "",
            "submitted_by": "john.doe",
            "issue_number": 123,
            "validation_results": {},
            "expected_workflow": "implement-plan.yml",
            "trigger_mechanism": "label-based-webhook",
        }
        with pytest.raises(ValueError, match="queued_at must not be empty"):
            schema.validate(data)

    def test_non_dict_validation_results(self) -> None:
        """validation_results must be dict."""
        schema = SubmissionQueuedSchema()
        data = {
            "status": "queued",
            "queued_at": "2024-01-15T10:30:00Z",
            "submitted_by": "john.doe",
            "issue_number": 123,
            "validation_results": "not a dict",
            "expected_workflow": "implement-plan.yml",
            "trigger_mechanism": "label-based-webhook",
        }
        with pytest.raises(ValueError, match="validation_results must be a dict"):
            schema.validate(data)


class TestWorkflowStartedSchema:
    """Test WorkflowStartedSchema validation."""

    def test_valid_minimal(self) -> None:
        """Valid workflow started with only required fields."""
        schema = WorkflowStartedSchema()
        data = {
            "status": "started",
            "started_at": "2024-01-15T10:30:00Z",
            "workflow_run_id": "123456789",
            "workflow_run_url": "https://github.com/org/repo/actions/runs/123456789",
            "issue_number": 123,
        }
        schema.validate(data)  # Should not raise

    def test_valid_with_optional_fields(self) -> None:
        """Valid workflow started with optional fields."""
        schema = WorkflowStartedSchema()
        data = {
            "status": "started",
            "started_at": "2024-01-15T10:30:00Z",
            "workflow_run_id": "123456789",
            "workflow_run_url": "https://github.com/org/repo/actions/runs/123456789",
            "issue_number": 123,
            "branch_name": "feature/new-feature",
            "worktree_path": "/path/to/worktree",
        }
        schema.validate(data)  # Should not raise

    def test_invalid_status(self) -> None:
        """Status must be 'started'."""
        schema = WorkflowStartedSchema()
        data = {
            "status": "completed",
            "started_at": "2024-01-15T10:30:00Z",
            "workflow_run_id": "123456789",
            "workflow_run_url": "https://github.com/org/repo/actions/runs/123456789",
            "issue_number": 123,
        }
        with pytest.raises(ValueError, match="Invalid status 'completed'. Must be 'started'"):
            schema.validate(data)

    def test_empty_workflow_run_id(self) -> None:
        """Empty workflow_run_id raises ValueError."""
        schema = WorkflowStartedSchema()
        data = {
            "status": "started",
            "started_at": "2024-01-15T10:30:00Z",
            "workflow_run_id": "",
            "workflow_run_url": "https://github.com/org/repo/actions/runs/123456789",
            "issue_number": 123,
        }
        with pytest.raises(ValueError, match="workflow_run_id must not be empty"):
            schema.validate(data)

    def test_empty_branch_name(self) -> None:
        """Empty branch_name raises ValueError."""
        schema = WorkflowStartedSchema()
        data = {
            "status": "started",
            "started_at": "2024-01-15T10:30:00Z",
            "workflow_run_id": "123456789",
            "workflow_run_url": "https://github.com/org/repo/actions/runs/123456789",
            "issue_number": 123,
            "branch_name": "",
        }
        with pytest.raises(ValueError, match="branch_name must not be empty"):
            schema.validate(data)

    def test_unknown_fields(self) -> None:
        """Unknown fields raise ValueError."""
        schema = WorkflowStartedSchema()
        data = {
            "status": "started",
            "started_at": "2024-01-15T10:30:00Z",
            "workflow_run_id": "123456789",
            "workflow_run_url": "https://github.com/org/repo/actions/runs/123456789",
            "issue_number": 123,
            "unknown_field": "value",
        }
        with pytest.raises(ValueError, match="Unknown fields: unknown_field"):
            schema.validate(data)


class TestPlanHeaderSchema:
    """Test PlanHeaderSchema validation."""

    def test_valid_without_worktree_name(self) -> None:
        """Valid plan-header without worktree_name (new issues before worktree creation)."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
        }
        schema.validate(data)  # Should not raise

    def test_valid_with_worktree_name(self) -> None:
        """Valid plan-header with worktree_name (after worktree creation)."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "worktree_name": "my-feature-25-11-28",
        }
        schema.validate(data)  # Should not raise

    def test_valid_with_all_optional_fields(self) -> None:
        """Valid plan-header with all optional fields."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "worktree_name": "my-feature-25-11-28",
            "last_dispatched_run_id": "123456789",
            "last_dispatched_at": "2024-01-15T11:00:00Z",
            "last_local_impl_at": "2024-01-15T12:00:00Z",
            "last_remote_impl_at": "2024-01-15T13:00:00Z",
        }
        schema.validate(data)  # Should not raise

    def test_valid_with_last_remote_impl_at(self) -> None:
        """Valid plan-header with last_remote_impl_at field."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "last_remote_impl_at": "2024-01-15T14:00:00Z",
        }
        schema.validate(data)  # Should not raise

    def test_null_last_remote_impl_at_is_valid(self) -> None:
        """Null last_remote_impl_at is valid (not set yet)."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "last_remote_impl_at": None,
        }
        schema.validate(data)  # Should not raise

    def test_non_string_last_remote_impl_at_raises(self) -> None:
        """Non-string last_remote_impl_at raises ValueError."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "last_remote_impl_at": 12345,
        }
        with pytest.raises(ValueError, match="last_remote_impl_at must be a string or null"):
            schema.validate(data)

    def test_missing_required_field(self) -> None:
        """Missing required field raises ValueError."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            # Missing created_by
        }
        with pytest.raises(ValueError, match="Missing required fields: created_by"):
            schema.validate(data)

    def test_invalid_schema_version(self) -> None:
        """Invalid schema_version raises ValueError."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "1",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
        }
        with pytest.raises(ValueError, match="Invalid schema_version '1'. Must be '2'"):
            schema.validate(data)

    def test_empty_worktree_name_raises(self) -> None:
        """Empty worktree_name raises ValueError."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "worktree_name": "",
        }
        with pytest.raises(ValueError, match="worktree_name must not be empty when provided"):
            schema.validate(data)

    def test_non_string_worktree_name_raises(self) -> None:
        """Non-string worktree_name raises ValueError."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "worktree_name": 123,
        }
        with pytest.raises(ValueError, match="worktree_name must be a string or null"):
            schema.validate(data)

    def test_null_worktree_name_is_valid(self) -> None:
        """Null worktree_name is valid (not set yet)."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "worktree_name": None,
        }
        schema.validate(data)  # Should not raise

    def test_unknown_fields_raises(self) -> None:
        """Unknown fields raise ValueError."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "unknown_field": "value",
        }
        with pytest.raises(ValueError, match="Unknown fields: unknown_field"):
            schema.validate(data)

    def test_valid_with_plan_comment_id(self) -> None:
        """Valid plan-header with plan_comment_id field."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "plan_comment_id": 12345678,
        }
        schema.validate(data)  # Should not raise

    def test_null_plan_comment_id_is_valid(self) -> None:
        """Null plan_comment_id is valid (not set yet)."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "plan_comment_id": None,
        }
        schema.validate(data)  # Should not raise

    def test_non_integer_plan_comment_id_raises(self) -> None:
        """Non-integer plan_comment_id raises ValueError."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "plan_comment_id": "12345678",
        }
        with pytest.raises(ValueError, match="plan_comment_id must be an integer or null"):
            schema.validate(data)

    def test_zero_plan_comment_id_raises(self) -> None:
        """Zero plan_comment_id raises ValueError."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "plan_comment_id": 0,
        }
        with pytest.raises(ValueError, match="plan_comment_id must be positive when provided"):
            schema.validate(data)

    def test_negative_plan_comment_id_raises(self) -> None:
        """Negative plan_comment_id raises ValueError."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "plan_comment_id": -1,
        }
        with pytest.raises(ValueError, match="plan_comment_id must be positive when provided"):
            schema.validate(data)

    def test_get_key(self) -> None:
        """get_key returns correct key."""
        schema = PlanHeaderSchema()
        assert schema.get_key() == "plan-header"
