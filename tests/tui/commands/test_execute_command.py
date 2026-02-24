"""Tests for PlanDetailScreen.execute_command."""

from datetime import UTC, datetime

from erk.tui.data.types import PlanRowData
from erk.tui.screens.plan_detail_screen import PlanDetailScreen
from erk_shared.gateway.command_executor.fake import FakeCommandExecutor
from erk_shared.gateway.plan_data_provider.fake import make_plan_row


class TestExecuteCommandBrowserCommands:
    """Tests for browser-related commands."""

    def test_open_browser_opens_pr_url_when_available(self) -> None:
        """open_browser opens PR URL when PR is available."""
        row = make_plan_row(
            123,
            "Test",
            pr_url="https://github.com/test/repo/pull/456",
            plan_url="https://github.com/test/repo/issues/123",
        )
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("open_browser")
        assert executor.opened_urls == ["https://github.com/test/repo/pull/456"]

    def test_open_browser_opens_issue_url_when_no_pr(self) -> None:
        """open_browser opens issue URL when no PR is available."""
        row = make_plan_row(123, "Test", plan_url="https://github.com/test/repo/issues/123")
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("open_browser")
        assert executor.opened_urls == ["https://github.com/test/repo/issues/123"]

    def test_open_issue_opens_issue_url(self) -> None:
        """open_issue opens the issue URL."""
        row = make_plan_row(123, "Test", plan_url="https://github.com/test/repo/issues/123")
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("open_issue")
        assert executor.opened_urls == ["https://github.com/test/repo/issues/123"]
        assert "Opened plan #123" in executor.notifications

    def test_open_pr_opens_pr_url(self) -> None:
        """open_pr opens the PR URL."""
        row = make_plan_row(
            123,
            "Test",
            pr_number=456,
            pr_url="https://github.com/test/repo/pull/456",
        )
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
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
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("open_run")
        assert executor.opened_urls == ["https://github.com/test/repo/actions/runs/789"]


class TestExecuteCommandCopyCommands:
    """Tests for copy-related commands."""

    def test_copy_checkout_copies_command(self) -> None:
        """copy_checkout copies branch checkout command."""
        row = make_plan_row(
            123,
            "Test",
            worktree_name="feature-123",
            worktree_branch="feature-123",
            exists_locally=True,
        )
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("copy_checkout")
        assert executor.copied_texts == ["erk br co feature-123"]
        assert "Copied: erk br co feature-123" in executor.notifications

    def test_copy_checkout_notifies_when_worktree_branch_none(self) -> None:
        """copy_checkout shows notification when worktree_branch is None."""
        row = make_plan_row(123, "Test")  # worktree_branch defaults to None
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("copy_checkout")
        # Should not copy anything
        assert executor.copied_texts == []
        # Should show notification
        expected_msg = "No branch associated with this plan is checked out in a local worktree"
        assert expected_msg in executor.notifications

    def test_copy_pr_checkout_copies_command(self) -> None:
        """copy_pr_checkout copies the PR checkout command."""
        row = make_plan_row(123, "Test", pr_number=456)
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("copy_pr_checkout")
        assert executor.copied_texts == ["erk pr co 456"]
        assert "Copied: erk pr co 456" in executor.notifications

    def test_copy_prepare_copies_command(self) -> None:
        """copy_prepare copies the prepare command."""
        row = make_plan_row(123, "Test")
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("copy_prepare")
        assert executor.copied_texts == ["erk br co --for-plan 123"]
        assert "Copied: erk br co --for-plan 123" in executor.notifications

    def test_copy_submit_copies_command(self) -> None:
        """copy_submit copies the submit command."""
        row = make_plan_row(123, "Test")
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("copy_submit")
        assert executor.copied_texts == ["erk plan submit 123"]
        assert "Copied: erk plan submit 123" in executor.notifications


class TestExecuteCommandClosePlan:
    """Tests for close_plan command.

    Note: close_plan now uses in-process HTTP client (no subprocess).
    These tests verify the guard conditions. The HTTP client behavior
    is tested in tests/tui/data/test_provider.py.
    """

    def test_close_plan_does_nothing_without_issue_url(self) -> None:
        """close_plan does nothing if no issue URL."""
        # Create row directly to set plan_url=None (make_plan_row defaults it)
        row = PlanRowData(
            plan_id=123,
            plan_url=None,  # Explicitly None
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
            plan_body="",
            pr_title=None,
            pr_state=None,
            pr_head_branch=None,
            worktree_branch=None,
            last_local_impl_at=None,
            last_remote_impl_at=None,
            run_id=None,
            run_status=None,
            run_conclusion=None,
            log_entries=(),
            resolved_comment_count=0,
            total_comment_count=0,
            comments_display="-",
            learn_status=None,
            learn_plan_issue=None,
            learn_plan_issue_closed=None,
            learn_plan_pr=None,
            learn_run_url=None,
            learn_display="- not started",
            learn_display_icon="-",
            objective_issue=None,
            objective_url=None,
            objective_display="-",
            objective_done_nodes=0,
            objective_total_nodes=0,
            objective_progress_display="-",
            objective_slug_display="-",
            objective_state_display="-",
            objective_deps_display="-",
            objective_deps_plans=(),
            objective_next_node_display="-",
            updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_display="-",
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            created_display="-",
            author="test-user",
            is_learn_plan=False,
            lifecycle_display="-",
            status_display="-",
        )
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("close_plan")
        assert executor.refresh_count == 0


