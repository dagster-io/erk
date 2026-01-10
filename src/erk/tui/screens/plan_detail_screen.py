"""Modal screen showing detailed plan information as an Action Hub."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import Label

from erk.tui.commands.executor import CommandExecutor
from erk.tui.commands.provider import PlanCommandProvider
from erk.tui.data.types import PlanRowData
from erk.tui.widgets.clickable_link import ClickableLink
from erk.tui.widgets.command_output import CommandOutputPanel
from erk.tui.widgets.copyable_label import CopyableLabel

if TYPE_CHECKING:
    from erk_shared.gateway.browser.abc import BrowserLauncher
    from erk_shared.gateway.clipboard.abc import Clipboard


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
        Binding("e", "copy_pr_checkout", "PR Checkout"),
        Binding("y", "copy_output_logs", "Copy Logs"),
        Binding("1", "copy_implement", "Implement"),
        Binding("2", "copy_implement_dangerous", "Dangerous"),
        Binding("3", "copy_implement_yolo", "Yolo"),
        Binding("4", "copy_submit", "Submit"),
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
    """

    def __init__(
        self,
        *,
        row: PlanRowData,
        clipboard: Clipboard | None = None,
        browser: BrowserLauncher | None = None,
        executor: CommandExecutor | None = None,
        repo_root: Path | None = None,
        auto_open_palette: bool = False,
    ) -> None:
        """Initialize with plan row data.

        Args:
            row: PlanRowData containing all plan information
            clipboard: Optional clipboard interface for copy operations
            browser: Optional browser launcher interface for opening URLs
            executor: Optional command executor for palette commands
            repo_root: Path to repository root for running commands
            auto_open_palette: If True, open command palette on mount
        """
        super().__init__()
        self._row = row
        self._clipboard = clipboard
        self._browser = browser
        self._executor = executor
        self._repo_root = repo_root
        self._output_panel: CommandOutputPanel | None = None
        self._command_running = False
        self._auto_open_palette = auto_open_palette
        self._running_process: subprocess.Popen[str] | None = None
        self._stream_timeout_timer: Timer | None = None

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
        elif self._row.issue_url:
            self._browser.launch(self._row.issue_url)

    def action_open_issue(self) -> None:
        """Open the issue in browser."""
        if self._browser is None:
            return
        if self._row.issue_url:
            self._browser.launch(self._row.issue_url)

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
        cmd = f"erk br co {self._row.worktree_branch}"
        self._copy_and_notify(cmd)

    def action_copy_pr_checkout(self) -> None:
        """Copy PR checkout command to clipboard."""
        if self._row.pr_number is not None:
            cmd = f"erk pr co {self._row.pr_number}"
            self._copy_and_notify(cmd)

    def action_copy_implement(self) -> None:
        """Copy basic implement command to clipboard."""
        cmd = f"erk implement {self._row.issue_number}"
        self._copy_and_notify(cmd)

    def action_copy_implement_dangerous(self) -> None:
        """Copy implement --dangerous command to clipboard."""
        cmd = f"erk implement {self._row.issue_number} --dangerous"
        self._copy_and_notify(cmd)

    def action_copy_implement_yolo(self) -> None:
        """Copy implement --yolo command to clipboard."""
        cmd = f"erk implement {self._row.issue_number} --yolo"
        self._copy_and_notify(cmd)

    def action_copy_submit(self) -> None:
        """Copy submit command to clipboard."""
        cmd = f"erk plan submit {self._row.issue_number}"
        self._copy_and_notify(cmd)

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
    ) -> None:
        """Run command with live output in bottom panel.

        Args:
            command: Command to run as list of arguments
            cwd: Working directory for the command
            title: Title to display in the output panel
            timeout: Timeout in seconds (default 30). Set to 0 to disable.
        """
        # Create and mount output panel
        self._output_panel = CommandOutputPanel(title)
        dialog = self.query_one("#detail-dialog")
        dialog.mount(self._output_panel)
        self._command_running = True

        # Set timeout timer if enabled
        if timeout > 0:
            self._stream_timeout_timer = self.set_timer(timeout, self._handle_stream_timeout)

        # Run subprocess in worker thread
        self._stream_subprocess(command, cwd)

    def run_close_plan_in_process(
        self,
        issue_number: int,
        issue_url: str,
    ) -> None:
        """Run close plan in-process using HTTP client directly.

        This is much faster than spawning a subprocess because it uses
        the HTTP client that was initialized at TUI startup.

        Args:
            issue_number: The issue number to close
            issue_url: The issue URL for PR linkage lookup
        """
        # Create and mount output panel
        title = f"Closing Plan #{issue_number}"
        self._output_panel = CommandOutputPanel(title)
        dialog = self.query_one("#detail-dialog")
        dialog.mount(self._output_panel)
        self._command_running = True

        # Run in-process worker (no timeout needed - HTTP has its own timeout)
        self._run_close_plan_worker(issue_number, issue_url)

    @work(thread=True)
    def _run_close_plan_worker(
        self,
        issue_number: int,
        issue_url: str,
    ) -> None:
        """Worker: close plan using executor's close_plan_fn.

        Args:
            issue_number: The issue number to close
            issue_url: The issue URL for PR linkage lookup
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
            closed_prs = self._executor.close_plan(issue_number, issue_url)

            if closed_prs:
                pr_list = ", ".join(f"#{pr}" for pr in closed_prs)
                self.app.call_from_thread(panel.append_line, f"Closed PRs: {pr_list}")

            self.app.call_from_thread(panel.append_line, f"Closed plan #{issue_number}")
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
            panel.append_line("⏱️  Command timed out after 30 seconds")
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
            url = row.pr_url or row.issue_url
            if url:
                executor.open_url(url)
                executor.notify(f"Opened {url}")

        elif command_id == "open_issue":
            if row.issue_url:
                executor.open_url(row.issue_url)
                executor.notify(f"Opened issue #{row.issue_number}")

        elif command_id == "open_pr":
            if row.pr_url:
                executor.open_url(row.pr_url)
                executor.notify(f"Opened PR #{row.pr_number}")

        elif command_id == "open_run":
            if row.run_url:
                executor.open_url(row.run_url)
                executor.notify(f"Opened run {row.run_id_display}")

        elif command_id == "copy_checkout":
            cmd = f"erk br co {row.worktree_branch}"
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}")

        elif command_id == "copy_pr_checkout":
            cmd = f"erk pr co {row.pr_number}"
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}")

        elif command_id == "copy_implement":
            cmd = f"erk implement {row.issue_number}"
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}")

        elif command_id == "copy_implement_dangerous":
            cmd = f"erk implement {row.issue_number} --dangerous"
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}")

        elif command_id == "copy_implement_yolo":
            cmd = f"erk implement {row.issue_number} --yolo"
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}")

        elif command_id == "copy_submit":
            cmd = f"erk plan submit {row.issue_number}"
            executor.copy_to_clipboard(cmd)
            executor.notify(f"Copied: {cmd}")

        elif command_id == "close_plan":
            if row.issue_url:
                # Dismiss detail screen first, then run async close on main app
                self.dismiss()
                # Access parent app and trigger async close with toast
                if isinstance(self.app, ErkDashApp):
                    self.app.notify(f"Closing plan #{row.issue_number}...")
                    self.app._close_plan_async(row.issue_number, row.issue_url)

        elif command_id == "submit_to_queue":
            if row.issue_url and self._repo_root is not None:
                # Use streaming output for submit command
                self.run_streaming_command(
                    ["erk", "plan", "submit", str(row.issue_number)],
                    cwd=self._repo_root,
                    title=f"Submitting Plan #{row.issue_number}",
                )
                # Don't dismiss - user must press Esc after completion

        elif command_id == "land_pr":
            if row.pr_number and self._repo_root is not None:
                self.run_streaming_command(
                    ["erk", "land", str(row.pr_number), "--script"],
                    cwd=self._repo_root,
                    title=f"Landing PR #{row.pr_number}",
                )

    def compose(self) -> ComposeResult:
        """Create detail dialog content as an Action Hub."""
        with Vertical(id="detail-dialog"):
            # Header: Plan number + title
            with Vertical(id="detail-header"):
                plan_text = f"Plan #{self._row.issue_number}"
                yield Label(plan_text, id="detail-plan-link")
                yield Label(self._row.full_title, id="detail-title", markup=False)

            # Divider
            yield Label("", id="detail-divider")

            # ISSUE/PR INFO SECTION
            # Issue Info - clickable issue number
            with Container(classes="info-row"):
                yield Label("Issue", classes="info-label")
                if self._row.issue_url:
                    yield ClickableLink(
                        f"#{self._row.issue_number}", self._row.issue_url, classes="info-value"
                    )
                else:
                    yield Label(f"#{self._row.issue_number}", classes="info-value", markup=False)

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
                pr_checkout_cmd = f"erk pr co {self._row.pr_number}"
                with Container(classes="command-row"):
                    yield CopyableLabel(pr_checkout_cmd, pr_checkout_cmd)

            # Implement commands
            implement_cmd = f"erk implement {self._row.issue_number}"
            with Container(classes="command-row"):
                yield Label("[1]", classes="command-key")
                yield CopyableLabel(implement_cmd, implement_cmd)

            dangerous_cmd = f"erk implement {self._row.issue_number} --dangerous"
            with Container(classes="command-row"):
                yield Label("[2]", classes="command-key")
                yield CopyableLabel(dangerous_cmd, dangerous_cmd)

            yolo_cmd = f"erk implement {self._row.issue_number} --yolo"
            with Container(classes="command-row"):
                yield Label("[3]", classes="command-key")
                yield CopyableLabel(yolo_cmd, yolo_cmd)

            # Submit command
            submit_cmd = f"erk plan submit {self._row.issue_number}"
            with Container(classes="command-row"):
                yield Label("[4]", classes="command-key")
                yield CopyableLabel(submit_cmd, submit_cmd)

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
