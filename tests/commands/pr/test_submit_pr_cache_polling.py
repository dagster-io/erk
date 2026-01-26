"""Tests for PR cache polling in erk pr submit command.

These tests verify that after PR submission with Graphite, the command
waits for the PR to appear in Graphite's cache before exiting. This ensures
the status line can immediately display the PR number.
"""

from datetime import datetime, timedelta
from pathlib import Path

from erk.cli.commands.pr.submit_cmd import (
    PR_CACHE_POLL_INTERVAL_SECONDS,
    PR_CACHE_POLL_MAX_WAIT_SECONDS,
    _wait_for_pr_in_cache,
)
from erk.core.context import context_for_test
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.types import PullRequestInfo
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.time.abc import Time


class ProgressingFakeTime(Time):
    """FakeTime that advances on each now() call for testing polling loops.

    Each call to now() returns a time that is `increment` seconds later than
    the previous call. This allows testing timeout logic without sleeping.
    """

    def __init__(
        self,
        *,
        start_time: datetime,
        increment_seconds: float,
    ) -> None:
        """Create ProgressingFakeTime.

        Args:
            start_time: Initial time to return
            increment_seconds: Seconds to add on each now() call
        """
        self._current_time = start_time
        self._increment = timedelta(seconds=increment_seconds)
        self._sleep_calls: list[float] = []
        self._now_calls: list[datetime] = []

    def now(self) -> datetime:
        """Return current time and advance for next call."""
        result = self._current_time
        self._now_calls.append(result)
        self._current_time = self._current_time + self._increment
        return result

    def sleep(self, seconds: float) -> None:
        """Track sleep call without actually sleeping."""
        self._sleep_calls.append(seconds)

    @property
    def sleep_calls(self) -> list[float]:
        """Get the list of sleep() calls that were made."""
        return self._sleep_calls

    @property
    def now_calls(self) -> list[datetime]:
        """Get the list of times returned by now()."""
        return self._now_calls


class DelayedPRFakeGraphite(FakeGraphite):
    """FakeGraphite that returns PR after N calls to get_prs_from_graphite.

    Simulates the delay between PR creation and cache update.
    """

    def __init__(
        self,
        *,
        pr_info_after_calls: int,
        final_pr_info: dict[str, PullRequestInfo],
        **kwargs,
    ) -> None:
        """Create DelayedPRFakeGraphite.

        Args:
            pr_info_after_calls: Return final_pr_info after this many calls
            final_pr_info: PR info to return after pr_info_after_calls
            **kwargs: Passed to FakeGraphite
        """
        super().__init__(**kwargs)
        self._pr_info_after_calls = pr_info_after_calls
        self._final_pr_info = final_pr_info
        self._get_prs_call_count = 0

    def get_prs_from_graphite(self, git_ops: Git, repo_root: Path) -> dict[str, PullRequestInfo]:
        """Return empty dict initially, then PR info after N calls."""
        self._get_prs_call_count += 1

        if self._get_prs_call_count >= self._pr_info_after_calls:
            return self._final_pr_info.copy()
        return {}

    @property
    def get_prs_call_count(self) -> int:
        """Number of times get_prs_from_graphite was called."""
        return self._get_prs_call_count


