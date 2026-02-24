"""Unit tests for learn status check prompts in land command."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import click
import pytest

from erk.cli.commands import land_cmd
from erk.cli.commands.land_cmd import (
    _check_learn_status_and_prompt,
    _store_learn_materials_branch,
    _trigger_async_learn,
)
from erk.core.context import context_for_test
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.console.fake import FakeConsole
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.plan_helpers import (
    create_plan_store_with_plans,
    format_plan_header_body_for_test,
)


def _make_plan(
    *,
    number: int,
    title: str = "Test plan",
    labels: list[str] | None = None,
    **header_kwargs: object,
) -> Plan:
    """Create a Plan object with plan-header metadata for testing."""
    now = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
    body = format_plan_header_body_for_test(**header_kwargs)
    return Plan(
        plan_identifier=str(number),
        title=title,
        body=body,
        state=PlanState.OPEN,
        url=f"https://github.com/test-owner/test-repo/pull/{number}",
        labels=labels if labels is not None else ["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
        objective_id=None,
        header_fields={},
    )


def test_check_learn_status_and_prompt_skips_when_already_learned(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that _check_learn_status_and_prompt shows positive feedback when plan has been
    learned from.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 123

    plan = _make_plan(
        number=issue_number,
        created_from_session="plan-session-1",
        last_local_impl_session="impl-session-1",
        last_learn_session="learn-session-1",
    )
    backend, fake_github = create_plan_store_with_plans({str(issue_number): plan})

    ctx = context_for_test(cwd=repo_root, github=fake_github, plan_store=backend)

    # Should return without any interaction (plan already learned from)
    _check_learn_status_and_prompt(
        ctx, repo_root=repo_root, plan_id=str(issue_number), force=False, script=False
    )

    # Verify positive feedback is shown
    captured = capsys.readouterr()
    assert "Learn completed for plan #123" in captured.err


def test_check_learn_status_and_prompt_skips_when_force(
    tmp_path: Path,
) -> None:
    """Test that _check_learn_status_and_prompt does nothing when force=True."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    ctx = context_for_test(cwd=repo_root)

    # With force=True, should return immediately without calling find_sessions_for_plan
    _check_learn_status_and_prompt(
        ctx, repo_root=repo_root, plan_id="123", force=True, script=False
    )


def test_check_learn_status_and_prompt_warns_when_not_learned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that _check_learn_status_and_prompt shows warning when not learned.

    When user chooses option 2 (continue without learning), the function returns normally.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 123

    plan = _make_plan(number=issue_number)
    backend, fake_github = create_plan_store_with_plans({str(issue_number): plan})

    # Mock click.prompt to return choice 2 (continue without learning)
    monkeypatch.setattr(click, "prompt", lambda *args, **kwargs: 2)

    # Create context with interactive FakeConsole
    fake_console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=True,
        is_stderr_tty=True,
        confirm_responses=[],  # Not used - we mock click.prompt instead
    )
    ctx = context_for_test(
        cwd=repo_root, console=fake_console, github=fake_github, plan_store=backend
    )

    # Should show warning and continue
    _check_learn_status_and_prompt(
        ctx, repo_root=repo_root, plan_id=str(issue_number), force=False, script=False
    )

    # Check that warning was shown
    captured = capsys.readouterr()
    assert "has not been learned from" in captured.err
    assert "#123" in captured.err
    assert "not been learned from" in captured.err


def test_check_learn_status_and_prompt_cancels_when_user_declines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that _check_learn_status_and_prompt exits when user chooses cancel."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 123

    plan = _make_plan(number=issue_number)
    backend, fake_github = create_plan_store_with_plans({str(issue_number): plan})

    # Mock click.prompt to return choice 3 (cancel)
    monkeypatch.setattr(click, "prompt", lambda *args, **kwargs: 3)

    # Create context with interactive FakeConsole
    fake_console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=True,
        is_stderr_tty=True,
        confirm_responses=[],  # Not used - we mock click.prompt instead
    )
    ctx = context_for_test(
        cwd=repo_root, console=fake_console, github=fake_github, plan_store=backend
    )

    # Should raise SystemExit(0) when user chooses cancel
    with pytest.raises(SystemExit) as exc_info:
        _check_learn_status_and_prompt(
            ctx, repo_root=repo_root, plan_id=str(issue_number), force=False, script=False
        )

    assert exc_info.value.code == 0


