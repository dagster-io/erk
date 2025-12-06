"""Unit tests for create-extraction-plan command."""

import json
from pathlib import Path

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.scratch.markers import PENDING_EXTRACTION_MARKER, create_marker, marker_exists

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_extraction_plan import (
    create_extraction_plan,
)


def test_create_extraction_plan_with_plan_content_success(tmp_path: Path) -> None:
    """Test successful issue creation with --plan-content option."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan_content = "# Extraction Plan\n\n## Items\n\n- Item 1"
    session_id = "test-session-123"

    result = runner.invoke(
        create_extraction_plan,
        [
            "--plan-content",
            plan_content,
            "--session-id",
            session_id,
            "--extraction-session-ids",
            session_id,
        ],
        obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 1
    assert output["title"] == "Extraction Plan"
    assert output["plan_type"] == "extraction"
    assert session_id in output["extraction_session_ids"]
    # scratch_path should be present when using --plan-content
    assert "scratch_path" in output
    assert session_id in output["scratch_path"]


def test_create_extraction_plan_writes_to_scratch(tmp_path: Path) -> None:
    """Test that --plan-content writes to scratch directory."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan_content = "# Test Plan\n\nContent here"
    session_id = "scratch-test-456"

    result = runner.invoke(
        create_extraction_plan,
        [
            "--plan-content",
            plan_content,
            "--session-id",
            session_id,
            "--extraction-session-ids",
            session_id,
        ],
        obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify file was written to scratch
    scratch_path = Path(output["scratch_path"])
    assert scratch_path.exists()
    assert scratch_path.read_text(encoding="utf-8") == plan_content
    assert ".erk/scratch" in str(scratch_path)
    assert session_id in str(scratch_path)


def test_create_extraction_plan_with_plan_file_success(tmp_path: Path) -> None:
    """Test backwards compatibility with --plan-file option."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    # Create a plan file
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Legacy Plan\n\nContent", encoding="utf-8")

    result = runner.invoke(
        create_extraction_plan,
        [
            "--plan-file",
            str(plan_file),
            "--extraction-session-ids",
            "session-abc",
        ],
        obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["title"] == "Legacy Plan"
    # scratch_path should NOT be present when using --plan-file
    assert "scratch_path" not in output


def test_create_extraction_plan_requires_plan_content_or_file() -> None:
    """Test error when neither --plan-content nor --plan-file provided."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_extraction_plan,
        ["--extraction-session-ids", "session-123"],
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Must provide either --plan-content or --plan-file" in output["error"]


def test_create_extraction_plan_rejects_both_options(tmp_path: Path) -> None:
    """Test error when both --plan-content and --plan-file provided."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Plan", encoding="utf-8")

    result = runner.invoke(
        create_extraction_plan,
        [
            "--plan-content",
            "# Plan",
            "--plan-file",
            str(plan_file),
            "--extraction-session-ids",
            "session-123",
        ],
        obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Cannot provide both --plan-content and --plan-file" in output["error"]


def test_create_extraction_plan_requires_session_id_with_content(tmp_path: Path) -> None:
    """Test error when --plan-content is provided without --session-id."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_extraction_plan,
        [
            "--plan-content",
            "# Plan",
            "--extraction-session-ids",
            "session-123",
        ],
        obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "--session-id is required when using --plan-content" in output["error"]


def test_create_extraction_plan_requires_extraction_session_ids(tmp_path: Path) -> None:
    """Test error when no extraction_session_ids provided."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_extraction_plan,
        [
            "--plan-content",
            "# Plan",
            "--session-id",
            "session-123",
        ],
        obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "extraction_session_id is required" in output["error"]


def test_create_extraction_plan_empty_content_error(tmp_path: Path) -> None:
    """Test error when plan content is empty."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_extraction_plan,
        [
            "--plan-content",
            "   ",  # Whitespace only
            "--session-id",
            "session-123",
            "--extraction-session-ids",
            "session-123",
        ],
        obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Empty plan content" in output["error"]


def test_create_extraction_plan_creates_labels(tmp_path: Path) -> None:
    """Test that erk-plan and erk-extraction labels are created."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_extraction_plan,
        [
            "--plan-content",
            "# Extraction\n\nContent",
            "--session-id",
            "session-123",
            "--extraction-session-ids",
            "session-123",
        ],
        obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
    )

    assert result.exit_code == 0

    # Verify labels were created
    label_names = [label[0] for label in fake_gh.created_labels]
    assert "erk-plan" in label_names
    assert "erk-extraction" in label_names


def test_create_extraction_plan_issue_format(tmp_path: Path) -> None:
    """Verify extraction plan format (metadata in body, plan in comment)."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_extraction_plan,
        [
            "--plan-content",
            "# My Extraction\n\n- Step 1",
            "--session-id",
            "session-abc",
            "--extraction-session-ids",
            "session-abc",
        ],
        obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
    )

    assert result.exit_code == 0

    # Verify: metadata in body
    assert len(fake_gh.created_issues) == 1
    title, body, labels = fake_gh.created_issues[0]
    assert "[erk-extraction]" in title
    assert "plan-header" in body
    assert "plan_type: extraction" in body
    assert "Step 1" not in body  # Plan NOT in body

    # Verify: plan in first comment
    assert len(fake_gh.added_comments) == 1
    _issue_num, comment = fake_gh.added_comments[0]
    assert "Step 1" in comment

    # Verify labels
    assert "erk-plan" in labels
    assert "erk-extraction" in labels


def test_create_extraction_plan_deletes_pending_extraction_marker(tmp_path: Path) -> None:
    """Test that pending extraction marker is deleted on success."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    # Create the pending extraction marker before running command
    create_marker(tmp_path, PENDING_EXTRACTION_MARKER)
    assert marker_exists(tmp_path, PENDING_EXTRACTION_MARKER)

    result = runner.invoke(
        create_extraction_plan,
        [
            "--plan-content",
            "# Extraction Plan\n\n## Items\n\n- Item 1",
            "--session-id",
            "test-session-123",
            "--extraction-session-ids",
            "test-session-123",
        ],
        obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path, cwd=tmp_path),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"

    # Verify marker was deleted
    assert not marker_exists(tmp_path, PENDING_EXTRACTION_MARKER)
