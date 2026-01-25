"""Unit tests for plan-save-to-issue command."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_save_to_issue import (
    plan_save_to_issue,
)
from erk_shared.context.context import ErkContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.learn.extraction.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)

# Valid plan content that passes validation (100+ chars with structure)
VALID_PLAN_CONTENT = """# Feature Plan

This plan describes the implementation of a new feature.

- Step 1: Set up the environment
- Step 2: Implement the core logic
- Step 3: Add tests and documentation"""


def test_plan_save_to_issue_success() -> None:
    """Test successful plan extraction and issue creation."""
    fake_gh = FakeGitHubIssues()
    plan_content = """# My Feature

This is a comprehensive feature plan that includes all the necessary details.

- Step 1: Implement the feature
- Step 2: Add tests for the feature"""
    fake_store = FakeClaudeInstallation.for_test(plans={"test-plan": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
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
    assert output["title"] == "My Feature"


def test_plan_save_to_issue_no_plan() -> None:
    """Test error when no plan found."""
    fake_gh = FakeGitHubIssues()
    # Empty session store - no plans
    fake_store = FakeClaudeInstallation.for_test()
    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
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


def test_plan_save_to_issue_format() -> None:
    """Verify plan format (metadata in body, plan in comment)."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    plan_content = VALID_PLAN_CONTENT
    fake_store = FakeClaudeInstallation.for_test(plans={"format-test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        [],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            claude_installation=fake_store,
        ),
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
    _issue_num, comment, _comment_id = fake_gh.added_comments[0]
    assert "Step 1" in comment


def test_plan_save_to_issue_display_format() -> None:
    """Test display output format."""
    fake_gh = FakeGitHubIssues()
    plan_content = """# Test Feature

This is a comprehensive test feature that covers the implementation.

- Implementation step
- Documentation step"""
    fake_store = FakeClaudeInstallation.for_test(plans={"display-test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "display"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0
    assert "Plan saved to GitHub issue #1" in result.output
    assert "Title: Test Feature" in result.output
    assert "URL: " in result.output
    # Verify Next steps section with copy/pasteable commands
    assert "Next steps:" in result.output
    assert "View Issue: gh issue view 1 --web" in result.output
    # Verify Claude Code slash command options
    assert "In Claude Code:" in result.output
    assert "Prepare worktree: /erk:prepare" in result.output
    assert "Submit to queue: /erk:plan-submit" in result.output
    # Verify exit Claude Code note and CLI commands
    assert "OR exit Claude Code first, then run one of:" in result.output
    assert "Local: erk prepare 1" in result.output
    assert (
        'Prepare+Implement: source "$(erk prepare 1 --script)" && erk implement --dangerous'
        in result.output
    )
    assert "Submit to Queue: erk plan submit 1" in result.output


def test_plan_save_to_issue_label_created() -> None:
    """Test that erk-plan label is created."""
    fake_gh = FakeGitHubIssues()
    plan_content = """# Feature

This feature adds a new capability to the system with comprehensive testing.

- Step 1: Implement core logic
- Step 2: Add unit tests"""
    fake_store = FakeClaudeInstallation.for_test(plans={"label-test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        [],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0

    # Verify label was created
    assert len(fake_gh.created_labels) == 1
    label, description, color = fake_gh.created_labels[0]
    assert label == "erk-plan"
    assert description == "Implementation plan for manual execution"
    assert color == "0E8A16"


def test_plan_save_to_issue_session_context_removed(tmp_path: Path) -> None:
    """Test that session context embedding feature has been removed."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )

    # Create session data and plan in FakeClaudeInstallation
    session_content = (
        '{"type": "user", "message": {"content": "Hello"}}\n'
        '{"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi!"}]}}\n'
    )
    plan_content = VALID_PLAN_CONTENT
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "test-session-id": FakeSessionData(
                        content=session_content,
                        size_bytes=2000,
                        modified_at=1234567890.0,
                    )
                }
            )
        },
        plans={"session-context-test": plan_content},
        session_slugs={"test-session-id": ["session-context-test"]},
    )

    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json", "--session-id", "test-session-id"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            claude_installation=fake_store,
            cwd=tmp_path,
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    # Session embedding fields are no longer present in output
    assert "session_context_chunks" not in output
    assert "session_ids" not in output

    # Plan comment + session exchanges comment are posted (but no session context)
    assert len(fake_gh.added_comments) == 2
    _issue_num, plan_comment, _comment_id = fake_gh.added_comments[0]
    assert "Step 1" in plan_comment
    _issue_num2, exchanges_comment, _comment_id2 = fake_gh.added_comments[1]
    assert "planning-session-prompts" in exchanges_comment
    assert "Hello" in exchanges_comment  # The user message from session_content
    # Verify it's using exchange format (with *User:* instead of **Prompt N:**)
    assert "*User:*" in exchanges_comment


def test_plan_save_to_issue_no_session_exchanges_without_session_id() -> None:
    """Test session exchanges comment is skipped when no session ID provided."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    plan_content = VALID_PLAN_CONTENT
    # Session store with no sessions but has a plan
    fake_store = FakeClaudeInstallation.for_test(plans={"no-session-test": plan_content})

    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    # Session embedding fields are no longer present
    assert "session_context_chunks" not in output
    assert "session_ids" not in output

    # Only plan comment, no session exchanges without session ID
    assert len(fake_gh.added_comments) == 1


def test_plan_save_to_issue_json_output_no_session_metadata() -> None:
    """Test JSON output no longer includes session embedding fields."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    plan_content = VALID_PLAN_CONTENT
    fake_store = FakeClaudeInstallation.for_test(plans={"metadata-test": plan_content})

    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify session embedding fields are NOT present (feature removed)
    assert "session_context_chunks" not in output
    assert "session_ids" not in output
    # Verify core fields are present
    assert "success" in output
    assert "issue_number" in output
    assert "title" in output


def test_plan_save_to_issue_session_id_still_creates_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that --session-id argument still creates marker file."""
    _ = monkeypatch  # Unused but kept for test signature compatibility
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )

    test_session_id = "test-session-12345"
    plan_content = VALID_PLAN_CONTENT

    fake_store = FakeClaudeInstallation.for_test(plans={"session-id-test": plan_content})

    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(
            plan_save_to_issue,
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
        # Session embedding fields are no longer present
        assert "session_ids" not in output
        assert "session_context_chunks" not in output

        # Marker file should still be created
        marker_file = (
            Path(td)
            / ".erk"
            / "scratch"
            / "sessions"
            / test_session_id
            / "exit-plan-mode-hook.plan-saved.marker"
        )
        assert marker_file.exists()


def test_plan_save_to_issue_display_format_no_session_context_shown(tmp_path: Path) -> None:
    """Test display format does NOT show session context (feature disabled)."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )

    session_content = '{"type": "user", "message": {"content": "Hello"}}\n'
    plan_content = VALID_PLAN_CONTENT
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "test-session-id": FakeSessionData(
                        content=session_content,
                        size_bytes=2000,
                        modified_at=1234567890.0,
                    )
                }
            )
        },
        plans={"display-session-test": plan_content},
        session_slugs={"test-session-id": ["display-session-test"]},
    )

    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "display", "--session-id", "test-session-id"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            claude_installation=fake_store,
            cwd=tmp_path,
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0
    # Session context embedding is disabled - no session context line shown
    assert "Session context:" not in result.output


def test_plan_save_to_issue_no_session_exchanges_without_flag(tmp_path: Path) -> None:
    """Test that no session exchanges are posted when --session-id is not provided."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )

    session_content = '{"type": "user", "message": {"content": "Test"}}\n'
    plan_content = VALID_PLAN_CONTENT

    # Session store has sessions but no session ID is passed via CLI
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "some-session-id": FakeSessionData(
                        content=session_content,
                        size_bytes=2000,
                        modified_at=1234567890.0,
                    )
                }
            )
        },
        plans={"store-session-test": plan_content},
    )

    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],  # No --session-id flag
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            claude_installation=fake_store,
            cwd=tmp_path,
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    # Session embedding fields are no longer present
    assert "session_ids" not in output
    assert "session_context_chunks" not in output


