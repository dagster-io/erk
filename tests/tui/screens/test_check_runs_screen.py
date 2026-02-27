"""Tests for _format_check_runs() in check_runs_screen."""

from erk.tui.screens.check_runs_screen import _format_check_runs
from erk_shared.gateway.github.types import PRCheckRun


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
    result = _format_check_runs([], summaries=None)
    assert result == "*No failing checks*"


def test_single_check_with_url() -> None:
    """Single check with detail_url formats with detail link."""
    check = _make_check_run(
        name="CI / lint",
        conclusion="failure",
        detail_url="https://github.com/runs/42",
    )

    result = _format_check_runs([check], summaries=None)

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

    result = _format_check_runs([check], summaries=None)

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

    result = _format_check_runs([check], summaries=None)

    assert "in progress" in result


def test_multiple_checks_formatted_as_list() -> None:
    """Multiple checks produce markdown list with one entry per line."""
    checks = [
        _make_check_run(name="CI / lint", conclusion="failure", detail_url=None),
        _make_check_run(name="CI / test", conclusion="failure", detail_url=None),
    ]

    result = _format_check_runs(checks, summaries=None)

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

    result = _format_check_runs([check], summaries=summaries)

    assert "  > - Unused import in foo.py" in result


def test_multiline_summary_each_line_blockquoted() -> None:
    """Each line of a multiline summary gets its own blockquote prefix."""
    check = _make_check_run(name="CI / unit-tests", conclusion="failure", detail_url=None)
    summaries = {"unit-tests": "- 3 tests failed\n- TypeError in Foo.bar()"}

    result = _format_check_runs([check], summaries=summaries)

    assert "  > - 3 tests failed" in result
    assert "  > - TypeError in Foo.bar()" in result


def test_summary_not_rendered_when_no_match() -> None:
    """Checks without matching summary keys have no blockquote lines."""
    check = _make_check_run(name="CI / build", conclusion="failure", detail_url=None)
    summaries = {"lint": "- Some lint issue"}

    result = _format_check_runs([check], summaries=summaries)

    assert ">" not in result


def test_empty_summaries_dict_no_blockquotes() -> None:
    """Empty summaries dict produces no blockquote lines."""
    check = _make_check_run(name="CI / lint", conclusion="failure", detail_url=None)

    result = _format_check_runs([check], summaries={})

    assert ">" not in result


def test_summary_with_multiple_checks_only_matching() -> None:
    """Only the check with a matching summary gets a blockquote."""
    checks = [
        _make_check_run(name="CI / lint", conclusion="failure", detail_url=None),
        _make_check_run(name="CI / test", conclusion="failure", detail_url=None),
    ]
    summaries = {"lint": "- Formatting error"}

    result = _format_check_runs(checks, summaries=summaries)

    lines = result.split("\n")
    # lint check line + summary line + test check line = 3 lines
    assert len(lines) == 3
    assert "  > - Formatting error" in lines[1]
