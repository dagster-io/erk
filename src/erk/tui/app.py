"""Main Textual application for erk dash interactive mode."""

from __future__ import annotations

import asyncio
import subprocess
import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.markup import escape as escape_markup
from textual import on, work
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.events import Click
from textual.screen import ModalScreen, Screen
from textual.timer import Timer
from textual.widgets import Header, Input, Label, Static

from erk.tui.commands.executor import CommandExecutor
from erk.tui.commands.provider import MainListCommandProvider, PlanCommandProvider
from erk.tui.commands.real_executor import RealCommandExecutor
from erk.tui.data.provider import PlanDataProvider
from erk.tui.data.types import PlanFilters, PlanRowData
from erk.tui.filtering.logic import filter_plans
from erk.tui.filtering.types import FilterMode, FilterState
from erk.tui.sorting.logic import sort_plans
from erk.tui.sorting.types import BranchActivity, SortKey, SortState
from erk.tui.widgets.command_output import CommandOutputPanel
from erk.tui.widgets.plan_table import PlanDataTable
from erk.tui.widgets.status_bar import StatusBar

if TYPE_CHECKING:
    from erk_shared.gateway.browser.abc import BrowserLauncher
    from erk_shared.gateway.clipboard.abc import Clipboard


class ClickableLink(Static):
    """A clickable link widget that opens a URL in the browser."""

    DEFAULT_CSS = """
    ClickableLink {
        color: $primary;
        text-style: underline;
    }
    ClickableLink:hover {
        color: $primary-lighten-2;
    }
    """

    def __init__(self, text: str, url: str, **kwargs) -> None:
        """Initialize clickable link.

        Args:
            text: Display text for the link
            url: URL to open when clicked
            **kwargs: Additional widget arguments
        """
        super().__init__(escape_markup(text), **kwargs)
        self._url = url

    def on_click(self, event: Click) -> None:
        """Open URL in browser when clicked."""
        event.stop()
        # Access browser through the app's provider (ErkDashApp)
        # Use getattr to avoid circular import isinstance issues
        app: Any = self.app
        provider = getattr(app, "_provider", None)
        if provider is not None:
            browser = getattr(provider, "browser", None)
            if browser is not None:
                browser.launch(self._url)


class CopyableLabel(Static):
    """A label that copies text to clipboard when clicked, styled with orange/accent color."""

    DEFAULT_CSS = """
    CopyableLabel {
        color: $accent;
    }
    CopyableLabel:hover {
        color: $accent-lighten-1;
        text-style: bold;
    }
    """

    def __init__(self, label: str, text_to_copy: str, **kwargs) -> None:
        """Initialize copyable label.

        Args:
            label: Display text for the label (e.g., "[1]" or "erk pr co 2022")
            text_to_copy: Text to copy to clipboard when clicked
            **kwargs: Additional widget arguments
        """
        super().__init__(label, **kwargs)
        self._text_to_copy = text_to_copy
        self._original_label = label

    def on_click(self, event: Click) -> None:
        """Copy text to clipboard when clicked."""
        event.stop()
        success = self._copy_to_clipboard()
        if success:
            self.update("Copied!")
            self.set_timer(1.5, lambda: self.update(self._original_label))

    def _copy_to_clipboard(self) -> bool:
        """Copy text to clipboard, finding the clipboard interface.

        Returns:
            True if copy succeeded, False otherwise.
        """
        # Access clipboard through the app's provider (ErkDashApp)
        # Use getattr to avoid circular import isinstance issues
        app: Any = self.app
        provider = getattr(app, "_provider", None)
        if provider is not None:
            clipboard = getattr(provider, "clipboard", None)
            if clipboard is not None:
                return clipboard.copy(self._text_to_copy)
        return False


