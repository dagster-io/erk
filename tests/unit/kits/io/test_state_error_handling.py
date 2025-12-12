"""Tests for state.py error handling utilities."""

from pydantic import BaseModel, ValidationError

from erk.kits.io.state import (
    _build_hook_validation_error_message,
    _extract_validation_error_details,
)


class SampleModel(BaseModel):
    """Sample model for testing validation errors."""

    required_field: str
    optional_field: str | None = None
    number_field: int


def test_extract_validation_error_details_missing_fields() -> None:
    """Test extracting missing field details from ValidationError."""
    # Create validation error with missing required fields
    try:
        SampleModel(number_field="not_a_number")  # type: ignore[arg-type]
    except ValidationError as e:
        missing_fields, invalid_fields = _extract_validation_error_details(e)

        # Should detect missing required_field
        assert "required_field" in missing_fields
        # Should detect invalid number_field
        assert any("number_field" in field for field in invalid_fields)


def test_extract_validation_error_details_invalid_types() -> None:
    """Test extracting invalid type details from ValidationError."""
    # Create validation error with wrong types
    try:
        SampleModel(
            required_field="valid",
            number_field="not_a_number",  # type: ignore[arg-type]
        )
    except ValidationError as e:
        missing_fields, invalid_fields = _extract_validation_error_details(e)

        # Should have no missing fields
        assert len(missing_fields) == 0
        # Should detect invalid number_field
        assert len(invalid_fields) == 1
        assert "number_field" in invalid_fields[0]


def test_extract_validation_error_details_multiple_missing() -> None:
    """Test extracting multiple missing fields from ValidationError."""
    # Create validation error with multiple missing fields
    try:
        SampleModel()  # type: ignore[call-arg]
    except ValidationError as e:
        missing_fields, invalid_fields = _extract_validation_error_details(e)

        # Should detect both missing required fields
        assert "required_field" in missing_fields
        assert "number_field" in missing_fields
        # No invalid fields, only missing
        assert len(invalid_fields) == 0


def test_build_hook_validation_error_message_with_missing_fields() -> None:
    """Test building error message with missing fields."""
    message = _build_hook_validation_error_message(
        kit_name="test-kit",
        hook_id="test-hook",
        hook_position=0,
        total_hooks=1,
        missing_fields=["lifecycle", "invocation", "description"],
        invalid_fields=[],
    )

    # Should include kit name
    assert "test-kit" in message
    # Should include hook ID
    assert "test-hook" in message
    # Should include missing fields
    assert "lifecycle" in message
    assert "invocation" in message
    assert "description" in message
    # Should include remediation steps
    assert "erk kit install" in message
    assert "manually edit kits.toml" in message


def test_build_hook_validation_error_message_with_invalid_fields() -> None:
    """Test building error message with invalid fields."""
    message = _build_hook_validation_error_message(
        kit_name="test-kit",
        hook_id="test-hook",
        hook_position=0,
        total_hooks=1,
        missing_fields=[],
        invalid_fields=["timeout (int_type)", "lifecycle (literal_error)"],
    )

    # Should include kit name
    assert "test-kit" in message
    # Should include hook ID
    assert "test-hook" in message
    # Should include invalid fields section
    assert "Invalid fields" in message
    assert "timeout (int_type)" in message
    assert "lifecycle (literal_error)" in message


def test_build_hook_validation_error_message_with_both() -> None:
    """Test building error message with both missing and invalid fields."""
    message = _build_hook_validation_error_message(
        kit_name="test-kit",
        hook_id="test-hook",
        hook_position=0,
        total_hooks=1,
        missing_fields=["description"],
        invalid_fields=["timeout (int_type)"],
    )

    # Should include both sections
    assert "Missing required fields" in message
    assert "Invalid fields" in message
    assert "description" in message
    assert "timeout (int_type)" in message


def test_build_hook_validation_error_message_unknown_hook_id() -> None:
    """Test building error message when hook ID is unknown."""
    message = _build_hook_validation_error_message(
        kit_name="test-kit",
        hook_id="unknown",
        hook_position=0,
        total_hooks=1,
        missing_fields=["lifecycle"],
        invalid_fields=[],
    )

    # Should handle unknown hook ID gracefully
    assert "unknown" in message
    assert "test-kit" in message


def test_build_hook_validation_error_message_format() -> None:
    """Test that error message follows expected format."""
    message = _build_hook_validation_error_message(
        kit_name="test-kit",
        hook_id="test-hook",
        hook_position=0,
        total_hooks=1,
        missing_fields=["lifecycle"],
        invalid_fields=[],
    )

    # Should have error indicator
    assert "❌ Error" in message
    # Should have Details section
    assert "Details:" in message
    # Should have Suggested action section
    assert "Suggested action:" in message
    # Should have numbered steps
    assert "1." in message
    assert "2." in message
    assert "3." in message


def test_build_hook_validation_error_message_with_position() -> None:
    """Test that error message includes position information."""
    message = _build_hook_validation_error_message(
        kit_name="test-kit",
        hook_id="test-hook",
        hook_position=1,
        total_hooks=3,
        missing_fields=["lifecycle"],
        invalid_fields=[],
    )

    # Should include position information (1-based, so hook_position=1 -> Hook #2)
    assert "Position: Hook #2 of 3" in message
    assert "test-hook" in message


def test_build_hook_validation_error_message_first_hook() -> None:
    """Test position display for first hook in list."""
    message = _build_hook_validation_error_message(
        kit_name="test-kit",
        hook_id="first-hook",
        hook_position=0,
        total_hooks=5,
        missing_fields=["description"],
        invalid_fields=[],
    )

    # Should show Hook #1 (0-based index 0 -> position 1)
    assert "Position: Hook #1 of 5" in message


def test_build_hook_validation_error_message_last_hook() -> None:
    """Test position display for last hook in list."""
    message = _build_hook_validation_error_message(
        kit_name="test-kit",
        hook_id="last-hook",
        hook_position=2,
        total_hooks=3,
        missing_fields=["invocation"],
        invalid_fields=[],
    )

    # Should show Hook #3 (0-based index 2 -> position 3)
    assert "Position: Hook #3 of 3" in message
