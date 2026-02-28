"""Tests for land_learn module: learn plan creation logic."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk.cli.commands.land_learn import (
    _compute_session_stats,
    _create_learn_pr_impl,
    _create_learn_pr_with_sessions,
    _log_session_discovery,
    _should_create_learn_pr,
)
from erk.cli.commands.land_pipeline import LandState
from erk.core.context import context_for_test
from erk_shared.context.types import GlobalConfig, LoadedConfig
from erk_shared.gateway.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from erk_shared.sessions.discovery import SessionsForPlan


def _make_pr_details(
    *,
    pr_number: int,
    branch: str,
    title: str = "Test PR",
    labels: tuple[str, ...] = (),
) -> PRDetails:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return PRDetails(
        number=pr_number,
        url=f"https://github.com/owner/repo/pull/{pr_number}",
        title=title,
        body="Test body",
        state="OPEN",
        base_ref_name="main",
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=True,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
        labels=labels,
        created_at=now,
        updated_at=now,
    )


def _land_state(
    tmp_path: Path,
    *,
    plan_id: str | None = None,
    merged_pr_number: int | None = None,
) -> LandState:
    return LandState(
        cwd=tmp_path,
        force=True,
        script=False,
        pull_flag=True,
        no_delete=False,
        up_flag=False,
        dry_run=False,
        target_arg=None,
        repo_root=tmp_path,
        main_repo_root=tmp_path,
        branch="feature",
        pr_number=42,
        pr_details=None,
        worktree_path=None,
        is_current_branch=False,
        use_graphite=False,
        target_child_branch=None,
        objective_number=None,
        plan_id=plan_id,
        cleanup_confirmed=True,
        merged_pr_number=merged_pr_number,
    )


# ---------------------------------------------------------------------------
# _should_create_learn_pr
# ---------------------------------------------------------------------------


def test_returns_local_config_when_set(tmp_path: Path) -> None:
    """Local config prompt_learn_on_land=True overrides global."""
    ctx = context_for_test(
        local_config=LoadedConfig.test(prompt_learn_on_land=True),
        global_config=GlobalConfig.test(tmp_path, prompt_learn_on_land=False),
        cwd=tmp_path,
    )
    assert _should_create_learn_pr(ctx) is True


def test_falls_back_to_global_config_when_local_unset(tmp_path: Path) -> None:
    """When local_config.prompt_learn_on_land is None, falls back to global."""
    ctx = context_for_test(
        local_config=LoadedConfig.test(prompt_learn_on_land=None),
        global_config=GlobalConfig.test(tmp_path, prompt_learn_on_land=False),
        cwd=tmp_path,
    )
    assert _should_create_learn_pr(ctx) is False


def test_returns_true_when_both_unset(tmp_path: Path) -> None:
    """When local is None and global_config is None, returns True (safe default)."""
    ctx = context_for_test(
        local_config=LoadedConfig.test(prompt_learn_on_land=None),
        global_config=None,
        cwd=tmp_path,
    )
    assert _should_create_learn_pr(ctx) is True


# ---------------------------------------------------------------------------
# _create_learn_pr_with_sessions
# ---------------------------------------------------------------------------


def test_returns_early_when_plan_id_is_none(tmp_path: Path) -> None:
    """No-op when state.plan_id is None."""
    fake_issues = FakeGitHubIssues(username="testuser")
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    ctx = context_for_test(github=fake_github, issues=fake_issues, cwd=tmp_path)
    state = _land_state(tmp_path, plan_id=None, merged_pr_number=99)

    _create_learn_pr_with_sessions(ctx, state=state)

    assert len(fake_github.created_prs) == 0


def test_returns_early_when_merged_pr_number_is_none(tmp_path: Path) -> None:
    """No-op when state.merged_pr_number is None."""
    fake_issues = FakeGitHubIssues(username="testuser")
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    ctx = context_for_test(github=fake_github, issues=fake_issues, cwd=tmp_path)
    state = _land_state(tmp_path, plan_id="100", merged_pr_number=None)

    _create_learn_pr_with_sessions(ctx, state=state)

    assert len(fake_github.created_prs) == 0


def test_shows_warning_on_exception(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exception in _create_learn_pr_impl is caught and shown as warning."""
    from erk.cli.commands import land_learn as learn_mod

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated network error")

    monkeypatch.setattr(learn_mod, "_create_learn_pr_impl", _raise)

    ctx = context_for_test(cwd=tmp_path)
    state = _land_state(tmp_path, plan_id="100", merged_pr_number=99)

    # Should NOT raise — exception is caught
    _create_learn_pr_with_sessions(ctx, state=state)

    captured = capsys.readouterr()
    assert "Warning" in captured.err
    assert "simulated network error" in captured.err


