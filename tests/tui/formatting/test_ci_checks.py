"""Tests for CI check run formatting utilities."""

from erk.tui.formatting.ci_checks import (
    format_check_line,
    format_check_runs,
    format_summary_blockquote,
)
from erk_shared.gateway.github.types import PRCheckRun


class TestFormatCheckLine:
    def test_with_detail_url(self) -> None:
        check = PRCheckRun(
            name="unit-tests",
            status="completed",
            conclusion="failure",
            detail_url="https://example.com/run/1",
        )
        result = format_check_line(check)
        assert result == "- **unit-tests** — failure ([details](https://example.com/run/1))"

    def test_without_detail_url(self) -> None:
        check = PRCheckRun(
            name="unit-tests",
            status="completed",
            conclusion="failure",
            detail_url=None,
        )
        result = format_check_line(check)
        assert result == "- **unit-tests** — failure"

    def test_in_progress(self) -> None:
        check = PRCheckRun(
            name="lint",
            status="in_progress",
            conclusion=None,
            detail_url=None,
        )
        result = format_check_line(check)
        assert result == "- **lint** — in progress"


class TestFormatSummaryBlockquote:
    def test_matching_summary(self) -> None:
        summaries = {"unit-tests": "FAILED test_foo.py\nAssertionError"}
        summary_keys = set(summaries.keys())
        result = format_summary_blockquote(
            "unit-tests",
            summaries=summaries,
            summary_keys=summary_keys,
        )
        assert result == ["  > FAILED test_foo.py", "  > AssertionError"]

    def test_no_matching_summary(self) -> None:
        summaries = {"lint": "some error"}
        summary_keys = set(summaries.keys())
        result = format_summary_blockquote(
            "unit-tests",
            summaries=summaries,
            summary_keys=summary_keys,
        )
        assert result == []

    def test_ci_prefix_stripping(self) -> None:
        summaries = {"unit-tests": "FAILED"}
        summary_keys = set(summaries.keys())
        result = format_summary_blockquote(
            "ci / unit-tests",
            summaries=summaries,
            summary_keys=summary_keys,
        )
        assert result == ["  > FAILED"]


class TestFormatCheckRuns:
    def test_empty_check_runs(self) -> None:
        result = format_check_runs([], summaries=None)
        assert result == "*No failing checks*"

    def test_without_summaries(self) -> None:
        checks = [
            PRCheckRun(
                name="unit-tests",
                status="completed",
                conclusion="failure",
                detail_url=None,
            ),
            PRCheckRun(
                name="lint",
                status="completed",
                conclusion="failure",
                detail_url=None,
            ),
        ]
        result = format_check_runs(checks, summaries=None)
        assert "- **unit-tests** — failure" in result
        assert "- **lint** — failure" in result

    def test_with_summaries(self) -> None:
        checks = [
            PRCheckRun(
                name="unit-tests",
                status="completed",
                conclusion="failure",
                detail_url=None,
            ),
        ]
        summaries = {"unit-tests": "FAILED test_foo.py"}
        result = format_check_runs(checks, summaries=summaries)
        assert "- **unit-tests** — failure" in result
        assert "  > FAILED test_foo.py" in result

    def test_with_summaries_no_match(self) -> None:
        checks = [
            PRCheckRun(
                name="lint",
                status="completed",
                conclusion="failure",
                detail_url=None,
            ),
        ]
        summaries = {"unit-tests": "FAILED test_foo.py"}
        result = format_check_runs(checks, summaries=summaries)
        assert "- **lint** — failure" in result
        assert "> FAILED" not in result
