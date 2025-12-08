"""Unit tests for plan-save-to-issue command."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
    FakeProject,
    FakeSessionData,
)
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues import FakeGitHubIssues

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue import (
    plan_save_to_issue,
)


@pytest.fixture
def plans_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a plans directory and monkeypatch get_plans_dir to use it.

    This fixture replaces the @patch decorator for get_latest_plan by allowing
    tests to create real plan files. The get_plans_dir() function is monkeypatched
    to return a temp directory, and tests write real .md files there.
    """
    plans = tmp_path / ".claude" / "plans"
    plans.mkdir(parents=True)
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.session_plan_extractor.get_plans_dir",
        lambda: plans,
    )
    return plans


def test_plan_save_to_issue_success(plans_dir: Path) -> None:
    """Test successful plan extraction and issue creation."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    # Create real plan file instead of mocking get_latest_plan
    plan_content = "# My Feature\n\n- Step 1\n- Step 2"
    (plans_dir / "test-plan.md").write_text(plan_content, encoding="utf-8")

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


def test_plan_save_to_issue_enriched_plan(plans_dir: Path) -> None:
    """Test detection of enriched plan."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    # Create plan file with enrichment section
    plan_content = "# My Feature\n\n## Enrichment Details\n\nContext here"
    (plans_dir / "enriched-plan.md").write_text(plan_content, encoding="utf-8")

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["enriched"] is True


def test_plan_save_to_issue_no_plan(plans_dir: Path) -> None:
    """Test error when no plan found."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    # plans_dir exists but is empty - no plan files
    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No plan found" in output["error"]


def test_plan_save_to_issue_format(plans_dir: Path) -> None:
    """Verify plan format (metadata in body, plan in comment)."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    # Empty session store - no sessions available, so no session context added
    fake_store = FakeClaudeCodeSessionStore(current_session_id=None)
    runner = CliRunner()

    # Create plan file
    plan_content = "# Test Plan\n\n- Step 1"
    (plans_dir / "format-test.md").write_text(plan_content, encoding="utf-8")

    result = runner.invoke(
        plan_save_to_issue,
        [],
        obj=DotAgentContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            session_store=fake_store,
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
    _issue_num, comment = fake_gh.added_comments[0]
    assert "Step 1" in comment


def test_plan_save_to_issue_display_format(plans_dir: Path) -> None:
    """Test display output format."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    # Create plan file
    plan_content = "# Test Feature\n\n- Implementation step"
    (plans_dir / "display-test.md").write_text(plan_content, encoding="utf-8")

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "display"],
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    assert "Plan saved to GitHub issue #1" in result.output
    assert "URL: " in result.output
    assert "Enrichment: No" in result.output
    # Verify Next steps section with copy/pasteable commands
    assert "Next steps:" in result.output
    assert "View Issue: gh issue view 1 --web" in result.output
    assert "Interactive: erk implement 1" in result.output
    assert "Dangerous Interactive: erk implement 1 --dangerous" in result.output
    assert "Dangerous, Non-Interactive, Auto-Submit: erk implement 1 --yolo" in result.output
    assert "Submit to Queue: erk submit issue 1" in result.output


def test_plan_save_to_issue_label_created(plans_dir: Path) -> None:
    """Test that erk-plan label is created."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    # Create plan file
    plan_content = "# Feature\n\nSteps here"
    (plans_dir / "label-test.md").write_text(plan_content, encoding="utf-8")

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


def test_plan_save_to_issue_session_context_captured(plans_dir: Path, tmp_path: Path) -> None:
    """Test that session context is captured and posted as comments."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )

    # Create session data in FakeClaudeCodeSessionStore
    session_content = (
        '{"type": "user", "message": {"content": "Hello"}}\n'
        '{"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi!"}]}}\n'
    )
    fake_store = FakeClaudeCodeSessionStore(
        current_session_id="test-session-id",
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
    )

    runner = CliRunner()

    # Create plan file
    plan_content = "# Feature Plan\n\n- Step 1"
    (plans_dir / "session-context-test.md").write_text(plan_content, encoding="utf-8")

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],
        obj=DotAgentContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            session_store=fake_store,
            cwd=tmp_path,
            repo_root=tmp_path,
        ),
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


def test_plan_save_to_issue_session_context_skipped_when_none(plans_dir: Path) -> None:
    """Test session context is skipped when no sessions available."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    # Empty session store - no projects
    fake_store = FakeClaudeCodeSessionStore(current_session_id=None)

    runner = CliRunner()

    # Create plan file
    plan_content = "# Feature Plan\n\n- Step 1"
    (plans_dir / "no-session-test.md").write_text(plan_content, encoding="utf-8")

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],
        obj=DotAgentContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            session_store=fake_store,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["session_context_chunks"] == 0
    assert output["session_ids"] == []

    # Only plan comment, no session context
    assert len(fake_gh.added_comments) == 1


