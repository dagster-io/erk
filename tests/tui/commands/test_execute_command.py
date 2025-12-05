"""Tests for PlanDetailScreen.execute_command."""

from erk.tui.app import PlanDetailScreen
from erk.tui.data.types import PlanRowData
from tests.fakes.command_executor import FakeCommandExecutor
from tests.fakes.plan_data_provider import make_plan_row


class TestExecuteCommandBrowserCommands:
    """Tests for browser-related commands."""

    def test_open_browser_opens_pr_url_when_available(self) -> None:
        """open_browser opens PR URL when PR is available."""
        row = make_plan_row(
            123,
            "Test",
            pr_url="https://github.com/test/repo/pull/456",
            issue_url="https://github.com/test/repo/issues/123",
        )
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("open_browser")
        assert executor.opened_urls == ["https://github.com/test/repo/pull/456"]

    def test_open_browser_opens_issue_url_when_no_pr(self) -> None:
        """open_browser opens issue URL when no PR is available."""
        row = make_plan_row(123, "Test", issue_url="https://github.com/test/repo/issues/123")
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("open_browser")
        assert executor.opened_urls == ["https://github.com/test/repo/issues/123"]

    def test_open_issue_opens_issue_url(self) -> None:
        """open_issue opens the issue URL."""
        row = make_plan_row(123, "Test", issue_url="https://github.com/test/repo/issues/123")
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("open_issue")
        assert executor.opened_urls == ["https://github.com/test/repo/issues/123"]
        assert "Opened issue #123" in executor.notifications

    def test_open_pr_opens_pr_url(self) -> None:
        """open_pr opens the PR URL."""
        row = make_plan_row(
            123,
            "Test",
            pr_number=456,
            pr_url="https://github.com/test/repo/pull/456",
        )
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("open_pr")
        assert executor.opened_urls == ["https://github.com/test/repo/pull/456"]
        assert "Opened PR #456" in executor.notifications

    def test_open_run_opens_run_url(self) -> None:
        """open_run opens the workflow run URL."""
        row = make_plan_row(
            123,
            "Test",
            run_url="https://github.com/test/repo/actions/runs/789",
        )
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("open_run")
        assert executor.opened_urls == ["https://github.com/test/repo/actions/runs/789"]


class TestExecuteCommandCopyCommands:
    """Tests for copy-related commands."""

    def test_copy_checkout_copies_command(self) -> None:
        """copy_checkout copies the checkout command."""
        row = make_plan_row(123, "Test", worktree_name="feature-123", exists_locally=True)
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("copy_checkout")
        assert executor.copied_texts == ["erk co feature-123"]
        assert "Copied: erk co feature-123" in executor.notifications

    def test_copy_pr_checkout_copies_command(self) -> None:
        """copy_pr_checkout copies the PR checkout command."""
        row = make_plan_row(123, "Test", pr_number=456)
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("copy_pr_checkout")
        assert executor.copied_texts == ["erk pr co 456"]
        assert "Copied: erk pr co 456" in executor.notifications

    def test_copy_implement_copies_command(self) -> None:
        """copy_implement copies the implement command."""
        row = make_plan_row(123, "Test")
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("copy_implement")
        assert executor.copied_texts == ["erk implement 123"]
        assert "Copied: erk implement 123" in executor.notifications

    def test_copy_implement_dangerous_copies_command(self) -> None:
        """copy_implement_dangerous copies the dangerous implement command."""
        row = make_plan_row(123, "Test")
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("copy_implement_dangerous")
        assert executor.copied_texts == ["erk implement 123 --dangerous"]
        assert "Copied: erk implement 123 --dangerous" in executor.notifications

    def test_copy_implement_yolo_copies_command(self) -> None:
        """copy_implement_yolo copies the yolo implement command."""
        row = make_plan_row(123, "Test")
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("copy_implement_yolo")
        assert executor.copied_texts == ["erk implement 123 --yolo"]
        assert "Copied: erk implement 123 --yolo" in executor.notifications

    def test_copy_submit_copies_command(self) -> None:
        """copy_submit copies the submit command."""
        row = make_plan_row(123, "Test")
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("copy_submit")
        assert executor.copied_texts == ["erk submit 123"]
        assert "Copied: erk submit 123" in executor.notifications


