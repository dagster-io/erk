"""Tests for CLI output formatting."""

from erk_shared.integrations.claude.abc import CommandResult

from erk.cli.output import format_implement_summary


def test_format_implement_summary_shows_pr_number_and_title() -> None:
    """Test that format_implement_summary includes PR number and title."""
    results = [
        CommandResult(
            success=True,
            pr_url="https://github.com/user/repo/pull/1306",
            pr_number=1306,
            pr_title="Fix more warnings in test suite",
            issue_number=None,
            duration_seconds=68.5,
            error_message=None,
            filtered_messages=[],
        )
    ]

    panel = format_implement_summary(results, 68.5)

    # Convert panel to string to check content
    panel_text = panel.renderable.plain

    # Verify PR number is shown
    assert "#1306" in panel_text
    # Verify PR title is shown
    assert "Fix more warnings in test suite" in panel_text
    # Verify PR URL is shown
    assert "https://github.com/user/repo/pull/1306" in panel_text


def test_format_implement_summary_handles_missing_pr_number() -> None:
    """Test that format_implement_summary handles missing PR number gracefully."""
    results = [
        CommandResult(
            success=True,
            pr_url="https://github.com/user/repo/pull/1306",
            pr_number=None,
            pr_title="Fix more warnings in test suite",
            issue_number=None,
            duration_seconds=68.5,
            error_message=None,
            filtered_messages=[],
        )
    ]

    panel = format_implement_summary(results, 68.5)
    panel_text = panel.renderable.plain

    # Verify PR URL is shown (without number)
    assert "https://github.com/user/repo/pull/1306" in panel_text
    # Verify PR title is shown
    assert "Fix more warnings in test suite" in panel_text


def test_format_implement_summary_handles_missing_pr_title() -> None:
    """Test that format_implement_summary handles missing PR title gracefully."""
    results = [
        CommandResult(
            success=True,
            pr_url="https://github.com/user/repo/pull/1306",
            pr_number=1306,
            pr_title=None,
            issue_number=None,
            duration_seconds=68.5,
            error_message=None,
            filtered_messages=[],
        )
    ]

    panel = format_implement_summary(results, 68.5)
    panel_text = panel.renderable.plain

    # Verify PR number and URL are shown
    assert "#1306" in panel_text
    assert "https://github.com/user/repo/pull/1306" in panel_text


def test_format_implement_summary_handles_no_pr() -> None:
    """Test that format_implement_summary handles no PR gracefully."""
    results = [
        CommandResult(
            success=True,
            pr_url=None,
            pr_number=None,
            pr_title=None,
            issue_number=None,
            duration_seconds=68.5,
            error_message=None,
            filtered_messages=[],
        )
    ]

    panel = format_implement_summary(results, 68.5)
    panel_text = panel.renderable.plain

    # Verify status is shown
    assert "Success" in panel_text
    # Verify duration is shown
    assert "Duration" in panel_text
