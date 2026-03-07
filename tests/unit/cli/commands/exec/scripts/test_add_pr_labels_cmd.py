"""Unit tests for add-pr-labels exec command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.add_pr_labels_cmd import add_pr_labels
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeLocalGitHub
from erk_shared.gateway.github.types import PRDetails


def _make_pr_details(*, number: int = 42) -> PRDetails:
    """Create a minimal PRDetails for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/test/repo/pull/{number}",
        title="Test PR",
        body="body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test",
        repo="repo",
        labels=(),
        created_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        author="test-user",
    )


def test_add_pr_labels_success() -> None:
    """Test successfully adding labels to a PR."""
    fake_github = FakeLocalGitHub(pr_details={42: _make_pr_details()})
    runner = CliRunner()

    result = runner.invoke(
        add_pr_labels,
        ["42", "--labels", "erk-plan", "--labels", "erk-learn"],
        obj=ErkContext.for_test(github=fake_github),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert sorted(output["added_labels"]) == ["erk-learn", "erk-plan"]
    assert output["failed_labels"] == []


def test_add_pr_labels_pr_not_found() -> None:
    """Test exit code 1 when PR does not exist."""
    fake_github = FakeLocalGitHub()
    runner = CliRunner()

    result = runner.invoke(
        add_pr_labels,
        ["999", "--labels", "erk-plan"],
        obj=ErkContext.for_test(github=fake_github),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "not found" in output["error"]


def test_add_pr_labels_single_label() -> None:
    """Test adding a single label."""
    fake_github = FakeLocalGitHub(pr_details={10: _make_pr_details(number=10)})
    runner = CliRunner()

    result = runner.invoke(
        add_pr_labels,
        ["10", "--labels", "bug"],
        obj=ErkContext.for_test(github=fake_github),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["added_labels"] == ["bug"]
    assert output["pr_number"] == 10