# ---------------------------------------------------------------------------
# _create_learn_pr_impl
# ---------------------------------------------------------------------------


def test_skips_when_config_disabled(tmp_path: Path) -> None:
    """Returns early when prompt_learn_on_land is False."""
    fake_issues = FakeGitHubIssues(username="testuser")
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    ctx = context_for_test(
        github=fake_github,
        issues=fake_issues,
        local_config=LoadedConfig.test(prompt_learn_on_land=False),
        cwd=tmp_path,
    )
    state = _land_state(tmp_path, plan_id="100", merged_pr_number=99)

    _create_learn_pr_impl(ctx, state=state)

    assert len(fake_github.created_prs) == 0


def test_skips_for_erk_learn_plan(tmp_path: Path) -> None:
    """Returns early when plan has erk-learn label (cycle prevention)."""
    pr = _make_pr_details(
        pr_number=100,
        branch="feature",
        title="Learn: some plan",
        labels=("erk-plan", "erk-learn"),
    )
    fake_issues = FakeGitHubIssues(username="testuser")
    fake_github = FakeGitHub(pr_details={100: pr}, issues_gateway=fake_issues)
    fake_time = FakeTime()
    plan_store = PlannedPRBackend(fake_github, fake_issues, time=fake_time)

    ctx = context_for_test(
        github=fake_github,
        issues=fake_issues,
        plan_store=plan_store,
        cwd=tmp_path,
    )
    state = _land_state(tmp_path, plan_id="100", merged_pr_number=99)

    _create_learn_pr_impl(ctx, state=state)

    assert len(fake_github.created_prs) == 0


def test_skips_when_plan_not_found(tmp_path: Path) -> None:
    """Returns silently when get_plan returns PlanNotFound."""
    fake_issues = FakeGitHubIssues(username="testuser")
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    fake_time = FakeTime()
    plan_store = PlannedPRBackend(fake_github, fake_issues, time=fake_time)

    ctx = context_for_test(
        github=fake_github,
        issues=fake_issues,
        plan_store=plan_store,
        cwd=tmp_path,
    )
    # plan_id "999" has no PR configured in FakeGitHub
    state = _land_state(tmp_path, plan_id="999", merged_pr_number=99)

    _create_learn_pr_impl(ctx, state=state)

    assert len(fake_github.created_prs) == 0


