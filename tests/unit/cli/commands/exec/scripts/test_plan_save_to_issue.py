"""Unit tests for plan-save-to-issue command."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_save_to_issue import (
    plan_save_to_issue,
)
from erk_shared.context import ErkContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.learn.extraction.claude_installation import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)


def test_plan_save_to_issue_success() -> None:
    """Test successful plan extraction and issue creation."""
    fake_gh = FakeGitHubIssues()
    plan_content = """# My Feature

- Step 1
- Step 2"""
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
    assert output["enriched"] is False


def test_plan_save_to_issue_enriched_plan() -> None:
    """Test detection of enriched plan."""
    fake_gh = FakeGitHubIssues()
    plan_content = """# My Feature

## Enrichment Details

Context here"""
    fake_store = FakeClaudeInstallation.for_test(plans={"enriched-plan": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["enriched"] is True


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
    plan_content = """# Test Plan

- Step 1"""
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

- Implementation step"""
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
    assert "Enrichment: No" in result.output
    # Verify Next steps section with copy/pasteable commands
    assert "Next steps:" in result.output
    assert "View Issue: gh issue view 1 --web" in result.output
    # Verify Claude Code slash command option
    assert "In Claude Code: /erk:plan-submit" in result.output
    # Verify exit Claude Code note and CLI commands
    assert "OR exit Claude Code first, then run one of:" in result.output
    assert "Interactive: erk implement 1" in result.output
    assert "Dangerous Interactive: erk implement 1 --dangerous" in result.output
    assert "Auto-Submit: erk implement 1 --yolo" in result.output
    assert "Submit to Queue: erk plan submit 1" in result.output


def test_plan_save_to_issue_label_created() -> None:
    """Test that erk-plan label is created."""
    fake_gh = FakeGitHubIssues()
    plan_content = """# Feature

Steps here"""
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
    plan_content = """# Feature Plan

- Step 1"""
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
    plan_content = """# Feature Plan

- Step 1"""
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
    plan_content = """# Feature

- Step 1"""
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
    plan_content = """# Feature Plan

- Step 1"""

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
    plan_content = """# Feature Plan

- Step 1"""
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
    plan_content = """# Feature Plan

- Step 1"""

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
    plan_content = """# Feature Plan

- Step 1"""

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
    plan_content = """# Feature Plan

- Step 1"""
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
    plan_content = """# Feature Plan

- Step 1"""
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
    plan_content = """# Feature Plan

- Step 1"""

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
