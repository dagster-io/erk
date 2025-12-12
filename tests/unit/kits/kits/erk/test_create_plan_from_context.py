"""Unit tests for create-plan-from-context command."""

import json

from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.create_plan_from_context import (
    create_plan_from_context,
)
from erk_shared.context import ErkContext
from erk_shared.github.issues import FakeGitHubIssues


def test_create_plan_issue_success() -> None:
    """Test successful issue creation from plan."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# My Feature\n\n- Step 1\n- Step 2"

    result = runner.invoke(
        create_plan_from_context,
        input=plan,
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 1
    assert "github.com/test-owner/test-repo/issues/1" in output["issue_url"]

    # Verify behavior through fake's mutation tracking
    assert len(fake_gh.created_issues) == 1
    title, body, labels = fake_gh.created_issues[0]
    assert title == "My Feature [erk-plan]"
    assert "erk-plan" in labels
    assert "Step 1" in body


def test_create_plan_issue_empty_plan() -> None:
    """Test error handling for empty plan."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_plan_from_context,
        input="",
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    assert "Error: Empty plan content" in result.output


def test_create_plan_issue_unicode() -> None:
    """Test issue creation with unicode content."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# café Feature 你好\n\n- Unicode test"

    result = runner.invoke(
        create_plan_from_context,
        input=plan,
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    # Verify issue was created (title will have unicode characters)
    assert len(fake_gh.created_issues) == 1


def test_create_plan_issue_ensures_label() -> None:
    """Test that command ensures erk-plan label exists."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# Test Plan\n\n- Step"

    result = runner.invoke(
        create_plan_from_context,
        input=plan,
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    # Verify label was created
    assert len(fake_gh.created_labels) == 1
    label, description, color = fake_gh.created_labels[0]
    assert label == "erk-plan"
    assert description == "Implementation plan for manual execution"
    assert color == "0E8A16"


def test_create_plan_issue_h2_title() -> None:
    """Test title extraction falls back to H2."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "## Secondary Title\n\n- Step"

    result = runner.invoke(
        create_plan_from_context,
        input=plan,
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    # Verify issue was created with H2 title (with [erk-plan] suffix)
    assert len(fake_gh.created_issues) == 1
    title, _body, _labels = fake_gh.created_issues[0]
    assert title == "Secondary Title [erk-plan]"


def test_create_plan_issue_preserves_body() -> None:
    """Test that full plan content is preserved in issue body."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = """# Feature Plan

## Context

Background information

## Steps

1. First step
2. Second step

## Testing

Test instructions
"""

    result = runner.invoke(
        create_plan_from_context,
        input=plan,
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    # Verify full plan content is preserved
    assert len(fake_gh.created_issues) == 1
    _title, body, _labels = fake_gh.created_issues[0]
    assert "## Context" in body
    assert "## Steps" in body
    assert "## Testing" in body
    assert "First step" in body