def test_plan_save_to_issue_session_id_posts_exchanges_comment(tmp_path: Path) -> None:
    """Test --session-id flag posts session exchanges comment.

    When --session-id is provided, session exchanges (prompts with context)
    are posted as a comment, but NOT the full session embedding.
    """
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )

    flag_session_id = "flag-based-session-id"
    session_content = '{"type": "user", "message": {"content": "Test"}}\n'
    plan_content = VALID_PLAN_CONTENT

    # Session store has the session that matches the flag
    fake_store = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    flag_session_id: FakeSessionData(
                        content=session_content,
                        size_bytes=2000,
                        modified_at=1234567891.0,
                    ),
                }
            )
        },
        plans={"session-flag-test": plan_content},
        session_slugs={flag_session_id: ["session-flag-test"]},
    )

    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json", "--session-id", flag_session_id],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            claude_installation=fake_store,
            cwd=tmp_path,
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    # Session embedding fields are no longer present
    assert "session_ids" not in output
    assert "session_context_chunks" not in output


def test_plan_save_to_issue_creates_marker_file(tmp_path: Path) -> None:
    """Test plan_save_to_issue creates marker file on success."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    test_session_id = "marker-test-session-id"
    plan_content = VALID_PLAN_CONTENT
    fake_store = FakeClaudeInstallation.for_test(plans={"marker-test": plan_content})
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json", "--session-id", test_session_id],
            obj=ErkContext.for_test(
                github_issues=fake_gh,
                git=fake_git,
                claude_installation=fake_store,
                repo_root=Path(td),
            ),
        )

        assert result.exit_code == 0, f"Failed: {result.output}"

        # Verify marker file was created at correct path with sessions/ segment
        marker_file = (
            Path(td)
            / ".erk"
            / "scratch"
            / "sessions"
            / test_session_id
            / "exit-plan-mode-hook.plan-saved.marker"
        )
        assert marker_file.exists()

        # Verify marker file has descriptive content
        content = marker_file.read_text(encoding="utf-8")
        assert "Created by:" in content
        assert "Trigger:" in content
        assert "Effect:" in content
        assert "Lifecycle:" in content


def test_plan_save_to_issue_no_marker_without_session_id(tmp_path: Path) -> None:
    """Test marker file is not created when no session ID is provided."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    plan_content = VALID_PLAN_CONTENT
    # Session store has plan but no session ID will be passed
    fake_store = FakeClaudeInstallation.for_test(plans={"no-marker-test": plan_content})
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json"],  # No --session-id, and store has None
            obj=ErkContext.for_test(
                github_issues=fake_gh, git=fake_git, claude_installation=fake_store
            ),
        )

        assert result.exit_code == 0, f"Failed: {result.output}"

        # Verify no marker directories were created
        scratch_dir = Path(td) / ".erk" / "scratch"
        if scratch_dir.exists():
            # Only the scratch dir should exist (no subdirectories)
            subdirs = list(scratch_dir.iterdir())
            # Should be empty or only contain current-session-id file (not directories)
            for item in subdirs:
                assert not item.is_dir(), f"Unexpected directory: {item}"


