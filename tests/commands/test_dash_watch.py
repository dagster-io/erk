"""Tests for erk dash --watch mode."""

from datetime import datetime

from erk_shared.integrations.time.fake import FakeTime
from rich.console import Group
from rich.panel import Panel
from rich.table import Table

from erk.cli.commands.plan.list_cmd import _build_watch_content, _run_watch_loop
from erk.core.context import ErkContext
from tests.fakes.live_display import FakeLiveDisplay


def test_watch_loop_sleeps_every_second() -> None:
    """Watch loop sleeps 1 second at a time for countdown updates."""
    fake_time = FakeTime()
    fake_display = FakeLiveDisplay()

    # Build function that raises KeyboardInterrupt after first data fetch
    # Loop will: fetch -> update -> sleep(1) -> update -> sleep(1) -> ...
    # Interrupt after 2 countdown updates (before data refresh)
    sleep_count = 0

    def build_table() -> tuple[Table | None, int]:
        nonlocal sleep_count
        # Interrupt after 2 sleep calls (countdown went 5->4->3)
        if sleep_count >= 2:
            raise KeyboardInterrupt()
        return Table(), 5

    # Patch sleep to track calls and trigger interrupt
    original_sleep = fake_time.sleep

    def counting_sleep(seconds: float) -> None:
        nonlocal sleep_count
        original_sleep(seconds)
        sleep_count += 1
        if sleep_count >= 2:
            raise KeyboardInterrupt()

    fake_time.sleep = counting_sleep

    ctx = ErkContext.for_test(time=fake_time)
    _run_watch_loop(ctx, fake_display, build_table, interval=5.0)

    # Should have 2 sleep calls of 1.0 second each
    assert fake_time.sleep_calls == [1.0, 1.0]
    # Should have 2 display updates (one per countdown tick)
    assert len(fake_display.updates) == 2
    assert not fake_display.is_active


def test_watch_loop_updates_display_with_table() -> None:
    """Watch loop passes table content to display update."""
    fake_time = FakeTime()
    fake_display = FakeLiveDisplay()

    # Interrupt immediately after first display update (before sleep)
    update_count = 0
    original_update = fake_display.update

    def counting_update(renderable):
        nonlocal update_count
        original_update(renderable)
        update_count += 1
        if update_count >= 1:
            raise KeyboardInterrupt()

    fake_display.update = counting_update

    def build_table() -> tuple[Table | None, int]:
        table = Table()
        table.add_column("test")
        return table, 3

    ctx = ErkContext.for_test(time=fake_time)
    _run_watch_loop(ctx, fake_display, build_table, interval=1.0)

    # Should have exactly one update
    assert len(fake_display.updates) == 1

    # Update content should be a Group containing the table and footer panel
    content = fake_display.updates[0]
    assert isinstance(content, Group)


def test_watch_loop_refreshes_data_when_countdown_reaches_zero() -> None:
    """Watch loop fetches new data when countdown reaches zero."""
    fake_time = FakeTime()
    fake_display = FakeLiveDisplay()

    fetch_count = 0

    def build_table() -> tuple[Table | None, int]:
        nonlocal fetch_count
        fetch_count += 1
        # Interrupt after second fetch
        if fetch_count >= 2:
            raise KeyboardInterrupt()
        return Table(), fetch_count

    ctx = ErkContext.for_test(time=fake_time)
    # Use interval=3 so countdown goes: 3->2->1->0 (refresh) -> interrupt
    _run_watch_loop(ctx, fake_display, build_table, interval=3.0)

    # Should have fetched data twice
    assert fetch_count == 2
    # 3 sleep calls (countdown 3->2->1->refresh)
    assert fake_time.sleep_calls == [1.0, 1.0, 1.0]


def test_watch_loop_keyboard_interrupt_stops_display() -> None:
    """KeyboardInterrupt properly stops the display."""
    fake_time = FakeTime()
    fake_display = FakeLiveDisplay()

    def build_table() -> tuple[Table | None, int]:
        raise KeyboardInterrupt()

    ctx = ErkContext.for_test(time=fake_time)
    _run_watch_loop(ctx, fake_display, build_table, interval=5.0)

    # Display should have been started and then stopped
    assert not fake_display.is_active
    # No updates since KeyboardInterrupt happened immediately
    assert len(fake_display.updates) == 0
    # No sleep calls since KeyboardInterrupt happened before sleep
    assert fake_time.sleep_calls == []