class TestExecuteCommandSubmitToQueue:
    """Tests for submit_to_queue command.

    Note: submit_to_queue uses dismiss-and-delegate to the app's background worker.
    These tests verify the guard conditions. The async worker behavior is tested
    in test_app.py.
    """

    def test_submit_to_queue_does_nothing_without_issue_url(self) -> None:
        """submit_to_queue does nothing if no issue URL."""
        row = PlanRowData(
            plan_id=123,
            plan_url=None,  # Explicitly None
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
            plan_body="",
            pr_title=None,
            pr_state=None,
            pr_head_branch=None,
            worktree_branch=None,
            last_local_impl_at=None,
            last_remote_impl_at=None,
            run_id=None,
            run_status=None,
            run_conclusion=None,
            log_entries=(),
            resolved_comment_count=0,
            total_comment_count=0,
            comments_display="-",
            learn_status=None,
            learn_plan_issue=None,
            learn_plan_issue_closed=None,
            learn_plan_pr=None,
            learn_run_url=None,
            learn_display="- not started",
            learn_display_icon="-",
            objective_issue=None,
            objective_url=None,
            objective_display="-",
            objective_done_nodes=0,
            objective_total_nodes=0,
            objective_progress_display="-",
            objective_slug_display="-",
            objective_state_display="-",
            objective_deps_display="-",
            objective_deps_plans=(),
            objective_next_node_display="-",
            updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_display="-",
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            created_display="-",
            author="test-user",
            is_learn_plan=False,
            lifecycle_display="-",
            status_display="-",
        )
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("submit_to_queue")
        assert executor.refresh_count == 0


class TestExecuteCommandLandPR:
    """Tests for land_pr command.

    Note: land_pr uses dismiss-and-delegate to the app's background worker.
    These tests verify the guard conditions. The async worker behavior
    (including objective update chaining) is tested in test_app.py.
    """

    def test_land_pr_does_nothing_without_pr_number(self) -> None:
        """land_pr does nothing if no PR is associated with the plan."""
        row = make_plan_row(123, "Test")  # No pr_number
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("land_pr")
        assert executor.refresh_count == 0


class TestExecuteCommandFixConflictsRemote:
    """Tests for fix_conflicts_remote command.

    Note: fix_conflicts_remote uses dismiss-and-delegate to the app's background worker.
    These tests verify the guard conditions. The async worker behavior is tested
    in test_app.py.
    """

    def test_fix_conflicts_remote_does_nothing_without_pr_number(self) -> None:
        """fix_conflicts_remote does nothing if no PR is associated with the plan."""
        row = make_plan_row(123, "Test")  # No pr_number
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("fix_conflicts_remote")
        assert executor.refresh_count == 0


class TestExecuteCommandCopyClosePlan:
    """Tests for copy_close_plan command."""

    def test_copy_close_plan_copies_command(self) -> None:
        """copy_close_plan copies the close plan command."""
        row = make_plan_row(123, "Test")
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("copy_close_plan")
        assert executor.copied_texts == ["erk plan close 123"]
        assert "Copied: erk plan close 123" in executor.notifications


class TestExecuteCommandCopyFixConflictsRemote:
    """Tests for copy_fix_conflicts_remote command."""

    def test_copy_fix_conflicts_remote_copies_command(self) -> None:
        """copy_fix_conflicts_remote copies the launch command when PR exists."""
        row = make_plan_row(123, "Test", pr_number=456)
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("copy_fix_conflicts_remote")
        assert executor.copied_texts == ["erk launch pr-fix-conflicts --pr 456"]
        assert "Copied: erk launch pr-fix-conflicts --pr 456" in executor.notifications

    def test_copy_fix_conflicts_remote_does_nothing_without_pr(self) -> None:
        """copy_fix_conflicts_remote does nothing when no PR number."""
        row = make_plan_row(123, "Test")  # No pr_number
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("copy_fix_conflicts_remote")
        assert executor.copied_texts == []


class TestExecuteCommandCopyAddressRemote:
    """Tests for copy_address_remote command."""

    def test_copy_address_remote_copies_command(self) -> None:
        """copy_address_remote copies the launch command when PR exists."""
        row = make_plan_row(123, "Test", pr_number=456)
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("copy_address_remote")
        assert executor.copied_texts == ["erk launch pr-address --pr 456"]
        assert "Copied: erk launch pr-address --pr 456" in executor.notifications

    def test_copy_address_remote_does_nothing_without_pr(self) -> None:
        """copy_address_remote does nothing when no PR number."""
        row = make_plan_row(123, "Test")  # No pr_number
        executor = FakeCommandExecutor()
        screen = PlanDetailScreen(row=row, executor=executor)
        screen.execute_command("copy_address_remote")
        assert executor.copied_texts == []


class TestExecuteCommandNoExecutor:
    """Tests for behavior when no executor is provided."""

    def test_does_nothing_without_executor(self) -> None:
        """Commands do nothing when no executor is provided."""
        row = make_plan_row(123, "Test")
        screen = PlanDetailScreen(row=row)  # No executor
        # Should not raise
        screen.execute_command("open_browser")
        screen.execute_command("copy_prepare")
        screen.execute_command("close_plan")
        screen.execute_command("submit_to_queue")
        screen.execute_command("land_pr")
        screen.execute_command("fix_conflicts_remote")
        screen.execute_command("copy_close_plan")
        screen.execute_command("copy_fix_conflicts_remote")
        screen.execute_command("copy_address_remote")
