"""Tests for FakeBrowserLauncher implementation."""

from erk_shared.integrations.browser.fake import FakeBrowserLauncher


def test_launched_urls_starts_empty() -> None:
    """FakeBrowserLauncher starts with empty URL list."""
    browser = FakeBrowserLauncher()
    assert browser.launched_urls == []


def test_launch_captures_url() -> None:
    """launch() captures URL in launched_urls list."""
    browser = FakeBrowserLauncher()

    browser.launch("https://github.com/test/repo")

    assert browser.launched_urls == ["https://github.com/test/repo"]


def test_launch_captures_multiple_urls() -> None:
    """launch() captures multiple URLs in order."""
    browser = FakeBrowserLauncher()

    browser.launch("https://github.com/first")
    browser.launch("https://github.com/second")
    browser.launch("https://github.com/third")

    assert browser.launched_urls == [
        "https://github.com/first",
        "https://github.com/second",
        "https://github.com/third",
    ]


def test_launch_captures_duplicate_urls() -> None:
    """launch() captures duplicate URLs without deduplication."""
    browser = FakeBrowserLauncher()

    browser.launch("https://example.com")
    browser.launch("https://example.com")

    assert browser.launched_urls == [
        "https://example.com",
        "https://example.com",
    ]
