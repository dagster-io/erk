"""Unit tests for track-learn-evaluation exec script.

Tests learn evaluation tracking on plan issues.
Uses fakes for fast, reliable testing without subprocess calls.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.track_learn_evaluation import track_learn_evaluation
from erk_shared.context.context import ErkContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.metadata.core import find_metadata_block
from tests.test_utils.github_helpers import create_test_issue
from tests.test_utils.plan_helpers import format_plan_header_body_for_test

# ============================================================================
# Success Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_track_learn_evaluation_posts_comment_and_updates_header(tmp_path: Path) -> None:
    """Test tracking posts comment and updates plan-header on issue."""
    fake_git = FakeGit()
    plan_body = format_plan_header_body_for_test()
    fake_issues = FakeGitHubIssues(issues={42: create_test_issue(42, "Test Plan #42", plan_body)})

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            track_learn_evaluation,
            ["42", "--session-id=test-session-123"],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42
    assert output["tracked"] is True

    # Verify comment was posted
    assert len(fake_issues.added_comments) == 1
    issue_num, comment_body, _comment_id = fake_issues.added_comments[0]
    assert issue_num == 42
    assert "learn-invoked" in comment_body
    assert "test-session-123" in comment_body

    # Verify plan-header was updated with learn fields
    updated_issue = fake_issues.get_issue(cwd, 42)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data.get("last_learn_session") == "test-session-123"
    assert block.data.get("last_learn_at") is not None


def test_track_learn_evaluation_without_session_id(tmp_path: Path) -> None:
    """Test tracking works without session ID."""
    fake_git = FakeGit()
    plan_body = format_plan_header_body_for_test()
    test_issue = create_test_issue(100, "Test Plan #100", plan_body)
    fake_issues = FakeGitHubIssues(issues={100: test_issue})

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            track_learn_evaluation,
            ["100"],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 100

    # Verify comment was posted
    assert len(fake_issues.added_comments) == 1

    # Verify plan-header was updated (session is None)
    updated_issue = fake_issues.get_issue(cwd, 100)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data.get("last_learn_session") is None
    assert block.data.get("last_learn_at") is not None


def test_track_learn_evaluation_infers_from_branch(tmp_path: Path) -> None:
    """Test tracking infers issue from branch name."""
    runner = CliRunner()
    plan_body = format_plan_header_body_for_test()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        fake_git = FakeGit(
            current_branches={cwd: "P456-implement-feature"},
        )
        fake_issues = FakeGitHubIssues(
            issues={456: create_test_issue(456, "Test Plan #456", plan_body)}
        )

        result = runner.invoke(
            track_learn_evaluation,
            ["--session-id=session-xyz"],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 456


def test_track_learn_evaluation_with_url_format(tmp_path: Path) -> None:
    """Test tracking accepts GitHub URL format."""
    fake_git = FakeGit()
    plan_body = format_plan_header_body_for_test()
    test_issue = create_test_issue(789, "Test Plan #789", plan_body)
    fake_issues = FakeGitHubIssues(issues={789: test_issue})

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            track_learn_evaluation,
            ["https://github.com/owner/repo/issues/789"],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 789


# ============================================================================
# Error Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_track_learn_evaluation_fails_without_issue(tmp_path: Path) -> None:
    """Test error when no issue provided and can't infer from branch."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        fake_git = FakeGit(
            current_branches={cwd: "main"},  # Not a P{issue} branch
        )
        fake_issues = FakeGitHubIssues()

        result = runner.invoke(
            track_learn_evaluation,
            [],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No issue specified" in output["error"]


def test_track_learn_evaluation_fails_with_invalid_issue(tmp_path: Path) -> None:
    """Test error with invalid issue identifier."""
    fake_git = FakeGit()
    fake_issues = FakeGitHubIssues()

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            track_learn_evaluation,
            ["not-a-number"],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Invalid issue identifier" in output["error"]


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_json_output_structure_success(tmp_path: Path) -> None:
    """Test JSON output structure on success."""
    fake_git = FakeGit()
    plan_body = format_plan_header_body_for_test()
    test_issue = create_test_issue(200, "Test Plan #200", plan_body)
    fake_issues = FakeGitHubIssues(issues={200: test_issue})

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            track_learn_evaluation,
            ["200"],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)

    # Verify required fields
    assert "success" in output
    assert "issue_number" in output
    assert "tracked" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["tracked"], bool)


def test_json_output_structure_error(tmp_path: Path) -> None:
    """Test JSON output structure on error."""
    fake_git = FakeGit()
    fake_issues = FakeGitHubIssues()

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            track_learn_evaluation,
            ["invalid"],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)

    # Verify error fields
    assert "success" in output
    assert "error" in output
    assert output["success"] is False
    assert isinstance(output["error"], str)
