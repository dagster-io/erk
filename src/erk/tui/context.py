"""Context for erk dash with dash-specific dependencies.

ErkDashContext uses composition to combine the core ErkContext with
dash-specific dependencies like BrowserLauncher, Time, and TuiRunner.
This enables dependency injection for testing TUI components.
"""

from dataclasses import dataclass

from erk_shared.integrations.browser.abc import BrowserLauncher
from erk_shared.integrations.browser.fake import FakeBrowserLauncher
from erk_shared.integrations.browser.real import RealBrowserLauncher
from erk_shared.integrations.time.abc import Time
from erk_shared.integrations.time.fake import FakeTime

from erk.core.context import ErkContext
from erk.tui.runner import FakeTuiRunner, RealTuiRunner, TuiRunner


@dataclass(frozen=True)
class ErkDashContext:
    """Context for erk dash with dash-specific dependencies.

    Uses composition pattern: wraps ErkContext and adds dash-specific
    dependencies like browser launcher, time, and TUI runner.

    This design:
    - Keeps ErkContext lean (no TUI concerns in core context)
    - Enables CLI routing tests without starting Textual (via FakeTuiRunner)
    - Enables TUI behavior tests with Pilot (via for_test() factories)
    - Follows the same ABC/Real/Fake pattern as other integrations
    """

    ctx: ErkContext  # Core erk context (composition, not inheritance)
    browser: BrowserLauncher
    time: Time
    tui_runner: TuiRunner

    @classmethod
    def for_production(cls, ctx: ErkContext) -> "ErkDashContext":
        """Create production context with real implementations.

        Args:
            ctx: Core ErkContext with production dependencies

        Returns:
            ErkDashContext configured for production use
        """
        return cls(
            ctx=ctx,
            browser=RealBrowserLauncher(),
            time=ctx.time,  # Use time from ErkContext for consistency
            tui_runner=RealTuiRunner(),
        )

    @classmethod
    def for_test(
        cls,
        ctx: ErkContext,
        *,
        browser: BrowserLauncher | None = None,
        time: Time | None = None,
        tui_runner: TuiRunner | None = None,
    ) -> "ErkDashContext":
        """Create test context with injectable fakes.

        Args:
            ctx: Core ErkContext (can be real or fake)
            browser: Optional BrowserLauncher. If None, creates FakeBrowserLauncher.
            time: Optional Time. If None, creates FakeTime.
            tui_runner: Optional TuiRunner. If None, creates FakeTuiRunner.

        Returns:
            ErkDashContext configured for testing

        Example:
            # For CLI routing tests (verify app created, no event loop)
            tui_runner = FakeTuiRunner()
            dash_ctx = ErkDashContext.for_test(ctx, tui_runner=tui_runner)
            # invoke CLI command
            assert len(tui_runner.apps_run) == 1
            assert tui_runner.apps_run[0]._plan_filters.state == "open"

            # For TUI behavior tests with Pilot
            browser = FakeBrowserLauncher()
            dash_ctx = ErkDashContext.for_test(ctx, browser=browser)
            app = ErkDashApp(dash_ctx, provider, filters)
            async with app.run_test() as pilot:
                await pilot.press("o")
            assert browser.launched_urls == ["https://github.com/..."]
        """
        return cls(
            ctx=ctx,
            browser=browser or FakeBrowserLauncher(),
            time=time or FakeTime(),
            tui_runner=tui_runner or FakeTuiRunner(),
        )
