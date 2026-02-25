"""Unit tests for PRDetails EnsurableResult inheritance."""

from erk_shared.gateway.github.types import PRDetails
from erk_shared.non_ideal_state import EnsurableResult


def _make_pr_details(pr_number: int = 123) -> PRDetails:
    return PRDetails(
        number=pr_number,
        url=f"https://github.com/test-owner/test-repo/pull/{pr_number}",
        title=f"Test PR #{pr_number}",
        body="Test PR body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )


# ============================================================================
# EnsurableResult inheritance
# ============================================================================


def test_pr_details_is_ensurable_result() -> None:
    """PRDetails is a subclass of EnsurableResult."""
    assert issubclass(PRDetails, EnsurableResult)


def test_pr_details_ensure_returns_self() -> None:
    """PRDetails.ensure() returns self, enabling one-liner unwrapping."""
    pr = _make_pr_details()
    assert pr.ensure() is pr


def test_pr_details_ensure_preserves_fields() -> None:
    """PRDetails.ensure() returns the same object with all fields intact."""
    pr = _make_pr_details(pr_number=42)
    result = pr.ensure()
    assert result.number == 42
    assert result.title == "Test PR #42"
    assert result.state == "OPEN"
