import sys
import time
from dataclasses import dataclass

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


@dataclass
class Message:
    """Represents a single message"""

    message_ts: str
    thread_ts: str | None
    content: str
    timestamp: float


class ThreadedMessenger:
    """An interactive threaded messaging system with keyboard navigation"""

    def __init__(self):
        # Force console to detect size and use force_terminal
        self.console = Console(force_terminal=True, force_interactive=True, legacy_windows=False)
        self.messages: dict[str, Message] = {}
        self.threads: dict[str, list[str]] = {}  # thread_ts -> list of message_ts
        self.message_counter = 0
        self.selected_thread_index = -1  # -1 means no thread selected (new message)
        self.input_buffer = ""
        self.message_history = []
        self.status_message = ""
        self.running = False

    def _generate_ts(self) -> str:
        """Generate a unique timestamp identifier"""
        self.message_counter += 1
        return f"{int(time.time() * 1000)}.{self.message_counter:06d}"

    def post_message(self, content: str, thread_ts: str | None = None) -> tuple[str, str]:
        """
        Post a new message, optionally to a thread.

        Args:
            content: The message content
            thread_ts: Optional thread timestamp to reply to

        Returns:
            tuple: (thread_ts, message_ts)
        """
        message_ts = self._generate_ts()

        # If no thread_ts provided, this is a new thread
        if thread_ts is None:
            thread_ts = message_ts
            self.threads[thread_ts] = []
            self.status_message = "✓ New thread created"
        elif thread_ts not in self.threads:
            raise ValueError(f"Thread {thread_ts} does not exist")
        else:
            self.status_message = "✓ Reply sent"

        # Create and store the message
        message = Message(
            message_ts=message_ts, thread_ts=thread_ts, content=content, timestamp=time.time()
        )
        self.messages[message_ts] = message
        self.threads[thread_ts].append(message_ts)

        return thread_ts, message_ts

    def update_message(self, message_ts: str, new_content: str) -> bool:
        """Update an existing message"""
        if message_ts not in self.messages:
            return False

        self.messages[message_ts].content = new_content
        self.status_message = "✓ Message updated"
        return True

    def delete_message(self, message_ts: str) -> bool:
        """Delete a message"""
        if message_ts not in self.messages:
            return False

        message = self.messages[message_ts]
        thread_ts = message.thread_ts

        # Remove from thread
        if thread_ts in self.threads:
            self.threads[thread_ts].remove(message_ts)

            # If deleting the root message, delete entire thread
            if message_ts == thread_ts:
                # Delete all messages in thread
                for ts in self.threads[thread_ts]:
                    if ts in self.messages:
                        del self.messages[ts]
                del self.threads[thread_ts]

        # Remove the message
        del self.messages[message_ts]
        self.status_message = "✓ Message deleted"

        return True

    def _get_sorted_thread_list(self) -> list[str]:
        """Get list of thread_ts sorted by timestamp"""
        return sorted(
            self.threads.keys(),
            key=lambda ts: self.messages[ts].timestamp if ts in self.messages else 0,
        )

    def _get_selected_thread_ts(self) -> str | None:
        """Get the currently selected thread_ts, or None if creating new thread"""
        if self.selected_thread_index == -1:
            return None

        thread_list = self._get_sorted_thread_list()
        if 0 <= self.selected_thread_index < len(thread_list):
            return thread_list[self.selected_thread_index]
        return None

    def render(self) -> Layout:
        """Render the current state of the messenger"""
        layout = Layout()

        # Split with fixed sizes for header/input, messages gets the rest
        layout.split_column(
            Layout(name="header", size=5, minimum_size=5),
            Layout(name="messages", ratio=1, minimum_size=10),
            Layout(name="input", size=5, minimum_size=5),
        )

        # Header
        debug_info = f"Messages: {len(self.messages)} | Threads: {len(self.threads)} | Selected: {self.selected_thread_index}"
        status = f" {self.status_message}" if self.status_message else ""
        layout["header"].update(
            Panel(
                f"[bold cyan]Threaded Messenger[/bold cyan]\n"
                f"[dim]↑/↓ arrows: select thread | Type & Enter: send message | Ctrl+C: quit[/dim]\n"
                f"[dim]{debug_info}[/dim][green]{status}[/green]",
                border_style="cyan",
                expand=True,
                padding=(0, 1),
            )
        )

        # Messages area
        messages_content = Text()

        if not self.threads:
            # Add significant padding to make empty state visible
            messages_content.append("\n" * 5, style="")
            messages_content.append("                    📭 No messages yet\n", style="bold yellow")
            messages_content.append(
                "                    Start typing below and press Enter to create your first message!\n",
                style="yellow",
            )
            messages_content.append("\n" * 5, style="")
        else:
            thread_list = self._get_sorted_thread_list()
            messages_content.append("\n")

            for idx, thread_ts in enumerate(thread_list):
                if thread_ts not in self.messages:
                    continue

                # Check if this thread is selected
                is_selected = idx == self.selected_thread_index

                # Display root message
                root_msg = self.messages[thread_ts]
                self._render_message(
                    messages_content, root_msg, is_root=True, is_selected=is_selected
                )

                # Display threaded replies (never highlighted, only root gets selection styling)
                replies = [ts for ts in self.threads[thread_ts] if ts != thread_ts]
                for reply_ts in replies:
                    if reply_ts in self.messages:
                        self._render_message(
                            messages_content,
                            self.messages[reply_ts],
                            is_root=False,
                            is_selected=False,
                        )

                messages_content.append("\n")

        layout["messages"].update(
            Panel(
                messages_content,
                border_style="white",
                title="[bold white]Messages[/bold white]",
                expand=True,
                padding=(1, 2),
            )
        )

        # Input area
        selected_thread_ts = self._get_selected_thread_ts()
        if selected_thread_ts and selected_thread_ts in self.messages:
            root_msg = self.messages[selected_thread_ts]
            prompt_text = f"💬 Replying to: {root_msg.content[:50]}"
            if len(root_msg.content) > 50:
                prompt_text += "..."
            border_style = "blue"
            title = "[bold blue]Reply Mode[/bold blue]"
        else:
            prompt_text = "✨ New message"
            border_style = "yellow"
            title = "[bold yellow]Compose Mode[/bold yellow]"

        input_content = Text()
        input_content.append(f"{prompt_text}\n", style="dim")
        input_content.append("> ", style=f"bold {border_style}")

        if self.input_buffer:
            input_content.append(self.input_buffer, style="bold white")
            input_content.append("█", style="bold white")  # Cursor
        else:
            input_content.append("█", style="bold white blink")  # Blinking cursor when empty

        layout["input"].update(
            Panel(
                input_content, border_style=border_style, title=title, expand=True, padding=(0, 1)
            )
        )

        return layout

    def _render_message(self, text: Text, message: Message, is_root: bool, is_selected: bool):
        """Render a single message into the text buffer"""
        indent = "  " if is_root else "      "
        prefix = "┗━" if not is_root else "●"

        # Format timestamp
        ts_display = message.message_ts[-6:]

        # Selection highlighting - use reverse video style for better visibility
        if is_selected:
            if is_root:
                prefix_style = "bold yellow reverse"
                text_style = "bold white reverse"
                ts_style = "dim reverse"
            else:
                prefix_style = "blue reverse"
                text_style = "white reverse"
                ts_style = "dim reverse"
        else:
            if is_root:
                prefix_style = "bold yellow"
                text_style = "bold white"
                ts_style = "dim"
            else:
                prefix_style = "blue"
                text_style = "white"
                ts_style = "dim"

        # Build the message display
        text.append(indent)
        text.append(f"{prefix} ", style=prefix_style)
        text.append(f"[{ts_display}] ", style=ts_style)
        text.append(message.content, style=text_style)
        text.append("\n")

    def move_selection_up(self):
        """Move selection up (toward newer threads or to 'new message')"""
        thread_count = len(self.threads)
        if thread_count == 0:
            self.selected_thread_index = -1
        else:
            # If in "new message" mode (-1), select the first (newest) thread
            # If at first thread (0), stay there (it's the top)
            # Otherwise move up one thread
            if self.selected_thread_index == -1:
                self.selected_thread_index = 0
            elif self.selected_thread_index > 0:
                self.selected_thread_index -= 1
            # If already at 0, stay at 0
        self.status_message = ""

    def move_selection_down(self):
        """Move selection down (toward older threads)"""
        thread_count = len(self.threads)
        if thread_count == 0:
            self.selected_thread_index = -1
        else:
            # If at last thread, move to "new message" mode (-1)
            # Otherwise move down one thread
            if self.selected_thread_index >= thread_count - 1:
                self.selected_thread_index = -1
            else:
                self.selected_thread_index += 1
        self.status_message = ""

    def send_message(self):
        """Send the current input buffer as a message"""
        if not self.input_buffer.strip():
            self.status_message = "⚠ Cannot send empty message"
            return

        content = self.input_buffer
        thread_ts = self._get_selected_thread_ts()

        self.post_message(content, thread_ts)
        self.message_history.append(content)
        self.input_buffer = ""

        # Only reset to "new message" if we were creating a new thread
        # If we were replying to an existing thread, stay in that thread
        if thread_ts is None:
            # We just created a new thread, reset to "new message" mode
            self.selected_thread_index = -1
        # else: keep selected_thread_index as is to stay in reply mode

    def run(self):
        """Run the interactive messenger"""
        import termios
        import tty

        # Save terminal settings but don't set raw mode yet
        old_settings = termios.tcgetattr(sys.stdin)

        try:
            # Set cbreak mode instead of raw mode - this is less invasive
            tty.setcbreak(sys.stdin.fileno())

            with Live(
                self.render(), refresh_per_second=20, screen=True, vertical_overflow="visible"
            ) as live:
                self.running = True

                while self.running:
                    # Read one character
                    char = sys.stdin.read(1)

                    # Handle special keys
                    if char == "\x1b":  # ESC sequence
                        next1 = sys.stdin.read(1)
                        next2 = sys.stdin.read(1)

                        if next1 == "[":
                            if next2 == "A":  # Up arrow
                                self.move_selection_up()
                            elif next2 == "B":  # Down arrow
                                self.move_selection_down()

                    elif char == "\r" or char == "\n":  # Enter
                        self.send_message()

                    elif char == "\x7f":  # Backspace
                        if self.input_buffer:
                            self.input_buffer = self.input_buffer[:-1]
                            self.status_message = ""

                    elif char == "\x03":  # Ctrl+C
                        break

                    elif ord(char) >= 32 and ord(char) < 127:  # Printable characters
                        self.input_buffer += char
                        self.status_message = ""

                    # Update display
                    live.update(self.render())

        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


# Example usage
if __name__ == "__main__":
    messenger = ThreadedMessenger()

    # Run the interactive interface
    try:
        messenger.run()
    except KeyboardInterrupt:
        pass

    print("\n\n👋 Goodbye!")
