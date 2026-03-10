"""Layer 4 unit tests for add_labels_resilient."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from erk_shared.gateway.github.label_ops import AddLabelsResult, add_labels_resilient
from erk_shared.gateway.github.types import PRDetails
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.time import FakeTime


def _make_pr_details(*, number: int = 42) -> PRDetails:
    """Create a minimal PRDetails for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/test/repo/pull/{number}",
        title="Test PR",
        body="body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test",
        repo="repo",
        labels=(),
        created_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        author="test-user",
    )


REPO_ROOT = Path("/fake/repo")


def test_all_labels_added_successfully() -> None:
    """All labels added without errors."""
    fake_github = FakeLocalGitHub(pr_details={42: _make_pr_details()})
    fake_time = FakeTime()

    result = add_labels_resilient(
        fake_github,
        time=fake_time,
        repo_root=REPO_ROOT,
        pr_number=42,
        labels=("bug", "erk-plan"),
    )

    assert result == AddLabelsResult(
        success=True,
        pr_number=42,
        added_labels=["bug", "erk-plan"],
        failed_labels=[],
        errors={},
    )
    assert fake_github.added_labels == [(42, "bug"), (42, "erk-plan")]


def test_empty_labels_returns_success() -> None:
    """Empty labels tuple returns success with no mutations."""
    fake_github = FakeLocalGitHub(pr_details={42: _make_pr_details()})
    fake_time = FakeTime()

    result = add_labels_resilient(
        fake_github,
        time=fake_time,
        repo_root=REPO_ROOT,
        pr_number=42,
        labels=(),
    )

    assert result.success is True
    assert result.added_labels == []
    assert fake_github.added_labels == []


def test_transient_error_retries_then_exhausted() -> None:
    """Transient error exhausts retries and records failure."""
    fake_github = FakeLocalGitHub(
        pr_details={42: _make_pr_details()},
        add_label_errors={"flaky": "connection reset by peer"},
    )
    fake_time = FakeTime()

    result = add_labels_resilient(
        fake_github,
        time=fake_time,
        repo_root=REPO_ROOT,
        pr_number=42,
        labels=("flaky",),
    )

    assert result.success is False
    assert result.added_labels == []
    assert result.failed_labels == ["flaky"]
    assert "connection reset" in result.errors["flaky"]
    # Verify retries happened (with_retries default: 3 attempts = 2 sleeps)
    assert len(fake_time.sleep_calls) == 2


def test_permanent_error_no_retry() -> None:
    """Non-transient error fails immediately without retrying."""
    fake_github = FakeLocalGitHub(
        pr_details={42: _make_pr_details()},
        add_label_errors={"bad": "label not found"},
    )
    fake_time = FakeTime()

    result = add_labels_resilient(
        fake_github,
        time=fake_time,
        repo_root=REPO_ROOT,
        pr_number=42,
        labels=("bad",),
    )

    assert result.success is False
    assert result.failed_labels == ["bad"]
    assert "label not found" in result.errors["bad"]
    # No retries for permanent errors
    assert fake_time.sleep_calls == []


def test_mixed_success_and_failure() -> None:
    """Some labels succeed, some fail — partial success reported."""
    fake_github = FakeLocalGitHub(
        pr_details={42: _make_pr_details()},
        add_label_errors={"bad-label": "permission denied"},
    )
    fake_time = FakeTime()

    result = add_labels_resilient(
        fake_github,
        time=fake_time,
        repo_root=REPO_ROOT,
        pr_number=42,
        labels=("good-label", "bad-label", "also-good"),
    )

    assert result.success is False
    assert result.added_labels == ["good-label", "also-good"]
    assert result.failed_labels == ["bad-label"]
    assert fake_github.added_labels == [(42, "good-label"), (42, "also-good")]
