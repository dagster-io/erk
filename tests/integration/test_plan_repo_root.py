"""Integration test verifying that plan-issue commands use correct git repository root.

This test verifies the fix for the bug where erk plan-issue list/get failed with
"not a git repository" error because they passed the erk metadata directory to gh
commands instead of using repo.root (the actual git repository).

The fix: plan-issue commands now explicitly use repo.root for GitHub operations
instead of relying on ensure_erk_metadata_dir()'s return value.
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import IssueInfo
from erk_shared.github.types import GitHubRepoLocation, PullRequestInfo
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState

from erk.cli.commands.plan.get import get_plan
from erk.cli.commands.plan.list_cmd import dash
from erk.core.services.plan_list_service import PlanListService
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
    Now: dash command uses PlanListService which calls GitHub.get_issues_with_pr_linkages().
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Track which directory is passed to GitHub operations
        captured_repo_root: Path | None = None

        class TrackingGitHub(FakeGitHub):
            def get_issues_with_pr_linkages(
                self,
                location: GitHubRepoLocation,
                labels: list[str],
                state: str | None = None,
                limit: int | None = None,
            ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
                nonlocal captured_repo_root
                captured_repo_root = location.root
                return [], {}  # Return empty results

        github = TrackingGitHub()
        # Create PlanListService with tracking GitHub
        from erk_shared.github.issues import FakeGitHubIssues

        plan_list_service = PlanListService(github, FakeGitHubIssues())
        ctx = env.build_context(github=github, plan_list_service=plan_list_service)

        # Act: Run the dash command
        # Mock ErkDashApp to prevent Textual TUI from launching and trigger data fetch
        # (Textual apps hang in test environments without a real terminal)
        from erk.tui.data.provider import PlanDataProvider

        captured_provider: PlanDataProvider | None = None
        captured_filters = None

        class MockApp:
            def __init__(self, provider, filters, refresh_interval):
                nonlocal captured_provider, captured_filters
                captured_provider = provider
                captured_filters = filters

            def run(self):
                # Trigger a data fetch to exercise the GitHub code path
                if captured_provider and captured_filters:
                    captured_provider.fetch_plans(captured_filters)

        with patch("erk.cli.commands.plan.list_cmd.ErkDashApp", MockApp):
            result = runner.invoke(dash, obj=ctx)

            # Assert: Command should succeed
            assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: repo_root passed to GitHub should be git root, NOT metadata dir
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