def test_check_learn_status_and_prompt_outputs_script_when_user_declines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that _check_learn_status_and_prompt outputs script when declining.

    When script=True and user chooses cancel, the function should output a
    no-op activation script path before exiting.
    This prevents 'cat: : No such file or directory' errors in land.sh.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 123

    plan = _make_plan(number=issue_number)
    backend, fake_github = create_plan_store_with_plans({str(issue_number): plan})

    # Mock click.prompt to return choice 3 (cancel)
    monkeypatch.setattr(click, "prompt", lambda *args, **kwargs: 3)

    # Create context with interactive FakeConsole
    fake_console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=True,
        is_stderr_tty=True,
        confirm_responses=[],  # Not used - we mock click.prompt instead
    )
    ctx = context_for_test(
        cwd=repo_root, console=fake_console, github=fake_github, plan_store=backend
    )

    # Should raise SystemExit(0) when user cancels, but with script output
    with pytest.raises(SystemExit) as exc_info:
        _check_learn_status_and_prompt(
            ctx, repo_root=repo_root, plan_id=str(issue_number), force=False, script=True
        )

    assert exc_info.value.code == 0

    # Verify that a script path was output to stdout (machine_output)
    captured = capsys.readouterr()
    # The script path should be in stdout and end with a valid file path
    assert ".erk/scratch/" in captured.out or "land" in captured.out


def test_check_learn_status_and_prompt_skips_for_learn_plans(
    tmp_path: Path,
) -> None:
    """Test that _check_learn_status_and_prompt skips check for learn plans.

    Learn plans (issues with erk-learn label) should not warn about needing
    to be learned from, since they are themselves for extracting insights.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 123

    plan = _make_plan(
        number=issue_number,
        title="Learn: Extract testing patterns",
        labels=["erk-plan", "erk-learn"],
    )
    backend, fake_github = create_plan_store_with_plans({str(issue_number): plan})

    ctx = context_for_test(cwd=repo_root, github=fake_github, plan_store=backend)

    # Should return immediately without calling find_sessions_for_plan
    _check_learn_status_and_prompt(
        ctx, repo_root=repo_root, plan_id=str(issue_number), force=False, script=False
    )


def test_check_learn_status_and_prompt_skips_when_config_disabled(
    tmp_path: Path,
) -> None:
    """Test that _check_learn_status_and_prompt skips when prompt_learn_on_land=False."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create context with prompt_learn_on_land=False
    global_config = GlobalConfig.test(
        erk_root=tmp_path / ".erk",
        prompt_learn_on_land=False,
    )
    ctx = context_for_test(cwd=repo_root, global_config=global_config)

    # With prompt_learn_on_land=False, should return immediately
    _check_learn_status_and_prompt(
        ctx, repo_root=repo_root, plan_id="123", force=False, script=False
    )


