"""Unit tests for create-plan-from-context command."""

import json

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.create_plan_from_context import (
    create_plan_from_context,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues


def test_create_plan_from_context_success() -> None:
    """Test successful draft PR creation from plan."""
    fake_gh = FakeGitHubIssues()
    fake_github = FakeGitHub(issues_gateway=fake_gh)
    runner = CliRunner()

    plan = "# My Feature\n\n- Step 1\n- Step 2"

    result = runner.invoke(
        create_plan_from_context,
        input=plan,
        obj=ErkContext.for_test(github=fake_github),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_number"] == 999
    assert "branch_name" in output

    # Verify draft PR was created
    assert len(fake_github.created_prs) == 1


def test_create_plan_from_context_empty_plan() -> None:
    """Test error handling for empty plan."""
    fake_gh = FakeGitHubIssues()
    fake_github = FakeGitHub(issues_gateway=fake_gh)
    runner = CliRunner()

    result = runner.invoke(
        create_plan_from_context,
        input="",
        obj=ErkContext.for_test(github=fake_github),
    )

    assert result.exit_code == 1
    assert "Error: Empty plan content" in result.output


def test_create_plan_from_context_unicode() -> None:
    """Test draft PR creation with unicode content."""
    fake_gh = FakeGitHubIssues()
    fake_github = FakeGitHub(issues_gateway=fake_gh)
    runner = CliRunner()

    plan = "# café Feature 你好\n\n- Unicode test"

    result = runner.invoke(
        create_plan_from_context,
        input=plan,
        obj=ErkContext.for_test(github=fake_github),
    )

    assert result.exit_code == 0
    # Verify draft PR was created
    assert len(fake_github.created_prs) == 1
