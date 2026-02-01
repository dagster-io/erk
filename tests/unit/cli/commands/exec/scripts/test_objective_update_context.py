"""Tests for erk exec objective-update-context."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.objective_update_context import (
    _parse_plan_number_from_branch,
    objective_update_context,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import PRDetails


def _make_issue(*, number: int, title: str, body: str) -> IssueInfo:
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-objective"],
        assignees=[],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        author="testuser",
    )


def _make_pr_details(*, number: int, title: str, body: str) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=title,
        body=body,
        state="MERGED",
        is_draft=False,
        base_ref_name="master",
        head_ref_name="P100-test-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


class TestParsePlanNumberFromBranch:
    def test_valid_pattern(self) -> None:
        assert _parse_plan_number_from_branch("P6513-phase-1b-implement") == 6513

    def test_single_digit(self) -> None:
        assert _parse_plan_number_from_branch("P1-fix") == 1

    def test_no_match(self) -> None:
        assert _parse_plan_number_from_branch("feature-branch") is None

    def test_lowercase_p(self) -> None:
        assert _parse_plan_number_from_branch("p123-branch") is None

    def test_no_hyphen_after_number(self) -> None:
        assert _parse_plan_number_from_branch("P123") is None


class TestObjectiveUpdateContext:
    def test_happy_path(self, tmp_path: Path) -> None:
        """All three fetches succeed, returns combined JSON."""
        objective = _make_issue(number=6423, title="My Objective", body="objective body")
        plan = _make_issue(number=6513, title="My Plan", body="plan body")
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective, 6513: plan})
        fake_github = FakeGitHub(pr_details={6517: pr})

        runner = CliRunner()
        result = runner.invoke(
            objective_update_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "P6513-some-branch"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["objective"]["number"] == 6423
        assert data["objective"]["title"] == "My Objective"
        assert data["plan"]["number"] == 6513
        assert data["plan"]["title"] == "My Plan"
        assert data["pr"]["number"] == 6517
        assert data["pr"]["title"] == "PR Title"

    def test_objective_not_found(self, tmp_path: Path) -> None:
        """Returns error JSON when objective issue not found."""
        plan = _make_issue(number=6513, title="My Plan", body="plan body")
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6513: plan})
        fake_github = FakeGitHub(pr_details={6517: pr})

        runner = CliRunner()
        result = runner.invoke(
            objective_update_context,
            ["--pr", "6517", "--objective", "9999", "--branch", "P6513-some-branch"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "9999" in data["error"]

    def test_pr_not_found(self, tmp_path: Path) -> None:
        """Returns error JSON when PR not found."""
        objective = _make_issue(number=6423, title="My Objective", body="objective body")
        plan = _make_issue(number=6513, title="My Plan", body="plan body")

        fake_issues = FakeGitHubIssues(issues={6423: objective, 6513: plan})
        fake_github = FakeGitHub()

        runner = CliRunner()
        result = runner.invoke(
            objective_update_context,
            ["--pr", "9999", "--objective", "6423", "--branch", "P6513-some-branch"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "9999" in data["error"]

    def test_bad_branch_pattern(self, tmp_path: Path) -> None:
        """Returns error JSON when branch doesn't match P<number>-... pattern."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeGitHub()

        runner = CliRunner()
        result = runner.invoke(
            objective_update_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "feature-branch"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "feature-branch" in data["error"]

    def test_plan_not_found(self, tmp_path: Path) -> None:
        """Returns error JSON when plan issue not found."""
        objective = _make_issue(number=6423, title="My Objective", body="objective body")
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective})
        fake_github = FakeGitHub(pr_details={6517: pr})

        runner = CliRunner()
        result = runner.invoke(
            objective_update_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "P6513-some-branch"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "6513" in data["error"]
