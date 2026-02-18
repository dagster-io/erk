"""Tests for metadata block schema validation."""

import pytest

from erk_shared.gateway.github.metadata_blocks import ImplementationStatusSchema


def test_schema_validation_accepts_valid_data() -> None:
    """Test ImplementationStatusSchema accepts valid data with summary."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "in_progress",
        "completed_nodes": 3,
        "total_nodes": 5,
        "summary": "Making progress",
        "timestamp": "2025-11-22T12:00:00Z",
    }
    schema.validate(data)  # Should not raise


def test_schema_validation_rejects_missing_fields() -> None:
    """Test schema rejects missing required fields."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_nodes": 5,
        # Missing total_nodes, timestamp
    }

    with pytest.raises(ValueError) as exc_info:
        schema.validate(data)

    error_msg = str(exc_info.value)
    assert "Missing required fields" in error_msg
    assert "timestamp" in error_msg
    assert "total_nodes" in error_msg


def test_schema_validation_rejects_invalid_status() -> None:
    """Test schema rejects invalid status values."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "invalid-status",
        "completed_nodes": 3,
        "total_nodes": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="Invalid status 'invalid-status'"):
        schema.validate(data)


def test_schema_validation_rejects_non_integer_completed_nodes() -> None:
    """Test schema rejects non-integer completed_nodes."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_nodes": "not-an-int",
        "total_nodes": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="completed_nodes must be an integer"):
        schema.validate(data)


def test_schema_validation_rejects_non_integer_total_nodes() -> None:
    """Test schema rejects non-integer total_nodes."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_nodes": 5,
        "total_nodes": 5.5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="total_nodes must be an integer"):
        schema.validate(data)


def test_schema_validation_rejects_negative_completed_nodes() -> None:
    """Test schema rejects negative completed_nodes."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_nodes": -1,
        "total_nodes": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="completed_nodes must be non-negative"):
        schema.validate(data)


def test_schema_validation_rejects_zero_total_nodes() -> None:
    """Test schema rejects zero total_nodes."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_nodes": 0,
        "total_nodes": 0,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="total_nodes must be at least 1"):
        schema.validate(data)


def test_schema_validation_rejects_completed_exceeds_total() -> None:
    """Test schema rejects completed_nodes > total_nodes."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_nodes": 10,
        "total_nodes": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="completed_nodes cannot exceed total_nodes"):
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
        "completed_nodes": 5,
        "total_nodes": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }
    schema.validate(data)  # Should not raise
