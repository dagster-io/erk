"""Unit tests for update_dispatch_info kit CLI command.

Tests GitHub issue plan-header dispatch info updates.
Uses FakeGitHubIssues for fast, reliable testing without subprocess mocking.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.update_dispatch_info import (
    update_dispatch_info,
)
from erk_shared.context import ErkContext
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.metadata import find_metadata_block


def make_plan_header_body(
    schema_version: str = "2",
    created_at: str = "2025-11-25T14:37:43.513418+00:00",
    created_by: str = "testuser",
    worktree_name: str = "test-worktree",
    last_dispatched_run_id: str | None = None,
    last_dispatched_at: str | None = None,
) -> str:
    """Create a test issue body with plan-header metadata block."""
    run_id_line = (
        f"last_dispatched_run_id: {last_dispatched_run_id}"
        if last_dispatched_run_id
        else "last_dispatched_run_id: null"
    )
    dispatched_at_line = (
        f"last_dispatched_at: '{last_dispatched_at}'"
        if last_dispatched_at
        else "last_dispatched_at: null"
    )

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '{schema_version}'
created_at: '{created_at}'
created_by: {created_by}
worktree_name: {worktree_name}
{run_id_line}
{dispatched_at_line}

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


def test_update_dispatch_info_success() -> None:
    """Test successful dispatch info update."""
    body = make_plan_header_body()
    fake_gh = FakeGitHubIssues(issues={123: make_issue_info(123, body)})
    runner = CliRunner()

    result = runner.invoke(
        update_dispatch_info,
        ["123", "12345678", "WFR_kwLOPxC3hc8AAAAEnZK8rQ", "2025-11-25T15:00:00Z"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 123
    assert output["run_id"] == "12345678"
    assert output["node_id"] == "WFR_kwLOPxC3hc8AAAAEnZK8rQ"

    # Verify issue body was updated with dispatch info
    updated_issue = fake_gh.get_issue(Path(), 123)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["last_dispatched_run_id"] == "12345678"
    assert block.data["last_dispatched_node_id"] == "WFR_kwLOPxC3hc8AAAAEnZK8rQ"
    assert block.data["last_dispatched_at"] == "2025-11-25T15:00:00Z"


def test_update_dispatch_info_overwrites_existing() -> None:
    """Test that dispatch info update overwrites existing values."""
    body = make_plan_header_body(
        last_dispatched_run_id="old-run-id",
        last_dispatched_at="2025-11-20T10:00:00Z",
    )
    fake_gh = FakeGitHubIssues(issues={456: make_issue_info(456, body)})
    runner = CliRunner()

    result = runner.invoke(
        update_dispatch_info,
        ["456", "new-run-id", "WFR_kwLOPxC3hc8AAAAEnZK8rQ", "2025-11-25T16:00:00Z"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify existing values were overwritten
    updated_issue = fake_gh.get_issue(Path(), 456)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["last_dispatched_run_id"] == "new-run-id"
    assert block.data["last_dispatched_node_id"] == "WFR_kwLOPxC3hc8AAAAEnZK8rQ"
    assert block.data["last_dispatched_at"] == "2025-11-25T16:00:00Z"


def test_update_dispatch_info_preserves_other_content() -> None:
    """Test that update preserves content outside the block."""
    body = make_plan_header_body()
    fake_gh = FakeGitHubIssues(issues={789: make_issue_info(789, body)})
    runner = CliRunner()

    result = runner.invoke(
        update_dispatch_info,
        ["789", "test-run", "WFR_kwLOPxC3hc8AAAAEnZK8rQ", "2025-11-25T17:00:00Z"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0

    # Verify content after block is preserved
    updated_issue = fake_gh.get_issue(Path(), 789)
    assert "Some extra content after the block." in updated_issue.body


# ============================================================================
# Error Cases
# ============================================================================


def test_update_dispatch_info_issue_not_found() -> None:
    """Test error when issue doesn't exist."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        update_dispatch_info,
        ["999", "test-run", "WFR_kwLOPxC3hc8AAAAEnZK8rQ", "2025-11-25T18:00:00Z"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "issue-not-found"
    assert "#999" in output["message"]


def test_update_dispatch_info_no_plan_header_block() -> None:
    """Test error when issue has no plan-header block (old format)."""
    old_format_body = """# Old Format Issue

This is an issue created before plan-header blocks were introduced.
"""
    fake_gh = FakeGitHubIssues(issues={100: make_issue_info(100, old_format_body)})
    runner = CliRunner()

    result = runner.invoke(
        update_dispatch_info,
        ["100", "test-run", "WFR_kwLOPxC3hc8AAAAEnZK8rQ", "2025-11-25T19:00:00Z"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no-plan-header-block"


def test_update_dispatch_info_github_api_failure() -> None:
    """Test error when GitHub API fails during update."""
    body = make_plan_header_body()

    class FailingFakeGitHubIssues(FakeGitHubIssues):
        def update_issue_body(self, repo_root: Path, number: int, body: str) -> None:
            raise RuntimeError("Network error")

    fake_gh = FailingFakeGitHubIssues(issues={200: make_issue_info(200, body)})
    runner = CliRunner()

    result = runner.invoke(
        update_dispatch_info,
        ["200", "test-run", "WFR_kwLOPxC3hc8AAAAEnZK8rQ", "2025-11-25T20:00:00Z"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "github-api-failed"
    assert "Network error" in output["message"]


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_json_output_structure_success() -> None:
    """Test JSON output structure on success."""
    body = make_plan_header_body()
    fake_gh = FakeGitHubIssues(issues={321: make_issue_info(321, body)})
    runner = CliRunner()

    result = runner.invoke(
        update_dispatch_info,
        ["321", "run-12345", "WFR_kwLOPxC3hc8AAAAEnZK8rQ", "2025-11-25T21:00:00Z"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "issue_number" in output
    assert "run_id" in output
    assert "node_id" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["run_id"], str)
    assert isinstance(output["node_id"], str)

    # Verify values
    assert output["success"] is True
    assert output["issue_number"] == 321
    assert output["run_id"] == "run-12345"
    assert output["node_id"] == "WFR_kwLOPxC3hc8AAAAEnZK8rQ"


def test_json_output_structure_error() -> None:
    """Test JSON output structure on error."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        update_dispatch_info,
        ["999", "run-abc", "WFR_kwLOPxC3hc8AAAAEnZK8rQ", "2025-11-25T22:00:00Z"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "error" in output
    assert "message" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error"], str)
    assert isinstance(output["message"], str)

    # Verify values
    assert output["success"] is False
