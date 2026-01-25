"""Tests for PR submission strategy types.

Tests the result types used by all submission strategies:
- SubmitStrategyResult: Unified success result
- SubmitStrategyError: Unified error result
"""

from erk_shared.gateway.pr.strategy.types import SubmitStrategyError, SubmitStrategyResult


class TestSubmitStrategyResult:
    """Tests for SubmitStrategyResult dataclass."""

    def test_creates_result_with_all_fields(self) -> None:
        """Test that result can be created with all fields."""
        result = SubmitStrategyResult(
            pr_number=42,
            base_branch="main",
            graphite_url="https://app.graphite.dev/github/pr/owner/repo/42",
            pr_url="https://github.com/owner/repo/pull/42",
            branch_name="feature-branch",
            was_created=True,
        )

        assert result.pr_number == 42
        assert result.base_branch == "main"
        assert result.graphite_url == "https://app.graphite.dev/github/pr/owner/repo/42"
        assert result.pr_url == "https://github.com/owner/repo/pull/42"
        assert result.branch_name == "feature-branch"
        assert result.was_created is True

    def test_creates_result_with_none_graphite_url(self) -> None:
        """Test that result can have None graphite_url (Core strategy)."""
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

    def test_result_is_frozen(self) -> None:
        """Test that result is immutable."""
        result = SubmitStrategyResult(
            pr_number=42,
            base_branch="main",
            graphite_url=None,
            pr_url="https://github.com/owner/repo/pull/42",
            branch_name="feature-branch",
            was_created=True,
        )

        # Attempt to modify should raise
        try:
            result.pr_number = 99  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected - frozen dataclass


class TestSubmitStrategyError:
    """Tests for SubmitStrategyError dataclass."""

    def test_creates_error_with_all_fields(self) -> None:
        """Test that error can be created with all fields."""
        error = SubmitStrategyError(
            error_type="no_branch",
            message="Not on a branch (detached HEAD state)",
            details={"git_status": "HEAD detached at abc123"},
        )

        assert error.error_type == "no_branch"
        assert error.message == "Not on a branch (detached HEAD state)"
        assert error.details == {"git_status": "HEAD detached at abc123"}

    def test_creates_error_with_empty_details(self) -> None:
        """Test that error can have empty details."""
        error = SubmitStrategyError(
            error_type="github_auth_failed",
            message="GitHub CLI is not authenticated",
            details={},
        )

        assert error.details == {}

    def test_error_is_frozen(self) -> None:
        """Test that error is immutable."""
        error = SubmitStrategyError(
            error_type="no_branch",
            message="Not on a branch",
            details={},
        )

        # Attempt to modify should raise
        try:
            error.error_type = "other"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected - frozen dataclass
