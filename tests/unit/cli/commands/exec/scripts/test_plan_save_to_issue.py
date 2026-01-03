"""Unit tests for plan-save-to-issue command."""

import json
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts import plan_save_to_issue as plan_save_to_issue_module
from erk.cli.commands.exec.scripts.plan_save_to_issue import (
    plan_save_to_issue,
    validate_plan_frontmatter,
)
from erk_shared.context import ErkContext
from erk_shared.extraction.claude_installation import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues import FakeGitHubIssues


def test_plan_save_to_issue_success() -> None:
    """Test successful plan extraction and issue creation."""
    fake_gh = FakeGitHubIssues()
    plan_content = """---
steps:
  - name: "Step 1"
  - name: "Step 2"
---

# My Feature

- Step 1
- Step 2"""
    fake_store = FakeClaudeInstallation(
        projects=None,
        plans={"test-plan": plan_content},
        settings=None,
        local_settings=None,
    )
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
    plan_content = """---
steps:
  - name: "Implement feature"
---

# My Feature

## Enrichment Details

Context here"""
    fake_store = FakeClaudeInstallation(
        projects=None,
        plans={"enriched-plan": plan_content},
        settings=None,
        local_settings=None,
    )
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
    fake_store = FakeClaudeInstallation(
        projects=None,
        plans=None,
        settings=None,
        local_settings=None,
    )
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
    plan_content = """---
steps:
  - name: "Step 1"
---

# Test Plan

- Step 1"""
    fake_store = FakeClaudeInstallation(
        projects=None,
        plans={"format-test": plan_content},
        settings=None,
        local_settings=None,
    )
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
    plan_content = """---
steps:
  - name: "Implementation step"
---

# Test Feature

- Implementation step"""
    fake_store = FakeClaudeInstallation(
        projects=None,
        plans={"display-test": plan_content},
        settings=None,
        local_settings=None,
    )
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
    assert "Interactive: erk implement 1" in result.output
    assert "Dangerous Interactive: erk implement 1 --dangerous" in result.output
    assert "Dangerous, Non-Interactive, Auto-Submit: erk implement 1 --yolo" in result.output
    assert "Submit to Queue: erk submit 1" in result.output
    assert "/erk:plan-submit" in result.output


def test_plan_save_to_issue_label_created() -> None:
    """Test that erk-plan label is created."""
    fake_gh = FakeGitHubIssues()
    plan_content = """---
steps:
  - name: "Implement feature"
---

# Feature

Steps here"""
    fake_store = FakeClaudeInstallation(
        projects=None,
        plans={"label-test": plan_content},
        settings=None,
        local_settings=None,
    )
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