class HelpScreen(ModalScreen):
    """Modal screen showing keyboard shortcuts."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("?", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-dialog {
        width: 60;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #help-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
        width: 100%;
    }

    .help-section {
        margin-top: 1;
    }

    .help-section-title {
        text-style: bold;
        color: $primary;
    }

    .help-binding {
        margin-left: 2;
    }
    """

    def compose(self) -> ComposeResult:
        """Create help dialog content."""
        with Vertical(id="help-dialog"):
            yield Label("erk dash - Keyboard Shortcuts", id="help-title")

            with Vertical(classes="help-section"):
                yield Label("Navigation", classes="help-section-title")
                yield Label("↑/k     Move cursor up", classes="help-binding")
                yield Label("↓/j     Move cursor down", classes="help-binding")
                yield Label("Home    Jump to first row", classes="help-binding")
                yield Label("End     Jump to last row", classes="help-binding")

            with Vertical(classes="help-section"):
                yield Label("Actions", classes="help-section-title")
                yield Label("Enter   View plan details", classes="help-binding")
                yield Label("Ctrl+P  Commands (opens detail modal)", classes="help-binding")
                yield Label("o       Open PR (or issue if no PR)", classes="help-binding")
                yield Label("p       Open PR in browser", classes="help-binding")
                yield Label("i       Show implement command", classes="help-binding")

            with Vertical(classes="help-section"):
                yield Label("Filter & Sort", classes="help-section-title")
                yield Label("/       Start filter mode", classes="help-binding")
                yield Label("Esc     Clear filter / exit filter", classes="help-binding")
                yield Label("Enter   Return focus to table", classes="help-binding")
                yield Label("s       Toggle sort mode", classes="help-binding")

            with Vertical(classes="help-section"):
                yield Label("General", classes="help-section-title")
                yield Label("r       Refresh data", classes="help-binding")
                yield Label("?       Show this help", classes="help-binding")
                yield Label("q/Esc   Quit", classes="help-binding")

            yield Label("")
            yield Label("Press any key to close", id="help-footer")


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


