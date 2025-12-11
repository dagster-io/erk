"""Unit tests for GitHub emoji formatting functions."""

from erk_shared.github.emoji import (
    CHECKS_FAILING_EMOJI,
    CHECKS_PASSING_EMOJI,
    CHECKS_PENDING_EMOJI,
    CONFLICTS_EMOJI,
    PR_STATE_EMOJIS,
    format_checks_cell,
    get_checks_status_emoji,
    get_issue_state_emoji,
    get_pr_status_emoji,
)
from erk_shared.github.types import PullRequestInfo


def test_pr_state_emojis_constants() -> None:
    """Test PR state emoji constants are defined correctly."""
    assert PR_STATE_EMOJIS["OPEN"] == "👀"
    assert PR_STATE_EMOJIS["DRAFT"] == "🚧"
    assert PR_STATE_EMOJIS["MERGED"] == "🎉"
    assert PR_STATE_EMOJIS["CLOSED"] == "⛔"


def test_checks_emoji_constants() -> None:
    """Test checks status emoji constants are defined correctly."""
    assert CHECKS_PENDING_EMOJI == "🔄"
    assert CHECKS_PASSING_EMOJI == "✅"
    assert CHECKS_FAILING_EMOJI == "🚫"


def test_conflicts_emoji_constant() -> None:
    """Test conflicts emoji constant is defined correctly."""
    assert CONFLICTS_EMOJI == "💥"


