"""Tests for ErkDashContext."""

from erk_shared.integrations.browser.fake import FakeBrowserLauncher
from erk_shared.integrations.browser.real import RealBrowserLauncher
from erk_shared.integrations.time.fake import FakeTime
from erk_shared.integrations.time.real import RealTime

from erk.core.context import ErkContext
from erk.tui.context import ErkDashContext
from erk.tui.runner import FakeTuiRunner, RealTuiRunner


def test_for_production_creates_real_implementations() -> None:
    """for_production() creates context with real implementations."""
    ctx = ErkContext.for_test()

    dash_ctx = ErkDashContext.for_production(ctx)

    assert dash_ctx.ctx is ctx
    assert isinstance(dash_ctx.browser, RealBrowserLauncher)
    assert isinstance(dash_ctx.tui_runner, RealTuiRunner)


def test_for_production_uses_ctx_time() -> None:
    """for_production() uses time from the ErkContext for consistency."""
    time = RealTime()
    ctx = ErkContext.for_test(time=time)

    dash_ctx = ErkDashContext.for_production(ctx)

    assert dash_ctx.time is ctx.time


def test_for_test_creates_fake_implementations() -> None:
    """for_test() creates context with fake implementations by default."""
    ctx = ErkContext.for_test()

    dash_ctx = ErkDashContext.for_test(ctx)

    assert dash_ctx.ctx is ctx
    assert isinstance(dash_ctx.browser, FakeBrowserLauncher)
    assert isinstance(dash_ctx.time, FakeTime)
    assert isinstance(dash_ctx.tui_runner, FakeTuiRunner)


def test_for_test_accepts_custom_browser() -> None:
    """for_test() accepts custom browser implementation."""
    ctx = ErkContext.for_test()
    browser = FakeBrowserLauncher()

    dash_ctx = ErkDashContext.for_test(ctx, browser=browser)

    assert dash_ctx.browser is browser


def test_for_test_accepts_custom_time() -> None:
    """for_test() accepts custom time implementation."""
    ctx = ErkContext.for_test()
    time = FakeTime()

    dash_ctx = ErkDashContext.for_test(ctx, time=time)

    assert dash_ctx.time is time


def test_for_test_accepts_custom_tui_runner() -> None:
    """for_test() accepts custom tui_runner implementation."""
    ctx = ErkContext.for_test()
    tui_runner = FakeTuiRunner()

    dash_ctx = ErkDashContext.for_test(ctx, tui_runner=tui_runner)

    assert dash_ctx.tui_runner is tui_runner


def test_context_is_frozen() -> None:
    """ErkDashContext is immutable (frozen dataclass)."""
    ctx = ErkContext.for_test()
    dash_ctx = ErkDashContext.for_test(ctx)

    # Attempting to modify should raise an error
    import dataclasses

    assert dataclasses.is_dataclass(dash_ctx)
    # Frozen dataclasses raise FrozenInstanceError on attribute assignment
    try:
        dash_ctx.browser = FakeBrowserLauncher()  # type: ignore[misc]
        raise AssertionError("Expected FrozenInstanceError")
    except dataclasses.FrozenInstanceError:
        pass  # Expected
