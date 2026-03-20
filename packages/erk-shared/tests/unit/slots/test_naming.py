"""Unit tests for erk_shared.slots.naming pure utilities."""

from erk_shared.slots.naming import (
    extract_slot_number,
    get_placeholder_branch_name,
    is_placeholder_branch,
)


def test_extract_slot_number_valid() -> None:
    """Extracts slot number from valid slot name."""
    assert extract_slot_number("erk-slot-01") == "01"
    assert extract_slot_number("erk-slot-03") == "03"
    assert extract_slot_number("erk-slot-99") == "99"


def test_extract_slot_number_invalid() -> None:
    """Returns None for invalid slot names."""
    assert extract_slot_number("invalid-name") is None
    assert extract_slot_number("erk-slot-1") is None  # Single digit
    assert extract_slot_number("erk-slot-001") is None  # Three digits
    assert extract_slot_number("erk-slot-ab") is None  # Non-numeric
    assert extract_slot_number("") is None


def test_get_placeholder_branch_name_valid() -> None:
    """Returns correct placeholder branch name for valid slot."""
    assert get_placeholder_branch_name("erk-slot-01") == "__erk-slot-01-br-stub__"
    assert get_placeholder_branch_name("erk-slot-03") == "__erk-slot-03-br-stub__"
    assert get_placeholder_branch_name("erk-slot-99") == "__erk-slot-99-br-stub__"


def test_get_placeholder_branch_name_invalid() -> None:
    """Returns None for invalid slot names."""
    assert get_placeholder_branch_name("invalid-name") is None
    assert get_placeholder_branch_name("erk-slot-1") is None


def test_is_placeholder_branch_valid() -> None:
    """Returns True for valid placeholder branch names."""
    assert is_placeholder_branch("__erk-slot-01-br-stub__") is True
    assert is_placeholder_branch("__erk-slot-02-br-stub__") is True
    assert is_placeholder_branch("__erk-slot-99-br-stub__") is True


def test_is_placeholder_branch_invalid() -> None:
    """Returns False for non-placeholder branch names."""
    assert is_placeholder_branch("main") is False
    assert is_placeholder_branch("master") is False
    assert is_placeholder_branch("feature/my-branch") is False
    # Missing underscores
    assert is_placeholder_branch("erk-slot-01-placeholder") is False
    # Wrong prefix
    assert is_placeholder_branch("__erk-slot-01__") is False
    # Missing suffix
    assert is_placeholder_branch("__erk-slot-01__") is False
    # Extra content
    assert is_placeholder_branch("__erk-slot-01-br-stub__-extra") is False
    # Non-numeric slot
    assert is_placeholder_branch("__erk-slot-xx-br-stub__") is False
