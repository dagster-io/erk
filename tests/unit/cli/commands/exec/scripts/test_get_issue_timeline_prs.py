"""Unit tests for get-issue-timeline-prs command."""

import json

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_issue_timeline_prs import (
    get_issue_timeline_prs,
)
from erk_shared.context import ErkContext
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.issues.types import PRReference


def test_get_issue_timeline_prs_returns_empty_list() -> None:
    """Test successful fetch with no PR references."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        get_issue_timeline_prs,
        ["42"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42
    assert output["prs"] == []


def test_get_issue_timeline_prs_returns_pr_list() -> None:
    """Test successful fetch with multiple PR references."""
    pr_refs = [
        PRReference(number=100, state="MERGED", is_draft=False),
        PRReference(number=101, state="OPEN", is_draft=True),
        PRReference(number=102, state="CLOSED", is_draft=False),
    ]
    fake_gh = FakeGitHubIssues(pr_references={42: pr_refs})
    runner = CliRunner()

    result = runner.invoke(
        get_issue_timeline_prs,
        ["42"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42
    assert len(output["prs"]) == 3
    assert output["prs"][0] == {"number": 100, "state": "MERGED", "is_draft": False}
    assert output["prs"][1] == {"number": 101, "state": "OPEN", "is_draft": True}
    assert output["prs"][2] == {"number": 102, "state": "CLOSED", "is_draft": False}


def test_get_issue_timeline_prs_different_issue_numbers() -> None:
    """Test that PR references are scoped to specific issue number."""
    fake_gh = FakeGitHubIssues(
        pr_references={
            42: [PRReference(number=100, state="MERGED", is_draft=False)],
            99: [PRReference(number=200, state="OPEN", is_draft=False)],
        }
    )
    runner = CliRunner()

    # Query for issue 42
    result = runner.invoke(
        get_issue_timeline_prs,
        ["42"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["issue_number"] == 42
    assert len(output["prs"]) == 1
    assert output["prs"][0]["number"] == 100


def test_json_output_structure() -> None:
    """Test JSON output structure contains expected fields."""
    fake_gh = FakeGitHubIssues(
        pr_references={
            123: [PRReference(number=456, state="OPEN", is_draft=False)],
        }
    )
    runner = CliRunner()

    result = runner.invoke(
        get_issue_timeline_prs,
        ["123"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify top-level keys
    assert "success" in output
    assert "issue_number" in output
    assert "prs" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["prs"], list)

    # Verify PR structure
    pr = output["prs"][0]
    assert "number" in pr
    assert "state" in pr
    assert "is_draft" in pr
