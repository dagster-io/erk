"""CLI tests for erk run list command.

This file focuses on CLI-specific concerns for the list runs command:
- Command execution and exit codes
- Output formatting and display (status indicators, Rich table)
- Run-centric view with plan/PR linkage

The integration layer (list_workflow_runs) is tested in:
- tests/unit/fakes/test_fake_github.py - Fake infrastructure tests
- tests/integration/test_real_github.py - Real implementation tests

This file trusts that unit layer and only tests CLI integration.
"""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.abc import WorktreeInfo
from erk_shared.github.types import PullRequestInfo, WorkflowRun
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState

from erk.cli.commands.run.list_cmd import list_runs
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from tests.fakes.context import create_test_context


def _make_plan(
    plan_identifier: str,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
) -> Plan:
    """Create a Plan for testing."""
    now = datetime.now(UTC)
    return Plan(
        plan_identifier=plan_identifier,
        title=title,
        body=body,
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/issues/{plan_identifier}",
        labels=labels or ["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={"number": int(plan_identifier)},
    )


def test_list_runs_empty_state(tmp_path: Path) -> None:
    """Test list command displays message when no runs found."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    github_ops = FakeGitHub(workflow_runs=[])  # Empty runs
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    assert "No workflow runs found" in result.output


def test_list_runs_single_success_run_with_issue_linkage(tmp_path: Path) -> None:
    """Test list command displays single successful run with plan linkage."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    workflow_runs = [
        WorkflowRun(
            run_id="1234567890",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc456",  # New format: issue_number:distinct_id
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    # Create plan for linkage
    plan = _make_plan("142", "Add user authentication with OAuth2", body="Plan content")
    plan_store = FakePlanStore(plans={"142": plan})

    ctx = create_test_context(git=git_ops, github=github_ops, plan_store=plan_store, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # Check for Rich table output - run_id should appear
    assert "1234567890" in result.output
    # Check for issue linkage
    assert "#142" in result.output
    # Check for title (or truncated version)
    assert "Add user authentication" in result.output
    # Success status indicator
    assert "Success" in result.output or "✅" in result.output


def test_list_runs_multiple_runs_different_statuses(tmp_path: Path) -> None:
    """Test list command displays multiple runs with different statuses."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc",
        ),
        WorkflowRun(
            run_id="456",
            status="completed",
            conclusion="failure",
            branch="feat-2",
            head_sha="def456",
            display_title="143:def",
        ),
        WorkflowRun(
            run_id="789",
            status="in_progress",
            conclusion=None,
            branch="feat-3",
            head_sha="ghi789",
            display_title="144:ghi",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    # Create plans for linkage
    plan_store = FakePlanStore(
        plans={
            "142": _make_plan("142", "Feature one"),
            "143": _make_plan("143", "Feature two"),
            "144": _make_plan("144", "Feature three"),
        }
    )

    ctx = create_test_context(git=git_ops, github=github_ops, plan_store=plan_store, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # All run IDs should appear
    assert "123" in result.output
    assert "456" in result.output
    assert "789" in result.output
    # All issue numbers should appear
    assert "#142" in result.output
    assert "#143" in result.output
    assert "#144" in result.output


def test_list_runs_run_without_issue_linkage(tmp_path: Path) -> None:
    """Test list command handles runs without valid issue linkage (old format).

    By default, runs without issue linkage should be filtered out.
    Use --show-legacy flag to see them.
    """
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            # Old format - no issue linkage possible
            display_title="Add user authentication [abc123]",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    plan_store = FakePlanStore(plans={})

    ctx = create_test_context(git=git_ops, github=github_ops, plan_store=plan_store, cwd=repo_root)

    runner = CliRunner()

    # Act - With --show-legacy flag to see legacy runs
    result = runner.invoke(list_runs, ["--show-legacy"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # Run ID should still appear
    assert "123" in result.output
    # Should show "X" for plan/title/pr/chks columns since legacy format can't be parsed
    # (distinguishes "can't parse" from "no data available" which uses "-")
    assert "X" in result.output


def test_list_runs_default_filters_out_runs_without_plans(tmp_path: Path) -> None:
    """By default, filter out runs without plan linkage (legacy format)."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    workflow_runs = [
        # New format - has plan linkage
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc456",  # Can be parsed
        ),
        # Old format - no plan linkage
        WorkflowRun(
            run_id="456",
            status="completed",
            conclusion="success",
            branch="feat-2",
            head_sha="def456",
            display_title="Add feature [def456]",  # Cannot be parsed
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    plan = _make_plan("142", "Feature one")
    plan_store = FakePlanStore(plans={"142": plan})

    ctx = create_test_context(git=git_ops, github=github_ops, plan_store=plan_store, cwd=repo_root)

    runner = CliRunner()

    # Act - Default behavior (without --all)
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # New format run should appear
    assert "123" in result.output
    assert "#142" in result.output
    # Old format run should NOT appear
    assert "456" not in result.output
    assert "Add feature" not in result.output


def test_list_runs_with_show_legacy_flag_shows_all_runs(tmp_path: Path) -> None:
    """With --show-legacy flag, show all runs including legacy format."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    workflow_runs = [
        # New format - has plan linkage
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc456",  # Can be parsed
        ),
        # Old format - no plan linkage
        WorkflowRun(
            run_id="456",
            status="completed",
            conclusion="success",
            branch="feat-2",
            head_sha="def456",
            display_title="Add feature [def456]",  # Cannot be parsed
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    plan = _make_plan("142", "Feature one")
    plan_store = FakePlanStore(plans={"142": plan})

    ctx = create_test_context(git=git_ops, github=github_ops, plan_store=plan_store, cwd=repo_root)

    runner = CliRunner()

    # Act - With --show-legacy flag
    result = runner.invoke(list_runs, ["--show-legacy"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # New format run should appear
    assert "123" in result.output
    assert "#142" in result.output
    # Old format run SHOULD appear with --show-legacy
    assert "456" in result.output
    # Legacy run should show "X" for plan/title/pr/chks
    assert "X" in result.output


def test_list_runs_with_pr_linkage(tmp_path: Path) -> None:
    """Test list command displays PR information when linked."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc456",
        ),
    ]

    # PR linked to issue 142
    pr_info = PullRequestInfo(
        number=201,
        state="OPEN",
        url="https://github.com/owner/repo/pull/201",
        is_draft=False,
        title="Add user auth",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    github_ops = FakeGitHub(
        workflow_runs=workflow_runs,
        pr_issue_linkages={142: [pr_info]},
    )

    plan = _make_plan("142", "Add user authentication")
    plan_store = FakePlanStore(plans={"142": plan})

    ctx = create_test_context(git=git_ops, github=github_ops, plan_store=plan_store, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # PR number should appear
    assert "#201" in result.output
    # Checks emoji should appear (✅ for passing)
    assert "✅" in result.output


def test_list_runs_handles_queued_status(tmp_path: Path) -> None:
    """Test list command displays queued status correctly."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="queued",
            conclusion=None,
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    plan = _make_plan("142", "Queued feature")
    plan_store = FakePlanStore(plans={"142": plan})

    ctx = create_test_context(git=git_ops, github=github_ops, plan_store=plan_store, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # Queued status indicator
    assert "Queued" in result.output or "⧗" in result.output


def test_list_runs_handles_cancelled_status(tmp_path: Path) -> None:
    """Test list command displays cancelled status correctly."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="cancelled",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    plan = _make_plan("142", "Cancelled feature")
    plan_store = FakePlanStore(plans={"142": plan})

    ctx = create_test_context(git=git_ops, github=github_ops, plan_store=plan_store, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # Cancelled status indicator
    assert "Cancelled" in result.output or "⛔" in result.output


def test_list_runs_truncates_long_titles(tmp_path: Path) -> None:
    """Test list command truncates titles longer than 50 characters."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    long_title = (
        "This is a very long title that exceeds fifty characters "
        "and should be truncated with ellipsis"
    )

    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    plan = _make_plan("142", long_title)
    plan_store = FakePlanStore(plans={"142": plan})

    ctx = create_test_context(git=git_ops, github=github_ops, plan_store=plan_store, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # Full title should NOT appear (it's too long)
    assert long_title not in result.output
    # Truncated version should appear with ellipsis
    assert "..." in result.output
    # Start of title should appear
    assert "This is a very long" in result.output


def test_list_runs_filters_missing_issue_data(tmp_path: Path) -> None:
    """Runs with missing/empty issue data are filtered by default."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    # Use distinctive run_ids that won't appear in ANSI escape codes
    # (short numbers like "200" can appear in 256-color ANSI sequences)
    workflow_runs = [
        # Valid run with plan
        WorkflowRun(
            run_id="111111",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc123",
        ),
        # Run with plan not found in plan_map
        WorkflowRun(
            run_id="222222",
            status="completed",
            conclusion="success",
            branch="feat-2",
            head_sha="def456",
            display_title="999:def456",  # Plan 999 doesn't exist
        ),
        # Run with empty title
        WorkflowRun(
            run_id="333333",
            status="completed",
            conclusion="success",
            branch="feat-3",
            head_sha="ghi789",
            display_title="143:ghi789",  # Plan 143 has empty title
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    # Only create plans 142 (valid) and 143 (empty title)
    plan_store = FakePlanStore(
        plans={
            "142": _make_plan("142", "Valid issue with title"),
            "143": _make_plan("143", ""),  # Empty title
        }
    )

    ctx = create_test_context(git=git_ops, github=github_ops, plan_store=plan_store, cwd=repo_root)

    runner = CliRunner()

    # Act - Default behavior (without --show-legacy)
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    # Assert - Only run 111111 should appear
    assert result.exit_code == 0
    assert "111111" in result.output
    assert "#142" in result.output
    # Runs 222222 and 333333 should be filtered out
    assert "222222" not in result.output
    assert "333333" not in result.output
    # Issue #999 and #143 should not be in the output
    # (use #-prefixed form to avoid false positives from timestamps)
    assert "#999" not in result.output
    assert "#143" not in result.output


def test_list_runs_displays_submission_time(tmp_path: Path) -> None:
    """Test list command displays submission time in local timezone."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    # Create a specific timestamp
    timestamp = datetime(2024, 11, 26, 14, 30, 45, tzinfo=UTC)

    workflow_runs = [
        WorkflowRun(
            run_id="1234567890",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc456",
            created_at=timestamp,
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    plan = _make_plan("142", "Test issue")
    plan_store = FakePlanStore(plans={"142": plan})

    ctx = create_test_context(git=git_ops, github=github_ops, plan_store=plan_store, cwd=repo_root)
    runner = CliRunner()

    # Act
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # The timestamp will be converted to local timezone
    # Check for the date part (month-day) which should be 11-26
    # (unless timezone shifts to next/previous day)
    assert "11-26" in result.output or "11-25" in result.output or "11-27" in result.output
    # Also check the table header
    assert "submitted" in result.output


def test_list_runs_handles_missing_timestamp(tmp_path: Path) -> None:
    """Test list command handles missing created_at gracefully."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    workflow_runs = [
        WorkflowRun(
            run_id="1234567890",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc456",
            created_at=None,  # Missing timestamp
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    plan = _make_plan("142", "Test issue")
    plan_store = FakePlanStore(plans={"142": plan})

    ctx = create_test_context(git=git_ops, github=github_ops, plan_store=plan_store, cwd=repo_root)
    runner = CliRunner()

    # Act
    result = runner.invoke(list_runs, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # Should display without error - the "-" placeholder is dimmed
    # Just check it doesn't crash and outputs a table
    assert "submitted" in result.output