def test_check_learn_status_and_prompt_runs_when_config_enabled(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that _check_learn_status_and_prompt runs normally when prompt_learn_on_land=True."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 123

    plan = _make_plan(
        number=issue_number,
        created_from_session="plan-session-1",
        last_local_impl_session="impl-session-1",
        last_learn_session="learn-session-1",
    )
    backend, fake_github = create_plan_store_with_plans({str(issue_number): plan})

    # Create context with prompt_learn_on_land=True (default)
    global_config = GlobalConfig.test(
        erk_root=tmp_path / ".erk",
        prompt_learn_on_land=True,
    )
    ctx = context_for_test(
        cwd=repo_root, global_config=global_config, github=fake_github, plan_store=backend
    )

    # Should run the check and show positive feedback
    _check_learn_status_and_prompt(
        ctx, repo_root=repo_root, plan_id=str(issue_number), force=False, script=False
    )

    # Verify positive feedback is shown (check actually ran)
    captured = capsys.readouterr()
    assert "Learn completed for plan #123" in captured.err


# Tests for learn_status from plan header metadata


def test_check_learn_status_completed_shows_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that completed learn_status in plan header shows success message."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 123

    plan = _make_plan(number=issue_number, learn_status="completed_no_plan")
    backend, fake_github = create_plan_store_with_plans({str(issue_number): plan})

    ctx = context_for_test(cwd=repo_root, github=fake_github, plan_store=backend)

    # Should return immediately with success message
    _check_learn_status_and_prompt(
        ctx, repo_root=repo_root, plan_id=str(issue_number), force=False, script=False
    )

    # Verify success message
    captured = capsys.readouterr()
    assert "Learn completed for plan #123" in captured.err


def test_check_learn_status_pending_shows_progress(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that learn_status='pending' in plan header shows progress message."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 123

    plan = _make_plan(number=issue_number, learn_status="pending")
    backend, fake_github = create_plan_store_with_plans({str(issue_number): plan})

    ctx = context_for_test(cwd=repo_root, github=fake_github, plan_store=backend)

    # Should return immediately with progress message
    _check_learn_status_and_prompt(
        ctx, repo_root=repo_root, plan_id=str(issue_number), force=False, script=False
    )

    # Verify progress message
    captured = capsys.readouterr()
    assert "Async learn in progress for plan #123" in captured.err


def test_check_learn_status_null_with_sessions_shows_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that null learn_status with existing learn sessions shows success.

    This tests backward compatibility - plans without learn_status field
    but with learn_session_ids should still be detected as learned.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 123

    plan = _make_plan(
        number=issue_number,
        learn_status=None,
        last_learn_session="learn-session-1",
    )
    backend, fake_github = create_plan_store_with_plans({str(issue_number): plan})

    ctx = context_for_test(cwd=repo_root, github=fake_github, plan_store=backend)

    # Should return with success message
    _check_learn_status_and_prompt(
        ctx, repo_root=repo_root, plan_id=str(issue_number), force=False, script=False
    )

    # Verify success message
    captured = capsys.readouterr()
    assert "Learn completed for plan #123" in captured.err


def test_check_learn_status_null_no_sessions_triggers_async_in_non_interactive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test null learn_status without sessions auto-triggers async learn in non-interactive."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 123

    plan = _make_plan(number=issue_number, learn_status=None)
    backend, fake_github = create_plan_store_with_plans({str(issue_number): plan})

    # Mock subprocess.Popen to simulate successful async learn trigger
    # The _trigger_async_learn function uses Popen to stream stderr in real-time
    class MockPopen:
        def __init__(self, cmd, **kwargs):
            self.args = cmd
            self.returncode = 0
            self._stdout = (
                '{"success": true, "plan_id": "123", '
                '"workflow_triggered": true, "run_id": "test-run-id"}'
            )

        def communicate(self):
            return self._stdout, None

    monkeypatch.setattr(subprocess, "Popen", MockPopen)

    # Create non-interactive console
    fake_console = FakeConsole(
        is_interactive=False,  # Non-interactive mode
        is_stdout_tty=False,
        is_stderr_tty=False,
        confirm_responses=[],
    )
    ctx = context_for_test(
        cwd=repo_root, console=fake_console, github=fake_github, plan_store=backend
    )

    # Should auto-trigger async learn without prompting
    _check_learn_status_and_prompt(
        ctx, repo_root=repo_root, plan_id=str(issue_number), force=False, script=False
    )

    # Verify async learn was triggered
    captured = capsys.readouterr()
    assert "Triggering async learn for plan #123" in captured.err
    assert "Async learn triggered" in captured.err


def test_check_learn_status_and_prompt_manual_learn_preprocesses_and_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that choosing option 4 preprocesses sessions and continues landing."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 456

    plan = _make_plan(number=issue_number)
    backend, fake_github = create_plan_store_with_plans({str(issue_number): plan})

    # Mock click.prompt to return choice 4 (preprocess and continue)
    monkeypatch.setattr(click, "prompt", lambda *args, **kwargs: 4)

    # Track whether _preprocess_and_prepare_manual_learn was called
    preprocess_calls: list[int] = []

    def mock_preprocess(ctx, *, repo_root, plan_issue_number):
        preprocess_calls.append(plan_issue_number)
        # Returns normally (no SystemExit) - landing continues

    monkeypatch.setattr(land_cmd, "_preprocess_and_prepare_manual_learn", mock_preprocess)

    # Create context with interactive FakeConsole
    fake_console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=True,
        is_stderr_tty=True,
        confirm_responses=[],
    )
    ctx = context_for_test(
        cwd=repo_root, console=fake_console, github=fake_github, plan_store=backend
    )

    # Should return normally (no SystemExit) - landing continues
    _check_learn_status_and_prompt(
        ctx, repo_root=repo_root, plan_id=str(issue_number), force=False, script=False
    )

    # Verify preprocessing was called
    assert preprocess_calls == [456]


# Tests for _store_learn_materials_branch


def test_store_learn_materials_branch_updates_plan_header(
    tmp_path: Path,
) -> None:
    """Test that _store_learn_materials_branch stores the branch on the plan issue."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 123

    plan = _make_plan(number=issue_number)
    backend, fake_github = create_plan_store_with_plans({str(issue_number): plan})

    ctx = context_for_test(cwd=repo_root, github=fake_github, plan_store=backend)

    _store_learn_materials_branch(
        ctx,
        repo_root=repo_root,
        plan_issue_number=issue_number,
        learn_branch="learn/123",
    )

    # Verify PR body was updated with learn_materials_branch
    pr = fake_github.get_pr(Path("/repo"), issue_number)
    assert "learn_materials_branch" in pr.body
    assert "learn/123" in pr.body


def test_store_learn_materials_branch_handles_missing_issue(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that _store_learn_materials_branch handles missing issue gracefully."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    ctx = context_for_test(cwd=repo_root)

    # Should not raise, just print warning
    _store_learn_materials_branch(
        ctx,
        repo_root=repo_root,
        plan_issue_number=999,
        learn_branch="learn/999",
    )

    # Verify warning was printed
    captured = capsys.readouterr()
    assert "Could not store learn branch" in captured.err
    assert "#999" in captured.err


# Tests for _trigger_async_learn storing learn branch


def test_trigger_async_learn_stores_learn_branch_on_plan_header(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test _trigger_async_learn stores learn branch on plan header."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 123

    plan = _make_plan(number=issue_number)
    backend, fake_github = create_plan_store_with_plans({str(issue_number): plan})

    # Mock subprocess.Popen to return successful JSON with learn_branch
    class MockPopen:
        def __init__(self, cmd, **kwargs):
            self.args = cmd
            self.returncode = 0
            self._stdout = json.dumps(
                {
                    "success": True,
                    "plan_id": "123",
                    "workflow_triggered": True,
                    "run_id": "test-run-id",
                    "workflow_url": "https://github.com/owner/repo/actions/runs/test-run-id",
                    "learn_branch": "learn/123",
                }
            )

        def communicate(self):
            return self._stdout, None

    monkeypatch.setattr(subprocess, "Popen", MockPopen)

    ctx = context_for_test(cwd=repo_root, github=fake_github, plan_store=backend)

    _trigger_async_learn(ctx, repo_root=repo_root, plan_issue_number=issue_number)

    # Verify PR body was updated with learn_materials_branch
    pr = fake_github.get_pr(Path("/repo"), issue_number)
    assert "learn_materials_branch" in pr.body
    assert "learn/123" in pr.body

    # Verify success message was shown
    captured = capsys.readouterr()
    assert "Async learn triggered" in captured.err


# Tests for option 4 calling preprocessing


def test_option4_calls_preprocess_and_continues_landing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that choosing option 4 calls _preprocess_and_prepare_manual_learn and continues."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 456

    plan = _make_plan(number=issue_number)
    backend, fake_github = create_plan_store_with_plans({str(issue_number): plan})

    # Mock click.prompt to return choice 4 (preprocess and continue)
    monkeypatch.setattr(click, "prompt", lambda *args, **kwargs: 4)

    # Track whether _preprocess_and_prepare_manual_learn was called
    preprocess_calls: list[tuple[Path, int]] = []

    def mock_preprocess_and_prepare(ctx, *, repo_root, plan_issue_number):
        preprocess_calls.append((repo_root, plan_issue_number))
        # Returns normally - no SystemExit, landing continues

    monkeypatch.setattr(
        land_cmd, "_preprocess_and_prepare_manual_learn", mock_preprocess_and_prepare
    )

    # Create context with interactive FakeConsole
    fake_console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=True,
        is_stderr_tty=True,
        confirm_responses=[],
    )
    ctx = context_for_test(
        cwd=repo_root, console=fake_console, github=fake_github, plan_store=backend
    )

    # Should return normally (no SystemExit) - landing continues after preprocessing
    _check_learn_status_and_prompt(
        ctx, repo_root=repo_root, plan_id=str(issue_number), force=False, script=False
    )

    # Verify _preprocess_and_prepare_manual_learn was called with correct args
    assert len(preprocess_calls) == 1
    assert preprocess_calls[0] == (repo_root, issue_number)


# Tests for _store_learn_materials_branch with planned-PR backend (Fix 2)


def test_store_learn_materials_branch_comment_fallback_on_missing_metadata(
    tmp_path: Path,
) -> None:
    """Test that _store_learn_materials_branch falls back to comment when no metadata block."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    issue_number = 7618

    # Create PR with no plan-header metadata block (just plain text body)
    fake_issues = FakeGitHubIssues()
    pr_details = PRDetails(
        number=issue_number,
        url=f"https://github.com/test-owner/test-repo/pull/{issue_number}",
        title="PR without metadata",
        body="# Plan\n\nNo metadata block here.",
        state="OPEN",
        is_draft=True,
        base_ref_name="master",
        head_ref_name="plan-fix-something",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )
    fake_gh = FakeGitHub(
        issues_gateway=fake_issues,
        pr_details={issue_number: pr_details},
    )
    draft_backend = PlannedPRBackend(fake_gh, fake_issues, time=FakeTime())

    ctx = context_for_test(
        cwd=repo_root,
        github=fake_gh,
        issues=fake_issues,
        plan_store=draft_backend,
    )

    _store_learn_materials_branch(
        ctx,
        repo_root=repo_root,
        plan_issue_number=issue_number,
        learn_branch="learn/7618",
    )

    # Verify a PR comment was added (fallback path) instead of metadata update
    # PlannedPRBackend.add_comment delegates to github.create_pr_comment
    assert len(fake_gh.pr_comments) == 1
    comment_pr, comment_body = fake_gh.pr_comments[0]
    assert comment_pr == issue_number
    assert "learn/7618" in comment_body