def test_plan_save_to_issue_session_context_disabled(tmp_path: Path) -> None:
    """Test that session context is NOT captured (feature disabled)."""
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
    plan_content = """---
steps:
  - name: "Step 1"
---

# Feature Plan

- Step 1"""
    fake_store = FakeClaudeInstallation(
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
        settings=None,
        local_settings=None,
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
    # Session context embedding is disabled - always returns 0 chunks and empty session_ids
    assert output["session_context_chunks"] == 0
    assert output["session_ids"] == []

    # Only plan comment is posted, no session context comments
    assert len(fake_gh.added_comments) == 1
    _issue_num, plan_comment, _comment_id = fake_gh.added_comments[0]
    assert "Step 1" in plan_comment


def test_plan_save_to_issue_session_context_skipped_when_none() -> None:
    """Test session context is skipped when no session ID provided."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    plan_content = """---
steps:
  - name: "Step 1"
---

# Feature Plan

- Step 1"""
    # Session store with no sessions but has a plan
    fake_store = FakeClaudeInstallation(
        projects=None,
        plans={"no-session-test": plan_content},
        settings=None,
        local_settings=None,
    )

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
    assert output["session_context_chunks"] == 0
    assert output["session_ids"] == []

    # Only plan comment, no session context
    assert len(fake_gh.added_comments) == 1


def test_plan_save_to_issue_json_output_includes_session_metadata() -> None:
    """Test JSON output includes session_context_chunks and session_ids fields."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    plan_content = """---
steps:
  - name: "Step 1"
---

# Feature

- Step 1"""
    fake_store = FakeClaudeInstallation(
        projects=None,
        plans={"metadata-test": plan_content},
        settings=None,
        local_settings=None,
    )

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

    # Verify both fields are always present
    assert "session_context_chunks" in output
    assert "session_ids" in output
    assert isinstance(output["session_context_chunks"], int)
    assert isinstance(output["session_ids"], list)


def test_plan_save_to_issue_session_id_still_creates_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that --session-id argument still creates marker file even with context disabled."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )

    # Patch to avoid reading real ~/.claude/projects/
    monkeypatch.setattr(
        plan_save_to_issue_module,
        "extract_slugs_from_session",
        lambda *args, **kwargs: [],
    )

    test_session_id = "test-session-12345"
    plan_content = """---
steps:
  - name: "Step 1"
---

# Feature Plan

- Step 1"""

    fake_store = FakeClaudeInstallation(
        projects=None,
        plans={"session-id-test": plan_content},
        settings=None,
        local_settings=None,
    )

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
        # Session context embedding is disabled - session_ids will be empty
        assert output["session_ids"] == []
        assert output["session_context_chunks"] == 0

        # But marker file should still be created
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
    plan_content = """---
steps:
  - name: "Step 1"
---

# Feature Plan

- Step 1"""
    fake_store = FakeClaudeInstallation(
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
        settings=None,
        local_settings=None,
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


def test_plan_save_to_issue_no_session_context_without_session_id(tmp_path: Path) -> None:
    """Test that no session context is captured when --session-id is not provided."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )

    session_content = '{"type": "user", "message": {"content": "Test"}}\n'
    plan_content = """---
steps:
  - name: "Step 1"
---

# Feature Plan

- Step 1"""

    # Session store has sessions but no session ID is passed via CLI
    fake_store = FakeClaudeInstallation(
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
        settings=None,
        local_settings=None,
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
    # Without --session-id, no session context is captured
    assert output["session_ids"] == []
    assert output["session_context_chunks"] == 0


def test_plan_save_to_issue_session_id_flag_does_not_capture_context(tmp_path: Path) -> None:
    """Test --session-id flag does NOT capture context (feature disabled).

    Even when --session-id is provided, session context is not captured
    because the feature is disabled.
    """
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )

    flag_session_id = "flag-based-session-id"
    session_content = '{"type": "user", "message": {"content": "Test"}}\n'
    plan_content = """---
steps:
  - name: "Step 1"
---

# Feature Plan

- Step 1"""

    # Session store has the session that matches the flag
    fake_store = FakeClaudeInstallation(
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
        settings=None,
        local_settings=None,
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
    # Session context embedding is disabled - session_ids will be empty
    assert output["session_ids"] == []
    assert output["session_context_chunks"] == 0


def test_plan_save_to_issue_creates_marker_file(tmp_path: Path) -> None:
    """Test plan_save_to_issue creates marker file on success."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    test_session_id = "marker-test-session-id"
    plan_content = """---
steps:
  - name: "Step 1"
---

# Feature Plan

- Step 1"""
    fake_store = FakeClaudeInstallation(
        projects=None,
        plans={"marker-test": plan_content},
        settings=None,
        local_settings=None,
    )
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
    plan_content = """---
steps:
  - name: "Step 1"
---

# Feature Plan

- Step 1"""
    # Session store has plan but no session ID will be passed
    fake_store = FakeClaudeInstallation(
        projects=None,
        plans={"no-marker-test": plan_content},
        settings=None,
        local_settings=None,
    )
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


# =============================================================================
# validate_plan_frontmatter Tests
# =============================================================================


def test_validate_plan_frontmatter_valid() -> None:
    """Test validation passes for valid frontmatter with steps."""
    plan_content = """---
steps:
  - name: "First step"
  - name: "Second step"
---

# Plan

Content here.
"""
    # Should not raise
    validate_plan_frontmatter(plan_content)


def test_validate_plan_frontmatter_missing_steps() -> None:
    """Test validation fails when steps key is missing."""
    plan_content = """---
title: "My Plan"
---

# Plan
"""
    with pytest.raises(click.ClickException) as exc_info:
        validate_plan_frontmatter(plan_content)

    assert "Plan missing required 'steps' in frontmatter" in exc_info.value.message


def test_validate_plan_frontmatter_no_frontmatter() -> None:
    """Test validation fails when no frontmatter present."""
    plan_content = """# Plan

No frontmatter.
"""
    with pytest.raises(click.ClickException) as exc_info:
        validate_plan_frontmatter(plan_content)

    assert "Plan missing required 'steps' in frontmatter" in exc_info.value.message


def test_validate_plan_frontmatter_steps_not_list() -> None:
    """Test validation fails when steps is not a list."""
    plan_content = """---
steps: "not a list"
---

# Plan
"""
    with pytest.raises(click.ClickException) as exc_info:
        validate_plan_frontmatter(plan_content)

    assert "'steps' must be a list" in exc_info.value.message


def test_validate_plan_frontmatter_empty_steps() -> None:
    """Test validation fails when steps array is empty."""
    plan_content = """---
steps: []
---

# Plan
"""
    with pytest.raises(click.ClickException) as exc_info:
        validate_plan_frontmatter(plan_content)

    assert "Plan has empty 'steps' array" in exc_info.value.message


def test_validate_plan_frontmatter_invalid_yaml() -> None:
    """Test validation fails for invalid YAML."""
    plan_content = """---
steps: [invalid yaml
---

# Plan
"""
    with pytest.raises(click.ClickException) as exc_info:
        validate_plan_frontmatter(plan_content)

    assert "Invalid YAML frontmatter" in exc_info.value.message


def test_validate_plan_frontmatter_step_not_dict() -> None:
    """Test validation fails when step is not a dictionary."""
    plan_content = """---
steps:
  - "Plain string not dict"
---

# Plan
"""
    with pytest.raises(click.ClickException) as exc_info:
        validate_plan_frontmatter(plan_content)

    assert "Step 1 must be a dictionary" in exc_info.value.message


def test_validate_plan_frontmatter_step_missing_name() -> None:
    """Test validation fails when step dict is missing name key."""
    plan_content = """---
steps:
  - description: "Has description but no name"
---

# Plan
"""
    with pytest.raises(click.ClickException) as exc_info:
        validate_plan_frontmatter(plan_content)

    assert "Step 1 missing required 'name' key" in exc_info.value.message


def test_plan_save_to_issue_rejects_plan_without_frontmatter() -> None:
    """Test command rejects plan without frontmatter steps."""
    fake_gh = FakeGitHubIssues()
    # Plan without frontmatter steps
    plan_content = "# My Feature\n\n- Step 1\n- Step 2"
    fake_store = FakeClaudeInstallation(
        projects=None,
        plans={"no-frontmatter": plan_content},
        settings=None,
        local_settings=None,
    )
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
    assert "Plan missing required 'steps' in frontmatter" in output["error"]


def test_plan_save_to_issue_accepts_plan_with_frontmatter() -> None:
    """Test command accepts plan with valid frontmatter steps."""
    fake_gh = FakeGitHubIssues()
    plan_content = """---
steps:
  - name: "First step"
  - name: "Second step"
---

# My Feature

Details here.
"""
    fake_store = FakeClaudeInstallation(
        projects=None,
        plans={"with-frontmatter": plan_content},
        settings=None,
        local_settings=None,
    )
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
