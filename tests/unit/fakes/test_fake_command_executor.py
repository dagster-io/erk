"""Tests for FakeCommandExecutor."""

from tests.fakes.command_executor import FakeCommandExecutor


def test_tracks_opened_urls() -> None:
    """Fake executor tracks URLs that were opened."""
    executor = FakeCommandExecutor()
    executor.open_url("https://example.com")
    executor.open_url("https://github.com")
    assert executor.opened_urls == ["https://example.com", "https://github.com"]


def test_tracks_copied_texts() -> None:
    """Fake executor tracks texts that were copied to clipboard."""
    executor = FakeCommandExecutor()
    executor.copy_to_clipboard("erk implement 123")
    executor.copy_to_clipboard("erk plan submit 456")
    assert executor.copied_texts == ["erk implement 123", "erk plan submit 456"]


def test_tracks_closed_plans() -> None:
    """Fake executor tracks plans that were closed."""
    executor = FakeCommandExecutor()
    executor.close_plan(123, "https://github.com/test/repo/issues/123")
    executor.close_plan(456, "https://github.com/test/repo/issues/456")
    assert executor.closed_plans == [
        (123, "https://github.com/test/repo/issues/123"),
        (456, "https://github.com/test/repo/issues/456"),
    ]


def test_tracks_notifications() -> None:
    """Fake executor tracks notifications shown."""
    executor = FakeCommandExecutor()
    executor.notify("Copied: erk implement 123")
    executor.notify("Closed plan #456")
    assert executor.notifications == [
        "Copied: erk implement 123",
        "Closed plan #456",
    ]


def test_tracks_refresh_count() -> None:
    """Fake executor tracks number of refreshes triggered."""
    executor = FakeCommandExecutor()
    assert executor.refresh_count == 0
    executor.refresh_data()
    assert executor.refresh_count == 1
    executor.refresh_data()
    executor.refresh_data()
    assert executor.refresh_count == 3


def test_close_plan_returns_empty_list_by_default() -> None:
    """close_plan returns empty list by default (no linked PRs)."""
    executor = FakeCommandExecutor()
    result = executor.close_plan(123, "https://github.com/test/repo/issues/123")
    assert result == []


def test_close_plan_returns_configured_pr_numbers() -> None:
    """close_plan returns configured PR numbers when set."""
    executor = FakeCommandExecutor()
    executor.set_close_plan_return([789, 790])
    result = executor.close_plan(123, "https://github.com/test/repo/issues/123")
    assert result == [789, 790]


def test_properties_return_copies() -> None:
    """Properties return copies to prevent external modification."""
    executor = FakeCommandExecutor()
    executor.open_url("https://example.com")

    urls = executor.opened_urls
    urls.append("https://should-not-be-added.com")

    assert executor.opened_urls == ["https://example.com"]
