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
from erk_shared.gateway.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import render_metadata_block
from erk_shared.gateway.github.metadata.types import MetadataBlock
from tests.fakes.prompt_executor import FakePromptExecutor


def test_display_shows_remote_impl_message_when_set(capsys: pytest.CaptureFixture[str]) -> None:
    """Display shows remote implementation message when last_remote_impl_at is set."""
    result = LearnResult(
        plan_id="123",
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
        plan_id="123",
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
        plan_id="123",
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

    fake_executor = FakePromptExecutor(available=True)

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
        prompt_executor=fake_executor,
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

    fake_executor = FakePromptExecutor(available=True)

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
        prompt_executor=fake_executor,
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


def _make_plan_body_with_learn_branch(session_id: str, learn_branch: str) -> str:
    """Create a valid issue body with plan-header metadata including learn_materials_branch."""
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "test-user",
        "created_from_session": session_id,
        "learn_materials_branch": learn_branch,
    }
    header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))
    return f"{header_block}\n\n# Plan\n\nTest plan content"


def test_learn_passes_learn_branch_when_available(tmp_path: Path) -> None:
    """Verify learn_materials_branch from plan header triggers learn branch path."""
    session_id = "test-session-branch"
    learn_branch = "learn/789"
    issue_body = _make_plan_body_with_learn_branch(session_id, learn_branch)

    now = datetime.now(UTC)
    fake_issues = FakeGitHubIssues(
        issues={
            789: IssueInfo(
                number=789,
                title="Test Plan",
                body=issue_body,
                state="OPEN",
                url="https://github.com/owner/repo/issues/789",
                labels=["erk-plan"],
                assignees=[],
                created_at=now,
                updated_at=now,
                author="testuser",
            ),
        },
    )

    git_dir = tmp_path / ".git"
    fake_git = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        current_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "https://github.com/owner/repo.git"},
    )

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

    fake_executor = FakePromptExecutor(available=True)

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
        prompt_executor=fake_executor,
        repo=repo,
        global_config=global_config,
    )

    runner = CliRunner()

    result = runner.invoke(cli, ["learn", "789", "-i"], obj=ctx)

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Verify execute_interactive was called without gist_url param (branch path uses plain command)
    assert len(fake_executor.interactive_calls) == 1
    _worktree_path, _dangerous, command, _target_subpath, _model, _ = (
        fake_executor.interactive_calls[0]
    )
    assert command == "/erk:learn 789"


def test_learn_branch_skips_session_discovery_and_display(tmp_path: Path) -> None:
    """When learn branch is present, session paths are not displayed."""
    session_id = "test-session-branch-skip"
    learn_branch = "learn/555"
    issue_body = _make_plan_body_with_learn_branch(session_id, learn_branch)

    now = datetime.now(UTC)
    fake_issues = FakeGitHubIssues(
        issues={
            555: IssueInfo(
                number=555,
                title="Test Plan",
                body=issue_body,
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

    git_dir = tmp_path / ".git"
    fake_git = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        current_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "https://github.com/owner/repo.git"},
    )

    # Set up fake Claude installation with a session that would normally be discovered
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

    fake_executor = FakePromptExecutor(available=True)

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
        prompt_executor=fake_executor,
        repo=repo,
        global_config=global_config,
    )

    runner = CliRunner()

    result = runner.invoke(cli, ["learn", "555", "-i"], obj=ctx)

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Output should contain the preprocessed materials message (user_output writes to stderr)
    captured_output = result.output
    # CliRunner captures stderr in output when mix_stderr=True (default)
    assert "Preprocessed learn materials for plan 555" in captured_output
    assert "learn/555" in captured_output
    assert "Sessions have been preprocessed and committed to the learn branch." in captured_output

    # Output should NOT contain session discovery artifacts
    assert "Sessions for plan" not in captured_output
    assert "Planning session" not in captured_output
    assert "Readable sessions" not in captured_output

    # The command passed to execute_interactive should NOT include gist_url
    assert len(fake_executor.interactive_calls) == 1
    _worktree_path, _dangerous, command, _target_subpath, _model, _ = (
        fake_executor.interactive_calls[0]
    )
    assert command == "/erk:learn 555"