def test_get_pr_status_emoji_open() -> None:
    """Test emoji for open PR without conflicts."""
    pr = PullRequestInfo(
        number=100,
        state="OPEN",
        url="https://github.com/owner/repo/pull/100",
        is_draft=False,
        title="Test PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    result = get_pr_status_emoji(pr)
    assert result == "👀"


def test_get_pr_status_emoji_draft() -> None:
    """Test emoji for draft PR without conflicts.

    Note: GitHub API returns state="OPEN" for draft PRs, with is_draft=True.
    """
    pr = PullRequestInfo(
        number=101,
        state="OPEN",  # GitHub API: draft PRs have state="OPEN", is_draft=True
        url="https://github.com/owner/repo/pull/101",
        is_draft=True,
        title="Draft PR",
        checks_passing=None,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    result = get_pr_status_emoji(pr)
    assert result == "🚧"


def test_get_pr_status_emoji_merged() -> None:
    """Test emoji for merged PR."""
    pr = PullRequestInfo(
        number=102,
        state="MERGED",
        url="https://github.com/owner/repo/pull/102",
        is_draft=False,
        title="Merged PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    result = get_pr_status_emoji(pr)
    assert result == "🎉"


def test_get_pr_status_emoji_closed() -> None:
    """Test emoji for closed PR."""
    pr = PullRequestInfo(
        number=103,
        state="CLOSED",
        url="https://github.com/owner/repo/pull/103",
        is_draft=False,
        title="Closed PR",
        checks_passing=False,
        owner="owner",
        repo="repo",
        has_conflicts=None,
    )

    result = get_pr_status_emoji(pr)
    assert result == "⛔"


def test_get_pr_status_emoji_open_with_conflicts() -> None:
    """Test emoji for open PR with conflicts includes conflict indicator."""
    pr = PullRequestInfo(
        number=104,
        state="OPEN",
        url="https://github.com/owner/repo/pull/104",
        is_draft=False,
        title="Conflicted PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=True,
    )

    result = get_pr_status_emoji(pr)
    assert result == "👀💥"


def test_get_pr_status_emoji_draft_with_conflicts() -> None:
    """Test emoji for draft PR with conflicts includes conflict indicator.

    Note: GitHub API returns state="OPEN" for draft PRs, with is_draft=True.
    """
    pr = PullRequestInfo(
        number=105,
        state="OPEN",  # GitHub API: draft PRs have state="OPEN", is_draft=True
        url="https://github.com/owner/repo/pull/105",
        is_draft=True,
        title="Conflicted Draft PR",
        checks_passing=None,
        owner="owner",
        repo="repo",
        has_conflicts=True,
    )

    result = get_pr_status_emoji(pr)
    assert result == "🚧💥"


def test_get_pr_status_emoji_merged_ignores_conflicts() -> None:
    """Test emoji for merged PR ignores conflicts (shouldn't happen but defensive)."""
    pr = PullRequestInfo(
        number=106,
        state="MERGED",
        url="https://github.com/owner/repo/pull/106",
        is_draft=False,
        title="Merged PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=True,  # Shouldn't happen but test defensive behavior
    )

    result = get_pr_status_emoji(pr)
    assert result == "🎉"  # No conflict indicator for merged PRs


def test_get_pr_status_emoji_closed_ignores_conflicts() -> None:
    """Test emoji for closed PR ignores conflicts (shouldn't happen but defensive)."""
    pr = PullRequestInfo(
        number=107,
        state="CLOSED",
        url="https://github.com/owner/repo/pull/107",
        is_draft=False,
        title="Closed PR",
        checks_passing=False,
        owner="owner",
        repo="repo",
        has_conflicts=True,  # Shouldn't happen but test defensive behavior
    )

    result = get_pr_status_emoji(pr)
    assert result == "⛔"  # No conflict indicator for closed PRs


def test_get_pr_status_emoji_unknown_state() -> None:
    """Test emoji for unknown PR state returns empty string."""
    pr = PullRequestInfo(
        number=108,
        state="UNKNOWN",  # type: ignore - testing defensive behavior
        url="https://github.com/owner/repo/pull/108",
        is_draft=False,
        title="Unknown State PR",
        checks_passing=None,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    result = get_pr_status_emoji(pr)
    assert result == ""


def test_get_checks_status_emoji_no_pr() -> None:
    """Test checks emoji for None PR returns dash."""
    result = get_checks_status_emoji(None)
    assert result == "-"


def test_get_checks_status_emoji_pending() -> None:
    """Test checks emoji for PR with no checks (None)."""
    pr = PullRequestInfo(
        number=200,
        state="OPEN",
        url="https://github.com/owner/repo/pull/200",
        is_draft=False,
        title="PR with pending checks",
        checks_passing=None,  # Pending or no checks
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    result = get_checks_status_emoji(pr)
    assert result == "🔄"


def test_get_checks_status_emoji_passing() -> None:
    """Test checks emoji for PR with passing checks."""
    pr = PullRequestInfo(
        number=201,
        state="OPEN",
        url="https://github.com/owner/repo/pull/201",
        is_draft=False,
        title="PR with passing checks",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    result = get_checks_status_emoji(pr)
    assert result == "✅"


def test_get_checks_status_emoji_failing() -> None:
    """Test checks emoji for PR with failing checks."""
    pr = PullRequestInfo(
        number=202,
        state="OPEN",
        url="https://github.com/owner/repo/pull/202",
        is_draft=False,
        title="PR with failing checks",
        checks_passing=False,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    result = get_checks_status_emoji(pr)
    assert result == "🚫"


def test_get_checks_status_emoji_merged_pr_with_passing_checks() -> None:
    """Test checks emoji for merged PR with passing checks."""
    pr = PullRequestInfo(
        number=203,
        state="MERGED",
        url="https://github.com/owner/repo/pull/203",
        is_draft=False,
        title="Merged PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    result = get_checks_status_emoji(pr)
    assert result == "✅"


def test_get_checks_status_emoji_draft_pr_with_pending_checks() -> None:
    """Test checks emoji for draft PR with pending checks.

    Note: GitHub API returns state="OPEN" for draft PRs, with is_draft=True.
    """
    pr = PullRequestInfo(
        number=204,
        state="OPEN",  # GitHub API: draft PRs have state="OPEN", is_draft=True
        url="https://github.com/owner/repo/pull/204",
        is_draft=True,
        title="Draft PR",
        checks_passing=None,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    result = get_checks_status_emoji(pr)
    assert result == "🔄"


def test_get_issue_state_emoji_open() -> None:
    """Test emoji for OPEN issue state."""
    result = get_issue_state_emoji("OPEN")
    assert result == "🟢"


def test_get_issue_state_emoji_closed() -> None:
    """Test emoji for CLOSED issue state."""
    result = get_issue_state_emoji("CLOSED")
    assert result == "🔴"


# Tests for format_checks_cell


def test_format_checks_cell_no_pr() -> None:
    """Test format_checks_cell for None PR returns dash."""
    result = format_checks_cell(None)
    assert result == "-"


def test_format_checks_cell_pending() -> None:
    """Test format_checks_cell for PR with no checks (None)."""
    pr = PullRequestInfo(
        number=300,
        state="OPEN",
        url="https://github.com/owner/repo/pull/300",
        is_draft=False,
        title="PR with pending checks",
        checks_passing=None,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    result = format_checks_cell(pr)
    assert result == "🔄"


def test_format_checks_cell_passing_with_counts() -> None:
    """Test format_checks_cell for PR with passing checks and counts."""
    pr = PullRequestInfo(
        number=301,
        state="OPEN",
        url="https://github.com/owner/repo/pull/301",
        is_draft=False,
        title="PR with passing checks",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
        checks_counts=(5, 5),
    )

    result = format_checks_cell(pr)
    assert result == "✅ 5/5"


def test_format_checks_cell_failing_with_counts() -> None:
    """Test format_checks_cell for PR with failing checks and counts."""
    pr = PullRequestInfo(
        number=302,
        state="OPEN",
        url="https://github.com/owner/repo/pull/302",
        is_draft=False,
        title="PR with failing checks",
        checks_passing=False,
        owner="owner",
        repo="repo",
        has_conflicts=False,
        checks_counts=(2, 5),
    )

    result = format_checks_cell(pr)
    assert result == "🚫 2/5"


def test_format_checks_cell_passing_without_counts() -> None:
    """Test format_checks_cell for PR with passing checks but no counts."""
    pr = PullRequestInfo(
        number=303,
        state="OPEN",
        url="https://github.com/owner/repo/pull/303",
        is_draft=False,
        title="PR with passing checks",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
        checks_counts=None,  # No counts available
    )

    result = format_checks_cell(pr)
    assert result == "✅"  # Just emoji, no counts


def test_format_checks_cell_failing_without_counts() -> None:
    """Test format_checks_cell for PR with failing checks but no counts."""
    pr = PullRequestInfo(
        number=304,
        state="OPEN",
        url="https://github.com/owner/repo/pull/304",
        is_draft=False,
        title="PR with failing checks",
        checks_passing=False,
        owner="owner",
        repo="repo",
        has_conflicts=False,
        checks_counts=None,  # No counts available
    )

    result = format_checks_cell(pr)
    assert result == "🚫"  # Just emoji, no counts


def test_format_checks_cell_zero_passing_zero_total() -> None:
    """Test format_checks_cell edge case: 0/0 counts (shouldn't happen)."""
    pr = PullRequestInfo(
        number=305,
        state="OPEN",
        url="https://github.com/owner/repo/pull/305",
        is_draft=False,
        title="Edge case PR",
        checks_passing=True,  # If counts is (0,0), passing should be True
        owner="owner",
        repo="repo",
        has_conflicts=False,
        checks_counts=(0, 0),
    )

    result = format_checks_cell(pr)
    assert result == "✅ 0/0"