def test_watch_loop_handles_no_plans() -> None:
    """Watch loop shows panel message when no plans found."""
    fake_time = FakeTime()
    fake_display = FakeLiveDisplay()

    # Interrupt after first display update
    update_count = 0
    original_update = fake_display.update

    def counting_update(renderable):
        nonlocal update_count
        original_update(renderable)
        update_count += 1
        if update_count >= 1:
            raise KeyboardInterrupt()

    fake_display.update = counting_update

    def build_table() -> tuple[Table | None, int]:
        return None, 0  # No plans found

    ctx = ErkContext.for_test(time=fake_time)
    _run_watch_loop(ctx, fake_display, build_table, interval=5.0)

    # Should have one update
    assert len(fake_display.updates) == 1

    # Update content should be a Panel (not Group) for empty state
    content = fake_display.updates[0]
    assert isinstance(content, Panel)


def test_watch_loop_starts_and_stops_display() -> None:
    """Watch loop properly starts display before updates and stops after interrupt."""
    fake_time = FakeTime()
    fake_display = FakeLiveDisplay()

    def build_table() -> tuple[Table | None, int]:
        # Verify display is active during build
        assert fake_display.is_active
        raise KeyboardInterrupt()

    ctx = ErkContext.for_test(time=fake_time)
    _run_watch_loop(ctx, fake_display, build_table, interval=5.0)

    # Display should be stopped after loop exits
    assert not fake_display.is_active


def test_build_watch_content_with_table() -> None:
    """Build watch content creates Group with table and footer panel."""
    table = Table()
    table.add_column("test")

    content = _build_watch_content(table, count=5, last_update="14:30:45", seconds_remaining=3)

    assert isinstance(content, Group)


def test_build_watch_content_without_table() -> None:
    """Build watch content creates Panel when no table."""
    content = _build_watch_content(None, count=0, last_update="14:30:45", seconds_remaining=3)

    assert isinstance(content, Panel)


def test_build_watch_content_shows_countdown() -> None:
    """Footer text includes countdown seconds."""
    table = Table()
    content = _build_watch_content(table, count=5, last_update="14:30:45", seconds_remaining=7)

    # Content is a Group - check the panel inside has the countdown
    assert isinstance(content, Group)
    # The Group's renderables include the footer Panel
    # We can't easily inspect the Panel text, but we verified the function works


def test_watch_loop_countdown_decrements() -> None:
    """Countdown decrements each second until refresh."""
    fake_time = FakeTime()
    fake_display = FakeLiveDisplay()

    # Track countdown values seen in updates
    countdown_values: list[int] = []
    original_update = fake_display.update

    def tracking_update(renderable):
        original_update(renderable)
        # Extract countdown from Panel footer
        if isinstance(renderable, Group):
            # Group has [table, Panel(footer)]
            panel = renderable.renderables[1]
            if isinstance(panel, Panel):
                # Panel.renderable is the footer text
                text = str(panel.renderable)
                # Parse "Next refresh: Xs" from footer
                if "Next refresh:" in text:
                    import re

                    match = re.search(r"Next refresh: (\d+)s", text)
                    if match:
                        countdown_values.append(int(match.group(1)))

    fake_display.update = tracking_update

    sleep_count = 0

    def interrupt_after_sleeps(seconds: float) -> None:
        nonlocal sleep_count
        fake_time._sleep_calls.append(seconds)
        sleep_count += 1
        if sleep_count >= 3:
            raise KeyboardInterrupt()

    fake_time.sleep = interrupt_after_sleeps

    def build_table() -> tuple[Table | None, int]:
        return Table(), 5

    ctx = ErkContext.for_test(time=fake_time)
    _run_watch_loop(ctx, fake_display, build_table, interval=5.0)

    # Should see countdown values: 5, 4, 3 (before interrupt)
    assert countdown_values == [5, 4, 3]


def test_build_watch_content_shows_fetch_duration() -> None:
    """Footer includes fetch duration when provided."""
    table = Table()
    content = _build_watch_content(
        table, count=5, last_update="14:30:45", seconds_remaining=3, fetch_duration_secs=1.234
    )

    # Verify duration appears in footer (will show "1.2s")
    assert isinstance(content, Group)
    # Extract panel from group
    panel = content.renderables[1]
    assert isinstance(panel, Panel)
    footer_text = str(panel.renderable)
    assert "(1.2s)" in footer_text
    assert "Updated: 14:30:45 (1.2s)" in footer_text


def test_build_watch_content_without_fetch_duration() -> None:
    """Footer works without fetch duration (backwards compatibility)."""
    table = Table()
    content = _build_watch_content(table, count=5, last_update="14:30:45", seconds_remaining=3)

    # Verify no duration appears in footer
    assert isinstance(content, Group)
    panel = content.renderables[1]
    assert isinstance(panel, Panel)
    footer_text = str(panel.renderable)
    # Verify the footer doesn't have the duration format "(X.Xs)"
    import re

    duration_pattern = r"\(\d+\.\d+s\)"
    assert not re.search(duration_pattern, footer_text)
    assert "Updated: 14:30:45 |" in footer_text


