"""Tests for metadata block schema validation."""

import pytest

from erk_shared.github.metadata_blocks import ImplementationStatusSchema


def test_schema_validation_accepts_valid_data() -> None:
    """Test ImplementationStatusSchema accepts valid data with summary."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "in_progress",
        "completed_steps": 3,
        "total_steps": 5,
        "summary": "Making progress",
        "timestamp": "2025-11-22T12:00:00Z",
    }
    schema.validate(data)  # Should not raise


def test_schema_validation_rejects_missing_fields() -> None:
    """Test schema rejects missing required fields."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 5,
        # Missing total_steps, timestamp
    }

    with pytest.raises(ValueError) as exc_info:
        schema.validate(data)

    error_msg = str(exc_info.value)
    assert "Missing required fields" in error_msg
    assert "timestamp" in error_msg
    assert "total_steps" in error_msg


def test_schema_validation_rejects_invalid_status() -> None:
    """Test schema rejects invalid status values."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "invalid-status",
        "completed_steps": 3,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="Invalid status 'invalid-status'"):
        schema.validate(data)


def test_schema_validation_rejects_non_integer_completed_steps() -> None:
    """Test schema rejects non-integer completed_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": "not-an-int",
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="completed_steps must be an integer"):
        schema.validate(data)


def test_schema_validation_rejects_non_integer_total_steps() -> None:
    """Test schema rejects non-integer total_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 5,
        "total_steps": 5.5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="total_steps must be an integer"):
        schema.validate(data)


def test_schema_validation_rejects_negative_completed_steps() -> None:
    """Test schema rejects negative completed_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": -1,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="completed_steps must be non-negative"):
        schema.validate(data)


def test_schema_validation_rejects_zero_total_steps() -> None:
    """Test schema rejects zero total_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 0,
        "total_steps": 0,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="total_steps must be at least 1"):
        schema.validate(data)


def test_schema_validation_rejects_completed_exceeds_total() -> None:
    """Test schema rejects completed_steps > total_steps."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 10,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="completed_steps cannot exceed total_steps"):
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
        "completed_steps": 5,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }
    schema.validate(data)  # Should not raise