def test_creates_pr_and_shows_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Happy path: plan found, not erk-learn, creates learn draft PR."""
    pr = _make_pr_details(
        pr_number=100,
        branch="feature",
        title="Add widgets",
        labels=("erk-plan",),
    )
    fake_issues = FakeGitHubIssues(username="testuser", labels={"erk-pr", "erk-learn", "erk-plan"})
    fake_github = FakeGitHub(pr_details={100: pr}, issues_gateway=fake_issues)
    fake_time = FakeTime()
    fake_git = FakeGit(trunk_branches={tmp_path: "main"})
    plan_store = PlannedPRBackend(fake_github, fake_issues, time=fake_time)

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        issues=fake_issues,
        plan_store=plan_store,
        time=fake_time,
        cwd=tmp_path,
    )
    state = _land_state(tmp_path, plan_id="100", merged_pr_number=42)

    _create_learn_pr_impl(ctx, state=state)

    # Draft PR should have been created
    assert len(fake_github.created_prs) == 1
    _branch, pr_title, _body, _base, _draft = fake_github.created_prs[0]
    assert "Learn: Add widgets" in pr_title

    # Success output (includes session discovery warning since no sessions configured)
    captured = capsys.readouterr()
    assert "Created learn plan" in captured.err
    assert "#100" in captured.err
    assert "No sessions discovered" in captured.err
    assert "https://github.com/" in captured.err


# ---------------------------------------------------------------------------
# _log_session_discovery
# ---------------------------------------------------------------------------


def _make_session_jsonl(*, session_id: str, user_turns: int, duration_seconds: int) -> str:
    """Build realistic JSONL content for a session with user turns and timestamps."""
    base_ts = 1700000000.0
    lines: list[str] = []
    ts = base_ts
    ts_step = duration_seconds / max(user_turns * 2 - 1, 1)
    for i in range(user_turns):
        lines.append(
            json.dumps(
                {
                    "type": "user",
                    "sessionId": session_id,
                    "timestamp": ts,
                    "message": {"content": [{"type": "text", "text": f"User message {i + 1}"}]},
                }
            )
        )
        ts += ts_step
        lines.append(
            json.dumps(
                {
                    "type": "assistant",
                    "sessionId": session_id,
                    "timestamp": ts,
                    "message": {
                        "content": [{"type": "text", "text": f"Assistant response {i + 1}"}]
                    },
                }
            )
        )
        ts += ts_step
    return "\n".join(lines) + "\n"


def _make_sessions(
    *,
    planning: str | None = None,
    impl: list[str] | None = None,
    learn: list[str] | None = None,
) -> SessionsForPlan:
    return SessionsForPlan(
        planning_session_id=planning,
        implementation_session_ids=impl or [],
        learn_session_ids=learn or [],
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        last_session_branch=None,
        last_session_id=None,
        last_session_source=None,
    )


def test_log_no_sessions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Logs warning when no sessions discovered."""
    ctx = context_for_test(cwd=tmp_path)
    sessions = _make_sessions()

    _log_session_discovery(ctx, sessions=sessions, all_session_ids=[])

    captured = capsys.readouterr()
    assert "No sessions discovered" in captured.err


def test_log_planning_and_impl_sessions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Logs session counts with per-session type badges."""
    sessions = _make_sessions(
        planning="aaaa1111-2222-3333-4444-555566667777",
        impl=["bbbb1111-2222-3333-4444-555566667777"],
    )
    ctx = context_for_test(cwd=tmp_path)

    _log_session_discovery(ctx, sessions=sessions, all_session_ids=sessions.all_session_ids())

    captured = capsys.readouterr()
    assert "Discovered 2 session(s): 1 planning, 1 impl" in captured.err
    # Per-session type badges
    assert "\U0001f4dd" in captured.err  # planning badge
    assert "planning:" in captured.err
    assert "aaaa1111..." in captured.err
    assert "\U0001f527" in captured.err  # impl badge
    assert "impl:" in captured.err
    assert "bbbb1111..." in captured.err
    # No learn sessions → "learn" should not appear in the summary line
    assert "learn" not in captured.err.split("\n")[0]


def test_log_includes_learn_count(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Learn session count and badge appear when present."""
    sessions = _make_sessions(
        planning="aaaa1111-2222-3333-4444-555566667777",
        learn=["cccc1111-2222-3333-4444-555566667777"],
    )
    ctx = context_for_test(cwd=tmp_path)

    _log_session_discovery(ctx, sessions=sessions, all_session_ids=sessions.all_session_ids())

    captured = capsys.readouterr()
    assert "1 learn" in captured.err
    assert "\U0001f4da" in captured.err  # learn badge
    assert "learn:" in captured.err


