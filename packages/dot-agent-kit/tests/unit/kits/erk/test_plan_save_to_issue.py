"""Unit tests for plan-save-to-issue command."""

import json
from unittest.mock import patch

from click.testing import CliRunner
from erk_shared.github.issues.fake import FakeGitHubIssues

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue import (
    plan_save_to_issue,
)


def test_plan_save_to_issue_success() -> None:
    """Test successful plan extraction and issue creation."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# My Feature\n\n- Step 1\n- Step 2"

    with patch(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
        return_value=plan,
    ):
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json"],
            obj=DotAgentContext.for_test(github_issues=fake_gh),
        )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 1
    assert output["title"] == "My Feature"
    assert output["enriched"] is False


def test_plan_save_to_issue_enriched_plan() -> None:
    """Test detection of enriched plan."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# My Feature\n\n## Enrichment Details\n\nContext here"

    with patch(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
        return_value=plan,
    ):
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json"],
            obj=DotAgentContext.for_test(github_issues=fake_gh),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["enriched"] is True


def test_plan_save_to_issue_no_plan() -> None:
    """Test error when no plan found."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    with patch(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
        return_value=None,
    ):
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json"],
            obj=DotAgentContext.for_test(github_issues=fake_gh),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No plan found" in output["error"]


def test_plan_save_to_issue_schema_v2() -> None:
    """Verify schema v2 format (metadata in body, plan in comment)."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# Test Plan\n\n- Step 1"

    with patch(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
        return_value=plan,
    ):
        result = runner.invoke(
            plan_save_to_issue,
            [],
            obj=DotAgentContext.for_test(github_issues=fake_gh),
        )

    assert result.exit_code == 0

    # Verify schema v2: metadata in body
    assert len(fake_gh.created_issues) == 1
    _title, body, _labels = fake_gh.created_issues[0]
    assert "plan-header" in body
    assert "schema_version: '2'" in body
    assert "Step 1" not in body  # Plan NOT in body

    # Verify schema v2: plan in first comment
    assert len(fake_gh.added_comments) == 1
    _issue_num, comment = fake_gh.added_comments[0]
    assert "Step 1" in comment


def test_plan_save_to_issue_display_format() -> None:
    """Test display output format."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# Test Feature\n\n- Implementation step"

    with patch(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
        return_value=plan,
    ):
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "display"],
            obj=DotAgentContext.for_test(github_issues=fake_gh),
        )

    assert result.exit_code == 0
    assert "Plan saved to GitHub issue #1" in result.output
    assert "URL: " in result.output
    assert "Enrichment: No" in result.output


def test_plan_save_to_issue_label_created() -> None:
    """Test that erk-plan label is created."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# Feature\n\nSteps here"

    with patch(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
        return_value=plan,
    ):
        result = runner.invoke(
            plan_save_to_issue,
            [],
            obj=DotAgentContext.for_test(github_issues=fake_gh),
        )

    assert result.exit_code == 0

    # Verify label was created
    assert len(fake_gh.created_labels) == 1
    label, description, color = fake_gh.created_labels[0]
    assert label == "erk-plan"
    assert description == "Implementation plan for manual execution"
    assert color == "0E8A16"
