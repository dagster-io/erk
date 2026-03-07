"""Command palette action handlers for TUI application."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from erk.tui.commands.registry import get_copy_text
from erk.tui.commands.types import CommandContext
from erk.tui.screens.one_shot_prompt_screen import OneShotPromptScreen
from erk.tui.screens.plan_input_screen import PlanInputScreen

if TYPE_CHECKING:
    from erk.tui.app import ErkDashApp


class PaletteActionsMixin:
    """Mixin providing command palette execution and one-shot prompt handling.

    Includes execute_palette_command, action_one_shot_prompt,
    and related helpers.
    """

    def execute_palette_command(self: ErkDashApp, command_id: str) -> None:
        """Execute a command from the palette on the selected row.

        Args:
            command_id: The ID of the command to execute
        """
        row = self._get_selected_row()
        if row is None:
            return

        if command_id == "open_browser":
            url = row.pr_url or row.plan_url
            if url:
                self._service.browser.launch(url)
                self.notify(f"Opened {url}")

        elif command_id == "open_issue":
            if row.plan_url:
                self._service.browser.launch(row.plan_url)
                self.notify(f"Opened plan #{row.plan_id}")

        elif command_id == "open_pr":
            if row.pr_url:
                self._service.browser.launch(row.pr_url)
                self.notify(f"Opened PR #{row.pr_number}")

        elif command_id == "open_run":
            if row.run_url:
                self._service.browser.launch(row.run_url)
                self.notify(f"Opened run {row.run_id_display}")

        elif command_id == "copy_checkout":
            self._copy_checkout_command(row)

        elif command_id in (
            "copy_pr_checkout_script",
            "copy_pr_checkout_plain",
            "copy_teleport",
            "copy_teleport_new_slot",
        ):
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                self._service.clipboard.copy(text)
                self.notify(f"Copied: {text}")

        elif command_id == "copy_implement_local":
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                self._service.clipboard.copy(text)
                self.notify(f"Copied: {text}")

        elif command_id == "copy_dispatch":
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                self._service.clipboard.copy(text)
                self.notify(f"Copied: {text}")

        elif command_id == "copy_replan":
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                self._service.clipboard.copy(text)
                self.notify(f"Copied: {text}")

        elif command_id == "copy_land":
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                self._service.clipboard.copy(text)
                self.notify(f"Copied: {text}")

        elif command_id == "copy_close_plan":
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                self._service.clipboard.copy(text)
                self.notify(f"Copied: {text}")

        elif command_id == "copy_rebase_remote":
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                self._service.clipboard.copy(text)
                self.notify(f"Copied: {text}")

        elif command_id == "copy_address_remote":
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                self._service.clipboard.copy(text)
                self.notify(f"Copied: {text}")

        elif command_id == "copy_rewrite_remote":
            if row.pr_number is not None:
                cmd = f"erk launch pr-rewrite --pr {row.pr_number}"
                self._service.clipboard.copy(cmd)
                self.notify(f"Copied: {cmd}")

        elif command_id in ("copy_cmux_checkout", "copy_cmux_teleport"):
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                self._service.clipboard.copy(text)
                self.notify(f"Copied: {text}")

        elif command_id == "cmux_checkout":
            if row.pr_number and row.pr_head_branch:
                op_id = f"cmux-checkout-{row.pr_number}"
                self._start_operation(
                    op_id=op_id,
                    label=f"Creating cmux workspace for PR #{row.pr_number}...",
                )
                self._cmux_checkout_async(op_id, row.pr_number, row.pr_head_branch)

        elif command_id == "cmux_teleport":
            if row.pr_number and row.pr_head_branch:
                op_id = f"cmux-teleport-{row.pr_number}"
                self._start_operation(
                    op_id=op_id,
                    label=f"Creating cmux workspace (teleport) for PR #{row.pr_number}...",
                )
                self._cmux_checkout_async(
                    op_id, row.pr_number, row.pr_head_branch, teleport=True
                )

        elif command_id == "rebase_remote":
            if row.pr_number:
                op_id = f"rebase-pr-{row.pr_number}"
                self._start_operation(
                    op_id=op_id,
                    label=f"Dispatching rebase for PR #{row.pr_number}...",
                )
                self._rebase_remote_async(op_id, row.pr_number)

        elif command_id == "address_remote":
            if row.pr_number:
                op_id = f"address-pr-{row.pr_number}"
                self._start_operation(
                    op_id=op_id, label=f"Dispatching address for PR #{row.pr_number}..."
                )
                self._address_remote_async(op_id, row.pr_number)

        elif command_id == "rewrite_remote":
            if row.pr_number:
                op_id = f"rewrite-pr-{row.pr_number}"
                self._start_operation(
                    op_id=op_id,
                    label=f"Dispatching rewrite for PR #{row.pr_number}...",
                )
                self._rewrite_remote_async(op_id, row.pr_number)

        elif command_id == "close_plan":
            if row.plan_url:
                op_id = f"close-plan-{row.plan_id}"
                self._start_operation(op_id=op_id, label=f"Closing plan #{row.plan_id}...")
                self._close_plan_async(op_id, row.plan_id, row.plan_url)

        elif command_id == "dispatch_to_queue":
            if row.plan_url:
                op_id = f"dispatch-plan-{row.plan_id}"
                self._start_operation(
                    op_id=op_id, label=f"Dispatching plan #{row.plan_id} to queue..."
                )
                self._dispatch_to_queue_async(op_id, row.plan_id)

        elif command_id == "land_pr":
            if row.pr_number and row.pr_head_branch:
                op_id = f"land-pr-{row.pr_number}"
                self._start_operation(op_id=op_id, label=f"Landing PR #{row.pr_number}...")
                plan_id = row.plan_id if not row.is_learn_plan else None
                self._land_pr_async(
                    op_id=op_id,
                    pr_number=row.pr_number,
                    branch=row.pr_head_branch,
                    objective_issue=row.objective_issue,
                    plan_id=plan_id,
                )

        elif command_id == "incremental_dispatch":
            if row.pr_number:
                self._pending_dispatch_pr = row.pr_number
                self.push_screen(
                    PlanInputScreen(pr_number=row.pr_number),
                    self._on_incremental_dispatch_result,
                )

        elif command_id == "copy_replan":
            cmd = f"/erk:replan {row.plan_id}"
            self._service.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        # === OBJECTIVE COMMANDS ===
        elif command_id == "copy_plan":
            cmd = f"erk objective plan {row.plan_id}"
            self._service.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_view":
            cmd = f"erk objective view {row.plan_id}"
            self._service.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "open_objective":
            if row.plan_url:
                self._service.browser.launch(row.plan_url)
                self.notify(f"Opened objective #{row.plan_id}")

        elif command_id == "one_shot_plan":
            op_id = f"one-shot-plan-{row.plan_id}"
            self._start_operation(
                op_id=op_id,
                label=f"Dispatching one-shot plan for objective #{row.plan_id}...",
            )
            self._one_shot_plan_async(op_id, row.plan_id)

        elif command_id == "check_objective":
            op_id = f"check-objective-{row.plan_id}"
            self._start_operation(op_id=op_id, label=f"Checking objective #{row.plan_id}...")
            self._check_objective_async(op_id, row.plan_id)

        elif command_id == "close_objective":
            op_id = f"close-objective-{row.plan_id}"
            self._start_operation(op_id=op_id, label=f"Closing objective #{row.plan_id}...")
            self._close_objective_async(op_id, row.plan_id)

        elif command_id == "codespace_run_plan":
            cmd = f"erk codespace run objective plan {row.plan_id}"
            self._service.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

    def action_one_shot_prompt(self: ErkDashApp) -> None:
        """Open the one-shot prompt modal (global -- no row selection required)."""
        self.push_screen(OneShotPromptScreen(), self._on_one_shot_prompt_result)

    def _on_one_shot_prompt_result(self: ErkDashApp, prompt_text: str | None) -> None:
        """Handle result from the one-shot prompt screen.

        Args:
            prompt_text: The user's prompt, or None if cancelled/empty
        """
        if prompt_text is None:
            return
        op_id = f"dispatch-one-shot-{time.monotonic_ns()}"
        self._start_operation(op_id=op_id, label="Dispatching one-shot prompt...")
        self._one_shot_dispatch_async(op_id, prompt_text)

    def _on_incremental_dispatch_result(self: ErkDashApp, plan_markdown: str | None) -> None:
        """Handle result from the incremental dispatch plan input screen.

        Args:
            plan_markdown: The user's plan markdown, or None if cancelled/empty
        """
        if plan_markdown is None:
            return
        pr_number = getattr(self, "_pending_dispatch_pr", None)
        if pr_number is None:
            return
        op_id = f"incremental-dispatch-pr-{pr_number}"
        self._start_operation(
            op_id=op_id,
            label=f"Dispatching incremental plan to PR #{pr_number}...",
        )
        self._incremental_dispatch_async(op_id, pr_number, plan_markdown)
