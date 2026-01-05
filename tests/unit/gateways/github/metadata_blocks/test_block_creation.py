"""Tests for metadata block creation."""

import pytest

from erk_shared.github.metadata_blocks import (
    ImplementationStatusSchema,
    MetadataBlock,
    create_metadata_block,
)


def test_create_block_without_schema() -> None:
    """Test basic block creation without schema validation."""
    block = create_metadata_block(
        key="test-key",
        data={"field": "value"},
    )
    assert block.key == "test-key"
    assert block.data == {"field": "value"}


def test_create_block_with_valid_schema() -> None:
    """Test block creation with valid schema."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "complete",
        "completed_steps": 5,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }
    block = create_metadata_block(
        key="test-status",
        data=data,
        schema=schema,
    )
    assert block.key == "test-status"
    assert block.data == data


def test_create_block_with_invalid_data_raises() -> None:
    """Test block creation with invalid data raises ValueError."""
    schema = ImplementationStatusSchema()
    data = {
        "status": "invalid-status",
        "completed_steps": 3,
        "total_steps": 5,
        "timestamp": "2025-11-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="Invalid status 'invalid-status'"):
        create_metadata_block(key="test-key", data=data, schema=schema)


def test_metadata_block_is_immutable() -> None:
    """Test that MetadataBlock is frozen (immutable)."""
    block = MetadataBlock(key="test", data={"field": "value"})
    with pytest.raises(AttributeError):  # FrozenInstanceError is subclass
        block.key = "changed"  # type: ignore[misc] -- intentionally mutating frozen dataclass to test immutability