def test_log_local_session_sizes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reports per-session preprocessing stats: turns, duration, and sizes."""
    session_id = "dddd1111-2222-3333-4444-555566667777"
    sessions = _make_sessions(impl=[session_id])

    # Write realistic JSONL so compute_session_stats can parse it
    jsonl_content = _make_session_jsonl(session_id=session_id, user_turns=5, duration_seconds=600)
    jsonl_file = tmp_path / f"{session_id}.jsonl"
    jsonl_file.write_text(jsonl_content, encoding="utf-8")

    fake_session = FakeSessionData(
        content=jsonl_content,
        size_bytes=len(jsonl_content),
        modified_at=0.0,
    )
    fake_claude = FakeClaudeInstallation.for_test(
        projects={tmp_path: FakeProject(sessions={session_id: fake_session})},
    )
    ctx = context_for_test(claude_installation=fake_claude, cwd=tmp_path)

    _log_session_discovery(ctx, sessions=sessions, all_session_ids=sessions.all_session_ids())

    captured = capsys.readouterr()
    assert "turns" in captured.err
    assert "\u2192" in captured.err  # arrow between raw and XML sizes
    assert "KB" in captured.err
    assert "dddd1111..." in captured.err


def test_log_session_mixed_local_and_not_found(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Shows stats for available sessions and 'not found' for missing ones."""
    local_id = "eeee1111-2222-3333-4444-555566667777"
    missing_id = "ffff1111-2222-3333-4444-555566667777"
    sessions = _make_sessions(
        planning=local_id,
        impl=[missing_id],
    )

    # Write realistic JSONL so compute_session_stats can parse it
    jsonl_content = _make_session_jsonl(session_id=local_id, user_turns=3, duration_seconds=300)
    jsonl_file = tmp_path / f"{local_id}.jsonl"
    jsonl_file.write_text(jsonl_content, encoding="utf-8")

    fake_session = FakeSessionData(
        content=jsonl_content,
        size_bytes=len(jsonl_content),
        modified_at=0.0,
    )
    fake_claude = FakeClaudeInstallation.for_test(
        projects={tmp_path: FakeProject(sessions={local_id: fake_session})},
    )
    ctx = context_for_test(claude_installation=fake_claude, cwd=tmp_path)

    _log_session_discovery(ctx, sessions=sessions, all_session_ids=sessions.all_session_ids())

    captured = capsys.readouterr()
    lines = captured.err.strip().split("\n")

    # Find the line for the local session — shows turns and KB
    local_line = next(line for line in lines if "eeee1111" in line)
    assert "turns" in local_line
    assert "KB" in local_line

    # Find the line for the missing session
    missing_line = next(line for line in lines if "ffff1111" in line)
    assert "not found" in missing_line


# ---------------------------------------------------------------------------
# _compute_session_stats
# ---------------------------------------------------------------------------


def test_compute_session_stats_returns_turns_and_duration(tmp_path: Path) -> None:
    """Computes user turns, duration, and sizes from JSONL."""
    session_id = "aaaa2222-3333-4444-5555-666677778888"
    jsonl_content = _make_session_jsonl(session_id=session_id, user_turns=4, duration_seconds=480)
    jsonl_file = tmp_path / f"{session_id}.jsonl"
    jsonl_file.write_text(jsonl_content, encoding="utf-8")

    stats = _compute_session_stats(jsonl_file, session_id=session_id)

    assert stats is not None
    assert stats.user_turns == 4
    assert stats.duration_minutes == 8
    assert stats.raw_size_kb >= 0
    assert stats.xml_size_kb >= 0


def test_compute_session_stats_returns_none_for_missing_file(tmp_path: Path) -> None:
    """Returns None when session file does not exist."""
    missing = tmp_path / "nonexistent.jsonl"
    stats = _compute_session_stats(missing, session_id="no-such-session")

    assert stats is None


