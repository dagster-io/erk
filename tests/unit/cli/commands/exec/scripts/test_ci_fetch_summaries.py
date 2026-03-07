"""Tests for ci-fetch-summaries exec command.

Tests the CLI command that fetches CI failure summaries for a PR by looking
for the ci-summarize job in the latest CI workflow run.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.ci_fetch_summaries import ci_fetch_summaries
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeLocalGitHub
from erk_shared.gateway.github.types import PRDetails, WorkflowRun


def _make_pr_details(*, head_ref_name: str = "feature-branch") -> PRDetails:
    return PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name=head_ref_name,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )


def _make_workflow_run(
    *,
    run_id: str = "999",
    branch: str = "feature-branch",
) -> WorkflowRun:
    return WorkflowRun(
        run_id=run_id,
        status="completed",
        conclusion="failure",
        branch=branch,
        head_sha="abc123",
    )


class TestCiFetchSummaries:
    """Tests for the ci-fetch-summaries CLI command."""

    def test_returns_summaries_as_json(self, tmp_path: Path) -> None:
        """Command outputs parsed CI summaries as JSON."""
        log_text = "=== ERK-CI-SUMMARY:lint ===\n- Formatting issues\n=== /ERK-CI-SUMMARY:lint ==="
        github = FakeLocalGitHub(
            pr_details={123: _make_pr_details()},
            workflow_runs=[_make_workflow_run()],
            ci_summary_logs={"999": log_text},
        )
        ctx = ErkContext.for_test(github=github, cwd=tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            ci_fetch_summaries,
            ["--pr-number", "123"],
            obj=ctx,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "lint" in data
        assert data["lint"] == "- Formatting issues"

    def test_pr_not_found_exits_with_error(self, tmp_path: Path) -> None:
        """Command exits with code 1 when PR is not found."""
        github = FakeLocalGitHub()
        ctx = ErkContext.for_test(github=github, cwd=tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            ci_fetch_summaries,
            ["--pr-number", "999"],
            obj=ctx,
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert "error" in data

    def test_no_workflow_run_returns_empty(self, tmp_path: Path) -> None:
        """Command returns empty JSON when no CI workflow run exists."""
        github = FakeLocalGitHub(
            pr_details={123: _make_pr_details()},
        )
        ctx = ErkContext.for_test(github=github, cwd=tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            ci_fetch_summaries,
            ["--pr-number", "123"],
            obj=ctx,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data == {}

    def test_no_ci_summarize_job_returns_empty(self, tmp_path: Path) -> None:
        """Command returns empty JSON when ci-summarize job doesn't exist."""
        github = FakeLocalGitHub(
            pr_details={123: _make_pr_details()},
            workflow_runs=[_make_workflow_run()],
            # No ci_summary_logs configured -> get_ci_summary_logs returns None
        )
        ctx = ErkContext.for_test(github=github, cwd=tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            ci_fetch_summaries,
            ["--pr-number", "123"],
            obj=ctx,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data == {}

    def test_multiple_summaries_returned(self, tmp_path: Path) -> None:
        """Command returns multiple summaries when present."""
        log_text = (
            "=== ERK-CI-SUMMARY:lint ===\n"
            "- Lint issue\n"
            "=== /ERK-CI-SUMMARY:lint ===\n"
            "\n"
            "=== ERK-CI-SUMMARY:unit-tests ===\n"
            "- 2 tests failed\n"
            "=== /ERK-CI-SUMMARY:unit-tests ==="
        )
        github = FakeLocalGitHub(
            pr_details={123: _make_pr_details()},
            workflow_runs=[_make_workflow_run()],
            ci_summary_logs={"999": log_text},
        )
        ctx = ErkContext.for_test(github=github, cwd=tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            ci_fetch_summaries,
            ["--pr-number", "123"],
            obj=ctx,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        assert "lint" in data
        assert "unit-tests" in data
