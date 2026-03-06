"""Tests for ci-generate-summaries exec command.

Tests the pure functions: _parse_failing_jobs, _truncate_logs, _build_summary_prompt.
The CLI command calls gh api via run_subprocess_with_context, so it is tested
via CI integration rather than unit tests.
"""

from __future__ import annotations

from pathlib import Path

from erk.cli.commands.exec.scripts.ci_generate_summaries import (
    FailingJob,
    _build_comment_body,
    _build_summary_prompt,
    _parse_failing_jobs,
    _truncate_logs,
)


class TestParseFailingJobs:
    """Tests for _parse_failing_jobs."""

    def test_empty_input(self) -> None:
        assert _parse_failing_jobs("") == []

    def test_whitespace_only(self) -> None:
        assert _parse_failing_jobs("  \n  \n  ") == []

    def test_single_job(self) -> None:
        result = _parse_failing_jobs("123\tlint")
        assert result == [FailingJob(job_id="123", name="lint")]

    def test_multiple_jobs(self) -> None:
        stdout = "100\tlint\n200\tunit-tests\n300\tintegration-tests"
        result = _parse_failing_jobs(stdout)
        assert result == [
            FailingJob(job_id="100", name="lint"),
            FailingJob(job_id="200", name="unit-tests"),
            FailingJob(job_id="300", name="integration-tests"),
        ]

    def test_skips_blank_lines(self) -> None:
        stdout = "100\tlint\n\n200\tunit-tests\n"
        result = _parse_failing_jobs(stdout)
        assert len(result) == 2

    def test_job_name_with_spaces(self) -> None:
        result = _parse_failing_jobs("100\tRun unit tests (3.10)")
        assert result == [FailingJob(job_id="100", name="Run unit tests (3.10)")]


class TestTruncateLogs:
    """Tests for _truncate_logs."""

    def test_within_limit(self) -> None:
        text = "line1\nline2\nline3"
        assert _truncate_logs(text, max_lines=5) == text

    def test_at_limit(self) -> None:
        text = "line1\nline2\nline3"
        assert _truncate_logs(text, max_lines=3) == text

    def test_exceeds_limit(self) -> None:
        text = "line1\nline2\nline3\nline4\nline5"
        result = _truncate_logs(text, max_lines=3)
        assert result == "line3\nline4\nline5"

    def test_empty_input(self) -> None:
        assert _truncate_logs("", max_lines=10) == ""


class TestBuildCommentBody:
    """Tests for _build_comment_body."""

    def test_single_summary(self) -> None:
        result = _build_comment_body([("lint", "- missing semicolons")])
        assert "## CI Failure Summary" in result
        assert "### lint" in result
        assert "- missing semicolons" in result
        assert "=== ERK-CI-SUMMARY:lint ===" in result
        assert "=== /ERK-CI-SUMMARY:lint ===" in result

    def test_multiple_summaries(self) -> None:
        summaries = [
            ("lint", "- format errors"),
            ("unit-tests", "- assertion failed in test_foo"),
        ]
        result = _build_comment_body(summaries)
        assert "### lint" in result
        assert "### unit-tests" in result
        assert "=== ERK-CI-SUMMARY:lint ===" in result
        assert "=== ERK-CI-SUMMARY:unit-tests ===" in result

    def test_empty_summaries(self) -> None:
        result = _build_comment_body([])
        assert "## CI Failure Summary" in result
        assert "===" not in result


class TestBuildSummaryPrompt:
    """Tests for _build_summary_prompt."""

    def test_with_template(self, tmp_path: Path) -> None:
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        template = prompts_dir / "ci-summarize.md"
        template.write_text("Job: {{ JOB_NAME }}\nLogs: {{ LOG_CONTENT }}")

        result = _build_summary_prompt(
            job_name="lint",
            log_content="error in foo.py",
            prompts_dir=tmp_path,
        )

        assert result == "Job: lint\nLogs: error in foo.py"

    def test_fallback_when_template_missing(self, tmp_path: Path) -> None:
        result = _build_summary_prompt(
            job_name="lint",
            log_content="some logs",
            prompts_dir=tmp_path,
        )

        assert "lint" in result
        assert "some logs" in result
        assert "2-5 concise" in result