def test_wait_for_pr_in_cache_finds_pr_immediately() -> None:
    """Test that polling returns True immediately when PR is already in cache."""
    pr_info = PullRequestInfo(
        number=123,
        state="OPEN",
        url="https://github.com/owner/repo/pull/123",
        is_draft=False,
        title="Feature PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )

    cwd = Path("/repo")
    git = FakeGit(
        git_common_dirs={cwd: cwd / ".git"},
        repository_roots={cwd: cwd},
    )
    graphite = FakeGraphite(pr_info={"feature": pr_info})
    fake_time = ProgressingFakeTime(
        start_time=datetime(2024, 1, 15, 14, 0, 0),
        increment_seconds=0.5,
    )

    ctx = context_for_test(
        git=git,
        graphite=graphite,
        time=fake_time,
        cwd=cwd,
    )

    result = _wait_for_pr_in_cache(
        ctx,
        cwd,
        "feature",
        max_wait_seconds=PR_CACHE_POLL_MAX_WAIT_SECONDS,
        poll_interval=PR_CACHE_POLL_INTERVAL_SECONDS,
    )

    assert result is True
    # Should find PR on first call, no sleeping needed
    assert len(fake_time.sleep_calls) == 0


def test_wait_for_pr_in_cache_polls_until_found() -> None:
    """Test that polling continues until PR appears in cache."""
    pr_info = PullRequestInfo(
        number=123,
        state="OPEN",
        url="https://github.com/owner/repo/pull/123",
        is_draft=False,
        title="Feature PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )

    cwd = Path("/repo")
    git = FakeGit(
        git_common_dirs={cwd: cwd / ".git"},
        repository_roots={cwd: cwd},
    )
    # PR appears after 3 calls
    graphite = DelayedPRFakeGraphite(
        pr_info_after_calls=3,
        final_pr_info={"feature": pr_info},
    )
    # Each now() call advances 0.5 seconds
    fake_time = ProgressingFakeTime(
        start_time=datetime(2024, 1, 15, 14, 0, 0),
        increment_seconds=0.5,
    )

    ctx = context_for_test(
        git=git,
        graphite=graphite,
        time=fake_time,
        cwd=cwd,
    )

    result = _wait_for_pr_in_cache(
        ctx,
        cwd,
        "feature",
        max_wait_seconds=PR_CACHE_POLL_MAX_WAIT_SECONDS,
        poll_interval=0.5,
    )

    assert result is True
    # Should have called get_prs 3 times
    assert graphite.get_prs_call_count == 3
    # Should have slept twice (before 2nd and 3rd calls)
    assert len(fake_time.sleep_calls) == 2
    assert fake_time.sleep_calls == [0.5, 0.5]


def test_wait_for_pr_in_cache_times_out() -> None:
    """Test that polling returns False when timeout is reached."""
    cwd = Path("/repo")
    git = FakeGit(
        git_common_dirs={cwd: cwd / ".git"},
        repository_roots={cwd: cwd},
    )
    # PR never appears
    graphite = FakeGraphite(pr_info={})
    # Each now() call advances 3 seconds, timeout is 5 seconds
    # So we'll have: 0s (start), 3s (check), 6s (timeout exceeded)
    fake_time = ProgressingFakeTime(
        start_time=datetime(2024, 1, 15, 14, 0, 0),
        increment_seconds=3.0,
    )

    ctx = context_for_test(
        git=git,
        graphite=graphite,
        time=fake_time,
        cwd=cwd,
    )

    result = _wait_for_pr_in_cache(
        ctx,
        cwd,
        "feature",
        max_wait_seconds=5.0,
        poll_interval=0.5,
    )

    assert result is False
    # Should have at least tried once and then timed out
    assert len(fake_time.now_calls) >= 2


def test_wait_for_pr_in_cache_uses_correct_poll_interval() -> None:
    """Test that the configured poll interval is used for sleeping."""
    pr_info = PullRequestInfo(
        number=123,
        state="OPEN",
        url="https://github.com/owner/repo/pull/123",
        is_draft=False,
        title="Feature PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )

    cwd = Path("/repo")
    git = FakeGit(
        git_common_dirs={cwd: cwd / ".git"},
        repository_roots={cwd: cwd},
    )
    # PR appears after 2 calls
    graphite = DelayedPRFakeGraphite(
        pr_info_after_calls=2,
        final_pr_info={"feature": pr_info},
    )
    fake_time = ProgressingFakeTime(
        start_time=datetime(2024, 1, 15, 14, 0, 0),
        increment_seconds=0.1,
    )

    ctx = context_for_test(
        git=git,
        graphite=graphite,
        time=fake_time,
        cwd=cwd,
    )

    # Use custom poll interval
    result = _wait_for_pr_in_cache(
        ctx,
        cwd,
        "feature",
        max_wait_seconds=PR_CACHE_POLL_MAX_WAIT_SECONDS,
        poll_interval=0.25,
    )

    assert result is True
    # Should have slept once with the configured interval
    assert len(fake_time.sleep_calls) == 1
    assert fake_time.sleep_calls[0] == 0.25


def test_wait_for_pr_in_cache_different_branch() -> None:
    """Test that polling looks for the correct branch in cache."""
    pr_info_feature = PullRequestInfo(
        number=123,
        state="OPEN",
        url="https://github.com/owner/repo/pull/123",
        is_draft=False,
        title="Feature PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )

    cwd = Path("/repo")
    git = FakeGit(
        git_common_dirs={cwd: cwd / ".git"},
        repository_roots={cwd: cwd},
    )
    # Cache has PR for 'feature' but we're looking for 'other-branch'
    graphite = FakeGraphite(pr_info={"feature": pr_info_feature})
    fake_time = ProgressingFakeTime(
        start_time=datetime(2024, 1, 15, 14, 0, 0),
        increment_seconds=3.0,  # Fast timeout
    )

    ctx = context_for_test(
        git=git,
        graphite=graphite,
        time=fake_time,
        cwd=cwd,
    )

    # Look for a different branch
    result = _wait_for_pr_in_cache(
        ctx,
        cwd,
        "other-branch",
        max_wait_seconds=5.0,
        poll_interval=PR_CACHE_POLL_INTERVAL_SECONDS,
    )

    # Should timeout because 'other-branch' is not in cache
    assert result is False
