"""Unit tests for stack validation functions."""

from erk_shared.stack.validation import (
    ParentNotTrunkError,
    validate_parent_is_trunk,
)


class TestValidateParentIsTrunk:
    def test_valid_parent_is_trunk(self) -> None:
        result = validate_parent_is_trunk(
            current_branch="feature-1",
            parent_branch="main",
            trunk_branch="main",
        )
        assert result is None

    def test_invalid_parent_not_trunk(self) -> None:
        result = validate_parent_is_trunk(
            current_branch="feature-1",
            parent_branch="develop",
            trunk_branch="main",
        )
        assert result is not None
        assert isinstance(result, ParentNotTrunkError)
        assert "Branch must be exactly one level up from main" in result.message
        assert "Parent branch: develop" in result.message
        assert "Current branch: feature-1" in result.message

    def test_none_parent_is_invalid(self) -> None:
        result = validate_parent_is_trunk(
            current_branch="feature-1",
            parent_branch=None,
            trunk_branch="main",
        )
        assert result is not None
        assert isinstance(result, ParentNotTrunkError)
        assert "Parent branch: unknown" in result.message

    def test_error_message_contains_expected_trunk(self) -> None:
        result = validate_parent_is_trunk(
            current_branch="my-feature",
            parent_branch="other-branch",
            trunk_branch="master",
        )
        assert result is not None
        assert "(expected: master)" in result.message

    def test_error_message_contains_navigation_hint(self) -> None:
        result = validate_parent_is_trunk(
            current_branch="feature",
            parent_branch="not-trunk",
            trunk_branch="main",
        )
        assert result is not None
        assert "Please navigate to a branch that branches directly from" in result.message


class TestParentNotTrunkError:
    def test_frozen_dataclass(self) -> None:
        error = ParentNotTrunkError(
            current_branch="feature",
            parent_branch="develop",
            trunk_branch="main",
        )
        # Verify it's frozen (can't modify attributes)
        try:
            error.current_branch = "other"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass

    def test_message_property_with_all_fields(self) -> None:
        error = ParentNotTrunkError(
            current_branch="my-branch",
            parent_branch="parent-branch",
            trunk_branch="main",
        )
        message = error.message
        assert "my-branch" in message
        assert "parent-branch" in message
        assert "main" in message

    def test_message_property_with_none_parent(self) -> None:
        error = ParentNotTrunkError(
            current_branch="my-branch",
            parent_branch=None,
            trunk_branch="main",
        )
        message = error.message
        assert "unknown" in message
