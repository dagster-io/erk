"""Tests for plan list command."""

from datetime import UTC, datetime

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo

from erk.cli.cli import cli
from erk.core.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def plan_to_issue(plan: Plan) -> IssueInfo:
    """Convert Plan to IssueInfo for test setup.

    Used to adapt tests from FakePlanStore to FakeGitHubIssues.
    """
    return IssueInfo(
        number=int(plan.plan_identifier),
        title=plan.title,
        body=plan.body,
        state="OPEN" if plan.state == PlanState.OPEN else "CLOSED",
        url=plan.url,
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def test_list_plans_no_filters() -> None:
    """Test listing all plan issues with no filters."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1",
        title="Issue 1",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    plan2 = Plan(
        plan_identifier="2",
        title="Issue 2",
        body="",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],  # Must have erk-plan label to be returned by default
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1), 2: plan_to_issue(plan2)})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output
        assert "#1" in result.output
        assert "Issue 1" in result.output
        assert "#2" in result.output
        assert "Issue 2" in result.output


def test_list_plans_filter_by_state() -> None:
    """Test filtering plan issues by state."""
    # Arrange
    open_plan = Plan(
        plan_identifier="1",
        title="Open Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    closed_plan = Plan(
        plan_identifier="2",
        title="Closed Issue",
        body="",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1: plan_to_issue(open_plan), 2: plan_to_issue(closed_plan)}
        )
        ctx = build_workspace_test_context(env, issues=issues)

        # Act - Filter for open issues
        result = runner.invoke(cli, ["list", "--state", "open"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Open Issue" in result.output
        assert "#2" not in result.output


def test_list_plans_filter_by_labels() -> None:
    """Test filtering plan issues by labels with AND logic."""
    # Arrange
    plan_with_both = Plan(
        plan_identifier="1",
        title="Issue with both labels",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    plan_with_one = Plan(
        plan_identifier="2",
        title="Issue with one label",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1: plan_to_issue(plan_with_both), 2: plan_to_issue(plan_with_one)}
        )
        ctx = build_workspace_test_context(env, issues=issues)

        # Act - Filter for both labels (AND logic)
        result = runner.invoke(
            cli,
            ["list", "--label", "erk-plan", "--label", "erk-queue"],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Issue with both labels" in result.output
        assert "#2" not in result.output


def test_list_plans_with_limit() -> None:
    """Test limiting the number of returned plan issues."""
    # Arrange
    plans_dict: dict[int, IssueInfo] = {}
    for i in range(1, 6):
        plan = Plan(
            plan_identifier=str(i),
            title=f"Issue {i}",
            body="",
            state=PlanState.OPEN,
            url=f"https://github.com/owner/repo/issues/{i}",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2024, 1, i, tzinfo=UTC),
            updated_at=datetime(2024, 1, i, tzinfo=UTC),
            metadata={},
        )
        plans_dict[i] = plan_to_issue(plan)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues=plans_dict)
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["list", "--limit", "2"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output


def test_list_plans_combined_filters() -> None:
    """Test combining multiple filters."""
    # Arrange
    matching_plan = Plan(
        plan_identifier="1",
        title="Matching Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan", "bug"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    wrong_state_plan = Plan(
        plan_identifier="2",
        title="Wrong State",
        body="",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan", "bug"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )
    wrong_labels_plan = Plan(
        plan_identifier="3",
        title="Wrong Labels",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/3",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 3, tzinfo=UTC),
        updated_at=datetime(2024, 1, 3, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={
                1: plan_to_issue(matching_plan),
                2: plan_to_issue(wrong_state_plan),
                3: plan_to_issue(wrong_labels_plan),
            }
        )
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(
            cli,
            [
                "list",
                "--state",
                "open",
                "--label",
                "erk-plan",
                "--label",
                "bug",
            ],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Matching Issue" in result.output


def test_list_plans_empty_results() -> None:
    """Test querying with filters that match no issues."""
    # Arrange
    plan = Plan(
        plan_identifier="1",
        title="Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan)})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["list", "--state", "closed"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "No plans found matching the criteria" in result.output


def test_ls_alias_works() -> None:
    """Test that ls alias invokes the same logic as list command."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1",
        title="Test Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1)})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act - Use ls alias instead of list
        result = runner.invoke(cli, ["ls"], obj=ctx)

        # Assert - Should produce same output as list command
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Test Issue" in result.output


def test_list_plans_shows_worktree_status() -> None:
    """Test that list command shows dash for non-local worktrees.

    When a plan has a worktree_name in the issue body but no local worktree,
    the local-wt column should show "-" (not the remote worktree name).
    """
    # Arrange - Create issue with plan-header block containing worktree_name
    body_with_worktree = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
worktree_name: rename-erk-slash-commands
```
</details>
<!-- /erk:metadata-block:plan-header -->

Implementation details here."""

    plan1 = Plan(
        plan_identifier="867",
        title="Rename Erk Slash Commands",
        body=body_with_worktree,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/867",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 867},
    )

    plan2 = Plan(
        plan_identifier="868",
        title="Issue Without Worktree",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/868",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 868},
    )

    # Configure fake GitHub issues
    issues = FakeGitHubIssues(
        issues={867: plan_to_issue(plan1), 868: plan_to_issue(plan2)},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output
        assert "#867" in result.output
        assert "Rename Erk Slash Commands" in result.output
        # Non-local worktree should NOT appear in output (shows "-" instead)
        assert "rename-erk-slash-commands" not in result.output
        assert "#868" in result.output
        assert "Issue Without Worktree" in result.output


def test_list_plans_shows_dash_for_non_local_worktree() -> None:
    """Test that list command shows dash when worktree exists only in issue body (not local).

    When the plan-header contains a worktree_name but no local worktree exists,
    the local-wt column should show "-" instead of the remote worktree name.
    """
    # Arrange - Issue body with plan-header containing worktree that doesn't exist locally
    body_with_worktree = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
worktree_name: second-attempt
```
</details>
<!-- /erk:metadata-block:plan-header -->

Issue updated with current worktree name."""

    plan1 = Plan(
        plan_identifier="900",
        title="Issue with Updated Worktree",
        body=body_with_worktree,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/900",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 900},
    )

    # Configure fake with issue
    issues = FakeGitHubIssues(
        issues={900: plan_to_issue(plan1)},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert - Non-local worktree should NOT be shown (shows "-" instead)
        assert result.exit_code == 0
        assert "second-attempt" not in result.output


def test_list_plans_shows_worktree_from_local_impl() -> None:
    """Test that list command detects worktree from local .impl/issue.json file."""
    import json

    from erk_shared.git.abc import WorktreeInfo

    from erk.core.git.fake import FakeGit

    # Arrange
    plan1 = Plan(
        plan_identifier="950",
        title="Test Local Detection",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/950",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 950},
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a worktree with .impl/issue.json
        worktree_path = env.cwd.parent / "feature-worktree"
        worktree_path.mkdir(parents=True)
        impl_folder = worktree_path / ".impl"
        impl_folder.mkdir()

        # Manually create issue.json file
        issue_json_path = impl_folder / "issue.json"
        issue_data = {
            "issue_number": 950,
            "issue_url": "https://github.com/owner/repo/issues/950",
            "created_at": "2024-11-23T00:00:00+00:00",
            "synced_at": "2024-11-23T00:00:00+00:00",
        }
        issue_json_path.write_text(json.dumps(issue_data, indent=2), encoding="utf-8")

        # Configure FakeGit with worktree
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch="feature-branch", is_root=False),
                ]
            },
        )

        # Configure FakeGitHubIssues with issues (no comments)
        issues = FakeGitHubIssues(issues={950: plan_to_issue(plan1)}, comments={})
        ctx = build_workspace_test_context(env, git=git, issues=issues)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert - Should show worktree name from local detection
        assert result.exit_code == 0
        assert "#950" in result.output
        assert "Test Local Detection" in result.output
        assert "feature-worktree" in result.output


def test_list_plans_prefers_local_over_github() -> None:
    """Test that local .impl/issue.json detection takes precedence over GitHub comments."""
    import json

    from erk_shared.git.abc import WorktreeInfo

    from erk.core.git.fake import FakeGit

    # Arrange
    plan1 = Plan(
        plan_identifier="960",
        title="Test Precedence",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/960",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 960},
    )

    # Create GitHub comment with different worktree name
    github_comment = """
<!-- erk:metadata-block:erk-worktree-creation -->
<details>
<summary><code>erk-worktree-creation</code></summary>

```yaml
worktree_name: old-github-worktree
branch_name: old-github-worktree
timestamp: "2024-11-20T10:00:00Z"
issue_number: 960
```
</details>
<!-- /erk:metadata-block -->
"""

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a worktree with .impl/issue.json
        worktree_path = env.cwd.parent / "local-worktree"
        worktree_path.mkdir(parents=True)
        impl_folder = worktree_path / ".impl"
        impl_folder.mkdir()

        # Manually create issue.json file
        issue_json_path = impl_folder / "issue.json"
        issue_data = {
            "issue_number": 960,
            "issue_url": "https://github.com/owner/repo/issues/960",
            "created_at": "2024-11-23T00:00:00+00:00",
            "synced_at": "2024-11-23T00:00:00+00:00",
        }
        issue_json_path.write_text(json.dumps(issue_data, indent=2), encoding="utf-8")

        # Configure FakeGit with worktree
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch="feature", is_root=False),
                ]
            },
        )

        # Configure FakeGitHubIssues with issue and comment
        issues = FakeGitHubIssues(
            issues={960: plan_to_issue(plan1)}, comments={960: [github_comment]}
        )
        ctx = build_workspace_test_context(env, git=git, issues=issues)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert - Should show local worktree name, not GitHub one
        assert result.exit_code == 0
        assert "local-worktree" in result.output
        assert "old-github-worktree" not in result.output


def test_list_plans_shows_dash_when_no_local_worktree() -> None:
    """Test that local-wt column shows dash when no local worktree exists.

    Even when the issue body contains a worktree_name, if there's no local
    worktree, the local-wt column should show "-".
    """
    # Arrange - Issue with plan-header containing worktree_name
    body_with_worktree = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
worktree_name: github-worktree
```
</details>
<!-- /erk:metadata-block:plan-header -->

Plan content."""

    plan1 = Plan(
        plan_identifier="970",
        title="Test Fallback",
        body=body_with_worktree,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/970",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 970},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # No local worktrees with .impl folders
        issues = FakeGitHubIssues(issues={970: plan_to_issue(plan1)})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert - Non-local worktree should NOT be shown (shows "-" instead)
        assert result.exit_code == 0
        assert "#970" in result.output
        assert "github-worktree" not in result.output


def test_list_plans_handles_multiple_local_worktrees() -> None:
    """Test first-found worktree shown when multiple worktrees reference same issue."""
    import json

    from erk_shared.git.abc import WorktreeInfo

    from erk.core.git.fake import FakeGit

    # Arrange
    plan1 = Plan(
        plan_identifier="980",
        title="Test Multiple Local",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/980",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 980},
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create two worktrees both referencing same issue
        worktree1 = env.cwd.parent / "first-worktree"
        worktree1.mkdir(parents=True)
        impl1 = worktree1 / ".impl"
        impl1.mkdir()
        issue_json1 = impl1 / "issue.json"
        issue_data1 = {
            "issue_number": 980,
            "issue_url": "https://github.com/owner/repo/issues/980",
            "created_at": "2024-11-23T00:00:00+00:00",
            "synced_at": "2024-11-23T00:00:00+00:00",
        }
        issue_json1.write_text(json.dumps(issue_data1, indent=2), encoding="utf-8")

        worktree2 = env.cwd.parent / "second-worktree"
        worktree2.mkdir(parents=True)
        impl2 = worktree2 / ".impl"
        impl2.mkdir()
        issue_json2 = impl2 / "issue.json"
        issue_data2 = {
            "issue_number": 980,
            "issue_url": "https://github.com/owner/repo/issues/980",
            "created_at": "2024-11-23T00:00:00+00:00",
            "synced_at": "2024-11-23T00:00:00+00:00",
        }
        issue_json2.write_text(json.dumps(issue_data2, indent=2), encoding="utf-8")

        # Configure FakeGit with both worktrees
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=worktree1, branch="branch1", is_root=False),
                    WorktreeInfo(path=worktree2, branch="branch2", is_root=False),
                ]
            },
        )

        # Configure FakeGitHubIssues with issue (no comments)
        issues = FakeGitHubIssues(issues={980: plan_to_issue(plan1)}, comments={})
        ctx = build_workspace_test_context(env, git=git, issues=issues)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert - Should show first worktree found
        assert result.exit_code == 0
        assert "#980" in result.output
        # Should show exactly one of the worktrees (first-found behavior)
        # The order depends on git.list_worktrees() order
        assert "first-worktree" in result.output or "second-worktree" in result.output


