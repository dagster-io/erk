"""Integration test verifying that plan-issue commands use correct git repository root.

This test verifies the fix for the bug where erk plan-issue list/get failed with
"not a git repository" error because they passed the erk metadata directory to gh
commands instead of using repo.root (the actual git repository).

The fix: plan-issue commands now explicitly use repo.root for GitHub operations
instead of relying on ensure_erk_metadata_dir()'s return value.
"""

from pathlib import Path

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState

from erk.cli.commands.plan.get import get_plan
from erk.cli.commands.plan.list_cmd import dash
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_plan_issue_list_uses_repo_root_not_metadata_dir() -> None:
    """Test that list command uses repo.root for gh operations.

    This is a regression test for the bug where plan-issue list failed with
    "not a git repository" error because it passed the erk metadata directory
    to gh commands instead of repo.root.

    The bug call chain was:
    1. list_cmd.py captured ensure_erk_metadata_dir() return value as repo_root
    2. ensure_erk_metadata_dir() returned repo.repo_dir (erk metadata dir)
    3. repo_root was passed to list_plans(repo_root, ...)
    4. This became cwd for gh subprocess calls
    5. gh failed because metadata dir has no .git

    After fix: Commands call ensure_erk_metadata_dir() for side effects but use repo.root directly.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Track which directory is passed to GitHubIssues operations
        captured_repo_root: Path | None = None

        class TrackingGitHubIssues(FakeGitHubIssues):
            def list_issues(self, repo_root: Path, **kwargs):
                nonlocal captured_repo_root
                captured_repo_root = repo_root
                return []  # Return empty list

        issues = TrackingGitHubIssues()
        ctx = env.build_context(issues=issues)

        # Act: Run the dash command
        result = runner.invoke(dash, obj=ctx)

        # Assert: Command should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: repo_root passed to GitHubIssues should be git root, NOT metadata dir
        assert captured_repo_root == env.cwd, (
            f"Expected repo_root to be git repository root ({env.cwd}), "
            f"but got erk metadata directory ({captured_repo_root})"
        )


def test_plan_issue_get_uses_repo_root_not_metadata_dir() -> None:
    """Test that get command uses repo.root for gh operations.

    Same regression test as above but for the 'get' command.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Track which directory is passed to gh operations
        captured_repo_root: Path | None = None

        class TrackingPlanStore(FakePlanStore):
            def get_plan(self, repo_root: Path, identifier: str):
                nonlocal captured_repo_root
                captured_repo_root = repo_root
                # Return minimal valid Plan to satisfy command
                return self._plan_issues[identifier]

        # Create a fake issue to return
        from datetime import UTC, datetime

        fake_issue = Plan(
            plan_identifier="42",
            title="Test Issue",
            body="Test body",
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/42",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
        )

        store = TrackingPlanStore()
        store._plan_issues = {"42": fake_issue}
        ctx = env.build_context(plan_store=store)

        # Act: Run the get command
        result = runner.invoke(get_plan, ["42"], obj=ctx)

        # Assert: Command should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: repo_root passed to store should be git root, NOT metadata dir
        assert captured_repo_root == env.cwd, (
            f"Expected repo_root to be git repository root ({env.cwd}), "
            f"but got erk metadata directory ({captured_repo_root})"
        )