def test_learn_without_learn_branch_does_not_include_param(tmp_path: Path) -> None:
    """Verify command has no learn_branch when plan header doesn't have one."""
    session_id = "test-session-no-branch"
    issue_body = _make_plan_body_with_session(session_id)

    now = datetime.now(UTC)
    fake_issues = FakeGitHubIssues(
        issues={
            321: IssueInfo(
                number=321,
                title="Test Plan",
                body=issue_body,
                state="OPEN",
                url="https://github.com/owner/repo/issues/321",
                labels=["erk-plan"],
                assignees=[],
                created_at=now,
                updated_at=now,
                author="testuser",
            ),
        },
    )

    git_dir = tmp_path / ".git"
    fake_git = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        current_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "https://github.com/owner/repo.git"},
    )

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

    fake_executor = FakePromptExecutor(available=True)

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
        prompt_executor=fake_executor,
        repo=repo,
        global_config=global_config,
    )

    runner = CliRunner()

    result = runner.invoke(cli, ["learn", "321", "-i"], obj=ctx)

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Verify command does NOT include learn_branch
    assert len(fake_executor.interactive_calls) == 1
    _worktree_path, _dangerous, command, _target_subpath, _model, _ = (
        fake_executor.interactive_calls[0]
    )
    assert command == "/erk:learn 321"
    assert "learn_branch" not in command


def test_learn_branch_auto_launches_without_interactive_flag(tmp_path: Path) -> None:
    """Learn-branch path always auto-launches, even without -i flag."""
    session_id = "test-session-branch-auto"
    learn_branch = "learn/900"
    issue_body = _make_plan_body_with_learn_branch(session_id, learn_branch)

    now = datetime.now(UTC)
    fake_issues = FakeGitHubIssues(
        issues={
            900: IssueInfo(
                number=900,
                title="Test Plan",
                body=issue_body,
                state="OPEN",
                url="https://github.com/owner/repo/issues/900",
                labels=["erk-plan"],
                assignees=[],
                created_at=now,
                updated_at=now,
                author="testuser",
            ),
        },
    )

    git_dir = tmp_path / ".git"
    fake_git = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        current_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "https://github.com/owner/repo.git"},
    )

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

    fake_executor = FakePromptExecutor(available=True)

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
        prompt_executor=fake_executor,
        repo=repo,
        global_config=global_config,
    )

    runner = CliRunner()

    # Act: Run learn WITHOUT -i flag — branch path should still auto-launch
    result = runner.invoke(cli, ["learn", "900"], obj=ctx)

    # Assert: Should auto-launch without prompting
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert len(fake_executor.interactive_calls) == 1
    _worktree_path, _dangerous, command, _target_subpath, _model, _ = (
        fake_executor.interactive_calls[0]
    )
    assert command == "/erk:learn 900"


def test_dangerous_flag_auto_launches_without_interactive_flag(tmp_path: Path) -> None:
    """The -d flag implies auto-launch, skipping the confirmation prompt."""
    session_id = "test-session-dangerous-auto"
    issue_body = _make_plan_body_with_session(session_id)

    now = datetime.now(UTC)
    fake_issues = FakeGitHubIssues(
        issues={
            901: IssueInfo(
                number=901,
                title="Test Plan",
                body=issue_body,
                state="OPEN",
                url="https://github.com/owner/repo/issues/901",
                labels=["erk-plan"],
                assignees=[],
                created_at=now,
                updated_at=now,
                author="testuser",
            ),
        },
    )

    git_dir = tmp_path / ".git"
    fake_git = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        current_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "https://github.com/owner/repo.git"},
    )

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

    fake_executor = FakePromptExecutor(available=True)

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
        prompt_executor=fake_executor,
        repo=repo,
        global_config=global_config,
    )

    runner = CliRunner()

    # Act: Run learn with -d but NOT -i — should auto-launch
    result = runner.invoke(cli, ["learn", "901", "-d"], obj=ctx)

    # Assert: Should auto-launch with dangerous=True
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert len(fake_executor.interactive_calls) == 1
    _worktree_path, dangerous, command, _target_subpath, _model, _ = (
        fake_executor.interactive_calls[0]
    )
    assert dangerous is True
    assert command == "/erk:learn 901"


def test_session_path_without_flags_prompts_user(tmp_path: Path) -> None:
    """Session-discovery path without -i or -d prompts for confirmation."""
    session_id = "test-session-prompt"
    issue_body = _make_plan_body_with_session(session_id)

    now = datetime.now(UTC)
    fake_issues = FakeGitHubIssues(
        issues={
            902: IssueInfo(
                number=902,
                title="Test Plan",
                body=issue_body,
                state="OPEN",
                url="https://github.com/owner/repo/issues/902",
                labels=["erk-plan"],
                assignees=[],
                created_at=now,
                updated_at=now,
                author="testuser",
            ),
        },
    )

    git_dir = tmp_path / ".git"
    fake_git = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        current_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "https://github.com/owner/repo.git"},
    )

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

    fake_executor = FakePromptExecutor(available=True)

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
        prompt_executor=fake_executor,
        repo=repo,
        global_config=global_config,
    )

    runner = CliRunner()

    # Act: Run learn without -i or -d, provide "n" to deny the prompt
    result = runner.invoke(cli, ["learn", "902"], obj=ctx, input="n\n")

    # Assert: Should NOT have auto-launched (user declined)
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert len(fake_executor.interactive_calls) == 0