def test_plan_save_to_issue_json_output_includes_session_metadata(plans_dir: Path) -> None:
    """Test JSON output includes session_context_chunks and session_ids fields."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    fake_store = FakeClaudeCodeSessionStore(current_session_id=None)

    runner = CliRunner()

    # Create plan file
    plan_content = "# Feature\n\n- Step 1"
    (plans_dir / "metadata-test.md").write_text(plan_content, encoding="utf-8")

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],
        obj=DotAgentContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            session_store=fake_store,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify both fields are always present
    assert "session_context_chunks" in output
    assert "session_ids" in output
    assert isinstance(output["session_context_chunks"], int)
    assert isinstance(output["session_ids"], list)


def test_plan_save_to_issue_passes_session_id_to_session_store(
    plans_dir: Path, tmp_path: Path
) -> None:
    """Test that --session-id argument affects session selection."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )

    test_session_id = "test-session-12345"
    session_content = '{"type": "user", "message": {"content": "Test"}}\n'

    # Session store with the specific session ID
    fake_store = FakeClaudeCodeSessionStore(
        current_session_id=test_session_id,
        projects={
            tmp_path: FakeProject(
                sessions={
                    test_session_id: FakeSessionData(
                        content=session_content,
                        size_bytes=2000,
                        modified_at=1234567890.0,
                    )
                }
            )
        },
    )

    runner = CliRunner()

    # Create plan file
    plan_content = "# Feature Plan\n\n- Step 1"
    (plans_dir / "session-id-test.md").write_text(plan_content, encoding="utf-8")

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json", "--session-id", test_session_id],
        obj=DotAgentContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            session_store=fake_store,
            cwd=tmp_path,
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    # The session should be captured
    assert test_session_id in output["session_ids"]


def test_plan_save_to_issue_display_format_shows_session_context(
    plans_dir: Path, tmp_path: Path
) -> None:
    """Test display format shows session context chunk count when present."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )

    session_content = '{"type": "user", "message": {"content": "Hello"}}\n'
    fake_store = FakeClaudeCodeSessionStore(
        current_session_id="test-session-id",
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
    )

    runner = CliRunner()

    # Create plan file
    plan_content = "# Feature Plan\n\n- Step 1"
    (plans_dir / "display-session-test.md").write_text(plan_content, encoding="utf-8")

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "display"],
        obj=DotAgentContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            session_store=fake_store,
            cwd=tmp_path,
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0
    assert "Session context:" in result.output
    assert "chunks" in result.output


def test_plan_save_to_issue_uses_session_store_for_current_session_id(
    plans_dir: Path, tmp_path: Path
) -> None:
    """Test that session ID is retrieved from session store when not provided via flag."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )

    store_session_id = "store-based-session-id"
    session_content = '{"type": "user", "message": {"content": "Test"}}\n'

    # Session store configured with current_session_id
    fake_store = FakeClaudeCodeSessionStore(
        current_session_id=store_session_id,
        projects={
            tmp_path: FakeProject(
                sessions={
                    store_session_id: FakeSessionData(
                        content=session_content,
                        size_bytes=2000,
                        modified_at=1234567890.0,
                    )
                }
            )
        },
    )

    runner = CliRunner()

    # Create plan file
    plan_content = "# Feature Plan\n\n- Step 1"
    (plans_dir / "store-session-test.md").write_text(plan_content, encoding="utf-8")

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],  # No --session-id flag
        obj=DotAgentContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            session_store=fake_store,
            cwd=tmp_path,
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    # The session from store should be captured
    assert store_session_id in output["session_ids"]


def test_plan_save_to_issue_flag_overrides_session_store(plans_dir: Path, tmp_path: Path) -> None:
    """Test --session-id flag takes priority over session store's current_session_id.

    When --session-id is provided, it should be used as effective_session_id,
    overriding session_store.get_current_session_id(). This test verifies that
    the flag session is captured even when the store has a different current session.
    """
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )

    store_session_id = "store-based-session-id"
    flag_session_id = "flag-based-session-id"
    session_content = '{"type": "user", "message": {"content": "Test"}}\n'

    # Session store has current_session_id set to store_session_id,
    # but ONLY the flag_session_id session exists in the project.
    # This tests that the flag is used to look up sessions.
    fake_store = FakeClaudeCodeSessionStore(
        current_session_id=store_session_id,  # Store points to different session
        projects={
            tmp_path: FakeProject(
                sessions={
                    # Only flag session exists - if store session was used, no sessions found
                    flag_session_id: FakeSessionData(
                        content=session_content,
                        size_bytes=2000,
                        modified_at=1234567891.0,
                    ),
                }
            )
        },
    )

    runner = CliRunner()

    # Create plan file
    plan_content = "# Feature Plan\n\n- Step 1"
    (plans_dir / "override-session-test.md").write_text(plan_content, encoding="utf-8")

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json", "--session-id", flag_session_id],
        obj=DotAgentContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            session_store=fake_store,
            cwd=tmp_path,
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    # The flag session should be captured
    assert flag_session_id in output["session_ids"]


def test_plan_save_to_issue_creates_marker_file(tmp_path: Path, plans_dir: Path) -> None:
    """Test plan_save_to_issue creates marker file on success."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    test_session_id = "marker-test-session-id"
    fake_store = FakeClaudeCodeSessionStore(current_session_id=test_session_id)
    runner = CliRunner()

    # Create plan file
    plan_content = "# Feature Plan\n\n- Step 1"
    (plans_dir / "marker-test.md").write_text(plan_content, encoding="utf-8")

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json", "--session-id", test_session_id],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, session_store=fake_store, repo_root=Path(td)
            ),
        )

        assert result.exit_code == 0, f"Failed: {result.output}"

        # Verify marker file was created at correct path with sessions/ segment
        marker_file = (
            Path(td) / ".erk" / "scratch" / "sessions" / test_session_id / "plan-saved-to-github"
        )
        assert marker_file.exists()


def test_plan_save_to_issue_no_marker_without_session_id(tmp_path: Path, plans_dir: Path) -> None:
    """Test marker file is not created when no session ID is available."""
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    # Session store with no current session ID
    fake_store = FakeClaudeCodeSessionStore(current_session_id=None)
    runner = CliRunner()

    # Create plan file
    plan_content = "# Feature Plan\n\n- Step 1"
    (plans_dir / "no-marker-test.md").write_text(plan_content, encoding="utf-8")

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json"],  # No --session-id, and store has None
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, session_store=fake_store
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
