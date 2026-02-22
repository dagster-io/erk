"""Tests for ObjectiveHeaderSchema validation logic."""

import pytest

from erk_shared.gateway.github.metadata.schemas import ObjectiveHeaderSchema


class TestObjectiveHeaderSchemaValidation:
    """Test ObjectiveHeaderSchema validates required/optional fields and edge cases."""

    def test_valid_data_with_all_fields(self) -> None:
        """Valid data with all fields passes validation."""
        schema = ObjectiveHeaderSchema()
        data = {
            "created_at": "2025-11-25T14:37:43+00:00",
            "created_by": "testuser",
            "objective_comment_id": 12345,
        }
        schema.validate(data)  # Should not raise

    def test_valid_data_with_null_comment_id(self) -> None:
        """Valid data with null objective_comment_id passes."""
        schema = ObjectiveHeaderSchema()
        data = {
            "created_at": "2025-11-25T14:37:43+00:00",
            "created_by": "testuser",
            "objective_comment_id": None,
        }
        schema.validate(data)  # Should not raise

    def test_valid_data_without_optional_field(self) -> None:
        """Valid data without optional objective_comment_id passes."""
        schema = ObjectiveHeaderSchema()
        data = {
            "created_at": "2025-11-25T14:37:43+00:00",
            "created_by": "testuser",
        }
        schema.validate(data)  # Should not raise

    def test_missing_created_at(self) -> None:
        """Missing created_at raises ValueError."""
        schema = ObjectiveHeaderSchema()
        data = {
            "created_by": "testuser",
        }
        with pytest.raises(ValueError, match="Missing required fields.*created_at"):
            schema.validate(data)

    def test_missing_created_by(self) -> None:
        """Missing created_by raises ValueError."""
        schema = ObjectiveHeaderSchema()
        data = {
            "created_at": "2025-11-25T14:37:43+00:00",
        }
        with pytest.raises(ValueError, match="Missing required fields.*created_by"):
            schema.validate(data)

    def test_missing_both_required_fields(self) -> None:
        """Missing both required fields raises ValueError."""
        schema = ObjectiveHeaderSchema()
        with pytest.raises(ValueError, match="Missing required fields"):
            schema.validate({})

    def test_empty_created_at(self) -> None:
        """Empty string created_at raises ValueError."""
        schema = ObjectiveHeaderSchema()
        data = {
            "created_at": "",
            "created_by": "testuser",
        }
        with pytest.raises(ValueError, match="created_at must not be empty"):
            schema.validate(data)

    def test_empty_created_by(self) -> None:
        """Empty string created_by raises ValueError."""
        schema = ObjectiveHeaderSchema()
        data = {
            "created_at": "2025-11-25T14:37:43+00:00",
            "created_by": "",
        }
        with pytest.raises(ValueError, match="created_by must not be empty"):
            schema.validate(data)

    def test_non_string_created_at(self) -> None:
        """Non-string created_at raises ValueError."""
        schema = ObjectiveHeaderSchema()
        data = {
            "created_at": 12345,
            "created_by": "testuser",
        }
        with pytest.raises(ValueError, match="created_at must be a string"):
            schema.validate(data)

    def test_non_string_created_by(self) -> None:
        """Non-string created_by raises ValueError."""
        schema = ObjectiveHeaderSchema()
        data = {
            "created_at": "2025-11-25T14:37:43+00:00",
            "created_by": 42,
        }
        with pytest.raises(ValueError, match="created_by must be a string"):
            schema.validate(data)

    def test_non_integer_comment_id(self) -> None:
        """Non-integer objective_comment_id raises ValueError."""
        schema = ObjectiveHeaderSchema()
        data = {
            "created_at": "2025-11-25T14:37:43+00:00",
            "created_by": "testuser",
            "objective_comment_id": "not-an-int",
        }
        with pytest.raises(ValueError, match="objective_comment_id must be an integer"):
            schema.validate(data)

    def test_zero_comment_id(self) -> None:
        """Zero objective_comment_id raises ValueError."""
        schema = ObjectiveHeaderSchema()
        data = {
            "created_at": "2025-11-25T14:37:43+00:00",
            "created_by": "testuser",
            "objective_comment_id": 0,
        }
        with pytest.raises(ValueError, match="objective_comment_id must be positive"):
            schema.validate(data)

    def test_negative_comment_id(self) -> None:
        """Negative objective_comment_id raises ValueError."""
        schema = ObjectiveHeaderSchema()
        data = {
            "created_at": "2025-11-25T14:37:43+00:00",
            "created_by": "testuser",
            "objective_comment_id": -1,
        }
        with pytest.raises(ValueError, match="objective_comment_id must be positive"):
            schema.validate(data)

    def test_unknown_fields_warns(self) -> None:
        """Unknown fields emit a warning instead of raising."""
        schema = ObjectiveHeaderSchema()
        data = {
            "created_at": "2025-11-25T14:37:43+00:00",
            "created_by": "testuser",
            "unexpected_field": "value",
        }
        with pytest.warns(UserWarning, match="Unknown fields.*unexpected_field"):
            schema.validate(data)

    def test_get_key(self) -> None:
        """get_key returns 'objective-header'."""
        schema = ObjectiveHeaderSchema()
        assert schema.get_key() == "objective-header"
