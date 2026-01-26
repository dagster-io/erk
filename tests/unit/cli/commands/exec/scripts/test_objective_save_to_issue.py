"""Unit tests for objective-save-to-issue command."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.objective_save_to_issue import (
    objective_save_to_issue,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.learn.extraction.claude_installation.fake import (
    FakeClaudeInstallation,
)

# Valid plan content that passes validation (100+ chars with structure)
VALID_PLAN_CONTENT = """# Feature Objective

This objective describes the implementation of a new feature.

- Step 1: Set up the environment
- Step 2: Implement the core logic
- Step 3: Add tests and documentation"""


def test_objective_save_to_issue_success() -> None:
    """Test successful objective issue creation."""
    fake_gh = FakeGitHubIssues()
    plan_content = """# My Objective

This is a comprehensive objective that includes all the necessary details.

- Step 1: Implement the feature
- Step 2: Add tests for the feature"""
    fake_store = FakeClaudeInstallation.for_test(plans={"test-plan": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        objective_save_to_issue,
        ["--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 1
    assert output["title"] == "My Objective"


def test_objective_save_to_issue_no_plan() -> None:
    """Test error when no plan found."""
    fake_gh = FakeGitHubIssues()
    # Empty session store - no plans
    fake_store = FakeClaudeInstallation.for_test()
    runner = CliRunner()

    result = runner.invoke(
        objective_save_to_issue,
        ["--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No plan found" in output["error"]


def test_objective_save_to_issue_display_format() -> None:
    """Test display output format."""
    fake_gh = FakeGitHubIssues()
    plan_content = """# Test Objective

This is a comprehensive test objective that covers the implementation.

