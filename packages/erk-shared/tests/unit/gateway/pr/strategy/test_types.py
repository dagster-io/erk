"""Tests for PR submit strategy types."""

import pytest

from erk_shared.gateway.pr.strategy.types import SubmitStrategyError, SubmitStrategyResult


class TestSubmitStrategyResult:
    """Tests for SubmitStrategyResult dataclass."""

    def test_result_fields(self) -> None:
        """Test that result has all expected fields."""
        result = SubmitStrategyResult(
            pr_number=123,
            base_branch="main",
            graphite_url="https://app.graphite.dev/github/pr/owner/repo/123",
            pr_url="https://github.com/owner/repo/pull/123",
            branch_name="feature-branch",
            was_created=True,
        )

        assert result.pr_number == 123
        assert result.base_branch == "main"
        assert result.graphite_url == "https://app.graphite.dev/github/pr/owner/repo/123"
        assert result.pr_url == "https://github.com/owner/repo/pull/123"
        assert result.branch_name == "feature-branch"
        assert result.was_created is True

    def test_graphite_url_none_for_core_flow(self) -> None:
        """Test that graphite_url can be None for core flow."""
        result = SubmitStrategyResult(
            pr_number=456,
            base_branch="master",
            graphite_url=None,  # Core flow doesn't use Graphite
            pr_url="https://github.com/owner/repo/pull/456",
            branch_name="fix-bug",
            was_created=False,
        )

        assert result.graphite_url is None
        assert result.was_created is False

    def test_frozen_dataclass(self) -> None:
        """Test that result is immutable."""
        result = SubmitStrategyResult(
            pr_number=789,
            base_branch="main",
            graphite_url=None,
            pr_url="https://github.com/owner/repo/pull/789",
            branch_name="feature",
            was_created=True,
        )

        with pytest.raises(AttributeError):
            result.pr_number = 999  # type: ignore[misc]


class TestSubmitStrategyError:
    """Tests for SubmitStrategyError dataclass."""

    def test_error_fields(self) -> None:
        """Test that error has all expected fields."""
        error = SubmitStrategyError(
            error_type="detached_head",
            message="Not on a branch (detached HEAD state)",
            details={},
        )

        assert error.error_type == "detached_head"
        assert error.message == "Not on a branch (detached HEAD state)"
        assert error.details == {}

    def test_error_with_details(self) -> None:
        """Test error with additional details."""
        error = SubmitStrategyError(
            error_type="gt_submit_failed",
            message="Graphite submit failed: network timeout",
            details={"error": "network timeout", "branch": "feature-x"},
        )

        assert error.error_type == "gt_submit_failed"
        assert error.details["error"] == "network timeout"
        assert error.details["branch"] == "feature-x"

    def test_frozen_dataclass(self) -> None:
        """Test that error is immutable."""
        error = SubmitStrategyError(
            error_type="test_error",
            message="Test message",
            details={},
        )

        with pytest.raises(AttributeError):
            error.error_type = "different_error"  # type: ignore[misc]