class ErkDashApp(App):
    """Interactive TUI for erk dash command.

    Displays plans in a navigable table with quick actions.
    """

    CSS_PATH = Path(__file__).parent / "styles" / "dash.tcss"
    COMMANDS = {MainListCommandProvider}

    BINDINGS = [
        Binding("q", "exit_app", "Quit"),
        Binding("escape", "exit_app", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "help", "Help"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "show_detail", "Detail"),
        Binding("space", "show_detail", "Detail", show=False),
        Binding("o", "open_row", "Open", show=False),
        Binding("p", "open_pr", "Open PR"),
        # NOTE: 'c' binding removed - close_plan now accessible via command palette
        # in the plan detail modal (Enter → Ctrl+P → "Close Plan")
        Binding("i", "show_implement", "Implement"),
        Binding("slash", "start_filter", "Filter", key_display="/"),
        Binding("s", "toggle_sort", "Sort"),
        Binding("ctrl+p", "command_palette", "Commands"),
    ]

    def get_system_commands(self, screen: Screen) -> Iterator[SystemCommand]:
        """Return system commands, hiding them when plan commands are available.

        Hides Keys, Quit, Screenshot, Theme from command palette when on
        PlanDetailScreen or when main list has a selected row, so only
        plan-specific commands appear.
        """
        if isinstance(screen, PlanDetailScreen):
            return iter(())
        # Hide system commands on main list when a row is selected
        if self._get_selected_row() is not None:
            return iter(())
        yield from super().get_system_commands(screen)

    def __init__(
        self,
        *,
        provider: PlanDataProvider,
        filters: PlanFilters,
        refresh_interval: float = 15.0,
        initial_sort: SortState | None = None,
    ) -> None:
        """Initialize the dashboard app.

        Args:
            provider: Data provider for fetching plan data
            filters: Filter options for the plan list
            refresh_interval: Seconds between auto-refresh (0 to disable)
            initial_sort: Initial sort state (defaults to by issue number)
        """
        super().__init__()
        self._provider = provider
        self._plan_filters = filters
        self._refresh_interval = refresh_interval
        self._table: PlanDataTable | None = None
        self._status_bar: StatusBar | None = None
        self._filter_input: Input | None = None
        self._all_rows: list[PlanRowData] = []  # Unfiltered data
        self._rows: list[PlanRowData] = []  # Currently displayed (possibly filtered)
        self._refresh_task: asyncio.Task | None = None
        self._loading = True
        self._filter_state = FilterState.initial()
        self._sort_state = initial_sort if initial_sort is not None else SortState.initial()
        self._activity_by_issue: dict[int, BranchActivity] = {}
        self._activity_loading = False

    def compose(self) -> ComposeResult:
        """Create the application layout."""
        yield Header(show_clock=True)
        with Container(id="main-container"):
            yield Label("Loading plans...", id="loading-message")
            yield PlanDataTable(self._plan_filters)
        yield Input(id="filter-input", placeholder="Filter...", disabled=True)
        yield StatusBar()

    def on_mount(self) -> None:
        """Initialize app after mounting."""
        self._table = self.query_one(PlanDataTable)
        self._status_bar = self.query_one(StatusBar)
        self._filter_input = self.query_one("#filter-input", Input)
        self._loading_label = self.query_one("#loading-message", Label)

        # Hide table until loaded
        self._table.display = False

        # Start data loading
        self.run_worker(self._load_data(), exclusive=True)

        # Start refresh timer if interval > 0
        if self._refresh_interval > 0:
            self._start_refresh_timer()

    async def _load_data(self) -> None:
        """Load plan data in background thread."""
        # Track fetch timing
        start_time = time.monotonic()

        try:
            # Run sync fetch in executor to avoid blocking
            loop = asyncio.get_running_loop()
            rows = await loop.run_in_executor(None, self._provider.fetch_plans, self._plan_filters)

            # If sorting by activity, also fetch activity data
            if self._sort_state.key == SortKey.BRANCH_ACTIVITY:
                activity = await loop.run_in_executor(
                    None, self._provider.fetch_branch_activity, rows
                )
                self._activity_by_issue = activity

        except Exception as e:
            # GitHub API failure, network error, etc.
            self.notify(f"Failed to load plans: {e}", severity="error", timeout=5)
            rows = []

        # Calculate duration
        duration = time.monotonic() - start_time
        update_time = datetime.now().strftime("%H:%M:%S")

        # Update UI directly since we're in async context
        self._update_table(rows, update_time, duration)

    def _update_table(
        self,
        rows: list[PlanRowData],
        update_time: str | None = None,
        duration: float | None = None,
    ) -> None:
        """Update table with new data.

        Args:
            rows: Plan data to display
            update_time: Formatted time of this update
            duration: Duration of the fetch in seconds
        """
        self._all_rows = rows
        self._loading = False

        # Apply filter and sort
        self._rows = self._apply_filter_and_sort(rows)

        if self._table is not None:
            self._loading_label.display = False
            self._table.display = True
            self._table.populate(self._rows)

        if self._status_bar is not None:
            self._status_bar.set_plan_count(len(self._rows))
            self._status_bar.set_sort_mode(self._sort_state.display_label)
            if update_time is not None:
                self._status_bar.set_last_update(update_time, duration)

    def _apply_filter_and_sort(self, rows: list[PlanRowData]) -> list[PlanRowData]:
        """Apply current filter and sort to rows.

        Args:
            rows: Raw rows to process

        Returns:
            Filtered and sorted rows
        """
        # Apply filter first
        if self._filter_state.mode == FilterMode.ACTIVE and self._filter_state.query:
            filtered = filter_plans(rows, self._filter_state.query)
        else:
            filtered = rows

        # Apply sort
        return sort_plans(
            filtered,
            self._sort_state.key,
            self._activity_by_issue if self._sort_state.key == SortKey.BRANCH_ACTIVITY else None,
        )

    def _start_refresh_timer(self) -> None:
        """Start the auto-refresh countdown timer."""
        self._seconds_remaining = int(self._refresh_interval)
        self.set_interval(1.0, self._tick_countdown)

    def _tick_countdown(self) -> None:
        """Handle countdown timer tick."""
        if self._status_bar is not None:
            self._status_bar.set_refresh_countdown(self._seconds_remaining)

        self._seconds_remaining -= 1
        if self._seconds_remaining <= 0:
            self.action_refresh()
            self._seconds_remaining = int(self._refresh_interval)

    def action_exit_app(self) -> None:
        """Quit the application or handle progressive escape from filter mode."""
        if self._filter_state.mode == FilterMode.ACTIVE:
            self._filter_state = self._filter_state.handle_escape()
            if self._filter_state.mode == FilterMode.INACTIVE:
                # Fully exited filter mode
                self._exit_filter_mode()
            else:
                # Just cleared text, stay in filter mode
                if self._filter_input is not None:
                    self._filter_input.value = ""
                # Reset to show all rows
                self._apply_filter()
            return
        self.exit()

    def action_refresh(self) -> None:
        """Refresh plan data and reset countdown timer."""
        # Reset countdown timer
        if self._refresh_interval > 0:
            self._seconds_remaining = int(self._refresh_interval)
        self.run_worker(self._load_data(), exclusive=True)

    def action_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())

    def action_toggle_sort(self) -> None:
        """Toggle between sort modes."""
        self._sort_state = self._sort_state.toggle()

        # If switching to activity sort, load activity data in background
        if self._sort_state.key == SortKey.BRANCH_ACTIVITY and not self._activity_by_issue:
            self._load_activity_and_resort()
        else:
            # Re-sort with current data
            self._rows = self._apply_filter_and_sort(self._all_rows)
            if self._table is not None:
                self._table.populate(self._rows)

        # Update status bar
        if self._status_bar is not None:
            self._status_bar.set_sort_mode(self._sort_state.display_label)

    @work(thread=True)
    def _load_activity_and_resort(self) -> None:
        """Load branch activity in background, then resort."""
        self._activity_loading = True

        # Fetch activity data
        activity = self._provider.fetch_branch_activity(self._all_rows)

        # Update on main thread
        self.app.call_from_thread(self._on_activity_loaded, activity)

    def _on_activity_loaded(self, activity: dict[int, BranchActivity]) -> None:
        """Handle activity data loaded - resort the table."""
        self._activity_by_issue = activity
        self._activity_loading = False

        # Re-sort with new activity data
        self._rows = self._apply_filter_and_sort(self._all_rows)
        if self._table is not None:
            self._table.populate(self._rows)

    @work(thread=True)
    def _close_plan_async(self, issue_number: int, issue_url: str) -> None:
        """Close plan in background thread with toast notifications.

        Args:
            issue_number: The plan issue number
            issue_url: The GitHub issue URL
        """
        # Error boundary: catch all exceptions from the close operation to display
        # them as toast notifications rather than crashing the TUI.
        try:
            closed_prs = self._provider.close_plan(issue_number, issue_url)
            # Success toast
            if closed_prs:
                msg = f"Closed plan #{issue_number} (and {len(closed_prs)} linked PRs)"
            else:
                msg = f"Closed plan #{issue_number}"
            self.call_from_thread(self.notify, msg, timeout=3)
            # Trigger data refresh
            self.call_from_thread(self.action_refresh)
        except Exception as e:
            # Error toast
            self.call_from_thread(
                self.notify,
                f"Failed to close plan #{issue_number}: {e}",
                severity="error",
                timeout=5,
            )

    def action_show_detail(self) -> None:
        """Show plan detail modal for selected row."""
        row = self._get_selected_row()
        if row is None:
            return

        # Create executor with injected dependencies
        executor = RealCommandExecutor(
            browser_launch=self._provider.browser.launch,
            clipboard_copy=self._provider.clipboard.copy,
            close_plan_fn=self._provider.close_plan,
            notify_fn=self.notify,
            refresh_fn=self.action_refresh,
            submit_to_queue_fn=self._provider.submit_to_queue,
        )

        self.push_screen(
            PlanDetailScreen(
                row=row,
                clipboard=self._provider.clipboard,
                browser=self._provider.browser,
                executor=executor,
                repo_root=self._provider.repo_root,
            )
        )

    def action_cursor_down(self) -> None:
        """Move cursor down (vim j key)."""
        if self._table is not None:
            self._table.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up (vim k key)."""
        if self._table is not None:
            self._table.action_cursor_up()

    def action_start_filter(self) -> None:
        """Activate filter mode and focus the input."""
        if self._filter_input is None:
            return
        self._filter_state = self._filter_state.activate()
        self._filter_input.disabled = False
        self._filter_input.add_class("visible")
        self._filter_input.focus()

    def _apply_filter(self) -> None:
        """Apply current filter query to the table."""
        self._rows = self._apply_filter_and_sort(self._all_rows)

        if self._table is not None:
            self._table.populate(self._rows)

        if self._status_bar is not None:
            self._status_bar.set_plan_count(len(self._rows))

    def _exit_filter_mode(self) -> None:
        """Exit filter mode, restore all rows, and focus table."""
        if self._filter_input is not None:
            self._filter_input.value = ""
            self._filter_input.remove_class("visible")
            self._filter_input.disabled = True

        self._filter_state = FilterState.initial()
        self._rows = self._apply_filter_and_sort(self._all_rows)

        if self._table is not None:
            self._table.populate(self._rows)
            self._table.focus()

        if self._status_bar is not None:
            self._status_bar.set_plan_count(len(self._rows))

    def action_open_row(self) -> None:
        """Open selected row - PR if available, otherwise issue."""
        row = self._get_selected_row()
        if row is None:
            return

        if row.pr_url:
            self._provider.browser.launch(row.pr_url)
            if self._status_bar is not None:
                self._status_bar.set_message(f"Opened PR #{row.pr_number}")
        elif row.issue_url:
            self._provider.browser.launch(row.issue_url)
            if self._status_bar is not None:
                self._status_bar.set_message(f"Opened issue #{row.issue_number}")

    def action_open_pr(self) -> None:
        """Open selected PR in browser."""
        row = self._get_selected_row()
        if row is None:
            return

        if row.pr_url:
            self._provider.browser.launch(row.pr_url)
            if self._status_bar is not None:
                self._status_bar.set_message(f"Opened PR #{row.pr_number}")
        else:
            if self._status_bar is not None:
                self._status_bar.set_message("No PR linked to this plan")

    def action_show_implement(self) -> None:
        """Show implement command in status bar."""
        row = self._get_selected_row()
        if row is None:
            return

        cmd = f"erk implement {row.issue_number}"
        if self._status_bar is not None:
            self._status_bar.set_message(f"Copy: {cmd}")

    def action_copy_checkout(self) -> None:
        """Copy checkout command for selected row."""
        row = self._get_selected_row()
        if row is None:
            return
        self._copy_checkout_command(row)

    def action_close_plan(self) -> None:
        """Close the selected plan and its linked PRs (async with toast)."""
        row = self._get_selected_row()
        if row is None:
            return

        if row.issue_url is None:
            self.notify("Cannot close plan: no issue URL", severity="warning")
            return

        # Show starting toast and run async - no blocking
        self.notify(f"Closing plan #{row.issue_number}...")
        self._close_plan_async(row.issue_number, row.issue_url)

    def _copy_checkout_command(self, row: PlanRowData) -> None:
        """Copy appropriate checkout command based on row state.

        If worktree exists locally, copies 'erk co {worktree_name}'.
        If only PR available, copies 'erk pr co {pr_number}'.
        Shows status message with result.

        Args:
            row: The plan row data to generate command from
        """
        # Determine which command to use
        if row.worktree_branch is not None:
            # Local worktree exists - use branch checkout
            cmd = f"erk br co {row.worktree_branch}"
        elif row.pr_number is not None:
            # No local worktree but PR exists - use PR checkout
            cmd = f"erk pr co {row.pr_number}"
        else:
            # Neither available
            if self._status_bar is not None:
                self._status_bar.set_message("No worktree or PR available for checkout")
            return

        # Copy to clipboard
        success = self._provider.clipboard.copy(cmd)

        # Show status message
        if self._status_bar is not None:
            if success:
                self._status_bar.set_message(f"Copied: {cmd}")
            else:
                self._status_bar.set_message(f"Clipboard unavailable. Copy manually: {cmd}")

    def _get_selected_row(self) -> PlanRowData | None:
        """Get currently selected row data."""
        if self._table is None:
            return None
        return self._table.get_selected_row_data()

    def execute_palette_command(self, command_id: str) -> None:
        """Execute a command from the palette on the selected row.

        Args:
            command_id: The ID of the command to execute
        """
        row = self._get_selected_row()
        if row is None:
            return

        if command_id == "open_browser":
            url = row.pr_url or row.issue_url
            if url:
                self._provider.browser.launch(url)
                self.notify(f"Opened {url}")

        elif command_id == "open_issue":
            if row.issue_url:
                self._provider.browser.launch(row.issue_url)
                self.notify(f"Opened issue #{row.issue_number}")

        elif command_id == "open_pr":
            if row.pr_url:
                self._provider.browser.launch(row.pr_url)
                self.notify(f"Opened PR #{row.pr_number}")

        elif command_id == "open_run":
            if row.run_url:
                self._provider.browser.launch(row.run_url)
                self.notify(f"Opened run {row.run_id_display}")

        elif command_id == "copy_checkout":
            cmd = f"erk br co {row.worktree_branch}"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_pr_checkout":
            cmd = f"erk pr co {row.pr_number}"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_implement":
            cmd = f"erk implement {row.issue_number}"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_implement_dangerous":
            cmd = f"erk implement {row.issue_number} --dangerous"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_implement_yolo":
            cmd = f"erk implement {row.issue_number} --yolo"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "copy_submit":
            cmd = f"erk plan submit {row.issue_number}"
            self._provider.clipboard.copy(cmd)
            self.notify(f"Copied: {cmd}")

        elif command_id == "close_plan":
            if row.issue_url:
                # Show starting toast and run async - no modal blocking
                self.notify(f"Closing plan #{row.issue_number}...")
                self._close_plan_async(row.issue_number, row.issue_url)

        elif command_id == "submit_to_queue":
            if row.issue_url:
                # Open detail modal to show streaming output
                executor = RealCommandExecutor(
                    browser_launch=self._provider.browser.launch,
                    clipboard_copy=self._provider.clipboard.copy,
                    close_plan_fn=self._provider.close_plan,
                    notify_fn=self.notify,
                    refresh_fn=self.action_refresh,
                    submit_to_queue_fn=self._provider.submit_to_queue,
                )
                detail_screen = PlanDetailScreen(
                    row=row,
                    clipboard=self._provider.clipboard,
                    browser=self._provider.browser,
                    executor=executor,
                    repo_root=self._provider.repo_root,
                )
                self.push_screen(detail_screen)
                # Trigger the streaming command after screen is mounted
                detail_screen.call_after_refresh(
                    lambda: detail_screen.run_streaming_command(
                        ["erk", "plan", "submit", str(row.issue_number)],
                        cwd=self._provider.repo_root,
                        title=f"Submitting Plan #{row.issue_number}",
                    )
                )

        elif command_id == "land_pr":
            if row.pr_number:
                executor = RealCommandExecutor(
                    browser_launch=self._provider.browser.launch,
                    clipboard_copy=self._provider.clipboard.copy,
                    close_plan_fn=self._provider.close_plan,
                    notify_fn=self.notify,
                    refresh_fn=self.action_refresh,
                    submit_to_queue_fn=self._provider.submit_to_queue,
                )
                detail_screen = PlanDetailScreen(
                    row=row,
                    clipboard=self._provider.clipboard,
                    browser=self._provider.browser,
                    executor=executor,
                    repo_root=self._provider.repo_root,
                )
                self.push_screen(detail_screen)
                detail_screen.call_after_refresh(
                    lambda: detail_screen.run_streaming_command(
                        ["erk", "land", str(row.pr_number), "--script"],
                        cwd=self._provider.repo_root,
                        title=f"Landing PR #{row.pr_number}",
                    )
                )

    @on(PlanDataTable.RowSelected)
    def on_row_selected(self, event: PlanDataTable.RowSelected) -> None:
        """Handle Enter/double-click on row - show plan details."""
        self.action_show_detail()

    @on(Input.Changed, "#filter-input")
    def on_filter_changed(self, event: Input.Changed) -> None:
        """Handle filter input text changes."""
        self._filter_state = self._filter_state.with_query(event.value)
        self._apply_filter()

    @on(Input.Submitted, "#filter-input")
    def on_filter_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in filter input - return focus to table."""
        if self._table is not None:
            self._table.focus()

    @on(PlanDataTable.PlanClicked)
    def on_plan_clicked(self, event: PlanDataTable.PlanClicked) -> None:
        """Handle click on plan cell - open issue in browser."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.issue_url:
                self._provider.browser.launch(row.issue_url)
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened issue #{row.issue_number}")

    @on(PlanDataTable.PrClicked)
    def on_pr_clicked(self, event: PlanDataTable.PrClicked) -> None:
        """Handle click on pr cell - open PR in browser."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.pr_url:
                self._provider.browser.launch(row.pr_url)
                if self._status_bar is not None:
                    self._status_bar.set_message(f"Opened PR #{row.pr_number}")

    @on(PlanDataTable.LocalWtClicked)
    def on_local_wt_clicked(self, event: PlanDataTable.LocalWtClicked) -> None:
        """Handle click on local-wt cell - copy worktree name to clipboard."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.worktree_name:
                success = self._provider.clipboard.copy(row.worktree_name)
                if success:
                    self.notify(f"Copied: {row.worktree_name}", timeout=2)
                else:
                    self.notify("Clipboard unavailable", severity="error", timeout=2)

    @on(PlanDataTable.RunIdClicked)
    def on_run_id_clicked(self, event: PlanDataTable.RunIdClicked) -> None:
        """Handle click on run-id cell - open run in browser."""
        if event.row_index < len(self._rows):
            row = self._rows[event.row_index]
            if row.run_url:
                self._provider.browser.launch(row.run_url)
                if self._status_bar is not None:
                    # Extract run ID from URL to avoid Rich markup in status bar
                    run_id = row.run_url.rsplit("/", 1)[-1]
                    self._status_bar.set_message(f"Opened run {run_id}")
