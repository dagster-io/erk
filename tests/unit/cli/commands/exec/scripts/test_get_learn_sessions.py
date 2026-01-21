"""Unit tests for get-learn-sessions exec script.

Tests session discovery for plan issues.
Uses fakes for fast, reliable testing without subprocess calls.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_learn_sessions import get_learn_sessions
from erk_shared.context.context import ErkContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.learn.extraction.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from tests.test_utils.github_helpers import create_test_issue
from tests.test_utils.plan_helpers import format_plan_header_body_for_test

# ============================================================================
# Success Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_get_learn_sessions_with_explicit_issue(tmp_path: Path) -> None:
    """Test session discovery with explicit issue number."""
    fake_git = FakeGit()
    test_issue = create_test_issue(123, "Test Plan #123", "Plan body")
    fake_issues = FakeGitHubIssues(issues={123: test_issue})
    fake_claude = FakeClaudeInstallation.for_test()

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            get_learn_sessions,
            ["123"],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                claude_installation=fake_claude,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 123


def test_get_learn_sessions_infers_from_branch(tmp_path: Path) -> None:
    """Test session discovery infers issue from branch name."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        fake_git = FakeGit(
            current_branches={cwd: "P456-implement-feature"},
        )
        fake_issues = FakeGitHubIssues(
            issues={456: create_test_issue(456, "Test Plan #456", "Plan body")}
        )
        fake_claude = FakeClaudeInstallation.for_test()

        result = runner.invoke(
            get_learn_sessions,
            [],  # No issue argument - should infer
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                claude_installation=fake_claude,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 456


def test_get_learn_sessions_with_url_format(tmp_path: Path) -> None:
    """Test session discovery accepts GitHub URL format."""
    fake_git = FakeGit()
    test_issue = create_test_issue(789, "Test Plan #789", "Plan body")
    fake_issues = FakeGitHubIssues(issues={789: test_issue})
    fake_claude = FakeClaudeInstallation.for_test()

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            get_learn_sessions,
            ["https://github.com/owner/repo/issues/789"],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                claude_installation=fake_claude,
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


def test_get_learn_sessions_fails_without_issue(tmp_path: Path) -> None:
    """Test error when no issue provided and can't infer from branch."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        fake_git = FakeGit(
            current_branches={cwd: "main"},  # Not a P{issue} branch
        )
        fake_issues = FakeGitHubIssues()
        fake_claude = FakeClaudeInstallation.for_test()

        result = runner.invoke(
            get_learn_sessions,
            [],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                claude_installation=fake_claude,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No issue specified" in output["error"]


def test_get_learn_sessions_fails_with_invalid_issue(tmp_path: Path) -> None:
    """Test error with invalid issue identifier."""
    fake_git = FakeGit()
    fake_issues = FakeGitHubIssues()
    fake_claude = FakeClaudeInstallation.for_test()

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            get_learn_sessions,
            ["not-a-number"],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                claude_installation=fake_claude,
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


def test_json_output_structure(tmp_path: Path) -> None:
    """Test JSON output contains all expected fields."""
    fake_git = FakeGit()
    test_issue = create_test_issue(100, "Test Plan #100", "Plan body")
    fake_issues = FakeGitHubIssues(issues={100: test_issue})
    fake_claude = FakeClaudeInstallation.for_test()

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            get_learn_sessions,
            ["100"],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                claude_installation=fake_claude,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)

    # Verify all expected fields exist
    assert "success" in output
    assert "issue_number" in output
    assert "planning_session_id" in output
    assert "implementation_session_ids" in output
    assert "learn_session_ids" in output
    assert "readable_session_ids" in output
    assert "session_paths" in output
    assert "local_session_ids" in output
    assert "last_remote_impl_at" in output
    assert "session_sources" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["implementation_session_ids"], list)
    assert isinstance(output["session_paths"], list)
    assert isinstance(output["session_sources"], list)


def test_session_sources_contains_local_session_data(tmp_path: Path) -> None:
    """Test session_sources includes properly structured LocalSessionSource data."""
    fake_git = FakeGit()
    test_issue = create_test_issue(200, "Test Plan #200", "Plan body")
    fake_issues = FakeGitHubIssues(issues={200: test_issue})

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        # Set up fake claude installation with sessions that will be returned
        # via the local session fallback path (when no readable_session_ids from GitHub)
        fake_claude = FakeClaudeInstallation.for_test(
            projects={
                cwd: FakeProject(
                    sessions={
                        "session-abc-123": FakeSessionData(
                            content='{"type": "user"}\n',
                            size_bytes=1024,
                            modified_at=1000.0,
                        ),
                        "session-def-456": FakeSessionData(
                            content='{"type": "user"}\n',
                            size_bytes=2048,
                            modified_at=2000.0,
                        ),
                    }
                )
            },
        )

        result = runner.invoke(
            get_learn_sessions,
            ["200"],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                claude_installation=fake_claude,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)

    # Verify session_sources contains LocalSessionSource data
    assert len(output["session_sources"]) == 2

    # Verify structure of each session source
    for source in output["session_sources"]:
        assert "source_type" in source
        assert "session_id" in source
        assert "run_id" in source
        assert "path" in source
        assert source["source_type"] == "local"
        assert source["run_id"] is None
        assert source["path"] is not None  # Local sessions have paths

    # Verify session IDs are present (sorted by mtime, newest first)
    session_ids = [s["session_id"] for s in output["session_sources"]]
    assert "session-def-456" in session_ids
    assert "session-abc-123" in session_ids


# ============================================================================
# Remote Session Tests
# ============================================================================


def test_session_sources_includes_remote_session(tmp_path: Path) -> None:
    """Test session_sources includes RemoteSessionSource when plan has remote implementation."""
    fake_git = FakeGit()

    # Create issue with plan header containing remote implementation metadata
    plan_header = format_plan_header_body_for_test(
        last_remote_impl_at="2024-01-15T12:00:00Z",
        last_remote_impl_run_id="12345678",
        last_remote_impl_session_id="remote-abc-123",
    )
    test_issue = create_test_issue(
        300,
        "Test Plan #300",
        body=plan_header + "\n\n# Plan Content\nThe actual plan.",
    )
    fake_issues = FakeGitHubIssues(issues={300: test_issue})
    fake_claude = FakeClaudeInstallation.for_test()

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            get_learn_sessions,
            ["300"],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                claude_installation=fake_claude,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)

    # Verify session_sources contains a RemoteSessionSource
    assert len(output["session_sources"]) == 1

    remote_source = output["session_sources"][0]
    assert remote_source["source_type"] == "remote"
    assert remote_source["session_id"] == "remote-abc-123"
    assert remote_source["run_id"] == "12345678"
    assert remote_source["path"] is None  # Path is None until downloaded


def test_session_sources_includes_mixed_local_and_remote(tmp_path: Path) -> None:
    """Test session_sources includes both local and remote sessions."""
    fake_git = FakeGit()

    # Create issue with plan header containing both local (created_from_session)
    # and remote implementation metadata
    plan_header = format_plan_header_body_for_test(
        created_from_session="planning-session-123",
        last_remote_impl_at="2024-01-16T14:00:00Z",
        last_remote_impl_run_id="98765432",
        last_remote_impl_session_id="remote-def-456",
    )
    test_issue = create_test_issue(
        400,
        "Test Plan #400",
        body=plan_header + "\n\n# Plan Content\nMixed local and remote.",
    )
    fake_issues = FakeGitHubIssues(issues={400: test_issue})

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        # Set up fake claude installation with the planning session in a project
        # find_session_globally searches all projects, so we put the session in the cwd project
        fake_claude = FakeClaudeInstallation.for_test(
            projects={
                cwd: FakeProject(
                    sessions={
                        "planning-session-123": FakeSessionData(
                            content='{"type": "user"}\n',
                            size_bytes=2048,
                            modified_at=1500.0,
                        ),
                    }
                )
            },
        )

        result = runner.invoke(
            get_learn_sessions,
            ["400"],
            obj=ErkContext.for_test(
                git=fake_git,
                github_issues=fake_issues,
                claude_installation=fake_claude,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)

    # Verify session_sources contains both local and remote sessions
    assert len(output["session_sources"]) == 2

    # Find local and remote sources
    local_sources = [s for s in output["session_sources"] if s["source_type"] == "local"]
    remote_sources = [s for s in output["session_sources"] if s["source_type"] == "remote"]

    assert len(local_sources) == 1
    assert len(remote_sources) == 1

    # Verify local session
    local_source = local_sources[0]
    assert local_source["session_id"] == "planning-session-123"
    assert local_source["run_id"] is None
    assert local_source["path"] is not None

    # Verify remote session
    remote_source = remote_sources[0]
    assert remote_source["session_id"] == "remote-def-456"
    assert remote_source["run_id"] == "98765432"
    assert remote_source["path"] is None
