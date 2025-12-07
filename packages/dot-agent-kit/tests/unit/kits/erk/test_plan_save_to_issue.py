"""Unit tests for plan-save-to-issue command."""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from erk_shared.extraction.session_context import SessionContextResult
from erk_shared.extraction.types import BranchContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues import FakeGitHubIssues

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


def test_plan_save_to_issue_format() -> None:
    """Verify plan format (metadata in body, plan in comment)."""
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

    # Verify: metadata in body
    assert len(fake_gh.created_issues) == 1
    _title, body, _labels = fake_gh.created_issues[0]
    assert "plan-header" in body
    assert "schema_version: '2'" in body
    assert "Step 1" not in body  # Plan NOT in body

    # Verify: plan in first comment
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


def test_plan_save_to_issue_session_context_captured(tmp_path: Path) -> None:
    """Test that session context is captured and posted as comments."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    plan = "# Feature Plan\n\n- Step 1"

    # Create a mock SessionContextResult
    branch_context = BranchContext(
        current_branch="feature-branch",
        trunk_branch="main",
        is_on_trunk=False,
    )
    session_result = SessionContextResult(
        combined_xml="<session><user>Hello</user></session>",
        session_ids=["test-session-id"],
        branch_context=branch_context,
    )

    with (
        patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
            return_value=plan,
        ),
        patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.collect_session_context",
            return_value=session_result,
        ),
    ):
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json"],
            obj=DotAgentContext.for_test(github_issues=fake_gh, git=fake_git),
        )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["session_context_chunks"] >= 1
    assert output["session_ids"] == ["test-session-id"]

    # Verify: plan comment + at least one session context comment
    assert len(fake_gh.added_comments) >= 2
    # First comment is the plan
    _issue_num1, plan_comment = fake_gh.added_comments[0]
    assert "Step 1" in plan_comment

    # Second comment is session context
    _issue_num2, session_comment = fake_gh.added_comments[1]
    assert "session-content" in session_comment


def test_plan_save_to_issue_session_context_skipped_when_none() -> None:
    """Test session context is skipped when collect_session_context returns None."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    plan = "# Feature Plan\n\n- Step 1"

    with (
        patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
            return_value=plan,
        ),
        patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.collect_session_context",
            return_value=None,  # No session context available
        ),
    ):
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json"],
            obj=DotAgentContext.for_test(github_issues=fake_gh, git=fake_git),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["session_context_chunks"] == 0
    assert output["session_ids"] == []

    # Only plan comment, no session context
    assert len(fake_gh.added_comments) == 1


def test_plan_save_to_issue_json_output_includes_session_metadata() -> None:
    """Test JSON output includes session_context_chunks and session_ids fields."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    plan = "# Feature\n\n- Step 1"

    # Test with no session context - fields should still be present
    with (
        patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
            return_value=plan,
        ),
        patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.collect_session_context",
            return_value=None,
        ),
    ):
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json"],
            obj=DotAgentContext.for_test(github_issues=fake_gh, git=fake_git),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify both fields are always present
    assert "session_context_chunks" in output
    assert "session_ids" in output
    assert isinstance(output["session_context_chunks"], int)
    assert isinstance(output["session_ids"], list)


def test_plan_save_to_issue_passes_session_id_to_collect_session_context() -> None:
    """Test that --session-id argument is forwarded to collect_session_context."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    plan = "# Feature Plan\n\n- Step 1"
    test_session_id = "test-session-12345"

    with (
        patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
            return_value=plan,
        ),
        patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.collect_session_context",
            return_value=None,
        ) as mock_collect,
    ):
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json", "--session-id", test_session_id],
            obj=DotAgentContext.for_test(github_issues=fake_gh, git=fake_git),
        )

    assert result.exit_code == 0, f"Failed: {result.output}"

    # Verify collect_session_context was called with the session_id
    mock_collect.assert_called_once()
    call_kwargs = mock_collect.call_args.kwargs
    assert call_kwargs.get("current_session_id") == test_session_id


def test_plan_save_to_issue_display_format_shows_session_context() -> None:
    """Test display format shows session context chunk count when present."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    plan = "# Feature Plan\n\n- Step 1"

    branch_context = BranchContext(
        current_branch="feature-branch",
        trunk_branch="main",
        is_on_trunk=False,
    )
    session_result = SessionContextResult(
        combined_xml="<session><user>Hello</user></session>",
        session_ids=["test-session-id"],
        branch_context=branch_context,
    )

    with (
        patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
            return_value=plan,
        ),
        patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.collect_session_context",
            return_value=session_result,
        ),
    ):
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "display"],
            obj=DotAgentContext.for_test(github_issues=fake_gh, git=fake_git),
        )

    assert result.exit_code == 0
    assert "Session context:" in result.output
    assert "chunks" in result.output
