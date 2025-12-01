"""Tests for FakeSlackListener."""

from erk.slack.listener.fake import FakeSlackListener
from erk.slack.types import SlackEvent, SlackMessage


class TestFakeSlackListener:
    """Tests for FakeSlackListener."""

    def test_yields_no_events_when_empty(self) -> None:
        """FakeSlackListener yields nothing when no events added."""
        listener = FakeSlackListener()

        events = list(listener.listen())

        assert events == []

    def test_yields_single_event(self) -> None:
        """FakeSlackListener yields a single added event."""
        listener = FakeSlackListener()
        msg = SlackMessage(
            channel="C12345",
            ts="1234567890.123456",
            thread_ts=None,
            user="U12345",
            text="Hello",
        )
        event = SlackEvent(event_type="app_mention", message=msg)
        listener.add_event(event)

        events = list(listener.listen())

        assert len(events) == 1
        assert events[0] == event

    def test_yields_multiple_events_in_order(self) -> None:
        """FakeSlackListener yields events in the order they were added."""
        listener = FakeSlackListener()
        msg1 = SlackMessage(
            channel="C12345",
            ts="1234567890.000001",
            thread_ts=None,
            user="U12345",
            text="First",
        )
        msg2 = SlackMessage(
            channel="C12345",
            ts="1234567890.000002",
            thread_ts="1234567890.000001",
            user="U12345",
            text="Second",
        )
        event1 = SlackEvent(event_type="app_mention", message=msg1)
        event2 = SlackEvent(event_type="message", message=msg2)
        listener.add_events([event1, event2])

        events = list(listener.listen())

        assert len(events) == 2
        assert events[0] == event1
        assert events[1] == event2

    def test_stop_prevents_further_events(self) -> None:
        """FakeSlackListener.stop() prevents remaining events from yielding."""
        listener = FakeSlackListener()
        msg = SlackMessage(
            channel="C12345",
            ts="1234567890.123456",
            thread_ts=None,
            user="U12345",
            text="Hello",
        )
        event1 = SlackEvent(event_type="app_mention", message=msg)
        event2 = SlackEvent(event_type="message", message=msg)
        listener.add_events([event1, event2])

        events = []
        for event in listener.listen():
            events.append(event)
            listener.stop()  # Stop after first event

        assert len(events) == 1
        assert events[0] == event1

    def test_events_added_property_returns_copy(self) -> None:
        """events_added returns a copy, not the internal list."""
        listener = FakeSlackListener()
        msg = SlackMessage(
            channel="C12345",
            ts="1234567890.123456",
            thread_ts=None,
            user="U12345",
            text="Hello",
        )
        event = SlackEvent(event_type="app_mention", message=msg)
        listener.add_event(event)

        events_copy = listener.events_added
        events_copy.clear()

        assert len(listener.events_added) == 1
