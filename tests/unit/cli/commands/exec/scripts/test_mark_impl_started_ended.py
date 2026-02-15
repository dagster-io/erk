"""Unit tests for mark_impl_started and mark_impl_ended commands.

Tests implementation event tracking via PlanBackend.
Uses real GitHubPlanStore with FakeGitHubIssues for testing.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.mark_impl_ended import mark_impl_ended
from erk.cli.commands.exec.scripts.mark_impl_started import mark_impl_started
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import find_metadata_block


def make_plan_header_body(
    *,
    schema_version: str,
    created_at: str,
    created_by: str,
    worktree_name: str,
) -> str:
    """Create a test issue body with plan-header metadata block."""
    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '{schema_version}'
created_at: '{created_at}'
created_by: {created_by}
worktree_name: {worktree_name}
last_local_impl_at: null
last_local_impl_event: null
last_local_impl_session: null
last_local_impl_user: null
last_remote_impl_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Test Plan

Some plan content here.
"""


def make_issue_info(number: int, body: str) -> IssueInfo:
    """Create test IssueInfo with given number and body."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title="Test Issue",
        body=body,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


# ============================================================================
# mark_impl_started Tests
# ============================================================================


def test_mark_impl_started_local_updates_metadata(tmp_path: Path) -> None:
    """mark-impl-started updates local impl metadata via PlanBackend."""
    # Setup .impl/ folder with plan-ref.json
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    plan_ref_file = impl_dir / "plan-ref.json"
    plan_ref_file.write_text(
        json.dumps(
            {
                "plan_id": "123",
                "provider": "github",
                "url": "https://github.com/test-owner/test-repo/issues/123",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    # Setup fake issue with plan-header
    body = make_plan_header_body(
        schema_version="2",
        created_at="2025-11-25T14:37:43.513418+00:00",
        created_by="testuser",
        worktree_name="test-worktree",
    )
    fake_gh = FakeGitHubIssues(issues={123: make_issue_info(123, body)})
    repo_root = Path("/fake/repo")
    runner = CliRunner()

    # Execute with session_id
    result = runner.invoke(
        mark_impl_started,
        ["--session-id", "test-session-id"],
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 123

    # Verify metadata updated
    updated_issue = fake_gh.get_issue(repo_root, 123)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["last_local_impl_event"] == "started"
    assert block.data["last_local_impl_session"] == "test-session-id"
    assert block.data["last_local_impl_at"] is not None
    assert block.data["last_local_impl_user"] is not None
    # Remote impl fields should remain null
    assert block.data["last_remote_impl_at"] is None

    # Verify .impl/local-run-state.json written
    local_state_file = impl_dir / "local-run-state.json"
    assert local_state_file.exists()
    local_state = json.loads(local_state_file.read_text(encoding="utf-8"))
    assert local_state["last_event"] == "started"
    assert local_state["session_id"] == "test-session-id"


def test_mark_impl_started_remote_updates_metadata(tmp_path: Path, monkeypatch) -> None:
    """mark-impl-started in GitHub Actions updates remote impl metadata."""
    # monkeypatch GITHUB_ACTIONS env var
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    # Setup .impl/ folder with plan-ref.json
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    plan_ref_file = impl_dir / "plan-ref.json"
    plan_ref_file.write_text(
        json.dumps(
            {
                "plan_id": "456",
                "provider": "github",
                "url": "https://github.com/test-owner/test-repo/issues/456",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    # Setup fake issue with plan-header
    body = make_plan_header_body(
        schema_version="2",
        created_at="2025-11-25T14:37:43.513418+00:00",
        created_by="testuser",
        worktree_name="test-worktree",
    )
    fake_gh = FakeGitHubIssues(issues={456: make_issue_info(456, body)})
    repo_root = Path("/fake/repo")
    runner = CliRunner()

    # Execute
    result = runner.invoke(
        mark_impl_started,
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify last_remote_impl_at updated (not local fields)
    updated_issue = fake_gh.get_issue(repo_root, 456)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["last_remote_impl_at"] is not None
    # Local impl fields should remain null in remote mode
    assert block.data["last_local_impl_event"] is None
    assert block.data["last_local_impl_session"] is None


def test_mark_impl_started_no_plan_ref(tmp_path: Path) -> None:
    """mark-impl-started gracefully handles missing plan-ref.json."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    # No .impl/ folder created
    result = runner.invoke(
        mark_impl_started,
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_gh),
    )

    assert result.exit_code == 0  # Graceful degradation
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "no-issue-reference"