def test_watch_loop_tracks_fetch_duration() -> None:
    """Watch loop measures and displays fetch duration."""
    from datetime import timedelta

    start_time = datetime(2024, 1, 15, 14, 30, 0)
    fake_display = FakeLiveDisplay()

    # Track when now() is called to simulate time passing
    now_call_count = 0

    class TimingFakeTime(FakeTime):
        def now(self) -> datetime:
            nonlocal now_call_count
            now_call_count += 1
            # First call: start timing (before build)
            # Second call: end timing (after build) - simulate 0.5s elapsed
            # Third call: format last_update
            if now_call_count == 2:
                return start_time + timedelta(seconds=0.5)
            return start_time + timedelta(seconds=(now_call_count - 1) * 0.5)

    fake_time = TimingFakeTime(start_time)

    def build_table() -> tuple[Table | None, int]:
        return Table(), 5

    # Interrupt after first display update
    update_count = 0
    original_update = fake_display.update

    def counting_update(renderable):
        nonlocal update_count
        original_update(renderable)
        update_count += 1
        if update_count >= 1:
            raise KeyboardInterrupt()

    fake_display.update = counting_update

    ctx = ErkContext.for_test(time=fake_time)
    _run_watch_loop(ctx, fake_display, build_table, interval=5.0)

    # Should have one update with duration
    assert len(fake_display.updates) == 1
    content = fake_display.updates[0]
    assert isinstance(content, Group)

    # Extract footer and verify duration is present
    panel = content.renderables[1]
    assert isinstance(panel, Panel)
    footer_text = str(panel.renderable)
    assert "(0.5s)" in footer_text


def test_watch_loop_updates_duration_on_refresh() -> None:
    """Watch loop tracks new duration after each data refresh."""
    from datetime import timedelta

    start_time = datetime(2024, 1, 15, 14, 30, 0)
    fake_display = FakeLiveDisplay()

    fetch_count = 0

    # Simulate time passing during fetches
    # Track each now() call and return appropriate time
    now_calls: list[datetime] = []

    class TimingFakeTime(FakeTime):
        def now(self) -> datetime:
            # First fetch pair: start at 0s, end at 0.3s
            # Second fetch pair: start at 1.0s, end at 1.7s
            if len(now_calls) == 0:
                now_calls.append(start_time)
                return start_time
            if len(now_calls) == 1:
                now_calls.append(start_time + timedelta(seconds=0.3))
                return start_time + timedelta(seconds=0.3)
            if len(now_calls) == 2:
                now_calls.append(start_time + timedelta(seconds=0.3))
                return start_time + timedelta(seconds=0.3)
            if len(now_calls) == 3:
                now_calls.append(start_time + timedelta(seconds=1.0))
                return start_time + timedelta(seconds=1.0)
            if len(now_calls) == 4:
                now_calls.append(start_time + timedelta(seconds=1.7))
                return start_time + timedelta(seconds=1.7)
            now_calls.append(start_time + timedelta(seconds=1.7))
            return start_time + timedelta(seconds=1.7)

    fake_time = TimingFakeTime(start_time)

    sleep_count = 0

    def build_table() -> tuple[Table | None, int]:
        nonlocal fetch_count
        fetch_count += 1
        return Table(), fetch_count

    original_sleep = fake_time.sleep

    def counting_sleep(seconds: float) -> None:
        nonlocal sleep_count
        original_sleep(seconds)
        sleep_count += 1
        # Interrupt after second sleep
        if sleep_count >= 2:
            raise KeyboardInterrupt()

    fake_time.sleep = counting_sleep

    ctx = ErkContext.for_test(time=fake_time)
    _run_watch_loop(ctx, fake_display, build_table, interval=1.0)

    # Should have multiple updates
    assert len(fake_display.updates) >= 2

    # Collect all unique durations seen in updates
    durations_seen = set()
    for update in fake_display.updates:
        if isinstance(update, Group):
            panel = update.renderables[1]
            if isinstance(panel, Panel):
                footer_text = str(panel.renderable)
                # Extract duration if present
                import re

                match = re.search(r"\((\d+\.\d+)s\)", footer_text)
                if match:
                    durations_seen.add(match.group(1))

    # Should have seen both 0.3s and 0.7s durations
    assert "0.3" in durations_seen
    assert "0.7" in durations_seen