def test_plan_save_to_issue_preserves_plan_file_after_save(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify Claude plan file is PRESERVED after save (not deleted).

    The plan file is kept after save to allow modifications and re-saving.
    Deletion now happens at implementation start (via impl-signal started),
    not at save time. This allows the user to modify and re-save the plan
    before implementing.
    """
    fake_gh = FakeGitHubIssues()
    test_session_id = "delete-test-session"
    test_slug = "test-plan-slug"
    plan_content = VALID_PLAN_CONTENT

    # Set up a real plans directory so we can verify deletion
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    plan_file = plans_dir / f"{test_slug}.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    fake_store = FakeClaudeInstallation.for_test(
        plans={test_slug: plan_content},
        session_slugs={test_session_id: [test_slug]},
        plans_dir_path=plans_dir,
    )

    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json", "--session-id", test_session_id],
            obj=ErkContext.for_test(
                github_issues=fake_gh,
                claude_installation=fake_store,
                cwd=Path(td),
                repo_root=Path(td),
            ),
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = json.loads(result.output)
        assert output["success"] is True

        # Verify the plan file is STILL present (not deleted)
        # Deletion now happens at implementation start (impl-signal started)
        assert plan_file.exists(), "Plan file should be preserved after save"


def test_plan_save_to_issue_learned_from_issue_sets_metadata() -> None:
    """Test --learned-from-issue flag sets learned_from_issue in plan metadata."""
    fake_gh = FakeGitHubIssues()
    plan_content = """# Learn Plan

This plan documents the learnings and insights from the implementation session.

- Document the architecture decisions
- Document the edge cases discovered"""
    fake_store = FakeClaudeInstallation.for_test(plans={"learn-test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json", "--plan-type", "learn", "--learned-from-issue", "123"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify issue was created with erk-learn label
    assert len(fake_gh.created_issues) == 1
    _title, body, labels = fake_gh.created_issues[0]
    assert "erk-learn" in labels

    # Verify learned_from_issue is in the metadata block
    assert "learned_from_issue: 123" in body


# --- Validation rejection tests ---


def test_plan_save_to_issue_rejects_empty_plan() -> None:
    """Test that empty plan content returns exit code 2 and no issue is created."""
    fake_gh = FakeGitHubIssues()
    # Empty plan content (whitespace only)
    plan_content = "   \n\n  "
    fake_store = FakeClaudeInstallation.for_test(plans={"empty-plan": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 2
    output = json.loads(result.output)
    assert output["success"] is False
    assert "validation_failed" == output["error_type"]
    assert "empty" in output["error"].lower() or "whitespace" in output["error"].lower()
    # Verify no issue was created
    assert len(fake_gh.created_issues) == 0


def test_plan_save_to_issue_rejects_too_short_plan() -> None:
    """Test that plan under 100 chars returns exit code 2 and no issue is created."""
    fake_gh = FakeGitHubIssues()
    # Plan content under 100 characters (has structure but too short)
    plan_content = """# Short

- Step"""  # ~15 characters after stripping
    fake_store = FakeClaudeInstallation.for_test(plans={"short-plan": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 2
    output = json.loads(result.output)
    assert output["success"] is False
    assert "validation_failed" == output["error_type"]
    assert "too short" in output["error"].lower()
    assert output["details"]["length"] < 100
    # Verify no issue was created
    assert len(fake_gh.created_issues) == 0


def test_plan_save_to_issue_rejects_unstructured_plan() -> None:
    """Test that plan without headers or lists returns exit code 2 and no issue is created."""
    fake_gh = FakeGitHubIssues()
    # Plan content with enough characters but no structure (no headers or lists)
    plan_content = """This is a plan that has enough characters to pass the length check.
It spans multiple lines and contains detailed information about what we're going to do.
However, it doesn't have any markdown headers or bullet points or numbered lists.
So it should fail the structure validation check."""
    fake_store = FakeClaudeInstallation.for_test(plans={"unstructured-plan": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 2
    output = json.loads(result.output)
    assert output["success"] is False
    assert "validation_failed" == output["error_type"]
    assert "structure" in output["error"].lower() or "lacks" in output["error"].lower()
    assert output["details"]["has_headers"] is False
    assert output["details"]["has_lists"] is False
    # Verify no issue was created
    assert len(fake_gh.created_issues) == 0


def test_plan_save_to_issue_rejects_whitespace_plan_display_format() -> None:
    """Test that whitespace-only plan shows error in display format."""
    fake_gh = FakeGitHubIssues()
    # Whitespace-only plan content (truthy but fails validation)
    plan_content = "   \n\n  "
    fake_store = FakeClaudeInstallation.for_test(plans={"whitespace-display": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "display"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 2
    assert "Plan validation failed" in result.output
    # Verify no issue was created
    assert len(fake_gh.created_issues) == 0


# --- Session deduplication tests ---


def test_plan_save_to_issue_skips_duplicate_json_format(tmp_path: Path) -> None:
    """Test that calling plan-save twice in same session returns existing issue."""
    fake_gh = FakeGitHubIssues()
    test_session_id = "duplicate-test-session"
    plan_content = VALID_PLAN_CONTENT
    fake_store = FakeClaudeInstallation.for_test(plans={"duplicate-test": plan_content})
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        ctx = ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
            repo_root=Path(td),
        )

        # First call - creates the issue
        result1 = runner.invoke(
            plan_save_to_issue,
            ["--format", "json", "--session-id", test_session_id],
            obj=ctx,
        )
        assert result1.exit_code == 0, f"First call failed: {result1.output}"
        output1 = json.loads(result1.output)
        assert output1["success"] is True
        assert output1["issue_number"] == 1
        assert "skipped_duplicate" not in output1

        # Second call - should return existing issue without creating new one
        result2 = runner.invoke(
            plan_save_to_issue,
            ["--format", "json", "--session-id", test_session_id],
            obj=ctx,
        )
        assert result2.exit_code == 0, f"Second call failed: {result2.output}"
        output2 = json.loads(result2.output)
        assert output2["success"] is True
        assert output2["issue_number"] == 1  # Same issue number
        assert output2["skipped_duplicate"] is True
        assert "already saved plan #1" in output2["message"]

        # Verify only one issue was created
        assert len(fake_gh.created_issues) == 1


def test_plan_save_to_issue_skips_duplicate_display_format(tmp_path: Path) -> None:
    """Test that calling plan-save twice in same session shows skip message in display format."""
    fake_gh = FakeGitHubIssues()
    test_session_id = "duplicate-display-session"
    plan_content = VALID_PLAN_CONTENT
    fake_store = FakeClaudeInstallation.for_test(plans={"duplicate-display": plan_content})
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        ctx = ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
            repo_root=Path(td),
        )

        # First call - creates the issue
        result1 = runner.invoke(
            plan_save_to_issue,
            ["--format", "display", "--session-id", test_session_id],
            obj=ctx,
        )
        assert result1.exit_code == 0, f"First call failed: {result1.output}"
        assert "Plan saved to GitHub issue #1" in result1.output

        # Second call - should skip with message
        result2 = runner.invoke(
            plan_save_to_issue,
            ["--format", "display", "--session-id", test_session_id],
            obj=ctx,
        )
        assert result2.exit_code == 0, f"Second call failed: {result2.output}"
        assert "already saved plan #1" in result2.output
        assert "Skipping duplicate" in result2.output

        # Verify only one issue was created
        assert len(fake_gh.created_issues) == 1


def test_plan_save_to_issue_no_dedup_without_session_id(tmp_path: Path) -> None:
    """Test that deduplication is skipped when no session ID is provided."""
    fake_gh = FakeGitHubIssues()
    plan_content = VALID_PLAN_CONTENT
    fake_store = FakeClaudeInstallation.for_test(plans={"no-dedup-test": plan_content})
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        ctx = ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
            repo_root=Path(td),
        )

        # First call without session ID
        result1 = runner.invoke(
            plan_save_to_issue,
            ["--format", "json"],  # No --session-id
            obj=ctx,
        )
        assert result1.exit_code == 0

        # Second call without session ID - should create another issue
        # (Note: in reality the plan is consumed, but with fake store it's still there)
        result2 = runner.invoke(
            plan_save_to_issue,
            ["--format", "json"],  # No --session-id
            obj=ctx,
        )
        assert result2.exit_code == 0
        output2 = json.loads(result2.output)
        assert "skipped_duplicate" not in output2

        # Both calls created issues (no dedup without session ID)
        assert len(fake_gh.created_issues) == 2


# --- Scratch plan priority tests ---


def test_plan_save_to_issue_scratch_plan_has_priority_over_claude_plans(tmp_path: Path) -> None:
    """Test that scratch directory plan takes priority over ~/.claude/plans/ lookup."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )
    test_session_id = "scratch-priority-session"

    # Content in scratch directory (should be used)
    scratch_plan_content = """# Scratch Plan

This plan is from the scratch directory and should be used.

- Step 1: Do something from scratch
- Step 2: More scratch steps"""

    # Content in Claude plans directory (should NOT be used)
    claude_plan_content = """# Claude Plan

This plan is from Claude plans directory and should NOT be used.

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
            plan_save_to_issue,
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
        assert output["title"] == "Scratch Plan"

        # Verify plan content in comment is from scratch
        assert len(fake_gh.added_comments) >= 1
        _issue_num, plan_comment, _comment_id = fake_gh.added_comments[0]
        assert "from scratch" in plan_comment.lower()
        assert "Claude plans" not in plan_comment


def test_plan_save_to_issue_falls_back_to_claude_plans_when_no_scratch(tmp_path: Path) -> None:
    """Test fallback to Claude plans when scratch directory has no plan."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )
    test_session_id = "fallback-session"

    # Only Claude plans directory has content
    claude_plan_content = """# Fallback Plan

This plan is from Claude plans directory as fallback.

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
            plan_save_to_issue,
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
        assert output["title"] == "Fallback Plan"


def test_plan_save_to_issue_scratch_not_checked_without_session_id() -> None:
    """Test that scratch is not checked when no session_id is provided."""
    fake_gh = FakeGitHubIssues()
    # Only Claude plans directory has content
    plan_content = """# No Session Plan

This plan is found without session ID.

- Step 1: Basic step
- Step 2: More steps"""

    fake_store = FakeClaudeInstallation.for_test(plans={"no-session-plan": plan_content})

    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],  # No --session-id
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["title"] == "No Session Plan"
