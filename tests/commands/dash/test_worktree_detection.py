"""Tests for local worktree detection in plan list command.

Tests verifying that the local-wt column shows worktree status from
local .impl/issue.json files, not from GitHub metadata.
"""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.plan_store.types import Plan, PlanState
from tests.commands.dash.conftest import plan_to_issue
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_plan_list_shows_worktree_status() -> None:
    """Test that plan list shows dash for non-local worktrees.

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
    github = FakeGitHub(issues_data=[plan_to_issue(plan1), plan_to_issue(plan2)])

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Use erk plan list for static output
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output
        assert "#867" in result.output
        assert "Rename Erk Slash Commands" in result.output
        # Non-local worktree should NOT appear in output (shows "-" instead)
        assert "rename-erk-slash-commands" not in result.output
        assert "#868" in result.output
        assert "Issue Without Worktree" in result.output


def test_plan_list_shows_dash_for_non_local_worktree() -> None:
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
    github = FakeGitHub(issues_data=[plan_to_issue(plan1)])

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Use erk plan list for static output
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert - Non-local worktree should NOT be shown (shows "-" instead)
        assert result.exit_code == 0
        assert "second-attempt" not in result.output


def test_plan_list_shows_worktree_from_local_impl() -> None:
    """Test that list command detects worktree from local .impl/issue.json file."""
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
        github = FakeGitHub(issues_data=[plan_to_issue(plan1)])
        ctx = build_workspace_test_context(env, git=git, issues=issues, github=github)

        # Act - Use erk plan list for static output
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert - Should show worktree name from local detection
        assert result.exit_code == 0
        assert "#950" in result.output
        assert "Test Local Detection" in result.output
        assert "feature-worktree" in result.output


def test_plan_list_prefers_local_over_github() -> None:
    """Test that local .impl/issue.json detection takes precedence over GitHub comments."""
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
        github = FakeGitHub(issues_data=[plan_to_issue(plan1)])
        ctx = build_workspace_test_context(env, git=git, issues=issues, github=github)

        # Act - Use erk plan list for static output
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert - Should show local worktree name, not GitHub one
        assert result.exit_code == 0
        assert "local-worktree" in result.output
        assert "old-github-worktree" not in result.output


def test_plan_list_shows_dash_when_no_local_worktree() -> None:
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
        github = FakeGitHub(issues_data=[plan_to_issue(plan1)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Use erk plan list for static output
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert - Non-local worktree should NOT be shown (shows "-" instead)
        assert result.exit_code == 0
        assert "#970" in result.output
        assert "github-worktree" not in result.output


def test_plan_list_handles_multiple_local_worktrees() -> None:
    """Test first-found worktree shown when multiple worktrees reference same issue."""
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
        github = FakeGitHub(issues_data=[plan_to_issue(plan1)])
        ctx = build_workspace_test_context(env, git=git, issues=issues, github=github)

        # Act - Use erk plan list for static output
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert - Should show first worktree found
        assert result.exit_code == 0
        assert "#980" in result.output
        # Should show exactly one of the worktrees (first-found behavior)
        # The order depends on git.list_worktrees() order
        assert "first-worktree" in result.output or "second-worktree" in result.output
