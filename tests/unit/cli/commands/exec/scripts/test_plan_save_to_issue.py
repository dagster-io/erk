"""Unit tests for plan-save-to-issue command."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_save_to_issue import (
    plan_save_to_issue,
)
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    SlotInfo,
    load_pool_state,
    save_pool_state,
)
from erk_shared.context.context import ErkContext
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.learn.extraction.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from tests.test_utils.env_helpers import erk_isolated_fs_env


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


def test_plan_save_to_issue_updates_slot_objective_when_in_slot() -> None:
    """Test slot objective is updated when --objective-issue provided and in slot worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory for slot
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        fake_gh = FakeGitHubIssues()
        plan_content = """# Feature Plan

- Step 1"""
        fake_store = FakeClaudeInstallation.for_test(plans={"slot-test": plan_content})

        # Build worktrees including the slot worktree
        base_worktrees = env.build_worktrees("main")
        # Add the slot worktree to the list so get_repository_root can find it
        base_worktrees[env.cwd].append(
            WorktreeInfo(path=worktree_path, branch="feature-branch", is_root=False)
        )

        git_ops = FakeGit(
            worktrees=base_worktrees,
            current_branches={worktree_path: "feature-branch"},
            git_common_dirs={worktree_path: env.git_dir},
        )

        repo = RepoContext(
            root=worktree_path,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool.json with slot
        state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(SlotInfo(name="erk-slot-01", last_objective_id=None),),
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-branch",
                    assigned_at="2025-01-01T12:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(
            cwd=worktree_path,
            git=git_ops,
            repo=repo,
            issues=fake_gh,
            claude_installation=fake_store,
        )

        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json", "--objective-issue=456"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["slot_name"] == "erk-slot-01"
        assert output["slot_objective_updated"] is True

        # Verify pool.json was updated
        updated_state = load_pool_state(repo.pool_json_path)
        assert updated_state is not None
        assert updated_state.slots[0].last_objective_id == 456


def test_plan_save_to_issue_no_slot_update_when_not_in_slot() -> None:
    """Test slot fields are absent from output when not in a slot worktree."""
    fake_gh = FakeGitHubIssues()
    plan_content = """# Feature Plan

- Step 1"""
    fake_store = FakeClaudeInstallation.for_test(plans={"no-slot-test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json", "--objective-issue=456"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    # Slot fields should NOT be present when not in a slot
    assert "slot_name" not in output
    assert "slot_objective_updated" not in output


def test_plan_save_to_issue_no_slot_update_without_objective_flag() -> None:
    """Test no slot update when --objective-issue not provided."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory for slot
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        fake_gh = FakeGitHubIssues()
        plan_content = """# Feature Plan

- Step 1"""
        fake_store = FakeClaudeInstallation.for_test(plans={"no-flag-test": plan_content})

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={worktree_path: "feature-branch"},
            git_common_dirs={worktree_path: env.git_dir},
        )

        repo = RepoContext(
            root=worktree_path,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool.json with slot that has existing objective
        state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(SlotInfo(name="erk-slot-01", last_objective_id=123),),
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-branch",
                    assigned_at="2025-01-01T12:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(
            cwd=worktree_path,
            git=git_ops,
            repo=repo,
            issues=fake_gh,
            claude_installation=fake_store,
        )

        # No --objective-issue flag
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = json.loads(result.output)
        assert output["success"] is True
        # Slot fields should NOT be present without --objective-issue
        assert "slot_name" not in output
        assert "slot_objective_updated" not in output

        # Verify pool.json was NOT modified
        unchanged_state = load_pool_state(repo.pool_json_path)
        assert unchanged_state is not None
        assert unchanged_state.slots[0].last_objective_id == 123


def test_plan_save_to_issue_learned_from_issue_sets_metadata() -> None:
    """Test --learned-from-issue flag sets learned_from_issue in plan metadata."""
    fake_gh = FakeGitHubIssues()
    plan_content = """# Learn Plan

- Document something"""
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


def test_plan_save_to_issue_display_format_shows_slot_update() -> None:
    """Test display format shows slot objective update message."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory for slot
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        fake_gh = FakeGitHubIssues()
        plan_content = """# Feature Plan

- Step 1"""
        fake_store = FakeClaudeInstallation.for_test(plans={"display-slot-test": plan_content})

        # Build worktrees including the slot worktree
        base_worktrees = env.build_worktrees("main")
        # Add the slot worktree to the list so get_repository_root can find it
        base_worktrees[env.cwd].append(
            WorktreeInfo(path=worktree_path, branch="feature-branch", is_root=False)
        )

        git_ops = FakeGit(
            worktrees=base_worktrees,
            current_branches={worktree_path: "feature-branch"},
            git_common_dirs={worktree_path: env.git_dir},
        )

        repo = RepoContext(
            root=worktree_path,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool.json with slot
        state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(SlotInfo(name="erk-slot-01", last_objective_id=None),),
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-branch",
                    assigned_at="2025-01-01T12:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(
            cwd=worktree_path,
            git=git_ops,
            repo=repo,
            issues=fake_gh,
            claude_installation=fake_store,
        )

        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "display", "--objective-issue=789"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Slot objective updated: erk-slot-01 → #789" in result.output