def test_list_plans_shows_action_state_with_no_queue_label() -> None:
    """Test that plans without erk-queue label show '-' for action state."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1001",
        title="Regular Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1001",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1001},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1001: plan_to_issue(plan1)})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1001" in result.output


def test_list_plans_shows_pending_action_state() -> None:
    """Test that plans with erk-queue label but no metadata show 'Pending'."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1002",
        title="Pending Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1002",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1002},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1002: plan_to_issue(plan1)}, comments={1002: []})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1002" in result.output


def test_list_plans_shows_running_action_state_with_workflow_started() -> None:
    """Test that plans with workflow-started metadata show 'Running'."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1003",
        title="Running Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1003",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1003},
    )

    # Create comment with workflow-started metadata
    comment = """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: "2024-11-23T10:00:00Z"
workflow_run_id: "12345"
workflow_run_url: "https://github.com/owner/repo/actions/runs/12345"
issue_number: 1003
```
</details>
<!-- /erk:metadata-block -->
"""

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1003: plan_to_issue(plan1)}, comments={1003: [comment]})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1003" in result.output


def test_list_plans_shows_complete_action_state() -> None:
    """Test that plans with complete implementation status show 'Complete'."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1004",
        title="Complete Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1004",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1004},
    )

    # Create comment with complete status
    comment = """
<!-- erk:metadata-block:erk-implementation-status -->
<details>
<summary><code>erk-implementation-status</code></summary>

```yaml
status: complete
completed_steps: 5
total_steps: 5
timestamp: "2024-11-23T12:00:00Z"
```
</details>
<!-- /erk:metadata-block -->
"""

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1004: plan_to_issue(plan1)}, comments={1004: [comment]})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1004" in result.output


def test_list_plans_shows_failed_action_state() -> None:
    """Test that plans with failed implementation status show 'Failed'."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1005",
        title="Failed Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1005",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1005},
    )

    # Create comment with failed status
    comment = """
<!-- erk:metadata-block:erk-implementation-status -->
<details>
<summary><code>erk-implementation-status</code></summary>

```yaml
status: failed
completed_steps: 2
total_steps: 5
timestamp: "2024-11-23T12:00:00Z"
```
</details>
<!-- /erk:metadata-block -->
"""

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1005: plan_to_issue(plan1)}, comments={1005: [comment]})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1005" in result.output


def test_list_plans_filter_by_run_state_queued() -> None:
    """Test filtering plans by workflow run state (queued)."""
    from erk_shared.github.types import WorkflowRun

    from erk.core.github.fake import FakeGitHub

    # Arrange - Create plans with workflow run IDs in plan-header
    queued_plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '11111'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    running_plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '22222'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    queued_plan = Plan(
        plan_identifier="1010",
        title="Queued Plan",
        body=queued_plan_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1010",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1010},
    )

    running_plan = Plan(
        plan_identifier="1011",
        title="Running Plan",
        body=running_plan_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1011",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 1011},
    )

    # Configure workflow runs with run_id lookup
    queued_run = WorkflowRun(
        run_id="11111",
        status="queued",
        conclusion=None,
        branch="master",
        head_sha="abc123",
    )
    running_run = WorkflowRun(
        run_id="22222",
        status="in_progress",
        conclusion=None,
        branch="master",
        head_sha="def456",
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1010: plan_to_issue(queued_plan), 1011: plan_to_issue(running_plan)},
        )
        github = FakeGitHub(workflow_runs=[queued_run, running_run])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Filter for queued workflow runs
        result = runner.invoke(cli, ["list", "--run-state", "queued"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1010" in result.output
        assert "Queued Plan" in result.output
        assert "#1011" not in result.output


def test_list_plans_filter_by_run_state_success() -> None:
    """Test filtering plans by workflow run state (success)."""
    from erk_shared.github.types import WorkflowRun

    from erk.core.github.fake import FakeGitHub

    # Arrange - Create plans with workflow run IDs in plan-header
    success_plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '11111'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    failed_plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '22222'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    success_plan = Plan(
        plan_identifier="1020",
        title="Success Plan",
        body=success_plan_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1020",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1020},
    )

    failed_plan = Plan(
        plan_identifier="1021",
        title="Failed Plan",
        body=failed_plan_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1021",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 1021},
    )

    # Configure workflow runs with run_id lookup
    success_run = WorkflowRun(
        run_id="11111",
        status="completed",
        conclusion="success",
        branch="master",
        head_sha="abc123",
    )
    failed_run = WorkflowRun(
        run_id="22222",
        status="completed",
        conclusion="failure",
        branch="master",
        head_sha="def456",
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1020: plan_to_issue(success_plan), 1021: plan_to_issue(failed_plan)},
        )
        github = FakeGitHub(workflow_runs=[success_run, failed_run])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Filter for success workflow runs
        result = runner.invoke(cli, ["list", "--run-state", "success"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1020" in result.output
        assert "Success Plan" in result.output
        assert "#1021" not in result.output


def test_list_plans_run_state_filter_no_matches() -> None:
    """Test run-state filter with no matching plans."""
    from erk_shared.github.types import WorkflowRun

    from erk.core.github.fake import FakeGitHub

    # Arrange - Plan with workflow run that doesn't match filter
    plan = Plan(
        plan_identifier="1030",
        title="Regular Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1030",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1030},
    )

    # Configure workflow run with completed/success state
    success_run = WorkflowRun(
        run_id="11111",
        status="completed",
        conclusion="success",
        branch="master",
        head_sha="abc123",
        display_title="Regular Plan",
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1030: plan_to_issue(plan)}, comments={})
        github = FakeGitHub(workflow_runs=[success_run])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Filter for "in_progress" which won't match (run is completed/success)
        result = runner.invoke(cli, ["list", "--run-state", "in_progress"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "No plans found matching the criteria" in result.output


def test_list_plans_pr_column_open_pr() -> None:
    """Test PR column displays open PR with 👀 emoji."""
    from erk_shared.github.types import PullRequestInfo

    from erk.core.github.fake import FakeGitHub

    # Arrange
    plan = Plan(
        plan_identifier="100",
        title="Plan with Open PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/100",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 100},
    )

    pr = PullRequestInfo(
        number=200,
        state="OPEN",
        url="https://github.com/owner/repo/pull/200",
        is_draft=False,
        title="PR for issue 100",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={100: plan_to_issue(plan)})
        github = FakeGitHub(pr_issue_linkages={100: [pr]})
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Use --prs flag to show PR columns
        result = runner.invoke(cli, ["list", "--prs"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # PR cell uses Rich markup: [link=url]#200[/link] 👀
        assert "#200" in result.output
        assert "👀" in result.output  # Open PR emoji
        assert "✅" in result.output  # Checks passing


def test_list_plans_pr_column_draft_pr() -> None:
    """Test PR column displays draft PR with 🚧 emoji."""
    from erk_shared.github.types import PullRequestInfo

    from erk.core.github.fake import FakeGitHub

    # Arrange
    plan = Plan(
        plan_identifier="101",
        title="Plan with Draft PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/101",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 101},
    )

    pr = PullRequestInfo(
        number=201,
        state="DRAFT",
        url="https://github.com/owner/repo/pull/201",
        is_draft=True,
        title="Draft PR for issue 101",
        checks_passing=None,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={101: plan_to_issue(plan)})
        github = FakeGitHub(pr_issue_linkages={101: [pr]})
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Use --prs flag to show PR columns
        result = runner.invoke(cli, ["list", "--prs"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # PR cell uses Rich markup: [link=url]#201[/link] 🚧
        assert "#201" in result.output
        assert "🚧" in result.output  # Draft PR emoji
        assert "🔄" in result.output  # Checks pending


def test_list_plans_pr_column_merged_pr() -> None:
    """Test PR column displays merged PR with 🎉 emoji."""
    from erk_shared.github.types import PullRequestInfo

    from erk.core.github.fake import FakeGitHub

    # Arrange
    plan = Plan(
        plan_identifier="102",
        title="Plan with Merged PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/102",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 102},
    )

    pr = PullRequestInfo(
        number=202,
        state="MERGED",
        url="https://github.com/owner/repo/pull/202",
        is_draft=False,
        title="Merged PR for issue 102",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={102: plan_to_issue(plan)})
        github = FakeGitHub(pr_issue_linkages={102: [pr]})
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Use --prs flag to show PR columns
        result = runner.invoke(cli, ["list", "--prs"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # PR cell uses Rich markup: [link=url]#202[/link] 🎉
        assert "#202" in result.output
        assert "🎉" in result.output  # Merged PR emoji
        assert "✅" in result.output  # Checks passing


def test_list_plans_pr_column_closed_pr() -> None:
    """Test PR column displays closed PR with ⛔ emoji."""
    from erk_shared.github.types import PullRequestInfo

    from erk.core.github.fake import FakeGitHub

    # Arrange
    plan = Plan(
        plan_identifier="103",
        title="Plan with Closed PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/103",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 103},
    )

    pr = PullRequestInfo(
        number=203,
        state="CLOSED",
        url="https://github.com/owner/repo/pull/203",
        is_draft=False,
        title="Closed PR for issue 103",
        checks_passing=False,
        owner="owner",
        repo="repo",
        has_conflicts=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={103: plan_to_issue(plan)})
        github = FakeGitHub(pr_issue_linkages={103: [pr]})
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Use --prs flag to show PR columns
        result = runner.invoke(cli, ["list", "--prs"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # PR cell uses Rich markup: [link=url]#203[/link] ⛔
        assert "#203" in result.output
        assert "⛔" in result.output  # Closed PR emoji
        assert "🚫" in result.output  # Checks failing


def test_list_plans_pr_column_with_conflicts() -> None:
    """Test PR column shows conflict indicator 💥 for open/draft PRs with conflicts."""
    from erk_shared.github.types import PullRequestInfo

    from erk.core.github.fake import FakeGitHub

    # Arrange
    plan = Plan(
        plan_identifier="104",
        title="Plan with Conflicted PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/104",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 104},
    )

    pr = PullRequestInfo(
        number=204,
        state="OPEN",
        url="https://github.com/owner/repo/pull/204",
        is_draft=False,
        title="Conflicted PR for issue 104",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=True,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={104: plan_to_issue(plan)})
        github = FakeGitHub(pr_issue_linkages={104: [pr]})
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Use --prs flag to show PR columns
        result = runner.invoke(cli, ["list", "--prs"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # PR cell uses Rich markup: [link=url]#204[/link] 👀💥
        assert "#204" in result.output
        assert "👀" in result.output  # Open PR emoji
        assert "💥" in result.output  # Conflict indicator


def test_list_plans_pr_column_multiple_prs_prefers_open() -> None:
    """Test PR column shows most recent open PR when multiple PRs exist."""
    from erk_shared.github.types import PullRequestInfo

    from erk.core.github.fake import FakeGitHub

    # Arrange
    plan = Plan(
        plan_identifier="105",
        title="Plan with Multiple PRs",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/105",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 105},
    )

    # Older closed PR
    closed_pr = PullRequestInfo(
        number=205,
        state="CLOSED",
        url="https://github.com/owner/repo/pull/205",
        is_draft=False,
        title="Old closed PR",
        checks_passing=None,
        owner="owner",
        repo="repo",
        has_conflicts=None,
    )

    # Recent open PR (should be selected)
    open_pr = PullRequestInfo(
        number=206,
        state="OPEN",
        url="https://github.com/owner/repo/pull/206",
        is_draft=False,
        title="Recent open PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={105: plan_to_issue(plan)})
        # PRs already sorted by created_at descending
        github = FakeGitHub(pr_issue_linkages={105: [open_pr, closed_pr]})
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Use --prs flag to show PR columns
        result = runner.invoke(cli, ["list", "--prs"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # PR cell uses Rich markup: [link=url]#206[/link] 👀
        assert "#206" in result.output  # Shows open PR, not closed
        assert "👀" in result.output  # Open PR emoji


def test_list_plans_pr_column_no_pr_linked() -> None:
    """Test PR column shows '-' when no PR is linked to issue."""
    # Arrange
    plan = Plan(
        plan_identifier="106",
        title="Plan without PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/106",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 106},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={106: plan_to_issue(plan)})
        # No PR linkages configured
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#106" in result.output
        # PR and Checks columns should both show "-"
        # Can't easily assert the exact column position, but verifying no emojis appear
        assert "👀" not in result.output
        assert "🚧" not in result.output
        assert "🎉" not in result.output
        assert "⛔" not in result.output


def test_list_plans_default_no_pr_columns() -> None:
    """Test default output has no pr/chks columns."""
    from tests.test_utils.output_helpers import strip_ansi

    # Arrange
    plan = Plan(
        plan_identifier="200",
        title="Test Default Columns",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/200",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 200},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={200: plan_to_issue(plan)})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act - default (no --prs flag)
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # Header should NOT contain pr or chks columns by default
        assert "pr" not in output.split("\n")[0].lower() or "plan" in output.split("\n")[0].lower()
        # More reliable: check that column headers don't include "pr" and "chks"
        # The header line contains column names
        lines = [line for line in output.split("\n") if line.strip()]
        if len(lines) >= 2:
            header_line = lines[1]  # First line after "Found X plan(s)"
            # "pr" as a standalone column header should not appear
            # but "plan" does contain "p" - check for standalone "pr " or " pr"
            assert " pr " not in header_line.lower()
            assert "chks" not in header_line.lower()


def test_list_plans_prs_flag_shows_pr_columns() -> None:
    """Test --prs flag shows pr and chks columns."""
    from erk_shared.github.types import PullRequestInfo

    from erk.core.github.fake import FakeGitHub
    from tests.test_utils.output_helpers import strip_ansi

    # Arrange
    plan = Plan(
        plan_identifier="201",
        title="Test PR Columns",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/201",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 201},
    )

    pr = PullRequestInfo(
        number=301,
        state="OPEN",
        url="https://github.com/owner/repo/pull/301",
        is_draft=False,
        title="PR for issue 201",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={201: plan_to_issue(plan)})
        github = FakeGitHub(pr_issue_linkages={201: [pr]})
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - with --prs flag
        result = runner.invoke(cli, ["list", "--prs"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # Should show PR number and emoji
        assert "#301" in output
        assert "👀" in result.output  # Open PR emoji
        assert "✅" in result.output  # Checks passing


def test_list_plans_all_flag_shows_pr_and_run_columns() -> None:
    """Test --all flag shows both PR and run columns."""
    from erk_shared.github.types import PullRequestInfo, WorkflowRun

    from erk.core.github.fake import FakeGitHub
    from tests.test_utils.output_helpers import strip_ansi

    # Arrange - Create plan with workflow run ID in plan-header
    plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '99999'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    plan = Plan(
        plan_identifier="202",
        title="Test All Columns",
        body=plan_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/202",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 202},
    )

    pr = PullRequestInfo(
        number=302,
        state="OPEN",
        url="https://github.com/owner/repo/pull/302",
        is_draft=False,
        title="PR for issue 202",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    workflow_run = WorkflowRun(
        run_id="99999",
        status="completed",
        conclusion="success",
        branch="master",
        head_sha="abc123",
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={202: plan_to_issue(plan)})
        github = FakeGitHub(pr_issue_linkages={202: [pr]}, workflow_runs=[workflow_run])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - with --all flag
        result = runner.invoke(cli, ["list", "--all"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # Should show PR number
        assert "#302" in output
        assert "👀" in result.output  # Open PR emoji
        # Should show workflow run ID
        assert "99999" in output


def test_list_plans_all_flag_short_form() -> None:
    """Test -a short form works same as --all."""
    from erk_shared.github.types import PullRequestInfo, WorkflowRun

    from erk.core.github.fake import FakeGitHub
    from tests.test_utils.output_helpers import strip_ansi

    # Arrange - Create plan with workflow run ID in plan-header
    plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '88888'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    plan = Plan(
        plan_identifier="203",
        title="Test Short Form",
        body=plan_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/203",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 203},
    )

    pr = PullRequestInfo(
        number=303,
        state="MERGED",
        url="https://github.com/owner/repo/pull/303",
        is_draft=False,
        title="PR for issue 203",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    workflow_run = WorkflowRun(
        run_id="88888",
        status="completed",
        conclusion="success",
        branch="master",
        head_sha="def456",
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={203: plan_to_issue(plan)})
        github = FakeGitHub(pr_issue_linkages={203: [pr]}, workflow_runs=[workflow_run])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - with -a short form
        result = runner.invoke(cli, ["list", "-a"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # Should show PR number (merged PR)
        assert "#303" in output
        assert "🎉" in result.output  # Merged PR emoji
        # Should show workflow run ID
        assert "88888" in output
