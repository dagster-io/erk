"""Tests for CI summary parsing utilities."""

from erk_shared.gateway.github.ci_summary_parsing import (
    match_summary_to_check,
    parse_ci_summaries,
)


class TestParseCiSummaries:
    """Tests for parse_ci_summaries()."""

    def test_single_summary(self) -> None:
        log_text = (
            "=== ERK-CI-SUMMARY:unit-tests ===\n"
            "- 3 tests failed in `tests/unit/test_foo.py`\n"
            "- `TypeError` in `Foo.bar()`: missing param\n"
            "=== /ERK-CI-SUMMARY:unit-tests ==="
        )
        result = parse_ci_summaries(log_text)
        assert result == {
            "unit-tests": (
                "- 3 tests failed in `tests/unit/test_foo.py`\n"
                "- `TypeError` in `Foo.bar()`: missing param"
            ),
        }

    def test_multiple_summaries(self) -> None:
        log_text = (
            "=== ERK-CI-SUMMARY:format ===\n"
            "- `src/foo.py` has formatting errors\n"
            "=== /ERK-CI-SUMMARY:format ===\n"
            "\n"
            "=== ERK-CI-SUMMARY:lint ===\n"
            "- Unused import `os` in `src/bar.py`\n"
            "=== /ERK-CI-SUMMARY:lint ==="
        )
        result = parse_ci_summaries(log_text)
        assert len(result) == 2
        assert "format" in result
        assert "lint" in result

    def test_no_markers_returns_empty(self) -> None:
        log_text = "Some random log output\nwith no markers"
        result = parse_ci_summaries(log_text)
        assert result == {}

    def test_empty_string_returns_empty(self) -> None:
        result = parse_ci_summaries("")
        assert result == {}

    def test_malformed_closing_marker_ignored(self) -> None:
        log_text = "=== ERK-CI-SUMMARY:test ===\n- Some summary\n=== /ERK-CI-SUMMARY:wrong-name ==="
        result = parse_ci_summaries(log_text)
        assert result == {}

    def test_matrix_job_name_with_parens(self) -> None:
        log_text = (
            "=== ERK-CI-SUMMARY:unit-tests (3.12) ===\n"
            "- Test `test_parse` failed\n"
            "=== /ERK-CI-SUMMARY:unit-tests (3.12) ==="
        )
        result = parse_ci_summaries(log_text)
        assert "unit-tests (3.12)" in result

    def test_summary_with_surrounding_log_noise(self) -> None:
        log_text = (
            "2024-01-01 Starting summarization...\n"
            "Summarizing: format (job 123)\n"
            "=== ERK-CI-SUMMARY:format ===\n"
            "- Formatting issues found\n"
            "=== /ERK-CI-SUMMARY:format ===\n"
            "Done.\n"
        )
        result = parse_ci_summaries(log_text)
        assert result == {"format": "- Formatting issues found"}

    def test_failed_summarization_marker(self) -> None:
        log_text = "=== ERK-CI-SUMMARY:ty ===\n(Summarization failed)\n=== /ERK-CI-SUMMARY:ty ==="
        result = parse_ci_summaries(log_text)
        assert result == {"ty": "(Summarization failed)"}

    def test_log_fetch_failed_marker(self) -> None:
        log_text = "=== ERK-CI-SUMMARY:lint ===\n(Log fetch failed)\n=== /ERK-CI-SUMMARY:lint ==="
        result = parse_ci_summaries(log_text)
        assert result == {"lint": "(Log fetch failed)"}

    def test_multiline_summary_preserved(self) -> None:
        log_text = (
            "=== ERK-CI-SUMMARY:integration-tests ===\n"
            "- Test `test_api` failed with `ConnectionError`\n"
            "- Affected file: `tests/integration/test_api.py`\n"
            "- Root cause: mock server not started\n"
            "=== /ERK-CI-SUMMARY:integration-tests ==="
        )
        result = parse_ci_summaries(log_text)
        summary = result["integration-tests"]
        assert summary.count("\n") == 2
        assert "ConnectionError" in summary
        assert "mock server" in summary


class TestMatchSummaryToCheck:
    """Tests for match_summary_to_check()."""

    def test_exact_match(self) -> None:
        keys = {"format", "lint", "unit-tests"}
        assert match_summary_to_check("format", keys) == "format"

    def test_ci_prefix_stripped(self) -> None:
        keys = {"format", "lint"}
        assert match_summary_to_check("ci / format", keys) == "format"

    def test_no_match_returns_none(self) -> None:
        keys = {"format", "lint"}
        assert match_summary_to_check("unknown-check", keys) is None

    def test_matrix_job_with_ci_prefix(self) -> None:
        keys = {"unit-tests (3.12)", "unit-tests (3.11)"}
        assert match_summary_to_check("ci / unit-tests (3.12)", keys) == "unit-tests (3.12)"

    def test_empty_keys_returns_none(self) -> None:
        assert match_summary_to_check("format", set()) is None

    def test_nested_slash_prefix(self) -> None:
        keys = {"deep / check"}
        assert match_summary_to_check("ci / deep / check", keys) == "deep / check"