- Implementation step
- Documentation step"""
    fake_store = FakeClaudeInstallation.for_test(plans={"display-test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        objective_save_to_issue,
        ["--format", "display"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0
    assert "Objective saved to GitHub issue #1" in result.output
    assert "Title: Test Objective" in result.output
    assert "URL: " in result.output


# --- Scratch plan priority tests ---


def test_objective_save_to_issue_scratch_plan_has_priority_over_claude_plans(
    tmp_path: Path,
) -> None:
    """Test that scratch directory plan takes priority over ~/.claude/plans/ lookup."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )
    test_session_id = "scratch-priority-session"

    # Content in scratch directory (should be used)
    scratch_plan_content = """# Scratch Objective

This objective is from the scratch directory and should be used.

- Step 1: Do something from scratch
- Step 2: More scratch steps"""

    # Content in Claude plans directory (should NOT be used)
    claude_plan_content = """# Claude Objective

This objective is from Claude plans directory and should NOT be used.

- Step 1: Do something from Claude plans
- Step 2: More Claude plans steps"""

    fake_store = FakeClaudeInstallation.for_test(
        plans={"session-plan": claude_plan_content},
        session_slugs={test_session_id: ["session-plan"]},
    )

    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        # Create scratch plan file
        scratch_dir = Path(td) / ".erk" / "scratch" / "sessions" / test_session_id
        scratch_dir.mkdir(parents=True)
        scratch_plan_file = scratch_dir / "plan.md"
        scratch_plan_file.write_text(scratch_plan_content, encoding="utf-8")

        result = runner.invoke(
            objective_save_to_issue,
            ["--format", "json", "--session-id", test_session_id],
            obj=ErkContext.for_test(
                github_issues=fake_gh,
                git=fake_git,
                claude_installation=fake_store,
                cwd=Path(td),
                repo_root=Path(td),
            ),
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = json.loads(result.output)
        assert output["success"] is True
        # Title should come from scratch plan, not Claude plan
        assert output["title"] == "Scratch Objective"


def test_objective_save_to_issue_falls_back_to_claude_plans_when_no_scratch(
    tmp_path: Path,
) -> None:
    """Test fallback to Claude plans when scratch directory has no plan."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )
    test_session_id = "fallback-session"

    # Only Claude plans directory has content
    claude_plan_content = """# Fallback Objective

This objective is from Claude plans directory as fallback.

- Step 1: Fallback step
- Step 2: More fallback steps"""

    fake_store = FakeClaudeInstallation.for_test(
        plans={"fallback-plan": claude_plan_content},
        session_slugs={test_session_id: ["fallback-plan"]},
    )

    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        # Create empty scratch directory (no plan.md)
        scratch_dir = Path(td) / ".erk" / "scratch" / "sessions" / test_session_id
        scratch_dir.mkdir(parents=True)
        # No plan.md file created

        result = runner.invoke(
            objective_save_to_issue,
            ["--format", "json", "--session-id", test_session_id],
            obj=ErkContext.for_test(
                github_issues=fake_gh,
                git=fake_git,
                claude_installation=fake_store,
                cwd=Path(td),
                repo_root=Path(td),
            ),
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = json.loads(result.output)
        assert output["success"] is True
        # Title should come from Claude plan (fallback)
        assert output["title"] == "Fallback Objective"


def test_objective_save_to_issue_scratch_not_checked_without_session_id() -> None:
    """Test that scratch is not checked when no session_id is provided."""
    fake_gh = FakeGitHubIssues()
    # Only Claude plans directory has content
    plan_content = """# No Session Objective

This objective is found without session ID.

- Step 1: Basic step
- Step 2: More steps"""

    fake_store = FakeClaudeInstallation.for_test(plans={"no-session-plan": plan_content})

    runner = CliRunner()

    result = runner.invoke(
        objective_save_to_issue,
        ["--format", "json"],  # No --session-id
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["title"] == "No Session Objective"


# --- Session deduplication tests ---


def test_objective_save_to_issue_idempotency_prevents_duplicates(
    tmp_path: Path,
) -> None:
    """Test that calling objective-save-to-issue twice returns the existing issue."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )
    test_session_id = "idempotency-session"

    plan_content = """# Idempotent Objective

This objective should only be created once.

- Step 1: Do something
- Step 2: More steps"""

    fake_store = FakeClaudeInstallation.for_test(
        plans={"idempotent-plan": plan_content},
        session_slugs={test_session_id: ["idempotent-plan"]},
    )

    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        ctx = ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            claude_installation=fake_store,
            cwd=Path(td),
            repo_root=Path(td),
        )

        # First call - should create issue
        result1 = runner.invoke(
            objective_save_to_issue,
            ["--format", "json", "--session-id", test_session_id],
            obj=ctx,
        )

        assert result1.exit_code == 0, f"First call failed: {result1.output}"
        output1 = json.loads(result1.output)
        assert output1["success"] is True
        assert output1["issue_number"] == 1
        assert output1.get("skipped_duplicate") is not True

        # Second call - should return existing issue (not create duplicate)
        result2 = runner.invoke(
            objective_save_to_issue,
            ["--format", "json", "--session-id", test_session_id],
            obj=ctx,
        )

        assert result2.exit_code == 0, f"Second call failed: {result2.output}"
        output2 = json.loads(result2.output)
        assert output2["success"] is True
        assert output2["issue_number"] == 1  # Same issue number
        assert output2["skipped_duplicate"] is True
        assert "already saved objective #1" in output2["message"]


def test_objective_save_to_issue_idempotency_display_format(
    tmp_path: Path,
) -> None:
    """Test idempotency with display format shows appropriate message."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )
    test_session_id = "display-idempotency-session"

    plan_content = """# Display Idempotent Objective

This objective tests display format idempotency.

- Step 1: Do something
- Step 2: More steps"""

    fake_store = FakeClaudeInstallation.for_test(
        plans={"display-idempotent-plan": plan_content},
        session_slugs={test_session_id: ["display-idempotent-plan"]},
    )

    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        ctx = ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            claude_installation=fake_store,
            cwd=Path(td),
            repo_root=Path(td),
        )

        # First call - create issue
        result1 = runner.invoke(
            objective_save_to_issue,
            ["--format", "display", "--session-id", test_session_id],
            obj=ctx,
        )
        assert result1.exit_code == 0

        # Second call with display format - should show skip message
        result2 = runner.invoke(
            objective_save_to_issue,
            ["--format", "display", "--session-id", test_session_id],
            obj=ctx,
        )

        assert result2.exit_code == 0
        assert "already saved objective #1" in result2.output
        assert "Skipping duplicate creation" in result2.output