# ============================================================================
# mark_impl_ended Tests
# ============================================================================


def test_mark_impl_ended_local_updates_metadata(tmp_path: Path) -> None:
    """mark-impl-ended updates local impl metadata via PlanBackend."""
    # Setup .impl/ folder with plan-ref.json
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    plan_ref_file = impl_dir / "plan-ref.json"
    plan_ref_file.write_text(
        json.dumps(
            {
                "plan_id": "789",
                "provider": "github",
                "url": "https://github.com/test-owner/test-repo/issues/789",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    # Setup fake issue with plan-header
    body = make_plan_header_body(
        schema_version="2",
        created_at="2025-11-25T14:37:43.513418+00:00",
        created_by="testuser",
        worktree_name="test-worktree",
    )
    fake_gh = FakeGitHubIssues(issues={789: make_issue_info(789, body)})
    repo_root = Path("/fake/repo")
    runner = CliRunner()

    # Execute with session_id
    result = runner.invoke(
        mark_impl_ended,
        ["--session-id", "test-session-id-2"],
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 789

    # Verify metadata updated
    updated_issue = fake_gh.get_issue(repo_root, 789)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["last_local_impl_event"] == "ended"
    assert block.data["last_local_impl_session"] == "test-session-id-2"
    assert block.data["last_local_impl_at"] is not None
    assert block.data["last_local_impl_user"] is not None
    # Remote impl fields should remain null
    assert block.data["last_remote_impl_at"] is None

    # Verify .impl/local-run-state.json written
    local_state_file = impl_dir / "local-run-state.json"
    assert local_state_file.exists()
    local_state = json.loads(local_state_file.read_text(encoding="utf-8"))
    assert local_state["last_event"] == "ended"
    assert local_state["session_id"] == "test-session-id-2"


def test_mark_impl_ended_remote_updates_metadata(tmp_path: Path, monkeypatch) -> None:
    """mark-impl-ended in GitHub Actions updates remote impl metadata."""
    # monkeypatch GITHUB_ACTIONS env var
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    # Setup .impl/ folder with plan-ref.json
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    plan_ref_file = impl_dir / "plan-ref.json"
    plan_ref_file.write_text(
        json.dumps(
            {
                "plan_id": "999",
                "provider": "github",
                "url": "https://github.com/test-owner/test-repo/issues/999",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    # Setup fake issue with plan-header
    body = make_plan_header_body(
        schema_version="2",
        created_at="2025-11-25T14:37:43.513418+00:00",
        created_by="testuser",
        worktree_name="test-worktree",
    )
    fake_gh = FakeGitHubIssues(issues={999: make_issue_info(999, body)})
    repo_root = Path("/fake/repo")
    runner = CliRunner()

    # Execute
    result = runner.invoke(
        mark_impl_ended,
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify last_remote_impl_at updated (not local fields)
    updated_issue = fake_gh.get_issue(repo_root, 999)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["last_remote_impl_at"] is not None
    # Local impl fields should remain null in remote mode
    assert block.data["last_local_impl_event"] is None
    assert block.data["last_local_impl_session"] is None


def test_mark_impl_ended_no_plan_ref(tmp_path: Path) -> None:
    """mark-impl-ended gracefully handles missing plan-ref.json."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    # No .impl/ folder created
    result = runner.invoke(
        mark_impl_ended,
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_gh),
    )

    assert result.exit_code == 0  # Graceful degradation
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "no-issue-reference"
