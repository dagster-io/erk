"""Tests for FakeSubmitStrategy.

Tests the fake implementation used for testing other components
that depend on SubmitStrategy.
"""

from pathlib import Path

from erk_shared.context.testing import context_for_test
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.fake import FakeSubmitStrategy
from erk_shared.gateway.pr.strategy.types import SubmitStrategyError, SubmitStrategyResult


class TestFakeSubmitStrategy:
    """Tests for FakeSubmitStrategy."""

    def test_yields_configured_success_result(self, tmp_path: Path) -> None:
        """Test that FakeSubmitStrategy yields the configured success result."""
        expected_result = SubmitStrategyResult(
            pr_number=42,
            base_branch="main",
            graphite_url="https://app.graphite.com/pr/42",
            pr_url="https://github.com/owner/repo/pull/42",
            branch_name="feature-branch",
            was_created=True,
        )

        strategy = FakeSubmitStrategy(result=expected_result)
        ctx = context_for_test(cwd=tmp_path)

        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        assert completion[0].result == expected_result

    def test_yields_configured_error_result(self, tmp_path: Path) -> None:
        """Test that FakeSubmitStrategy yields the configured error result."""
        expected_error = SubmitStrategyError(
            error_type="github_auth_failed",
            message="GitHub CLI is not authenticated",
            details={},
        )

        strategy = FakeSubmitStrategy(result=expected_error)
        ctx = context_for_test(cwd=tmp_path)

        events = list(strategy.execute(ctx, tmp_path, force=False))

        completion = [e for e in events if isinstance(e, CompletionEvent)]
        assert len(completion) == 1
        assert completion[0].result == expected_error

    def test_yields_configured_progress_messages(self, tmp_path: Path) -> None:
        """Test that FakeSubmitStrategy yields configured progress messages."""
        result = SubmitStrategyResult(
            pr_number=42,
            base_branch="main",
            graphite_url=None,
            pr_url="https://github.com/owner/repo/pull/42",
            branch_name="feature-branch",
            was_created=True,
        )

        strategy = FakeSubmitStrategy(
            result=result,
            progress_messages=("Step 1: Pushing...", "Step 2: Creating PR..."),
        )
        ctx = context_for_test(cwd=tmp_path)

        events = list(strategy.execute(ctx, tmp_path, force=False))

        progress_events = [e for e in events if isinstance(e, ProgressEvent)]
        assert len(progress_events) == 2
        assert progress_events[0].message == "Step 1: Pushing..."
        assert progress_events[1].message == "Step 2: Creating PR..."

    def test_is_frozen_dataclass(self) -> None:
        """Test that FakeSubmitStrategy is immutable."""
        result = SubmitStrategyResult(
            pr_number=42,
            base_branch="main",
            graphite_url=None,
            pr_url="https://github.com/owner/repo/pull/42",
            branch_name="feature-branch",
            was_created=True,
        )

        strategy = FakeSubmitStrategy(result=result)

        # Attempt to modify should raise
        try:
            strategy.result = result  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected - frozen dataclass
