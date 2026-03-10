"""Tests for erk exec objective-post-action-comment."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.objective_post_action_comment import (
    format_action_comment,
    objective_post_action_comment,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.types import IssueInfo
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues


def _make_issue(*, number: int) -> IssueInfo:
    return IssueInfo(
        number=number,
        title="My Objective",
        body="objective body",
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-objective"],
        assignees=[],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        author="testuser",
    )


class TestFormatActionComment:
    def test_full_template(self) -> None:
        """Formats all sections correctly."""
        result = format_action_comment(
            title="Implement auth system",
            date="2026-02-17",
            pr_number=6517,
            phase_step="1.1, 1.2",
            what_was_done=["Added user model", "Added JWT library"],
            lessons_learned=["Frozen dataclasses work well"],
            roadmap_updates=["Step 1.1: pending -> done", "Step 1.2: pending -> done"],
            body_reconciliation=[
                {"section": "Design Decisions", "change": "Updated auth approach"}
            ],
        )

        assert "## Action: Implement auth system" in result
        assert "**Date:** 2026-02-17" in result
        assert "**PR:** #6517" in result
        assert "**Node:** 1.1, 1.2" in result
        assert "### What Was Done" in result
        assert "- Added user model" in result
        assert "- Added JWT library" in result
        assert "### Lessons Learned" in result
        assert "- Frozen dataclasses work well" in result
        assert "### Roadmap Updates" in result
        assert "- Step 1.1: pending -> done" in result
        assert "### Body Reconciliation" in result
        assert "- **Design Decisions**: Updated auth approach" in result

    def test_no_body_reconciliation(self) -> None:
        """Omits Body Reconciliation section when empty."""
        result = format_action_comment(
            title="Simple update",
            date="2026-02-17",
            pr_number=100,
            phase_step="1.1",
            what_was_done=["Did thing"],
            lessons_learned=["Learned thing"],
            roadmap_updates=["Step 1.1: pending -> done"],
            body_reconciliation=[],
        )

        assert "### Body Reconciliation" not in result

    def test_empty_lessons_dropped(self) -> None:
        """Empty lessons learned section is dropped entirely."""
        result = format_action_comment(
            title="Update",
            date="2026-02-17",
            pr_number=100,
            phase_step="1.1",
            what_was_done=["Did thing"],
            lessons_learned=[],
            roadmap_updates=["Step 1.1: pending -> done"],
            body_reconciliation=[],
        )

        assert "### Lessons Learned" not in result

    def test_no_pr_number(self) -> None:
        """PR line is omitted when pr_number is None."""
        result = format_action_comment(
            title="Removed node 3.6",
            date="2026-03-10",
            pr_number=None,
            phase_step="3.6",
            what_was_done=["Removed node 3.6 from roadmap"],
            lessons_learned=[],
            roadmap_updates=["Node 3.6: removed"],
            body_reconciliation=[],
        )

        assert "**PR:**" not in result
        assert "**Node:** 3.6" in result

    def test_no_phase_step(self) -> None:
        """Node line is omitted when phase_step is None."""
        result = format_action_comment(
            title="General update",
            date="2026-03-10",
            pr_number=None,
            phase_step=None,
            what_was_done=["Did something"],
            lessons_learned=[],
            roadmap_updates=[],
            body_reconciliation=[],
        )

        assert "**Node:**" not in result
        assert "**PR:**" not in result


class TestObjectivePostActionComment:
    def test_happy_path(self, tmp_path: Path) -> None:
        """Posts formatted comment and returns success."""
        objective = _make_issue(number=6423)
        fake_issues = FakeGitHubIssues(issues={6423: objective})

        input_data = json.dumps(
            {
                "issue_number": 6423,
                "date": "2026-02-17",
                "pr_number": 6517,
                "phase_step": "1.1",
                "title": "Add user model",
                "what_was_done": ["Added user model"],
                "lessons_learned": ["Works well"],
                "roadmap_updates": ["Step 1.1: pending -> done"],
            }
        )

        runner = CliRunner()
        result = runner.invoke(
            objective_post_action_comment,
            [],
            input=input_data,
            obj=ErkContext.for_test(
                github=FakeLocalGitHub(issues_gateway=fake_issues),
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert "comment_id" in data

        # Verify the comment was posted
        assert len(fake_issues.added_comments) == 1
        issue_number, body, _comment_id = fake_issues.added_comments[0]
        assert issue_number == 6423
        assert "## Action: Add user model" in body
        assert "**PR:** #6517" in body

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        """Returns error when required fields are missing."""
        fake_issues = FakeGitHubIssues()

        input_data = json.dumps({"issue_number": 6423, "date": "2026-02-17"})

        runner = CliRunner()
        result = runner.invoke(
            objective_post_action_comment,
            [],
            input=input_data,
            obj=ErkContext.for_test(
                github=FakeLocalGitHub(issues_gateway=fake_issues),
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "Missing required fields" in data["error"]

    def test_empty_stdin(self, tmp_path: Path) -> None:
        """Returns error when stdin is empty."""
        fake_issues = FakeGitHubIssues()

        runner = CliRunner()
        result = runner.invoke(
            objective_post_action_comment,
            [],
            input="",
            obj=ErkContext.for_test(
                github=FakeLocalGitHub(issues_gateway=fake_issues),
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "No input" in data["error"]

    def test_with_body_reconciliation(self, tmp_path: Path) -> None:
        """Includes Body Reconciliation section when provided."""
        objective = _make_issue(number=6423)
        fake_issues = FakeGitHubIssues(issues={6423: objective})

        input_data = json.dumps(
            {
                "issue_number": 6423,
                "date": "2026-02-17",
                "pr_number": 6517,
                "phase_step": "1.1",
                "title": "Update approach",
                "what_was_done": ["Changed approach"],
                "body_reconciliation": [
                    {"section": "Design Decisions", "change": "Switched to WebSockets"}
                ],
            }
        )

        runner = CliRunner()
        result = runner.invoke(
            objective_post_action_comment,
            [],
            input=input_data,
            obj=ErkContext.for_test(
                github=FakeLocalGitHub(issues_gateway=fake_issues),
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        _, body, _ = fake_issues.added_comments[0]
        assert "### Body Reconciliation" in body
        assert "**Design Decisions**: Switched to WebSockets" in body
