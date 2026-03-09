"""Tests for check_runs_screen formatting and async behavior."""

import pytest
from textual.widgets import Markdown

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.formatting.ci_checks import format_check_runs
from erk.tui.screens.check_runs_screen import CheckRunsScreen
from erk_shared.gateway.github.types import PRCheckRun
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
from erk_shared.gateway.pr_service.fake import FakePrService


def _make_check_run(
    *,
    name: str = "CI / unit-tests",
    status: str = "completed",
    conclusion: str | None = "failure",
    detail_url: str | None = "https://github.com/runs/1",
) -> PRCheckRun:
    return PRCheckRun(
        name=name,
        status=status,
        conclusion=conclusion,
        detail_url=detail_url,
    )


def test_empty_list_returns_no_failing_checks_message() -> None:
    """Empty list returns italic 'No failing checks' message."""
    result = format_check_runs([], summaries=None)
    assert result == "*No failing checks*"


def test_single_check_with_url() -> None:
    """Single check with detail_url formats with detail link."""
    check = _make_check_run(
        name="CI / lint",
        conclusion="failure",
        detail_url="https://github.com/runs/42",
    )

    result = format_check_runs([check], summaries=None)

    assert "**CI / lint**" in result
    assert "failure" in result
    assert "[details](https://github.com/runs/42)" in result


def test_single_check_without_url() -> None:
    """Single check without detail_url formats without detail link."""
    check = _make_check_run(
        name="CI / build",
        conclusion="failure",
        detail_url=None,
    )

    result = format_check_runs([check], summaries=None)

    assert "**CI / build**" in result
    assert "failure" in result
    assert "details" not in result


def test_in_progress_check_shows_in_progress() -> None:
    """Check with conclusion=None shows 'in progress'."""
    check = _make_check_run(
        name="CI / deploy",
        conclusion=None,
        detail_url=None,
    )

    result = format_check_runs([check], summaries=None)

    assert "in progress" in result


def test_multiple_checks_formatted_as_list() -> None:
    """Multiple checks produce markdown list with one entry per line."""
    checks = [
        _make_check_run(name="CI / lint", conclusion="failure", detail_url=None),
        _make_check_run(name="CI / test", conclusion="failure", detail_url=None),
    ]

    result = format_check_runs(checks, summaries=None)

    lines = result.split("\n")
    assert len(lines) == 2
    assert lines[0].startswith("- ")
    assert lines[1].startswith("- ")
    assert "CI / lint" in lines[0]
    assert "CI / test" in lines[1]


# ============================================================================
# Summary rendering tests
# ============================================================================


def test_summary_rendered_as_blockquote() -> None:
    """Summary for a matching check is rendered as blockquote lines."""
    check = _make_check_run(name="CI / lint", conclusion="failure", detail_url=None)
    summaries = {"lint": "- Unused import in foo.py"}

    result = format_check_runs([check], summaries=summaries)

    assert "  > - Unused import in foo.py" in result


def test_multiline_summary_each_line_blockquoted() -> None:
    """Each line of a multiline summary gets its own blockquote prefix."""
    check = _make_check_run(name="CI / unit-tests", conclusion="failure", detail_url=None)
    summaries = {"unit-tests": "- 3 tests failed\n- TypeError in Foo.bar()"}

    result = format_check_runs([check], summaries=summaries)

    assert "  > - 3 tests failed" in result
    assert "  > - TypeError in Foo.bar()" in result


def test_summary_not_rendered_when_no_match() -> None:
    """Checks without matching summary keys have no blockquote lines."""
    check = _make_check_run(name="CI / build", conclusion="failure", detail_url=None)
    summaries = {"lint": "- Some lint issue"}

    result = format_check_runs([check], summaries=summaries)

    assert ">" not in result


def test_empty_summaries_dict_no_blockquotes() -> None:
    """Empty summaries dict produces no blockquote lines."""
    check = _make_check_run(name="CI / lint", conclusion="failure", detail_url=None)

    result = format_check_runs([check], summaries={})

    assert ">" not in result


def test_summary_with_multiple_checks_only_matching() -> None:
    """Only the check with a matching summary gets a blockquote."""
    checks = [
        _make_check_run(name="CI / lint", conclusion="failure", detail_url=None),
        _make_check_run(name="CI / test", conclusion="failure", detail_url=None),
    ]
    summaries = {"lint": "- Formatting error"}

    result = format_check_runs(checks, summaries=summaries)

    lines = result.split("\n")
    # lint check line + summary line + test check line = 3 lines
    assert len(lines) == 3
    assert "  > - Formatting error" in lines[1]


# ============================================================================
# Async screen tests — two-phase loading lifecycle
# ============================================================================


@pytest.mark.asyncio
async def test_summaries_update_markdown_in_place() -> None:
    """Summaries update existing Markdown widget in-place (no remove/mount race)."""
    provider = FakePlanDataProvider(
        plans=[
            make_plan_row(
                100,
                "Test Plan",
                pr_number=42,
                pr_url="https://github.com/test/repo/pull/42",
                checks_passing=False,
                checks_counts=(3, 4),
            )
        ]
    )
    service = FakePrService()
    service.set_check_runs(
        42,
        [
            PRCheckRun(
                name="CI / lint",
                status="completed",
                conclusion="failure",
                detail_url=None,
            ),
        ],
    )
    service.set_ci_summaries(42, {"lint": "- Unused import in foo.py"})

    filters = PlanFilters.default()
    app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()

        # Open CheckRunsScreen via the view-checks action (bound to 'h')
        await pilot.press("h")
        await pilot.pause()
        await pilot.pause()

        screen = app.screen_stack[-1]
        assert isinstance(screen, CheckRunsScreen)

        # Wait for both Phase 1 (check runs) and Phase 2 (summaries) to complete
        await pilot.pause(0.5)

        # The #checks-content Markdown widget should exist (updated in-place, not removed)
        screen.query_one("#checks-content", Markdown)

        # Check runs should be stored on the screen
        assert len(screen._check_runs) == 1
        assert screen._check_runs[0].name == "CI / lint"

        # The summaries-loading indicator should be gone
        loading_widgets = screen.query("#checks-summaries-loading")
        assert len(loading_widgets) == 0
