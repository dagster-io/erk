"""Tests for metadata block schema validation."""

import pytest

from erk_shared.gateway.github.metadata.schemas import ImplementationStatusSchema


def test_schema_validation_accepts_valid_data() -> None:
    """Test ImplementationStatusSchema accepts valid data with summary."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "in_progress",
        "timestamp": "2025-11-22T12:00:00Z",
    }
    schema.validate(data)  # Should not raise


def test_schema_validation_rejects_missing_fields() -> None:
    """Test schema rejects missing required fields."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        # Missing timestamp
    }

    with pytest.raises(ValueError) as exc_info:
        schema.validate(data)

    error_msg = str(exc_info.value)
    assert "Missing required fields" in error_msg
    assert "timestamp" in error_msg


def test_schema_validation_rejects_invalid_status() -> None:
    """Test schema rejects invalid status values."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "invalid-status",
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="Invalid status 'invalid-status'"):
        schema.validate(data)


def test_schema_get_key() -> None:
    """Test schema returns correct key."""
    schema = ImplementationStatusSchema()
    assert schema.get_key() == "erk-implementation-status"


def test_implementation_status_schema_accepts_without_summary() -> None:
    """Test ImplementationStatusSchema accepts data without optional summary."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "timestamp": "2025-11-22T12:00:00Z",
    }
    schema.validate(data)  # Should not raise
