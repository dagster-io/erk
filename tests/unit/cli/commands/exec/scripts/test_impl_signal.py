"""Tests for impl-signal exec CLI command.

Tests the started/ended event signaling for /erk:plan-implement.
Uses ErkContext.for_test() for dependency injection with FakeGitHubIssues.
"""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.impl_signal import impl_signal
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo


def _is_on_git_branch() -> bool:
    """Check if the process is running in a git repo on a named branch.

    Returns False in detached HEAD state (common in CI), which causes
    _get_branch_name() to return None and started events to fail.
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False


_requires_git_branch = pytest.mark.skipif(
    not _is_on_git_branch(),
    reason="Requires named git branch (CI may use detached HEAD)",
)


def _make_plan_header_body() -> str:
    """Create a minimal valid plan-header metadata block for testing."""
    return """## Plan

<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: testuser
```

</details>
<!-- /erk:metadata-block:plan-header -->
"""


def _make_issue(*, number: int) -> IssueInfo:
    """Create a test IssueInfo with valid plan-header body."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title="Test Plan",
        body=_make_plan_header_body(),
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def _setup_plan_ref(impl_dir: Path, *, plan_id: str) -> None:
    """Create a plan-ref.json file in the impl directory."""
    plan_ref = {
        "provider": "github",
        "plan_id": plan_id,
        "url": f"https://github.com/test/repo/issues/{plan_id}",
        "created_at": "2024-01-15T10:30:00+00:00",
        "synced_at": "2024-01-15T10:30:00+00:00",
        "labels": [],
        "objective_id": None,
    }
    impl_dir.mkdir(exist_ok=True)
    (impl_dir / "plan-ref.json").write_text(json.dumps(plan_ref, indent=2), encoding="utf-8")
    (impl_dir / "plan.md").write_text("# Test Plan\n", encoding="utf-8")


# --- Error path tests (no plan reference) ---


def test_started_no_plan_reference(tmp_path: Path) -> None:
    """Returns error when no plan-ref.json exists."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    (impl_dir / "plan.md").write_text("# Plan", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        impl_signal,
        ["started", "--session-id", "test-session-id"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["event"] == "started"
    assert data["error_type"] == "no-issue-reference"


def test_ended_no_plan_reference(tmp_path: Path) -> None:
    """Returns error when no plan-ref.json exists."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    (impl_dir / "plan.md").write_text("# Plan", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        impl_signal,
        ["ended"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["event"] == "ended"
    assert data["error_type"] == "no-issue-reference"


def test_started_missing_impl_folder(tmp_path: Path) -> None:
    """Returns error when .impl/ folder is missing."""
    runner = CliRunner()
    result = runner.invoke(
        impl_signal,
        ["started", "--session-id", "test-session-id"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["event"] == "started"
    assert data["error_type"] == "no-issue-reference"


def test_ended_missing_impl_folder(tmp_path: Path) -> None:
    """Returns error when .impl/ folder is missing."""
    runner = CliRunner()
    result = runner.invoke(
        impl_signal,
        ["ended"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["event"] == "ended"
    assert data["error_type"] == "no-issue-reference"


def test_worker_impl_fallback(tmp_path: Path) -> None:
    """Detects .worker-impl/ folder when .impl/ is missing."""
    impl_dir = tmp_path / ".worker-impl"
    impl_dir.mkdir()
    (impl_dir / "plan.md").write_text("# Plan", encoding="utf-8")
    # No plan-ref.json — should fail on that, not folder detection

    runner = CliRunner()
    result = runner.invoke(
        impl_signal,
        ["started", "--session-id", "test-session-id"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["error_type"] == "no-issue-reference"


def test_invalid_event() -> None:
    """Rejects invalid event names via Click validation."""
    runner = CliRunner()
    result = runner.invoke(impl_signal, ["invalid"])

    assert result.exit_code == 2
    assert "invalid" in result.output.lower()


# --- Session ID validation ---


def test_started_fails_without_session_id(tmp_path: Path) -> None:
    """Returns error when no session-id provided."""
    _setup_plan_ref(tmp_path / ".impl", plan_id="123")

    runner = CliRunner()
    result = runner.invoke(
        impl_signal,
        ["started"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error_type"] == "session-id-required"


def test_started_fails_with_empty_session_id(tmp_path: Path) -> None:
    """Returns error when session-id is empty string."""
    _setup_plan_ref(tmp_path / ".impl", plan_id="123")

    runner = CliRunner()
    result = runner.invoke(
        impl_signal,
        ["started", "--session-id", ""],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error_type"] == "session-id-required"


def test_started_fails_with_whitespace_session_id(tmp_path: Path) -> None:
    """Returns error when session-id is whitespace only."""
    _setup_plan_ref(tmp_path / ".impl", plan_id="123")

    runner = CliRunner()
    result = runner.invoke(
        impl_signal,
        ["started", "--session-id", "   "],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error_type"] == "session-id-required"


# --- Happy path tests ---


@_requires_git_branch
def test_started_posts_comment_and_updates_metadata(tmp_path: Path) -> None:
    """Started event posts a comment and updates issue metadata via PlanBackend."""
    issue = _make_issue(number=123)
    fake_issues = FakeGitHubIssues(issues={123: issue})
    _setup_plan_ref(tmp_path / ".impl", plan_id="123")

    runner = CliRunner()
    result = runner.invoke(
        impl_signal,
        ["started", "--session-id", "test-session-123"],
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_issues),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["event"] == "started"
    assert data["issue_number"] == 123

    # Verify comment was posted
    assert len(fake_issues.added_comments) == 1
    comment_issue_number, comment_body, _comment_id = fake_issues.added_comments[0]
    assert comment_issue_number == 123
    assert "Starting implementation" in comment_body

    # Verify issue body was updated (metadata block)
    assert len(fake_issues.updated_bodies) == 1
    updated_issue_number, updated_body = fake_issues.updated_bodies[0]
    assert updated_issue_number == 123
    assert "plan-header" in updated_body


def test_ended_updates_metadata(tmp_path: Path) -> None:
    """Ended event updates issue metadata via PlanBackend without posting a comment."""
    issue = _make_issue(number=456)
    fake_issues = FakeGitHubIssues(issues={456: issue})
    _setup_plan_ref(tmp_path / ".impl", plan_id="456")

    runner = CliRunner()
    result = runner.invoke(
        impl_signal,
        ["ended", "--session-id", "test-session-456"],
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_issues),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["event"] == "ended"
    assert data["issue_number"] == 456

    # No comment for ended events
    assert len(fake_issues.added_comments) == 0

    # Verify issue body was updated (metadata block)
    assert len(fake_issues.updated_bodies) == 1
    updated_issue_number, updated_body = fake_issues.updated_bodies[0]
    assert updated_issue_number == 456
    assert "plan-header" in updated_body


@_requires_git_branch
def test_started_writes_local_run_state(tmp_path: Path) -> None:
    """Started event writes local run state file."""
    issue = _make_issue(number=789)
    fake_issues = FakeGitHubIssues(issues={789: issue})
    _setup_plan_ref(tmp_path / ".impl", plan_id="789")

    runner = CliRunner()
    result = runner.invoke(
        impl_signal,
        ["started", "--session-id", "test-session-789"],
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_issues),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True

    # Verify local run state was written
    run_state_file = tmp_path / ".impl" / "local-run-state.json"
    assert run_state_file.exists()
    run_state = json.loads(run_state_file.read_text(encoding="utf-8"))
    assert run_state["last_event"] == "started"
    assert run_state["session_id"] == "test-session-789"


# --- Submitted event tests ---


def test_submitted_updates_lifecycle_stage(tmp_path: Path) -> None:
    """Submitted event sets lifecycle_stage to 'implemented' via PlanBackend."""
    issue = _make_issue(number=100)
    fake_issues = FakeGitHubIssues(issues={100: issue})
    _setup_plan_ref(tmp_path / ".impl", plan_id="100")

    runner = CliRunner()
    result = runner.invoke(
        impl_signal,
        ["submitted"],
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_issues),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["event"] == "submitted"
    assert data["issue_number"] == 100

    # No comment for submitted events
    assert len(fake_issues.added_comments) == 0

    # Verify issue body was updated (metadata block with lifecycle_stage)
    assert len(fake_issues.updated_bodies) == 1
    updated_issue_number, updated_body = fake_issues.updated_bodies[0]
    assert updated_issue_number == 100
    assert "implemented" in updated_body


def test_submitted_no_plan_ref(tmp_path: Path) -> None:
    """Returns error when no plan-ref.json exists for submitted event."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    (impl_dir / "plan.md").write_text("# Plan", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        impl_signal,
        ["submitted"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["event"] == "submitted"
    assert data["error_type"] == "no-issue-reference"


def test_submitted_no_session_id_ok(tmp_path: Path) -> None:
    """Submitted event succeeds without --session-id (not required)."""
    issue = _make_issue(number=200)
    fake_issues = FakeGitHubIssues(issues={200: issue})
    _setup_plan_ref(tmp_path / ".impl", plan_id="200")

    runner = CliRunner()
    result = runner.invoke(
        impl_signal,
        ["submitted"],
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_issues),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["event"] == "submitted"
    assert data["issue_number"] == 200
