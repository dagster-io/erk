"""Tests for create-impl-from-issue kit CLI command.

Layer 4 (Business Logic Tests): Tests command logic over fakes.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_impl_from_issue import (
    create_impl_from_issue,
)


def test_create_impl_from_issue_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful .impl/ folder creation from issue."""
    # Arrange: Set up fake plan store with test data
    plan_content = "# Test Plan\n\n1. First step\n2. Second step"
    plan = Plan(
        plan_identifier="1028",
        title="Test Issue Title",
        body=plan_content,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1028",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    fake_plan_store = FakePlanStore(plans={"1028": plan})

    # Mock GitHubPlanStore to return our fake
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_impl_from_issue.GitHubPlanStore",
        lambda github_issues: fake_plan_store,
    )
    # Mock RealGitHubIssues (not used since GitHubPlanStore is mocked)
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_impl_from_issue.RealGitHubIssues",
        lambda: None,
    )

    # Act: Run command
    runner = CliRunner()
    result = runner.invoke(
        create_impl_from_issue,
        ["1028", "--repo-root", str(tmp_path)],
    )

    # Assert: Command succeeded
    assert result.exit_code == 0

    # Assert: Output is valid JSON with expected fields
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 1028
    assert output["issue_url"] == "https://github.com/owner/repo/issues/1028"
    assert "impl_path" in output

    # Assert: .impl/ folder was created with expected files
    impl_path = tmp_path / ".impl"
    assert impl_path.exists()
    assert (impl_path / "plan.md").exists()
    assert (impl_path / "progress.md").exists()
    assert (impl_path / "issue.json").exists()

    # Assert: plan.md contains the plan content
    plan_content_read = (impl_path / "plan.md").read_text(encoding="utf-8")
    assert "# Test Plan" in plan_content_read
    assert "1. First step" in plan_content_read


def test_create_impl_from_issue_plan_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test error handling when plan cannot be fetched."""
    # Arrange: Set up fake plan store with no plans
    fake_plan_store = FakePlanStore()

    # Mock GitHubPlanStore to return our empty fake
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_impl_from_issue.GitHubPlanStore",
        lambda github_issues: fake_plan_store,
    )
    # Mock RealGitHubIssues (not used since GitHubPlanStore is mocked)
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_impl_from_issue.RealGitHubIssues",
        lambda: None,
    )

    # Act: Run command with non-existent issue
    runner = CliRunner()
    result = runner.invoke(
        create_impl_from_issue,
        ["999", "--repo-root", str(tmp_path)],
    )

    # Assert: Command failed with exit code 1
    assert result.exit_code == 1

    # Assert: Error output is valid JSON with error details
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "plan_not_found"
    assert "Could not fetch plan" in output["message"]

    # Assert: .impl/ folder was NOT created
    impl_path = tmp_path / ".impl"
    assert not impl_path.exists()


def test_create_impl_from_issue_uses_cwd_when_no_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test command defaults to current working directory when --repo-root not specified."""
    # Arrange: Set up fake plan store
    plan_content = "# Default CWD Test\n\n1. Testing default behavior."
    plan = Plan(
        plan_identifier="100",
        title="Default CWD Issue",
        body=plan_content,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/100",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    fake_plan_store = FakePlanStore(plans={"100": plan})

    # Mock GitHubPlanStore to return our fake
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_impl_from_issue.GitHubPlanStore",
        lambda github_issues: fake_plan_store,
    )
    # Mock RealGitHubIssues (not used since GitHubPlanStore is mocked)
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_impl_from_issue.RealGitHubIssues",
        lambda: None,
    )

    # Mock Path.cwd() to return tmp_path
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    # Act: Run command WITHOUT --repo-root
    runner = CliRunner()
    result = runner.invoke(
        create_impl_from_issue,
        ["100"],
    )

    # Assert: Command succeeded
    assert result.exit_code == 0

    # Assert: .impl/ folder was created in cwd (tmp_path)
    impl_path = tmp_path / ".impl"
    assert impl_path.exists()
    assert (impl_path / "plan.md").exists()
    assert (impl_path / "progress.md").exists()
    assert (impl_path / "issue.json").exists()


def test_create_impl_from_issue_removes_stale_impl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that stale .impl/ is removed before creating new one (for reruns)."""
    # Arrange: Create a stale .impl/ folder with old content
    stale_impl = tmp_path / ".impl"
    stale_impl.mkdir()
    (stale_impl / "plan.md").write_text("# Old stale plan", encoding="utf-8")
    (stale_impl / "stale_file.txt").write_text("This should be removed", encoding="utf-8")

    # Set up fake plan store with test data
    plan_content = "# Fresh Plan\n\n1. Step one"
    plan = Plan(
        plan_identifier="200",
        title="Fresh Issue",
        body=plan_content,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/200",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    fake_plan_store = FakePlanStore(plans={"200": plan})

    # Mock GitHubPlanStore to return our fake
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_impl_from_issue.GitHubPlanStore",
        lambda github_issues: fake_plan_store,
    )
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_impl_from_issue.RealGitHubIssues",
        lambda: None,
    )

    # Act: Run command
    runner = CliRunner()
    result = runner.invoke(
        create_impl_from_issue,
        ["200", "--repo-root", str(tmp_path)],
    )

    # Assert: Command succeeded
    assert result.exit_code == 0

    # Assert: .impl/ folder contains fresh content, not stale
    impl_path = tmp_path / ".impl"
    assert impl_path.exists()
    assert (impl_path / "plan.md").exists()
    plan_content_read = (impl_path / "plan.md").read_text(encoding="utf-8")
    assert "# Fresh Plan" in plan_content_read
    assert "Old stale plan" not in plan_content_read

    # Assert: Stale file was removed
    assert not (impl_path / "stale_file.txt").exists()


def test_create_impl_from_issue_creates_issue_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that issue.json is created with correct content."""
    # Arrange
    plan = Plan(
        plan_identifier="300",
        title="Issue JSON Test",
        body="# Plan\n\n1. Step",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/300",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    fake_plan_store = FakePlanStore(plans={"300": plan})

    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_impl_from_issue.GitHubPlanStore",
        lambda github_issues: fake_plan_store,
    )
    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_impl_from_issue.RealGitHubIssues",
        lambda: None,
    )

    # Act
    runner = CliRunner()
    result = runner.invoke(
        create_impl_from_issue,
        ["300", "--repo-root", str(tmp_path)],
    )

    # Assert
    assert result.exit_code == 0

    issue_json_path = tmp_path / ".impl" / "issue.json"
    assert issue_json_path.exists()

    issue_data = json.loads(issue_json_path.read_text(encoding="utf-8"))
    assert issue_data["issue_number"] == 300
    assert issue_data["issue_url"] == "https://github.com/owner/repo/issues/300"
    assert "created_at" in issue_data
    assert "synced_at" in issue_data
