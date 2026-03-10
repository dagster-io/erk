"""Modal screen showing detailed plan information as an Action Hub."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import Label

from erk.tui.commands.provider import PlanCommandProvider
from erk.tui.commands.registry import get_copy_text
from erk.tui.commands.types import CommandContext
from erk.tui.data.types import PrRowData
from erk.tui.views.types import ViewMode
from erk.tui.widgets.clickable_link import ClickableLink
from erk.tui.widgets.command_output import CommandOutputPanel
from erk.tui.widgets.copyable_label import CopyableLabel
from erk_shared.gateway.command_executor.abc import CommandExecutor

if TYPE_CHECKING:
    from erk_shared.gateway.browser.abc import BrowserLauncher
    from erk_shared.gateway.clipboard.abc import Clipboard


def _extract_repo_base_url(pr_url: str) -> str:
    """Extract repository base URL from a plan URL.

    Handles both /pull/ (new plan-as-PR format) and /issues/ (legacy).
    """
    if "/pull/" in pr_url:
        return pr_url.rsplit("/pull/", 1)[0]
    return pr_url.rsplit("/issues/", 1)[0]


class PlanDetailScreen(ModalScreen):
    """Modal screen showing detailed plan information as an Action Hub."""

    COMMANDS = {PlanCommandProvider}  # Register command provider for palette

    BINDINGS = [
        # Navigation
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("space", "dismiss", "Close"),
        # Links section
        Binding("o", "open_browser", "Open"),
        Binding("i", "open_issue", "Issue"),
        Binding("p", "open_pr", "PR"),
        Binding("r", "open_run", "Run"),
        # Copy section
        Binding("c", "copy_checkout", "Checkout"),
        Binding("e", "copy_pr_checkout_script", "PR Checkout"),
        Binding("y", "copy_output_logs", "Copy Logs"),
        Binding("1", "copy_prepare", "Prepare"),
        Binding("4", "copy_prepare_activate", "Activate"),
        Binding("2", "copy_implement_local", "Implement Local"),
        Binding("3", "copy_dispatch", "Dispatch"),
        Binding("5", "rebase_remote", "Rebase"),
    ]

    DEFAULT_CSS = """
    PlanDetailScreen {
        align: center middle;
    }

    #detail-dialog {
        width: 80%;
        max-width: 120;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #detail-header {
        width: 100%;
        height: auto;
    }

    #detail-plan-link {
        text-style: bold;
    }

    #detail-title {
        color: $text;
    }

    .status-badge {
        margin-left: 1;
        padding: 0 1;
    }

    .badge-open {
        background: #238636;
        color: white;
    }

    .badge-closed {
        background: #8957e5;
        color: white;
    }

    .badge-merged {
        background: #8957e5;
        color: white;
    }

    .badge-pr {
        background: $primary;
        color: white;
    }

    .badge-success {
        background: #238636;
        color: white;
    }

    .badge-failure {
        background: #da3633;
        color: white;
    }

    .badge-pending {
        background: #9e6a03;
        color: white;
    }

    .badge-local {
        background: #58a6ff;
        color: black;
        text-style: bold;
    }

    .badge-dim {
        background: $surface-lighten-1;
        color: $text-muted;
    }

    #detail-divider {
        height: 1;
        background: $primary-darken-2;
    }

    .info-row {
        layout: horizontal;
        height: 1;
    }

    .info-label {
        color: $text-muted;
        width: 12;
    }

    .info-value {
        color: $text;
        min-width: 20;
    }

    .copyable-row {
        layout: horizontal;
        height: 1;
    }

    .copyable-text {
        color: $text;
    }

    #detail-footer {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }

    .log-entry {
        color: $text-muted;
        margin-left: 1;
    }

    .log-section {
        margin-top: 1;
        max-height: 6;
        overflow-y: auto;
    }

    .log-header {
        color: $text-muted;
        text-style: italic;
    }

    .section-header {
        color: $text-muted;
        text-style: bold italic;
        margin-top: 1;
    }

    .command-row {
        layout: horizontal;
        height: 1;
    }

    .command-key {
        color: $accent;
        width: 4;
    }

    .command-text {
        color: $text;
    }

    .legend-text {
        color: $text-muted;
        margin-left: 1;
    }
    """

    def __init__(
        self,
        *,
        row: PrRowData,
        clipboard: Clipboard | None = None,
        browser: BrowserLauncher | None = None,
        executor: CommandExecutor | None = None,
        repo_root: Path | None = None,
        auto_open_palette: bool = False,
        view_mode: ViewMode,
        cmux_integration: bool = False,
    ) -> None:
        """Initialize with plan row data.

        Args:
            row: PrRowData containing all plan information
            clipboard: Optional clipboard interface for copy operations
            browser: Optional browser launcher interface for opening URLs
            executor: Optional command executor for palette commands
            repo_root: Path to repository root for running commands
            auto_open_palette: If True, open command palette on mount
            view_mode: The current view mode (for generating correct copy text)
            cmux_integration: Whether cmux workspace integration is enabled
        """
        super().__init__()
        self._row = row
        self._clipboard = clipboard
        self._browser = browser
        self._executor = executor
        self._repo_root = repo_root
        self._view_mode = view_mode
        self._cmux_integration = cmux_integration
        self._output_panel: CommandOutputPanel | None = None
        self._command_running = False
        self._auto_open_palette = auto_open_palette
        self._running_process: subprocess.Popen[str] | None = None
        self._stream_timeout_timer: Timer | None = None
        self._stream_timeout_seconds: float = 0.0
        self._on_success_callback: Callable[[], None] | None = None

    def on_mount(self) -> None:
        """Handle mount event - optionally open command palette."""
        if self._auto_open_palette:
            # Use call_after_refresh to ensure screen is fully active
            # before opening command palette
            self.call_after_refresh(self.app.action_command_palette)

    def _get_pr_state_badge(self) -> tuple[str, str]:
        """Get PR state display text and CSS class."""
        state = self._row.pr_state
        if state == "MERGED":
            return ("MERGED", "badge-merged")
        elif state == "CLOSED":
            return ("CLOSED", "badge-closed")
        elif state == "OPEN":
            return ("OPEN", "badge-open")
        return ("PR", "badge-pr")

    def _get_run_badge(self) -> tuple[str, str]:
        """Get workflow run display text and CSS class."""
        if not self._row.run_status:
            return ("No runs", "badge-dim")

        conclusion = self._row.run_conclusion
        if conclusion == "success":
            return ("✓ Passed", "badge-success")
        elif conclusion == "failure":
            return ("✗ Failed", "badge-failure")
        elif conclusion == "cancelled":
            return ("Cancelled", "badge-dim")
        elif self._row.run_status == "in_progress":
            return ("Running...", "badge-pending")
        elif self._row.run_status == "queued":
            return ("Queued", "badge-pending")
        return (self._row.run_status, "badge-dim")

    def action_open_browser(self) -> None:
        """Open the plan (PR if available, otherwise issue) in browser."""
        if self._browser is None:
            return
        if self._row.pr_url:
            self._browser.launch(self._row.pr_url)

    def action_open_issue(self) -> None:
        """Open the issue in browser."""
        if self._browser is None:
            return
        if self._row.pr_url:
            self._browser.launch(self._row.pr_url)

    def action_open_pr(self) -> None:
        """Open the PR in browser."""
        if self._browser is None:
            return
        if self._row.pr_url:
            self._browser.launch(self._row.pr_url)

    def action_open_run(self) -> None:
        """Open the workflow run in browser."""
        if self._browser is None:
            return
        if self._row.run_url:
            self._browser.launch(self._row.run_url)

    def _copy_and_notify(self, text: str) -> None:
        """Copy text to clipboard and show notification.

        Args:
            text: Text to copy to clipboard
        """
        if self._clipboard is not None:
            self._clipboard.copy(text)
        # Show brief notification via app's notify method
        self.notify(f"Copied: {text}", timeout=2)

    def action_copy_checkout(self) -> None:
        """Copy local checkout command to clipboard."""
        if self._row.worktree_branch is None:
            self.notify(
                "No branch associated with this plan is checked out in a local worktree",
                severity="warning",
            )
            return
        cmd = f"erk br co {self._row.worktree_branch}"
        self._copy_and_notify(cmd)

    def action_copy_pr_checkout_script(self) -> None:
        """Copy PR checkout (with cd) command to clipboard."""
        ctx = CommandContext(
            row=self._row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
        )
        text = get_copy_text("copy_pr_checkout_script", ctx)
        if text is not None:
            self._copy_and_notify(text)

    def action_copy_prepare(self) -> None:
        """Copy basic prepare command to clipboard."""
        cmd = f"erk br co --for-plan {self._row.pr_number}"
        self._copy_and_notify(cmd)

    def action_copy_prepare_activate(self) -> None:
        """Copy one-liner to prepare worktree and start implementation."""
        cmd = (
            f'source "$(erk br co --for-plan {self._row.pr_number} --script)"'
            " && erk implement --dangerous"
        )
        self._copy_and_notify(cmd)

    def action_copy_implement_local(self) -> None:
        """Copy one-liner to checkout PR and start local implementation."""
        if self._row.pr_number is not None:
            cmd = (
                f'source "$(erk pr checkout {self._row.pr_number} --script)"'
                " && erk implement --dangerous"
            )
            self._copy_and_notify(cmd)

    def action_copy_dispatch(self) -> None:
        """Copy dispatch command to clipboard."""
        cmd = f"erk pr dispatch {self._row.pr_number}"
        self._copy_and_notify(cmd)

    def action_rebase_remote(self) -> None:
        """Launch remote rebase workflow."""
        from erk.tui.app import ErkDashApp

        if self._row.pr_number is None or self._repo_root is None:
            return
        self.dismiss()
        if isinstance(self.app, ErkDashApp):
            op_id = f"rebase-pr-{self._row.pr_number}"
            self.app.notify(f"Dispatching rebase for PR #{self._row.pr_number}...")
            self.app._start_operation(
                op_id=op_id,
                label=f"Dispatching rebase for PR #{self._row.pr_number}...",
            )
            self.app._rebase_remote_async(op_id, self._row.pr_number)

    def action_copy_output_logs(self) -> None:
        """Copy command output logs to clipboard."""
        if self._output_panel is None:
            return
        if not self._output_panel.is_completed:
            return
        self._copy_and_notify(self._output_panel.get_output_text())

    async def action_dismiss(self, result: object = None) -> None:
        """Dismiss the modal, blocking while command is running.

        Args:
            result: Optional result to pass to dismiss (unused, for API compat)
        """
        # Block while command is running
        if self._command_running:
            return

        # If panel exists and completed, refresh data if successful
        if self._output_panel is not None:
            if self._output_panel.is_completed:
                if self._executor and self._output_panel.succeeded:
                    self._executor.refresh_data()
                await self._flush_next_callbacks()
                self.dismiss(result)
            return

        # Normal dismiss
        await self._flush_next_callbacks()
        self.dismiss(result)

    def run_streaming_command(
        self,
        command: list[str],
        cwd: Path,
        title: str,
        *,
        timeout: float = 30.0,
        on_success: Callable[[], None] | None = None,
    ) -> None:
        """Run command with live output in bottom panel.

        Args:
            command: Command to run as list of arguments
            cwd: Working directory for the command
            title: Title to display in the output panel
            timeout: Timeout in seconds (default 30). Set to 0 to disable.
            on_success: Optional callback to invoke on successful completion.
        """
        # Create and mount output panel
        self._output_panel = CommandOutputPanel(title)
        dialog = self.query_one("#detail-dialog")
        dialog.mount(self._output_panel)
        self._command_running = True
        self._on_success_callback = on_success

        # Set timeout timer if enabled
        if timeout > 0:
            self._stream_timeout_seconds = timeout
            self._stream_timeout_timer = self.set_timer(timeout, self._handle_stream_timeout)

        # Run subprocess in worker thread
        self._stream_subprocess(command, cwd)

    def run_close_pr_in_process(
        self,
        pr_number: int,
        pr_url: str,
    ) -> None:
        """Run close plan in-process using HTTP client directly.

        This is much faster than spawning a subprocess because it uses
        the HTTP client that was initialized at TUI startup.

        Args:
            pr_number: The plan identifier to close
            pr_url: The plan URL for PR linkage lookup
        """
        # Create and mount output panel
        title = f"Closing PR #{pr_number}"
        self._output_panel = CommandOutputPanel(title)
        dialog = self.query_one("#detail-dialog")
        dialog.mount(self._output_panel)
        self._command_running = True

        # Run in-process worker (no timeout needed - HTTP has its own timeout)
        self._run_close_pr_worker(pr_number, pr_url)

    @work(thread=True)
    def _run_close_pr_worker(
        self,
        pr_number: int,
        pr_url: str,
    ) -> None:
        """Worker: close plan using executor's close_pr_fn.

        Args:
            pr_number: The plan identifier to close
            pr_url: The plan URL for PR linkage lookup
        """
        panel = self._output_panel
        if panel is None or self._executor is None:
            self._command_running = False
            return

        success = True
        # Error boundary: catch all exceptions from HTTP operations to display
        # them in the output panel rather than crashing the TUI.
        try:
            self.app.call_from_thread(panel.append_line, "Closing linked PRs...")
            closed_prs = self._executor.close_plan(pr_number, pr_url)

            if closed_prs:
                pr_list = ", ".join(f"#{pr}" for pr in closed_prs)
                self.app.call_from_thread(panel.append_line, f"Closed PRs: {pr_list}")

            self.app.call_from_thread(panel.append_line, f"Closed PR #{pr_number}")
        except Exception as e:
            self.app.call_from_thread(panel.append_line, f"Error: {e}")
            success = False

        self.app.call_from_thread(panel.set_completed, success)
        self._command_running = False

    def _handle_stream_timeout(self) -> None:
        """Handle timeout of streaming command.

        Called by Textual timer when the subprocess exceeds the timeout.
        Kills the process and marks the command as failed.
        """
        # Clear timer reference since it has fired
        self._stream_timeout_timer = None

        # Check if process is still running
        process = self._running_process
        if process is None:
            return

        # Kill the process if still running (LBYL pattern)
        if process.poll() is None:
            process.kill()

        # Append timeout message to output panel
        panel = self._output_panel
        if panel is not None:
            panel.append_line("")
            # Format timeout as minutes if >= 60 seconds for readability
            timeout_secs = self._stream_timeout_seconds
            if timeout_secs >= 60:
                minutes = int(timeout_secs // 60)
                timeout_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
            else:
                timeout_str = f"{int(timeout_secs)} seconds"
            panel.append_line(f"⏱️  Command timed out after {timeout_str}")
            panel.set_completed(success=False)

        # Mark command as no longer running
        self._command_running = False

    @work(thread=True)
    def _stream_subprocess(self, command: list[str], cwd: Path) -> None:
        """Worker: stream subprocess output to panel.

        Args:
            command: Command to run
            cwd: Working directory
        """
        # Capture panel reference at start (won't be None since run_streaming_command sets it)
        panel = self._output_panel
        if panel is None:
            self._command_running = False
            return

        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

        # Store process reference for timeout handler
        self._running_process = process

        if process.stdout is not None:
            for line in process.stdout:
                self.app.call_from_thread(
                    panel.append_line,
                    line.rstrip(),
                )

        return_code = process.wait()

        # Clear process reference
        self._running_process = None

        # Cancel timeout timer if still active
        timer = self._stream_timeout_timer
        if timer is not None:
            timer.stop()
            self._stream_timeout_timer = None

        # Only mark complete if timeout handler hasn't already done so
        if self._command_running:
            success = return_code == 0
            self.app.call_from_thread(panel.set_completed, success)
            self._command_running = False
            # Invoke success callback if provided and command succeeded
            if success:
                callback = self._on_success_callback
                if callback is not None:
                    self.app.call_from_thread(callback)

    def execute_command(self, command_id: str) -> None:
        """Execute a command from the palette.

        Args:
            command_id: The ID of the command to execute
        """
        # Import here to avoid circular import at module level
        from erk.tui.app import ErkDashApp

        if self._executor is None:
            return

        row = self._row
        executor = self._executor

        if command_id == "open_browser":
            url = row.pr_url
            if url:
                executor.open_url(url)
                executor.notify(f"Opened {url}", severity=None)

        elif command_id == "open_issue":
            if row.pr_url:
                executor.open_url(row.pr_url)
                executor.notify(f"Opened plan #{row.pr_number}", severity=None)

        elif command_id == "open_pr":
            if row.pr_url:
                executor.open_url(row.pr_url)
                executor.notify(f"Opened PR #{row.pr_number}", severity=None)

        elif command_id == "open_run":
            if row.run_url:
                executor.open_url(row.run_url)
                executor.notify(f"Opened run {row.run_id_display}", severity=None)

        elif command_id == "copy_checkout":
            if row.worktree_branch is None:
                executor.notify(
                    "No branch associated with this plan is checked out in a local worktree",
                    severity="warning",
                )
                return
            cmd = f"erk br co {row.worktree_branch}"
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}", severity=None)

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
                executor.copy_to_clipboard(text)
                executor.notify(f"Copied: {text}", severity=None)

        elif command_id == "copy_prepare":
            cmd = f"erk br co --for-plan {row.pr_number}"
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}", severity=None)

        elif command_id == "copy_prepare_activate":
            cmd = (
                f'source "$(erk br co --for-plan {row.pr_number} --script)"'
                " && erk implement --dangerous"
            )
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}", severity=None)

        elif command_id == "copy_implement_local":
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                executor.copy_to_clipboard(text)
                executor.notify(f"Copied: {text}", severity=None)

        elif command_id == "copy_dispatch":
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                executor.copy_to_clipboard(text)
                executor.notify(f"Copied: {text}", severity=None)

        elif command_id == "copy_replan":
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                executor.copy_to_clipboard(text)
                executor.notify(f"Copied: {text}", severity=None)

        elif command_id == "copy_land":
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                executor.copy_to_clipboard(text)
                executor.notify(f"Copied: {text}", severity=None)

        elif command_id == "copy_close_pr":
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                executor.copy_to_clipboard(text)
                executor.notify(f"Copied: {text}", severity=None)

        elif command_id == "copy_rebase_remote":
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                executor.copy_to_clipboard(text)
                executor.notify(f"Copied: {text}", severity=None)

        elif command_id == "copy_address_remote":
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                executor.copy_to_clipboard(text)
                executor.notify(f"Copied: {text}", severity=None)

        elif command_id == "copy_rewrite_remote":
            if row.pr_number is not None:
                cmd = f"erk launch pr-rewrite --pr {row.pr_number}"
                executor.copy_to_clipboard(cmd)
                executor.notify(f"Copied: {cmd}", severity=None)

        elif command_id in ("copy_cmux_checkout", "copy_cmux_teleport"):
            ctx = CommandContext(
                row=row, view_mode=self._view_mode, cmux_integration=self._cmux_integration
            )
            text = get_copy_text(command_id, ctx)
            if text is not None:
                executor.copy_to_clipboard(text)
                executor.notify(f"Copied: {text}", severity=None)

        elif command_id == "cmux_checkout":
            if row.pr_number and row.pr_head_branch:
                self.dismiss()
                if isinstance(self.app, ErkDashApp):
                    op_id = f"cmux-checkout-{row.pr_number}"
                    self.app._start_operation(
                        op_id=op_id,
                        label=f"Creating cmux workspace for PR #{row.pr_number}...",
                    )
                    self.app._cmux_checkout_async(
                        op_id, row.pr_number, row.pr_head_branch, teleport=False
                    )

        elif command_id == "cmux_teleport":
            if row.pr_number and row.pr_head_branch:
                self.dismiss()
                if isinstance(self.app, ErkDashApp):
                    op_id = f"cmux-teleport-{row.pr_number}"
                    self.app._start_operation(
                        op_id=op_id,
                        label=f"Creating cmux workspace (teleport) for PR #{row.pr_number}...",
                    )
                    self.app._cmux_checkout_async(
                        op_id, row.pr_number, row.pr_head_branch, teleport=True
                    )

        elif command_id == "rebase_remote":
            if row.pr_number is not None:
                self.dismiss()
                if isinstance(self.app, ErkDashApp):
                    op_id = f"rebase-pr-{row.pr_number}"
                    self.app.notify(f"Dispatching rebase for PR #{row.pr_number}...")
                    self.app._start_operation(
                        op_id=op_id,
                        label=f"Dispatching rebase for PR #{row.pr_number}...",
                    )
                    self.app._rebase_remote_async(op_id, row.pr_number)

        elif command_id == "address_remote":
            if row.pr_number is not None and self._repo_root is not None:
                self.run_streaming_command(
                    ["erk", "launch", "pr-address", "--pr", str(row.pr_number)],
                    cwd=self._repo_root,
                    title=f"Address Remote PR #{row.pr_number}",
                )

        elif command_id == "rewrite_remote":
            if row.pr_number is not None:
                self.dismiss()
                if isinstance(self.app, ErkDashApp):
                    self.app.notify(f"Dispatching rewrite for PR #{row.pr_number}...")
                    op_id = f"rewrite-pr-{row.pr_number}"
                    self.app._start_operation(
                        op_id=op_id,
                        label=f"Dispatching rewrite for PR #{row.pr_number}...",
                    )
                    self.app._rewrite_remote_async(op_id, row.pr_number)

        elif command_id == "close_pr":
            if row.pr_url:
                # Dismiss detail screen first, then run async close on main app
                self.dismiss()
                # Access parent app and trigger async close with toast
                if isinstance(self.app, ErkDashApp):
                    op_id = f"close-plan-{row.pr_number}"
                    label = f"Closing plan #{row.pr_number}..."
                    self.app._start_operation(op_id=op_id, label=label)
                    self.app._close_pr_async(op_id, row.pr_number, row.pr_url)

        elif command_id == "dispatch_to_queue":
            if row.pr_url:
                self.dismiss()
                if isinstance(self.app, ErkDashApp):
                    op_id = f"dispatch-plan-{row.pr_number}"
                    self.app._start_operation(
                        op_id=op_id, label=f"Dispatching plan #{row.pr_number} to queue..."
                    )
                    self.app._dispatch_to_queue_async(op_id, row.pr_number)

        elif command_id == "land_pr":
            if row.pr_number and row.pr_head_branch:
                self.dismiss()
                if isinstance(self.app, ErkDashApp):
                    op_id = f"land-pr-{row.pr_number}"
                    self.app._start_operation(op_id=op_id, label=f"Landing PR #{row.pr_number}...")
                    self.app._land_pr_async(
                        op_id,
                        row.pr_number,
                        row.pr_head_branch,
                        row.objective_issue,
                    )

        elif command_id == "incremental_dispatch":
            if row.pr_number is not None:
                self.dismiss()
                if isinstance(self.app, ErkDashApp):
                    self.app.execute_palette_command("incremental_dispatch")

    def compose(self) -> ComposeResult:
        """Create detail dialog content as an Action Hub."""
        with Vertical(id="detail-dialog"):
            # Header: Plan number + title
            with Vertical(id="detail-header"):
                plan_text = f"Plan #{self._row.pr_number}"
                yield Label(plan_text, id="detail-plan-link")
                yield Label(self._row.full_title, id="detail-title", markup=False)

            # Divider
            yield Label("", id="detail-divider")

            # PLAN/PR INFO SECTION
            # Plan Info - clickable plan number
            with Container(classes="info-row"):
                yield Label("Plan", classes="info-label")
                if self._row.pr_url:
                    yield ClickableLink(
                        f"#{self._row.pr_number}", self._row.pr_url, classes="info-value"
                    )
                else:
                    yield Label(f"#{self._row.pr_number}", classes="info-value", markup=False)

            # PR Info (if exists) - clickable PR number with state badge inline
            if self._row.pr_number:
                with Container(classes="info-row"):
                    yield Label("PR", classes="info-label")
                    if self._row.pr_url:
                        yield ClickableLink(
                            f"#{self._row.pr_number}", self._row.pr_url, classes="info-value"
                        )
                    else:
                        yield Label(f"#{self._row.pr_number}", classes="info-value", markup=False)
                    # PR state badge inline
                    pr_text, pr_class = self._get_pr_state_badge()
                    yield Label(pr_text, classes=f"status-badge {pr_class}")

                # PR title if different from issue title
                if self._row.pr_title and self._row.pr_title != self._row.full_title:
                    with Container(classes="info-row"):
                        yield Label("PR Title", classes="info-label")
                        yield Label(self._row.pr_title, classes="info-value", markup=False)

                # Checks status
                if self._row.checks_display and self._row.checks_display != "-":
                    with Container(classes="info-row"):
                        yield Label("Checks", classes="info-label")
                        yield Label(self._row.checks_display, classes="info-value", markup=False)

            # Learn status - always show for visibility into learn workflow
            with Container(classes="info-row"):
                yield Label("Learn", classes="info-label")
                # Make clickable if there's a plan issue, PR, or workflow run
                if self._row.learn_plan_pr is not None and self._row.pr_url:
                    base_url = _extract_repo_base_url(self._row.pr_url)
                    pr_url = f"{base_url}/pull/{self._row.learn_plan_pr}"
                    yield ClickableLink(self._row.learn_display, pr_url, classes="info-value")
                elif self._row.learn_plan_issue is not None and self._row.pr_url:
                    base_url = _extract_repo_base_url(self._row.pr_url)
                    issue_url = f"{base_url}/issues/{self._row.learn_plan_issue}"
                    yield ClickableLink(self._row.learn_display, issue_url, classes="info-value")
                elif self._row.learn_run_url is not None:
                    yield ClickableLink(
                        self._row.learn_display, self._row.learn_run_url, classes="info-value"
                    )
                else:
                    yield Label(self._row.learn_display, classes="info-value", markup=False)

            # Objective info (if linked)
            if self._row.objective_issue is not None:
                with Container(classes="info-row"):
                    yield Label("Objective", classes="info-label")
                    display_text = (
                        f"{self._row.objective_display} ({self._row.objective_progress_display})"
                        if self._row.objective_progress_display != "-"
                        else self._row.objective_display
                    )
                    if self._row.pr_url:
                        objective_url = (
                            _extract_repo_base_url(self._row.pr_url)
                            + f"/issues/{self._row.objective_issue}"
                        )
                        yield ClickableLink(display_text, objective_url, classes="info-value")
                    else:
                        yield Label(display_text, classes="info-value", markup=False)

            # REMOTE RUN INFO SECTION (separate from worktree/local info)
            if self._row.run_id:
                with Container(classes="info-row"):
                    yield Label("Run", classes="info-label")
                    if self._row.run_url:
                        yield ClickableLink(
                            self._row.run_id, self._row.run_url, classes="info-value"
                        )
                    else:
                        yield Label(self._row.run_id, classes="info-value", markup=False)
                    # Run status badge inline
                    run_text, run_class = self._get_run_badge()
                    yield Label(run_text, classes=f"status-badge {run_class}")

                if self._row.remote_impl_display and self._row.remote_impl_display != "-":
                    with Container(classes="info-row"):
                        yield Label("Last remote impl", classes="info-label")
                        yield Label(
                            self._row.remote_impl_display, classes="info-value", markup=False
                        )

            # COMMANDS SECTION (copy to clipboard)
            # All items below use uniform orange labels that copy when clicked
            yield Label("COMMANDS (copy)", classes="section-header")

            # PR checkout command (if PR exists)
            if self._row.pr_number is not None:
                ctx = CommandContext(
                    row=self._row,
                    view_mode=self._view_mode,
                    cmux_integration=self._cmux_integration,
                )
                pr_checkout_cmd = get_copy_text("copy_pr_checkout_script", ctx)
                if pr_checkout_cmd:
                    with Container(classes="command-row"):
                        yield CopyableLabel(pr_checkout_cmd, pr_checkout_cmd)

            # Prepare commands
            prepare_cmd = f"erk br co --for-plan {self._row.pr_number}"
            with Container(classes="command-row"):
                yield Label("[1]", classes="command-key")
                yield CopyableLabel(prepare_cmd, prepare_cmd)

            # Submit command
            dispatch_cmd = f"erk pr dispatch {self._row.pr_number}"
            with Container(classes="command-row"):
                yield Label("[3]", classes="command-key")
                yield CopyableLabel(dispatch_cmd, dispatch_cmd)

            # Log entries (if any) - clickable timestamps
            if self._row.log_entries:
                with Vertical(classes="log-section"):
                    yield Label("Recent activity", classes="log-header")
                    for event_name, timestamp, comment_url in self._row.log_entries[:5]:
                        log_text = f"{timestamp}  {event_name}"
                        if comment_url:
                            yield ClickableLink(log_text, comment_url, classes="log-entry")
                        else:
                            yield Label(log_text, classes="log-entry", markup=False)

            yield Label("Ctrl+P: commands  Esc: close", id="detail-footer")
