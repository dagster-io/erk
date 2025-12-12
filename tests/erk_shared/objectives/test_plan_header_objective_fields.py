"""Tests for objective-related fields in PlanHeaderSchema."""

import pytest

from erk_shared.github.metadata import (
    PlanHeaderSchema,
    create_plan_header_block,
)


class TestPlanHeaderSchemaObjectiveFields:
    """Tests for objective mixin fields in PlanHeaderSchema."""

    def test_validates_objective_plan_type(self) -> None:
        """Should accept 'objective' as valid plan_type."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "plan_type": "objective",
            "source_objective": "cli-ensure-error-handling",
        }

        # Should not raise
        schema.validate(data)

    def test_validates_source_objective_string(self) -> None:
        """Should accept valid source_objective string."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "source_objective": "my-objective",
        }

        # Should not raise
        schema.validate(data)

    def test_rejects_empty_source_objective(self) -> None:
        """Should reject empty source_objective string."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "source_objective": "",
        }

        with pytest.raises(ValueError, match="source_objective must not be empty"):
            schema.validate(data)

    def test_rejects_non_string_source_objective(self) -> None:
        """Should reject non-string source_objective."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "source_objective": 123,
        }

        with pytest.raises(ValueError, match="source_objective must be a string"):
            schema.validate(data)

    def test_validates_completable_objective_type(self) -> None:
        """Should accept 'completable' as valid objective_type."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "objective_type": "completable",
        }

        # Should not raise
        schema.validate(data)

    def test_validates_perpetual_objective_type(self) -> None:
        """Should accept 'perpetual' as valid objective_type."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "objective_type": "perpetual",
        }

        # Should not raise
        schema.validate(data)

    def test_rejects_invalid_objective_type(self) -> None:
        """Should reject invalid objective_type value."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "objective_type": "invalid",
        }

        with pytest.raises(ValueError, match="Invalid objective_type"):
            schema.validate(data)

    def test_validates_turn_context_dict(self) -> None:
        """Should accept valid turn_context dict."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "turn_context": {
                "gap_size": "small",
                "files_evaluated": 15,
                "evaluation_timestamp": "2024-01-15T10:00:00Z",
            },
        }

        # Should not raise
        schema.validate(data)

    def test_rejects_non_dict_turn_context(self) -> None:
        """Should reject non-dict turn_context."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "turn_context": "not a dict",
        }

        with pytest.raises(ValueError, match="turn_context must be a dict"):
            schema.validate(data)

    def test_rejects_unknown_turn_context_keys(self) -> None:
        """Should reject turn_context with unknown keys."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "turn_context": {
                "unknown_key": "value",
            },
        }

        with pytest.raises(ValueError, match="Unknown turn_context field"):
            schema.validate(data)

    def test_requires_source_objective_when_plan_type_is_objective(self) -> None:
        """Should require source_objective when plan_type is 'objective'."""
        schema = PlanHeaderSchema()
        data = {
            "schema_version": "2",
            "created_at": "2024-01-15T10:30:00Z",
            "created_by": "testuser",
            "plan_type": "objective",
        }

        with pytest.raises(ValueError, match="source_objective is required"):
            schema.validate(data)


class TestCreatePlanHeaderBlockObjectiveFields:
    """Tests for create_plan_header_block with objective fields."""

    def test_creates_block_with_objective_fields(self) -> None:
        """Should create block with all objective fields."""
        block = create_plan_header_block(
            created_at="2024-01-15T10:30:00Z",
            created_by="testuser",
            plan_type="objective",
            source_objective="cli-ensure-error-handling",
            objective_type="completable",
            turn_context={
                "gap_size": "medium",
                "files_evaluated": 25,
            },
        )

        assert block.data["plan_type"] == "objective"
        assert block.data["source_objective"] == "cli-ensure-error-handling"
        assert block.data["objective_type"] == "completable"
        assert block.data["turn_context"]["gap_size"] == "medium"
        assert block.data["turn_context"]["files_evaluated"] == 25

    def test_creates_block_without_optional_objective_fields(self) -> None:
        """Should create block without objective fields when not provided."""
        block = create_plan_header_block(
            created_at="2024-01-15T10:30:00Z",
            created_by="testuser",
        )

        assert "source_objective" not in block.data
        assert "objective_type" not in block.data
        assert "turn_context" not in block.data
