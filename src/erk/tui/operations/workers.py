"""Background worker methods for TUI operations."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from textual import work

from erk.tui.operations.logic import extract_learn_plan_number, last_output_line

if TYPE_CHECKING:
    from erk.tui.app import ErkDashApp


class BackgroundWorkersMixin:
    """Mixin providing all @work(thread=True) background worker methods.

    Methods access self._provider, self._run_streaming_operation,
    self._start_operation, self._finish_operation, self._update_operation,
    self.call_from_thread, self.notify, and self.action_refresh
    which are provided by ErkDashApp at runtime through inheritance.
    """

    @work(thread=True)
    def _close_plan_async(self: ErkDashApp, op_id: str, plan_id: int, plan_url: str) -> None:
        """Close plan in background thread with toast notifications.

        Args:
            op_id: Operation identifier for status bar tracking
            plan_id: The plan identifier
            plan_url: The plan URL
        """
        # Error boundary: catch all exceptions from the close operation to display
        # them as toast notifications rather than crashing the TUI.
        try:
            closed_prs = self._provider.close_plan(plan_id, plan_url)
            # Success toast
            if closed_prs:
                msg = f"Closed plan #{plan_id} (and {len(closed_prs)} linked PRs)"
            else:
                msg = f"Closed plan #{plan_id}"
            self.call_from_thread(self._finish_operation, op_id=op_id)
            self.call_from_thread(self.notify, msg, timeout=3)
            # Trigger data refresh
            self.call_from_thread(self.action_refresh)
        except Exception as e:
            # Error toast
            self.call_from_thread(self._finish_operation, op_id=op_id)
            self.call_from_thread(
                self.notify,
                f"Failed to close plan #{plan_id}: {e}",
                severity="error",
                timeout=5,
            )

    @work(thread=True)
    def _address_remote_async(self: ErkDashApp, op_id: str, pr_number: int) -> None:
        """Dispatch address-remote workflow in background thread with toast."""
        result = self._run_streaming_operation(
            op_id=op_id,
            command=["erk", "launch", "pr-address", "--pr", str(pr_number)],
        )
        self.call_from_thread(self._finish_operation, op_id=op_id)
        if result.success:
            metadata_updated = any(
                "Updated dispatch metadata" in line for line in result.output_lines
            )
            if metadata_updated:
                self.call_from_thread(
                    self.notify, f"Dispatched address for PR #{pr_number}", timeout=3
                )
            else:
                self.call_from_thread(
                    self.notify,
                    f"Dispatched address for PR #{pr_number} (metadata not updated)",
                    timeout=5,
                )
            self.call_from_thread(self.action_refresh)
        else:
            error_msg = last_output_line(result)
            self.call_from_thread(
                self.notify,
                f"Failed to dispatch address for PR #{pr_number}: {error_msg}",
                severity="error",
                timeout=5,
            )

    @work(thread=True)
    def _rebase_remote_async(self: ErkDashApp, op_id: str, pr_number: int) -> None:
        """Dispatch rebase workflow in background thread with toast."""
        result = self._run_streaming_operation(
            op_id=op_id,
            command=["erk", "launch", "pr-rebase", "--pr", str(pr_number)],
        )
        self.call_from_thread(self._finish_operation, op_id=op_id)
        if result.success:
            metadata_updated = any(
                "Updated dispatch metadata" in line for line in result.output_lines
            )
            if metadata_updated:
                self.call_from_thread(
                    self.notify,
                    f"Dispatched rebase for PR #{pr_number}",
                    timeout=3,
                )
            else:
                self.call_from_thread(
                    self.notify,
                    f"Dispatched rebase for PR #{pr_number} (metadata not updated)",
                    timeout=5,
                )
            self.call_from_thread(self.action_refresh)
        else:
            error_msg = last_output_line(result)
            self.call_from_thread(
                self.notify,
                f"Failed to dispatch rebase for PR #{pr_number}: {error_msg}",
                severity="error",
                timeout=5,
            )

    @work(thread=True)
    def _cmux_sync_async(self: ErkDashApp, op_id: str, pr_number: int, branch: str) -> None:
        """Create cmux workspace, sync PR, and focus the workspace.

        Args:
            op_id: Operation identifier for status bar tracking
            pr_number: The PR number to checkout and sync
            branch: The PR head branch name (used to rename and focus the workspace)
        """
        result = self._run_streaming_operation(
            op_id=op_id,
            command=[
                "erk",
                "exec",
                "cmux-sync-workspace",
                "--pr",
                str(pr_number),
                "--branch",
                branch,
            ],
        )
        self.call_from_thread(self._finish_operation, op_id=op_id)
        if result.success:
            self._cmux_focus_workspace(branch)
            self.call_from_thread(
                self.notify,
                f"Created and focused cmux workspace for PR #{pr_number}",
                timeout=3,
            )
            self.call_from_thread(self.action_refresh)
        else:
            error_msg = last_output_line(result)
            self.call_from_thread(
                self.notify,
                f"Failed to create cmux workspace for PR #{pr_number}: {error_msg}",
                severity="error",
                timeout=5,
            )

    def _cmux_focus_workspace(self: ErkDashApp, branch: str) -> None:
        """Focus the cmux workspace matching a branch name.

        Lists cmux workspaces, finds one whose title matches the branch,
        and selects it. Both cmux calls are fast Unix socket operations.
        Called from a background thread -- does not need @work decorator.

        Args:
            branch: The branch name to match against workspace titles
        """
        import shutil

        if shutil.which("cmux") is None:
            return

        list_result = subprocess.run(
            ["cmux", "--json", "list-workspaces"],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        if list_result.returncode != 0 or not list_result.stdout:
            return

        try:
            data = json.loads(list_result.stdout)
        except json.JSONDecodeError:
            return

        if not isinstance(data, dict):
            return
        workspaces = data.get("workspaces", [])
        matching = [ws for ws in workspaces if ws.get("title") == branch]
        if not matching:
            return

        ref = matching[0].get("ref")
        if ref is None:
            return

        subprocess.run(
            ["cmux", "select-workspace", "--workspace", ref],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )

    @work(thread=True)
    def _rewrite_remote_async(self: ErkDashApp, op_id: str, pr_number: int) -> None:
        """Dispatch rewrite workflow in background thread with toast."""
        result = self._run_streaming_operation(
            op_id=op_id,
            command=["erk", "launch", "pr-rewrite", "--pr", str(pr_number)],
        )
        self.call_from_thread(self._finish_operation, op_id=op_id)
        if result.success:
            metadata_updated = any(
                "Updated dispatch metadata" in line for line in result.output_lines
            )
            if metadata_updated:
                self.call_from_thread(
                    self.notify,
                    f"Dispatched rewrite for PR #{pr_number}",
                    timeout=3,
                )
            else:
                self.call_from_thread(
                    self.notify,
                    f"Dispatched rewrite for PR #{pr_number} (metadata not updated)",
                    timeout=5,
                )
            self.call_from_thread(self.action_refresh)
        else:
            error_msg = last_output_line(result)
            self.call_from_thread(
                self.notify,
                f"Failed to dispatch rewrite for PR #{pr_number}: {error_msg}",
                severity="error",
                timeout=5,
            )

    @work(thread=True)
    def _land_pr_async(
        self: ErkDashApp,
        *,
        op_id: str,
        pr_number: int,
        branch: str,
        objective_issue: int | None,
        plan_id: int | None,
    ) -> None:
        """Land PR in background thread with toast."""
        command = [
            "erk",
            "exec",
            "land-execute",
            f"--pr-number={pr_number}",
            f"--branch={branch}",
            "-f",
        ]
        if plan_id is not None:
            command.append(f"--plan-number={plan_id}")
        result = self._run_streaming_operation(
            op_id=op_id,
            command=command,
        )
        if not result.success:
            error_msg = last_output_line(result)
            self.call_from_thread(self._finish_operation, op_id=op_id)
            self.call_from_thread(
                self.notify,
                f"Failed to land PR #{pr_number}: {error_msg}",
                severity="error",
                timeout=5,
            )
            return

        self.call_from_thread(self.notify, f"Landed PR #{pr_number}", timeout=3)
        learn_pr = extract_learn_plan_number(result)
        if learn_pr is not None:
            self.call_from_thread(self.notify, f"Created learn plan #{learn_pr}", timeout=3)
        self.call_from_thread(self.action_refresh)

        if objective_issue is not None:
            self.call_from_thread(
                self._update_operation,
                op_id=op_id,
                progress=f"Updating objective #{objective_issue}...",
            )
            obj_result = self._run_streaming_operation(
                op_id=op_id,
                command=[
                    "erk",
                    "exec",
                    "objective-update-after-land",
                    f"--objective={objective_issue}",
                    f"--pr={pr_number}",
                    f"--branch={branch}",
                ],
            )
            if obj_result.success:
                self.call_from_thread(
                    self.notify, f"Updated objective #{objective_issue}", timeout=3
                )
            else:
                error_msg = last_output_line(obj_result)
                self.call_from_thread(
                    self.notify,
                    f"Failed to update objective #{objective_issue}: {error_msg}",
                    severity="error",
                    timeout=5,
                )

        self.call_from_thread(self._finish_operation, op_id=op_id)

    @work(thread=True)
    def _dispatch_to_queue_async(self: ErkDashApp, op_id: str, plan_id: int) -> None:
        """Dispatch plan to queue in background thread with toast."""
        result = self._run_streaming_operation(
            op_id=op_id,
            command=["erk", "pr", "dispatch", str(plan_id)],
        )
        self.call_from_thread(self._finish_operation, op_id=op_id)
        if result.success:
            self.call_from_thread(self.notify, f"Dispatched plan #{plan_id} to queue", timeout=3)
            self.call_from_thread(self.action_refresh)
        else:
            error_msg = last_output_line(result)
            self.call_from_thread(
                self.notify,
                f"Failed to dispatch plan #{plan_id}: {error_msg}",
                severity="error",
                timeout=5,
            )

    @work(thread=True)
    def _close_objective_async(self: ErkDashApp, op_id: str, plan_id: int) -> None:
        """Close objective in background thread with toast."""
        result = self._run_streaming_operation(
            op_id=op_id,
            command=["erk", "objective", "close", str(plan_id), "--force"],
        )
        self.call_from_thread(self._finish_operation, op_id=op_id)
        if result.success:
            self.call_from_thread(self.notify, f"Closed objective #{plan_id}", timeout=3)
            self.call_from_thread(self.action_refresh)
        else:
            error_msg = last_output_line(result)
            self.call_from_thread(
                self.notify,
                f"Failed to close objective #{plan_id}: {error_msg}",
                severity="error",
                timeout=5,
            )

    @work(thread=True)
    def _check_objective_async(self: ErkDashApp, op_id: str, plan_id: int) -> None:
        """Check objective in background thread with toast."""
        result = self._run_streaming_operation(
            op_id=op_id,
            command=["erk", "objective", "check", str(plan_id)],
        )
        self.call_from_thread(self._finish_operation, op_id=op_id)
        if result.success:
            self.call_from_thread(self.notify, f"Checked objective #{plan_id}", timeout=3)
        else:
            error_msg = last_output_line(result)
            self.call_from_thread(
                self.notify,
                f"Failed to check objective #{plan_id}: {error_msg}",
                severity="error",
                timeout=5,
            )

    @work(thread=True)
    def _one_shot_plan_async(self: ErkDashApp, op_id: str, plan_id: int) -> None:
        """Dispatch one-shot plan in background thread with toast."""
        result = self._run_streaming_operation(
            op_id=op_id,
            command=["erk", "objective", "plan", str(plan_id), "--one-shot"],
        )
        self.call_from_thread(self._finish_operation, op_id=op_id)
        if result.success:
            self.call_from_thread(
                self.notify, f"Dispatched one-shot plan for objective #{plan_id}", timeout=3
            )
            self.call_from_thread(self.action_refresh)
        else:
            error_msg = last_output_line(result)
            self.call_from_thread(
                self.notify,
                f"Failed to dispatch one-shot plan for objective #{plan_id}: {error_msg}",
                severity="error",
                timeout=5,
            )

    @work(thread=True)
    def _one_shot_dispatch_async(self: ErkDashApp, op_id: str, prompt_text: str) -> None:
        """Dispatch one-shot prompt in background thread with toast."""
        result = self._run_streaming_operation(
            op_id=op_id,
            command=["erk", "one-shot", prompt_text],
        )
        self.call_from_thread(self._finish_operation, op_id=op_id)
        if result.success:
            self.call_from_thread(self.notify, "One-shot dispatched", timeout=3)
            self.call_from_thread(self.action_refresh)
        else:
            error_msg = last_output_line(result)
            self.call_from_thread(
                self.notify,
                f"One-shot dispatch failed: {error_msg}",
                severity="error",
                timeout=5,
            )

    @work(thread=True)
    def _load_activity_and_resort(self: ErkDashApp) -> None:
        """Load branch activity in background, then resort."""
        self._activity_loading = True

        # Fetch activity data
        activity = self._provider.fetch_branch_activity(self._all_rows)

        # Update on main thread
        self.app.call_from_thread(self._on_activity_loaded, activity)