def test_compute_session_stats_returns_xml_chunks(tmp_path: Path) -> None:
    """SessionStats includes xml_chunks from preprocessing pipeline."""
    session_id = "bbbb2222-3333-4444-5555-666677778888"
    jsonl_content = _make_session_jsonl(session_id=session_id, user_turns=3, duration_seconds=180)
    jsonl_file = tmp_path / f"{session_id}.jsonl"
    jsonl_file.write_text(jsonl_content, encoding="utf-8")

    stats = _compute_session_stats(jsonl_file, session_id=session_id)

    assert stats is not None
    assert isinstance(stats.xml_chunks, tuple)
    # Non-empty session should produce at least one XML chunk
    assert len(stats.xml_chunks) >= 1
    # xml_size_kb should match the chunks
    total_bytes = sum(len(chunk.encode("utf-8")) for chunk in stats.xml_chunks)
    assert stats.xml_size_kb == total_bytes // 1024


# ---------------------------------------------------------------------------
# _log_session_discovery return value
# ---------------------------------------------------------------------------


def test_log_session_discovery_returns_empty_dict_when_no_sessions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Returns empty dict when no sessions are discovered."""
    ctx = context_for_test(cwd=tmp_path)
    sessions = _make_sessions()

    result = _log_session_discovery(ctx, sessions=sessions, all_session_ids=[])

    assert result == {}
    captured = capsys.readouterr()
    assert "No sessions discovered" in captured.err


def test_log_session_discovery_returns_xml_files_for_readable_session(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Returns XML files dict when sessions have readable content."""
    session_id = "cccc1111-2222-3333-4444-555566667777"
    sessions = _make_sessions(impl=[session_id])

    jsonl_content = _make_session_jsonl(session_id=session_id, user_turns=3, duration_seconds=180)
    jsonl_file = tmp_path / f"{session_id}.jsonl"
    jsonl_file.write_text(jsonl_content, encoding="utf-8")

    fake_session = FakeSessionData(
        content=jsonl_content,
        size_bytes=len(jsonl_content),
        modified_at=0.0,
    )
    fake_claude = FakeClaudeInstallation.for_test(
        projects={tmp_path: FakeProject(sessions={session_id: fake_session})},
    )
    ctx = context_for_test(claude_installation=fake_claude, cwd=tmp_path)

    xml_files = _log_session_discovery(
        ctx, sessions=sessions, all_session_ids=sessions.all_session_ids()
    )

    # Should have at least one XML file for the readable session
    assert len(xml_files) >= 1
    for path, content in xml_files.items():
        # Path follows the naming convention
        assert "impl" in path  # session type prefix
        assert session_id in path
        assert path.endswith(".xml")
        assert path.startswith(".erk/impl-context/sessions/")
        # Content is non-empty XML
        assert len(content) > 0


def test_log_session_discovery_uses_correct_type_prefix(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """XML file paths use the correct session type prefix."""
    planning_id = "dddd1111-2222-3333-4444-555566667777"
    impl_id = "eeee1111-2222-3333-4444-555566667777"
    sessions = _make_sessions(planning=planning_id, impl=[impl_id])

    def _write_session(sid: str) -> FakeSessionData:
        content = _make_session_jsonl(session_id=sid, user_turns=2, duration_seconds=120)
        (tmp_path / f"{sid}.jsonl").write_text(content, encoding="utf-8")
        return FakeSessionData(content=content, size_bytes=len(content), modified_at=0.0)

    fake_claude = FakeClaudeInstallation.for_test(
        projects={
            tmp_path: FakeProject(
                sessions={
                    planning_id: _write_session(planning_id),
                    impl_id: _write_session(impl_id),
                }
            )
        },
    )
    ctx = context_for_test(claude_installation=fake_claude, cwd=tmp_path)

    xml_files = _log_session_discovery(
        ctx, sessions=sessions, all_session_ids=sessions.all_session_ids()
    )

    paths = list(xml_files.keys())
    planning_paths = [p for p in paths if "planning" in p]
    impl_paths = [p for p in paths if "impl" in p]
    assert len(planning_paths) >= 1
    assert len(impl_paths) >= 1
