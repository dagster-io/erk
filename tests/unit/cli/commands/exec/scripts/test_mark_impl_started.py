"""Unit tests for mark_impl_started exec CLI command.

Tests GitHub issue plan-header impl event updates with local state file writes.
Uses FakeGitHubIssues for fast, reliable testing without subprocess mocking.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.mark_impl_started import mark_impl_started
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import find_metadata_block
from erk_shared.gateway.github.types import BodyContent


def make_plan_header_body(
    schema_version: str = "2",
    created_at: str = "2025-11-25T14:37:43.513418+00:00",
    created_by: str = "testuser",
    worktree_name: str = "test-worktree",
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

```

</details>
<!-- /erk:metadata-block:plan-header -->

Some extra content after the block."""


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
# Success Cases
# ============================================================================


def test_mark_impl_started_local_environment(tmp_path: Path) -> None:
    """Test successful impl started marking in local environment."""
    # Create .impl/ directory with plan-ref.json
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    plan_ref = {
        "provider": "github",
        "plan_id": "123",
        "url": "https://github.com/test-owner/test-repo/issues/123",
        "created_at": "2025-11-25T14:37:43.513418+00:00",
        "synced_at": "2025-11-25T14:37:43.513418+00:00",
        "labels": ["erk-plan"],
    }
    (impl_dir / "plan-ref.json").write_text(json.dumps(plan_ref))

    # Set up fake GitHub with issue
    body = make_plan_header_body()
    fake_gh = FakeGitHubIssues(issues={123: make_issue_info(123, body)})
    runner = CliRunner()

    # Run command
    result = runner.invoke(
        mark_impl_started,
        ["--session-id", "test-session-123"],
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 123

    # Verify local state file was created
    local_state_file = impl_dir / "local-run-state.json"
    assert local_state_file.exists()
    local_state = json.loads(local_state_file.read_text())
    assert local_state["last_event"] == "started"
    assert local_state["session_id"] == "test-session-123"

    # Verify issue body was updated with local impl fields
    updated_issue = fake_gh.get_issue(Path("/fake/repo"), 123)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["last_local_impl_event"] == "started"
    assert block.data["last_local_impl_session"] == "test-session-123"
    assert block.data["last_local_impl_at"] is not None
    assert block.data["last_local_impl_user"] is not None


def test_mark_impl_started_preserves_other_content(tmp_path: Path) -> None:
    """Test that impl started marking preserves content outside the block."""
    # Create .impl/ directory with plan-ref.json
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    plan_ref = {
        "provider": "github",
        "plan_id": "456",
        "url": "https://github.com/test-owner/test-repo/issues/456",
        "created_at": "2025-11-25T14:37:43.513418+00:00",
        "synced_at": "2025-11-25T14:37:43.513418+00:00",
        "labels": ["erk-plan"],
    }
    (impl_dir / "plan-ref.json").write_text(json.dumps(plan_ref))

    # Set up fake GitHub with issue
    body = make_plan_header_body()
    fake_gh = FakeGitHubIssues(issues={456: make_issue_info(456, body)})
    runner = CliRunner()

    # Run command
    result = runner.invoke(
        mark_impl_started,
        ["--session-id", "test-session-456"],
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_gh),
    )

    assert result.exit_code == 0

    # Verify content after block is preserved
    updated_issue = fake_gh.get_issue(Path("/fake/repo"), 456)
    assert "Some extra content after the block." in updated_issue.body


# ============================================================================
# Error Cases
# ============================================================================


def test_mark_impl_started_no_plan_ref(tmp_path: Path) -> None:
    """Test error when no plan-ref.json exists."""
    runner = CliRunner()

    result = runner.invoke(
        mark_impl_started,
        ["--session-id", "test-session"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0  # Always exits 0 for graceful degradation
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "no-issue-reference"


def test_mark_impl_started_update_failed(tmp_path: Path) -> None:
    """Test error when backend update fails."""
    # Create .impl/ directory with plan-ref.json
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    plan_ref = {
        "provider": "github",
        "plan_id": "999",
        "url": "https://github.com/test-owner/test-repo/issues/999",
        "created_at": "2025-11-25T14:37:43.513418+00:00",
        "synced_at": "2025-11-25T14:37:43.513418+00:00",
        "labels": ["erk-plan"],
    }
    (impl_dir / "plan-ref.json").write_text(json.dumps(plan_ref))

    # Set up failing fake
    class FailingFakeGitHubIssues(FakeGitHubIssues):
        def update_issue_body(self, repo_root: Path, number: int, body: BodyContent) -> None:
            raise RuntimeError("Network error")

    fake_gh = FailingFakeGitHubIssues(issues={999: make_issue_info(999, make_plan_header_body())})
    runner = CliRunner()

    result = runner.invoke(
        mark_impl_started,
        ["--session-id", "test-session"],
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_gh),
    )

    assert result.exit_code == 0  # Always exits 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "github-api-failed"
    assert "Network error" in output["message"]


def test_mark_impl_started_local_state_write_failed(tmp_path: Path) -> None:
    """Test error when local state file cannot be written."""
    # Create .impl/ directory with plan-ref.json but make it read-only
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    plan_ref = {
        "provider": "github",
        "plan_id": "123",
        "url": "https://github.com/test-owner/test-repo/issues/123",
        "created_at": "2025-11-25T14:37:43.513418+00:00",
        "synced_at": "2025-11-25T14:37:43.513418+00:00",
        "labels": ["erk-plan"],
    }
    (impl_dir / "plan-ref.json").write_text(json.dumps(plan_ref))
    impl_dir.chmod(0o555)  # Read+execute only (can read files, cannot create new files)

    fake_gh = FakeGitHubIssues(issues={123: make_issue_info(123, make_plan_header_body())})
    runner = CliRunner()

    result = runner.invoke(
        mark_impl_started,
        ["--session-id", "test-session"],
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_gh),
    )

    # Restore permissions for cleanup
    impl_dir.chmod(0o755)

    assert result.exit_code == 0  # Always exits 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "local-state-write-failed"


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_json_output_structure_success(tmp_path: Path) -> None:
    """Test JSON output structure on success."""
    # Create .impl/ directory with plan-ref.json
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    plan_ref = {
        "provider": "github",
        "plan_id": "321",
        "url": "https://github.com/test-owner/test-repo/issues/321",
        "created_at": "2025-11-25T14:37:43.513418+00:00",
        "synced_at": "2025-11-25T14:37:43.513418+00:00",
        "labels": ["erk-plan"],
    }
    (impl_dir / "plan-ref.json").write_text(json.dumps(plan_ref))

    # Set up fake GitHub with issue
    body = make_plan_header_body()
    fake_gh = FakeGitHubIssues(issues={321: make_issue_info(321, body)})
    runner = CliRunner()

    result = runner.invoke(
        mark_impl_started,
        ["--session-id", "test-session-321"],
        obj=ErkContext.for_test(cwd=tmp_path, github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "issue_number" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)

    # Verify values
    assert output["success"] is True
    assert output["issue_number"] == 321


def test_json_output_structure_error(tmp_path: Path) -> None:
    """Test JSON output structure on error."""
    runner = CliRunner()

    result = runner.invoke(
        mark_impl_started,
        ["--session-id", "test-session"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0  # Always exits 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "error_type" in output
    assert "message" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error_type"], str)
    assert isinstance(output["message"], str)

    # Verify values
    assert output["success"] is False
