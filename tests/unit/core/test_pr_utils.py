"""Tests for PR utility functions."""

from erk.core.pr_utils import select_display_pr
from erk_shared.gateway.github.types import PullRequestInfo


def _make_pr(*, number: int, state: str) -> PullRequestInfo:
    return PullRequestInfo(
        number=number,
        state=state,
        url=f"https://github.com/org/repo/pull/{number}",
        is_draft=state == "DRAFT",
        title=f"PR #{number}",
        checks_passing=None,
        owner="org",
        repo="repo",
    )


class TestSelectDisplayPr:
    def test_returns_none_for_empty_list(self) -> None:
        assert select_display_pr([], exclude_pr_numbers=None) is None

    def test_prefers_open_over_merged(self) -> None:
        merged = _make_pr(number=1, state="MERGED")
        open_pr = _make_pr(number=2, state="OPEN")
        result = select_display_pr([merged, open_pr], exclude_pr_numbers=None)
        assert result is not None
        assert result.number == 2

    def test_prefers_merged_over_closed(self) -> None:
        closed = _make_pr(number=1, state="CLOSED")
        merged = _make_pr(number=2, state="MERGED")
        result = select_display_pr([closed, merged], exclude_pr_numbers=None)
        assert result is not None
        assert result.number == 2

    def test_excludes_review_pr(self) -> None:
        review_pr = _make_pr(number=100, state="OPEN")
        impl_pr = _make_pr(number=101, state="OPEN")
        result = select_display_pr([review_pr, impl_pr], exclude_pr_numbers={100})
        assert result is not None
        assert result.number == 101

    def test_falls_back_to_excluded_pr_when_no_other_candidates(self) -> None:
        review_pr = _make_pr(number=100, state="OPEN")
        result = select_display_pr([review_pr], exclude_pr_numbers={100})
        assert result is not None
        assert result.number == 100

    def test_exclude_none_does_not_filter(self) -> None:
        pr = _make_pr(number=1, state="OPEN")
        result = select_display_pr([pr], exclude_pr_numbers=None)
        assert result is not None
        assert result.number == 1

    def test_exclude_empty_set_does_not_filter(self) -> None:
        pr = _make_pr(number=1, state="OPEN")
        result = select_display_pr([pr], exclude_pr_numbers=set())
        assert result is not None
        assert result.number == 1

    def test_prefers_most_recent_open_pr(self) -> None:
        """First open PR in list (most recent) is preferred."""
        newer = _make_pr(number=2, state="OPEN")
        older = _make_pr(number=1, state="OPEN")
        result = select_display_pr([newer, older], exclude_pr_numbers=None)
        assert result is not None
        assert result.number == 2

    def test_excludes_review_pr_still_prefers_open_over_merged(self) -> None:
        review_pr = _make_pr(number=100, state="OPEN")
        merged_pr = _make_pr(number=101, state="MERGED")
        open_pr = _make_pr(number=102, state="OPEN")
        result = select_display_pr([review_pr, merged_pr, open_pr], exclude_pr_numbers={100})
        assert result is not None
        assert result.number == 102
