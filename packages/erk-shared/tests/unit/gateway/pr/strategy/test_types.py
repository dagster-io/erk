"""Tests for PR submit strategy types."""

from dataclasses import FrozenInstanceError

import pytest

from erk_shared.gateway.pr.strategy.types import (
    SubmitStrategyError,
    SubmitStrategyResult,
)


class TestSubmitStrategyResult:
    """Tests for SubmitStrategyResult dataclass."""

    def test_field_access(self) -> None:
        """Test that all fields are accessible."""
        result = SubmitStrategyResult(
            pr_number=42,
            base_branch="main",
            graphite_url="https://app.graphite.dev/pr/42",
            pr_url="https://github.com/owner/repo/pull/42",
            branch_name="feature-branch",
            was_created=True,
        )

        assert result.pr_number == 42
        assert result.base_branch == "main"
        assert result.graphite_url == "https://app.graphite.dev/pr/42"
        assert result.pr_url == "https://github.com/owner/repo/pull/42"
        assert result.branch_name == "feature-branch"
        assert result.was_created is True

    def test_graphite_url_can_be_none(self) -> None:
        """Test that graphite_url can be None for standard flow."""
        result = SubmitStrategyResult(
            pr_number=42,
            base_branch="main",
            graphite_url=None,
            pr_url="https://github.com/owner/repo/pull/42",
            branch_name="feature-branch",
            was_created=False,
        )

        assert result.graphite_url is None
        assert result.was_created is False

    def test_frozen_dataclass_behavior(self) -> None:
        """Test that the dataclass is immutable (frozen)."""
        result = SubmitStrategyResult(
            pr_number=42,
            base_branch="main",
            graphite_url=None,
            pr_url="https://github.com/owner/repo/pull/42",
            branch_name="feature-branch",
            was_created=True,
        )

        with pytest.raises(FrozenInstanceError):
            result.pr_number = 99  # type: ignore[misc]


class TestSubmitStrategyError:
    """Tests for SubmitStrategyError dataclass."""

    def test_field_access(self) -> None:
        """Test that all fields are accessible."""
        error = SubmitStrategyError(
            error_type="detached-head",
            message="Not on a branch",
            details={"hint": "checkout a branch first"},
        )

        assert error.error_type == "detached-head"
        assert error.message == "Not on a branch"
        assert error.details == {"hint": "checkout a branch first"}

    def test_empty_details(self) -> None:
        """Test that details can be empty."""
        error = SubmitStrategyError(
            error_type="unknown",
            message="Something went wrong",
            details={},
        )

        assert error.details == {}

    def test_frozen_dataclass_behavior(self) -> None:
        """Test that the dataclass is immutable (frozen)."""
        error = SubmitStrategyError(
            error_type="test",
            message="test error",
            details={},
        )

        with pytest.raises(FrozenInstanceError):
            error.message = "modified"  # type: ignore[misc]
