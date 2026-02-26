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

from erk.cli.commands.pr.list_cmd import dash
from erk.cli.commands.pr.view_cmd import pr_view
from erk.core.services.plan_list_service import RealPlanListService
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import (
    GitHubRepoLocation,
    PRDetails,
    PRNotFound,
    PullRequestInfo,
)
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import issue_info_to_pr_details


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
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # Track which directory is passed to GitHub operations
        captured_repo_root: Path | None = None

        class TrackingGitHub(FakeGitHub):
            def get_issues_with_pr_linkages(
                self,
                location: GitHubRepoLocation,
                labels: list[str],
                state: str = "open",
                limit: int | None = None,
                creator: str | None = None,
            ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
                nonlocal captured_repo_root
                captured_repo_root = location.root
                return [], {}  # Return empty results

        github = TrackingGitHub()
        from erk_shared.gateway.github.issues.fake import FakeGitHubIssues

        plan_list_service = RealPlanListService(github, FakeGitHubIssues(), time=FakeTime())
        ctx = env.build_context(github=github, plan_list_service=plan_list_service)

        # Act: Run the dash command
        # Mock ErkDashApp to prevent Textual TUI from launching and trigger data fetch
        # (Textual apps hang in test environments without a real terminal)
        from erk_shared.gateway.plan_data_provider.abc import PlanDataProvider

        captured_provider: PlanDataProvider | None = None
        captured_filters = None

        class MockApp:
            def __init__(
                self,
                provider,
                filters,
                refresh_interval,
                initial_sort=None,
                plan_backend=None,
            ):
                nonlocal captured_provider, captured_filters
                captured_provider = provider
                captured_filters = filters

            def run(self):
                # Trigger a data fetch to exercise the GitHub code path
                if captured_provider and captured_filters:
                    captured_provider.fetch_plans(captured_filters)

        with (
            patch("erk.cli.commands.pr.list_cmd.ErkDashApp", MockApp),
            patch("erk.cli.commands.pr.list_cmd.fetch_github_token", return_value="fake-token"),
        ):
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
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # Track which directory is passed to gh operations
        captured_repo_root: Path | None = None

        from datetime import UTC, datetime

        # Create a fake issue and convert to PR details for PlannedPRBackend
        fake_issue = IssueInfo(
            number=42,
            title="Test Issue",
            body="Test body",
            state="OPEN",
            url="https://github.com/test/repo/issues/42",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            author="test-user",
        )
        pr_details = issue_info_to_pr_details(fake_issue)

        # Create a tracking FakeGitHub that captures the repo_root on get_pr
        class TrackingFakeGitHub(FakeGitHub):
            def get_pr(self, repo_root: Path, pr_number: int) -> PRDetails | PRNotFound:
                nonlocal captured_repo_root
                captured_repo_root = repo_root
                return super().get_pr(repo_root, pr_number)

        tracking_github = TrackingFakeGitHub(pr_details={42: pr_details})
        store = PlannedPRBackend(tracking_github, tracking_github.issues, time=FakeTime())
        ctx = env.build_context(plan_store=store, issues=tracking_github.issues)

        # Act: Run the get command
        result = runner.invoke(pr_view, ["42"], obj=ctx)

        # Assert: Command should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: repo_root passed to store should be git root, NOT metadata dir
        assert captured_repo_root == env.cwd, (
            f"Expected repo_root to be git repository root ({env.cwd}), "
            f"but got erk metadata directory ({captured_repo_root})"
        )
