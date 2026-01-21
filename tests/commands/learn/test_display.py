"""Tests for learn command display and CLI behavior."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.learn.learn_cmd import LearnResult, _display_human_readable
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.context.types import GlobalConfig
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.metadata.core import find_metadata_block, render_metadata_block
from erk_shared.github.metadata.types import MetadataBlock
from erk_shared.learn.extraction.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def test_display_shows_remote_impl_message_when_set(capsys: pytest.CaptureFixture[str]) -> None:
    """Display shows remote implementation message when last_remote_impl_at is set."""
    result = LearnResult(
        issue_number=123,
        planning_session_id=None,
        implementation_session_ids=[],
        learn_session_ids=[],
        readable_session_ids=[],
        session_paths=[],
        local_session_ids=[],
        last_remote_impl_at="2024-01-16T14:30:00Z",
    )

    _display_human_readable(result)

    captured = capsys.readouterr()
    # user_output writes to stderr
    assert "(ran remotely - logs not accessible locally)" in captured.err


def test_display_shows_none_when_no_impl_at_all(capsys: pytest.CaptureFixture[str]) -> None:
    """Display shows (none) when no implementation happened."""
    result = LearnResult(
        issue_number=123,
        planning_session_id=None,
        implementation_session_ids=[],
        learn_session_ids=[],
        readable_session_ids=[],
        session_paths=[],
        local_session_ids=[],
        last_remote_impl_at=None,
    )

    _display_human_readable(result)

    captured = capsys.readouterr()
    assert "Implementation sessions:" in captured.err
    assert "(none)" in captured.err
    assert "(ran remotely" not in captured.err


def test_display_shows_impl_sessions_when_present(capsys: pytest.CaptureFixture[str]) -> None:
    """Display shows implementation sessions when they exist."""
    result = LearnResult(
        issue_number=123,
        planning_session_id=None,
        implementation_session_ids=["impl-session-abc"],
        learn_session_ids=[],
        readable_session_ids=[],
        session_paths=[],
        local_session_ids=[],
        last_remote_impl_at="2024-01-16T14:30:00Z",  # Even with remote, local takes precedence
    )

    _display_human_readable(result)

    captured = capsys.readouterr()
    assert "Implementation sessions (1):" in captured.err
    assert "impl-session-abc" in captured.err
    # Should NOT show remote message when local sessions exist
    assert "(ran remotely" not in captured.err


# CLI Behavior Tests


def _make_plan_body_with_session(session_id: str) -> str:
    """Create a valid issue body with plan-header metadata including created_from_session."""
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "test-user",
        "created_from_session": session_id,
    }
    header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))
    return f"{header_block}\n\n# Plan\n\nTest plan content"


def test_dangerous_flag_passed_to_execute_interactive(tmp_path: Path) -> None:
    """Verify --dangerous flag is passed to execute_interactive."""
    # Arrange: Create issue with session metadata
    session_id = "test-session-abc123"
    issue_body = _make_plan_body_with_session(session_id)

    now = datetime.now(UTC)
    fake_issues = FakeGitHubIssues(
        issues={
            123: IssueInfo(
                number=123,
                title="Test Plan",
                body=issue_body,
                state="OPEN",
                url="https://github.com/owner/repo/issues/123",
                labels=["erk-plan"],
                assignees=[],
                created_at=now,
                updated_at=now,
                author="testuser",
            ),
        },
    )

    # Set up fake git with proper directory structure
    git_dir = tmp_path / ".git"
    fake_git = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        current_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "https://github.com/owner/repo.git"},
    )

    # Set up fake Claude installation with matching session
    fake_installation = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    session_id: FakeSessionData(
                        content='{"type": "user"}\n',
                        size_bytes=1024,
                        modified_at=now.timestamp(),
                    )
                }
            )
        }
    )

    fake_executor = FakeClaudeExecutor(claude_available=True)

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )

    global_config = GlobalConfig.test(erk_root=repo_dir)

    ctx = context_for_test(
        cwd=tmp_path,
        git=fake_git,
        issues=fake_issues,
        claude_installation=fake_installation,
        claude_executor=fake_executor,
        repo=repo,
        global_config=global_config,
    )

    runner = CliRunner()

    # Act: Run learn with --dangerous and -i flags
    result = runner.invoke(cli, ["learn", "123", "--dangerous", "-i"], obj=ctx)

    # Assert
    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Verify execute_interactive was called with dangerous=True
    assert len(fake_executor.interactive_calls) == 1
    worktree_path, dangerous, command, target_subpath, model, _ = fake_executor.interactive_calls[0]
    assert dangerous is True, "Expected dangerous=True to be passed to execute_interactive"
    assert "/erk:learn" in command


def test_learn_without_dangerous_flag(tmp_path: Path) -> None:
    """Verify dangerous=False when --dangerous flag is not provided."""
    # Arrange: Create issue with session metadata
    session_id = "test-session-def456"
    issue_body = _make_plan_body_with_session(session_id)

    now = datetime.now(UTC)
    fake_issues = FakeGitHubIssues(
        issues={
            456: IssueInfo(
                number=456,
                title="Test Plan",
                body=issue_body,
                state="OPEN",
                url="https://github.com/owner/repo/issues/456",
                labels=["erk-plan"],
                assignees=[],
                created_at=now,
                updated_at=now,
                author="testuser",
            ),
        },
    )

    # Set up fake git with proper directory structure
    git_dir = tmp_path / ".git"
    fake_git = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        current_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "https://github.com/owner/repo.git"},
    )

    # Set up fake Claude installation with matching session
    fake_installation = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    session_id: FakeSessionData(
                        content='{"type": "user"}\n',
                        size_bytes=1024,
                        modified_at=now.timestamp(),
                    )
                }
            )
        }
    )

    fake_executor = FakeClaudeExecutor(claude_available=True)

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )

    global_config = GlobalConfig.test(erk_root=repo_dir)

    ctx = context_for_test(
        cwd=tmp_path,
        git=fake_git,
        issues=fake_issues,
        claude_installation=fake_installation,
        claude_executor=fake_executor,
        repo=repo,
        global_config=global_config,
    )

    runner = CliRunner()

    # Act: Run learn with -i flag only (no --dangerous)
    result = runner.invoke(cli, ["learn", "456", "-i"], obj=ctx)

    # Assert
    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Verify execute_interactive was called with dangerous=False
    assert len(fake_executor.interactive_calls) == 1
    worktree_path, dangerous, command, target_subpath, model, _ = fake_executor.interactive_calls[0]
    assert dangerous is False, "Expected dangerous=False when --dangerous flag not provided"
    assert "/erk:learn" in command


# Async Mode Tests


def test_async_flag_triggers_workflow(tmp_path: Path) -> None:
    """Verify --async flag triggers workflow instead of interactive Claude."""
    # Create plan issue with remote session data (required for async learn)
    plan_body = format_plan_header_body_for_test(
        last_remote_impl_run_id="12345678",
        last_remote_impl_session_id="abc-def-ghi",
    )
    plan_body += "\n\n# Plan\n\nThis is the plan content."

    now = datetime.now(UTC)
    fake_issues = FakeGitHubIssues(
        issues={
            123: IssueInfo(
                number=123,
                title="Test Plan",
                body=plan_body,
                state="OPEN",
                url="https://github.com/owner/repo/issues/123",
                labels=["erk-plan"],
                assignees=[],
                created_at=now,
                updated_at=now,
                author="testuser",
            ),
        },
    )

    fake_github = FakeGitHub(issues_gateway=fake_issues)

    # Set up fake git with proper directory structure
    git_dir = tmp_path / ".git"
    fake_git = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        current_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "https://github.com/owner/repo.git"},
    )

    fake_executor = FakeClaudeExecutor(claude_available=True)

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )

    global_config = GlobalConfig.test(erk_root=repo_dir)

    ctx = context_for_test(
        cwd=tmp_path,
        git=fake_git,
        github=fake_github,
        issues=fake_issues,
        claude_executor=fake_executor,
        repo=repo,
        global_config=global_config,
    )

    runner = CliRunner()

    # Act: Run learn with --async flag
    result = runner.invoke(cli, ["learn", "123", "--async"], obj=ctx)

    # Assert
    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Verify workflow was triggered
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    assert workflow == "learn-async.yml"
    assert inputs["issue_number"] == "123"

    # Verify Claude was NOT launched interactively
    assert len(fake_executor.interactive_calls) == 0

    # Verify success output
    assert "Async learn job enqueued successfully" in result.output
    assert "Issue: #123" in result.output
    assert "https://github.com/owner/repo/actions/runs/" in result.output


def test_async_flag_updates_learn_status(tmp_path: Path) -> None:
    """Verify --async flag updates learn_status to pending."""
    # Create plan issue with local session data
    plan_body = format_plan_header_body_for_test(
        last_local_impl_session="local-session-xyz",
    )
    plan_body += "\n\n# Plan\n\nThis is the plan content."

    now = datetime.now(UTC)
    fake_issues = FakeGitHubIssues(
        issues={
            456: IssueInfo(
                number=456,
                title="Test Plan",
                body=plan_body,
                state="OPEN",
                url="https://github.com/owner/repo/issues/456",
                labels=["erk-plan"],
                assignees=[],
                created_at=now,
                updated_at=now,
                author="testuser",
            ),
        },
    )

    fake_github = FakeGitHub(issues_gateway=fake_issues)

    # Set up fake git with proper directory structure
    git_dir = tmp_path / ".git"
    fake_git = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        current_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "https://github.com/owner/repo.git"},
    )

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )

    global_config = GlobalConfig.test(erk_root=repo_dir)

    ctx = context_for_test(
        cwd=tmp_path,
        git=fake_git,
        github=fake_github,
        issues=fake_issues,
        repo=repo,
        global_config=global_config,
    )

    runner = CliRunner()

    # Act: Run learn with --async flag
    result = runner.invoke(cli, ["learn", "456", "--async"], obj=ctx)

    # Assert
    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Verify issue was updated with learn_status=pending
    assert len(fake_issues.updated_bodies) == 1
    issue_number, updated_body = fake_issues.updated_bodies[0]
    assert issue_number == 456

    # Verify learn_status is set in the updated body
    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data.get("learn_status") == "pending"


def test_async_flag_fails_not_erk_plan(tmp_path: Path) -> None:
    """Verify --async flag fails for non-erk-plan issues."""
    now = datetime.now(UTC)
    fake_issues = FakeGitHubIssues(
        issues={
            789: IssueInfo(
                number=789,
                title="Not a Plan",
                body="Just a regular issue",
                state="OPEN",
                url="https://github.com/owner/repo/issues/789",
                labels=["bug"],  # Not erk-plan
                assignees=[],
                created_at=now,
                updated_at=now,
                author="testuser",
            ),
        },
    )

    fake_github = FakeGitHub(issues_gateway=fake_issues)

    # Set up fake git with proper directory structure
    git_dir = tmp_path / ".git"
    fake_git = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        current_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "https://github.com/owner/repo.git"},
    )

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )

    global_config = GlobalConfig.test(erk_root=repo_dir)

    ctx = context_for_test(
        cwd=tmp_path,
        git=fake_git,
        github=fake_github,
        issues=fake_issues,
        repo=repo,
        global_config=global_config,
    )

    runner = CliRunner()

    # Act: Run learn with --async flag on non-erk-plan issue
    result = runner.invoke(cli, ["learn", "789", "--async"], obj=ctx)

    # Assert: Should fail
    assert result.exit_code == 1
    assert "is not an erk-plan" in result.output

    # Verify workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0


def test_async_flag_fails_no_session_data(tmp_path: Path) -> None:
    """Verify --async flag fails when no session data available."""
    # Create plan issue without session data
    plan_body = format_plan_header_body_for_test()  # No session data
    plan_body += "\n\n# Plan\n\nThis is the plan content."

    now = datetime.now(UTC)
    fake_issues = FakeGitHubIssues(
        issues={
            999: IssueInfo(
                number=999,
                title="Test Plan Without Sessions",
                body=plan_body,
                state="OPEN",
                url="https://github.com/owner/repo/issues/999",
                labels=["erk-plan"],
                assignees=[],
                created_at=now,
                updated_at=now,
                author="testuser",
            ),
        },
    )

    fake_github = FakeGitHub(issues_gateway=fake_issues)

    # Set up fake git with proper directory structure
    git_dir = tmp_path / ".git"
    fake_git = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        current_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "https://github.com/owner/repo.git"},
    )

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )

    global_config = GlobalConfig.test(erk_root=repo_dir)

    ctx = context_for_test(
        cwd=tmp_path,
        git=fake_git,
        github=fake_github,
        issues=fake_issues,
        repo=repo,
        global_config=global_config,
    )

    runner = CliRunner()

    # Act: Run learn with --async flag on plan without session data
    result = runner.invoke(cli, ["learn", "999", "--async"], obj=ctx)

    # Assert: Should fail
    assert result.exit_code == 1
    assert "No session data available" in result.output

    # Verify workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0


def test_async_flag_with_branch_inference(tmp_path: Path) -> None:
    """Verify --async flag works with issue number inferred from branch."""
    # Create plan issue with remote session data
    plan_body = format_plan_header_body_for_test(
        last_remote_impl_run_id="12345678",
    )
    plan_body += "\n\n# Plan\n\nThis is the plan content."

    now = datetime.now(UTC)
    fake_issues = FakeGitHubIssues(
        issues={
            555: IssueInfo(
                number=555,
                title="Test Plan",
                body=plan_body,
                state="OPEN",
                url="https://github.com/owner/repo/issues/555",
                labels=["erk-plan"],
                assignees=[],
                created_at=now,
                updated_at=now,
                author="testuser",
            ),
        },
    )

    fake_github = FakeGitHub(issues_gateway=fake_issues)

    # Set up fake git with branch name containing issue number
    git_dir = tmp_path / ".git"
    fake_git = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        current_branches={tmp_path: "P555-add-feature"},  # Issue number in branch
        remote_urls={(tmp_path, "origin"): "https://github.com/owner/repo.git"},
    )

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )

    global_config = GlobalConfig.test(erk_root=repo_dir)

    ctx = context_for_test(
        cwd=tmp_path,
        git=fake_git,
        github=fake_github,
        issues=fake_issues,
        repo=repo,
        global_config=global_config,
    )

    runner = CliRunner()

    # Act: Run learn with --async flag without specifying issue number
    result = runner.invoke(cli, ["learn", "--async"], obj=ctx)

    # Assert
    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Verify workflow was triggered with correct issue number
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    assert workflow == "learn-async.yml"
    assert inputs["issue_number"] == "555"
