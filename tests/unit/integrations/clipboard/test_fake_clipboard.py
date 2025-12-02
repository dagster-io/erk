"""Tests for FakeClipboard implementation."""

from erk_shared.integrations.clipboard.fake import FakeClipboard


class TestFakeClipboardCopyTracking:
    """Tests for FakeClipboard copy tracking functionality."""

    def test_copy_tracks_calls(self) -> None:
        """copy() calls are tracked in copy_calls property."""
        clipboard = FakeClipboard()
        clipboard.copy("first")
        clipboard.copy("second")

        assert clipboard.copy_calls == ["first", "second"]

    def test_last_copied_returns_most_recent(self) -> None:
        """last_copied returns most recent copy call."""
        clipboard = FakeClipboard()
        clipboard.copy("first")
        clipboard.copy("second")

        assert clipboard.last_copied == "second"

    def test_last_copied_returns_none_when_empty(self) -> None:
        """last_copied returns None when no copy calls made."""
        clipboard = FakeClipboard()

        assert clipboard.last_copied is None

    def test_copy_calls_empty_initially(self) -> None:
        """copy_calls is empty list initially."""
        clipboard = FakeClipboard()

        assert clipboard.copy_calls == []


class TestFakeClipboardSuccessMode:
    """Tests for FakeClipboard success/failure configuration."""

    def test_default_success_mode_returns_true(self) -> None:
        """Default clipboard returns True from copy()."""
        clipboard = FakeClipboard()

        result = clipboard.copy("test")

        assert result is True

    def test_should_succeed_true_returns_true(self) -> None:
        """Explicit should_succeed=True returns True."""
        clipboard = FakeClipboard(should_succeed=True)

        result = clipboard.copy("test")

        assert result is True

    def test_should_succeed_false_returns_false(self) -> None:
        """should_succeed=False returns False from copy()."""
        clipboard = FakeClipboard(should_succeed=False)

        result = clipboard.copy("test")

        assert result is False

    def test_failure_mode_still_tracks_calls(self) -> None:
        """Failure mode still tracks copy calls."""
        clipboard = FakeClipboard(should_succeed=False)
        clipboard.copy("test")

        assert clipboard.copy_calls == ["test"]
        assert clipboard.last_copied == "test"


class TestFakeClipboardDefensiveCopying:
    """Tests for FakeClipboard defensive copying behavior."""

    def test_copy_calls_returns_copy_of_list(self) -> None:
        """copy_calls returns a copy to prevent external mutation."""
        clipboard = FakeClipboard()
        clipboard.copy("test")

        # Modify the returned list
        returned_list = clipboard.copy_calls
        returned_list.append("mutated")

        # Original should be unchanged
        assert clipboard.copy_calls == ["test"]