class TestExecuteCommandClosePlan:
    """Tests for close_plan command."""

    def test_close_plan_closes_and_refreshes(self) -> None:
        """close_plan closes the plan and triggers refresh."""
        row = make_plan_row(123, "Test", issue_url="https://github.com/test/repo/issues/123")
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("close_plan")
        assert executor.closed_plans == [(123, "https://github.com/test/repo/issues/123")]
        assert executor.refresh_count == 1
        assert "Closed plan #123" in executor.notifications

    def test_close_plan_reports_closed_prs(self) -> None:
        """close_plan reports PR numbers when PRs are closed."""
        row = make_plan_row(123, "Test", issue_url="https://github.com/test/repo/issues/123")
        executor = FakeCommandExecutor()
        executor.set_close_plan_return([456, 457])
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("close_plan")
        assert "Closed plan #123 and PRs: #456, #457" in executor.notifications

    def test_close_plan_does_nothing_without_issue_url(self) -> None:
        """close_plan does nothing if no issue URL."""
        # Create row directly to set issue_url=None (make_plan_row defaults it)
        row = PlanRowData(
            issue_number=123,
            issue_url=None,  # Explicitly None
            title="Test",
            pr_number=None,
            pr_url=None,
            pr_display="-",
            checks_display="-",
            worktree_name="",
            exists_locally=False,
            local_impl_display="-",
            remote_impl_display="-",
            run_id_display="-",
            run_state_display="-",
            run_url=None,
            full_title="Test",
            pr_title=None,
            pr_state=None,
            worktree_branch=None,
            last_local_impl_at=None,
            last_remote_impl_at=None,
            run_id=None,
            run_status=None,
            run_conclusion=None,
            log_entries=(),
        )
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("close_plan")
        assert executor.closed_plans == []
        assert executor.refresh_count == 0


class TestExecuteCommandSubmitToQueue:
    """Tests for submit_to_queue command.

    Note: submit_to_queue now uses streaming output via subprocess when repo_root
    is provided. These tests verify the guard conditions but actual streaming
    behavior is tested via integration tests.
    """

    def test_submit_to_queue_does_nothing_without_repo_root(self) -> None:
        """submit_to_queue does nothing if repo_root is not provided."""
        row = make_plan_row(123, "Test", issue_url="https://github.com/test/repo/issues/123")
        executor = FakeCommandExecutor()
        # repo_root not provided - streaming command should not execute
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("submit_to_queue")
        # No executor methods should be called (streaming is independent)
        assert executor.refresh_count == 0

    def test_submit_to_queue_does_nothing_without_issue_url(self) -> None:
        """submit_to_queue does nothing if no issue URL."""
        row = PlanRowData(
            issue_number=123,
            issue_url=None,  # Explicitly None
            title="Test",
            pr_number=None,
            pr_url=None,
            pr_display="-",
            checks_display="-",
            worktree_name="",
            exists_locally=False,
            local_impl_display="-",
            remote_impl_display="-",
            run_id_display="-",
            run_state_display="-",
            run_url=None,
            full_title="Test",
            pr_title=None,
            pr_state=None,
            worktree_branch=None,
            last_local_impl_at=None,
            last_remote_impl_at=None,
            run_id=None,
            run_status=None,
            run_conclusion=None,
            log_entries=(),
        )
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row, executor=executor)
        screen.execute_command("submit_to_queue")
        assert executor.refresh_count == 0



class TestExecuteCommandNoExecutor:
    """Tests for behavior when no executor is provided."""

    def test_does_nothing_without_executor(self) -> None:
        """Commands do nothing when no executor is provided."""
        row = make_plan_row(123, "Test")
        screen = PlanDetailScreen(row)  # No executor
        # Should not raise
        screen.execute_command("open_browser")
        screen.execute_command("copy_implement")
        screen.execute_command("close_plan")
        screen.execute_command("submit_to_queue")
