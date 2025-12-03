"""Tests for FakeBrowserLauncher implementation."""

from erk_shared.integrations.browser.fake import FakeBrowserLauncher


class TestFakeBrowserLauncherLaunchTracking:
    """Tests for FakeBrowserLauncher launch tracking functionality."""

    def test_launch_tracks_calls(self) -> None:
        """launch() calls are tracked in launch_calls property."""
        browser = FakeBrowserLauncher()
        browser.launch("https://first.com")
        browser.launch("https://second.com")

        assert browser.launch_calls == ["https://first.com", "https://second.com"]

    def test_last_launched_returns_most_recent(self) -> None:
        """last_launched returns most recent launch call."""
        browser = FakeBrowserLauncher()
        browser.launch("https://first.com")
        browser.launch("https://second.com")

        assert browser.last_launched == "https://second.com"

    def test_last_launched_returns_none_when_empty(self) -> None:
        """last_launched returns None when no launch calls made."""
        browser = FakeBrowserLauncher()

        assert browser.last_launched is None

    def test_launch_calls_empty_initially(self) -> None:
        """launch_calls is empty list initially."""
        browser = FakeBrowserLauncher()

        assert browser.launch_calls == []


class TestFakeBrowserLauncherSuccessMode:
    """Tests for FakeBrowserLauncher success/failure configuration."""

    def test_default_success_mode_returns_true(self) -> None:
        """Default browser returns True from launch()."""
        browser = FakeBrowserLauncher()

        result = browser.launch("https://test.com")

        assert result is True

    def test_should_succeed_true_returns_true(self) -> None:
        """Explicit should_succeed=True returns True."""
        browser = FakeBrowserLauncher(should_succeed=True)

        result = browser.launch("https://test.com")

        assert result is True

    def test_should_succeed_false_returns_false(self) -> None:
        """should_succeed=False returns False from launch()."""
        browser = FakeBrowserLauncher(should_succeed=False)

        result = browser.launch("https://test.com")

        assert result is False

    def test_failure_mode_still_tracks_calls(self) -> None:
        """Failure mode still tracks launch calls."""
        browser = FakeBrowserLauncher(should_succeed=False)
        browser.launch("https://test.com")

        assert browser.launch_calls == ["https://test.com"]
        assert browser.last_launched == "https://test.com"


class TestFakeBrowserLauncherDefensiveCopying:
    """Tests for FakeBrowserLauncher defensive copying behavior."""

    def test_launch_calls_returns_copy_of_list(self) -> None:
        """launch_calls returns a copy to prevent external mutation."""
        browser = FakeBrowserLauncher()
        browser.launch("https://test.com")

        # Modify the returned list
        returned_list = browser.launch_calls
        returned_list.append("mutated")

        # Original should be unchanged
        assert browser.launch_calls == ["https://test.com"]
