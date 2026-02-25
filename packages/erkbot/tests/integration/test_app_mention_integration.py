# NOTE: @patch usage is deliberate here. erk-slack-bot is a standalone package that
# tests third-party Slack SDK wiring and does not use erk's gateway layer.

from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from erkbot.config import Settings
from erkbot.models import RunResult
from slack_bolt.async_app import AsyncApp
from slack_bolt.request.async_request import AsyncBoltRequest

from tests.integration.conftest import dispatch_and_settle
from tests.mock_web_api_server.mock_server_thread import MockServerThread
from tests.mock_web_api_server.received_requests import ReceivedRequests

BOT_MENTION = "<@B123>"


@pytest.mark.asyncio
async def test_plan_list_success(
    app: AsyncApp,
    build_app_mention_request,
    received: ReceivedRequests,
) -> None:
    """plan list: reactions.add called, 'Running...' posted, plan output in code blocks."""
    with patch(
        "erkbot.slack_handlers.run_erk_plan_list",
        new_callable=AsyncMock,
        return_value=RunResult(exit_code=0, output="Plan #1: Fix bug\nPlan #2: Add feature"),
    ):
        request: AsyncBoltRequest = build_app_mention_request(f"{BOT_MENTION} plan list")
        response = await dispatch_and_settle(app, request, timeout_seconds=5.0)

    assert response.status == 200

    received.drain()

    assert received.get_count("/reactions.add") >= 1

    post_bodies = received.get_bodies("/chat.postMessage")
    texts = [b.get("text", "") for b in post_bodies]

    assert any("Running" in t and "pr list" in t for t in texts)
    assert any("Result from" in t and "pr list" in t for t in texts)
    assert any("Plan #1" in t for t in texts)


@pytest.mark.asyncio
async def test_plan_list_ansi_codes_stripped(
    app: AsyncApp,
    build_app_mention_request,
    received: ReceivedRequests,
) -> None:
    """plan list: ANSI escape codes from Rich Console are stripped before posting to Slack.

    Mocks CliRunner.invoke (not run_erk_plan_list) so the runner's strip_ansi
    logic is exercised end-to-end through the Slack handler.
    """
    # Simulate what CliRunner captures from Console(force_terminal=True):
    # user_output() goes to stderr (via click.echo(err=True))
    # Console(stderr=True, force_terminal=True).print(table) goes to stderr with ANSI
    ansi_stderr = (
        "\nFound 2 plan(s):\n\n"
        "\x1b[1mpr    \x1b[0m \x1b[1mstage\x1b[0m\n"
        "\x1b]8;;https://github.com/test/repo/issues/1\x1b\\#1\x1b]8;;\x1b\\"
        "     \x1b[36mimpl\x1b[0m\n"
        "\x1b]8;;https://github.com/test/repo/issues/2\x1b\\#2\x1b]8;;\x1b\\"
        "     \x1b[36mqueued\x1b[0m"
    )
    fake_result = MagicMock()
    fake_result.output = ansi_stderr
    fake_result.exit_code = 0

    with patch("erkbot.runner.CliRunner") as mock_runner_cls:
        mock_runner_cls.return_value.invoke.return_value = fake_result
        request: AsyncBoltRequest = build_app_mention_request(f"{BOT_MENTION} plan list")
        response = await dispatch_and_settle(app, request, timeout_seconds=5.0)

    assert response.status == 200

    received.drain()

    post_bodies = received.get_bodies("/chat.postMessage")
    texts = [b.get("text", "") for b in post_bodies]

    # ANSI codes should not appear in any Slack message
    for text in texts:
        assert "\x1b" not in text, f"ANSI escape code found in Slack message: {text!r}"

    # Content should still be present (ANSI stripped, text preserved)
    assert any("#1" in t for t in texts)
    assert any("#2" in t for t in texts)


@pytest.mark.asyncio
async def test_plan_list_error(
    app: AsyncApp,
    build_app_mention_request,
    received: ReceivedRequests,
) -> None:
    """plan list with runner failure: error status line posted."""
    with patch(
        "erkbot.slack_handlers.run_erk_plan_list",
        new_callable=AsyncMock,
        return_value=RunResult(exit_code=1, output="Error: connection refused"),
    ):
        request: AsyncBoltRequest = build_app_mention_request(f"{BOT_MENTION} plan list")
        response = await dispatch_and_settle(app, request, timeout_seconds=5.0)

    assert response.status == 200

    received.drain()

    post_bodies = received.get_bodies("/chat.postMessage")
    texts = [b.get("text", "") for b in post_bodies]

    assert any("failed" in t and "exit 1" in t for t in texts)
    assert any("Error: connection refused" in t for t in texts)


@pytest.mark.asyncio
async def test_quote(
    app: AsyncApp,
    build_app_mention_request,
    received: ReceivedRequests,
) -> None:
    """quote: posts quote text."""
    request: AsyncBoltRequest = build_app_mention_request(f"{BOT_MENTION} quote")
    response = await dispatch_and_settle(app, request, timeout_seconds=5.0)

    assert response.status == 200

    received.drain()

    post_bodies = received.get_bodies("/chat.postMessage")
    texts = [b.get("text", "") for b in post_bodies]

    assert len(post_bodies) >= 1
    assert any(len(t) > 10 for t in texts)


@pytest.mark.asyncio
async def test_one_shot_missing_message(
    app: AsyncApp,
    build_app_mention_request,
    received: ReceivedRequests,
) -> None:
    """one-shot without message: usage message posted."""
    request: AsyncBoltRequest = build_app_mention_request(f"{BOT_MENTION} one-shot")
    response = await dispatch_and_settle(app, request, timeout_seconds=5.0)

    assert response.status == 200

    received.drain()

    post_bodies = received.get_bodies("/chat.postMessage")
    texts = [b.get("text", "") for b in post_bodies]

    assert any("Usage:" in t and "one-shot" in t for t in texts)


@pytest.mark.asyncio
async def test_one_shot_too_long(
    app: AsyncApp,
    build_app_mention_request,
    received: ReceivedRequests,
    settings: Settings,
) -> None:
    """one-shot with oversized message: rejection message posted."""
    long_message = "x" * (settings.max_one_shot_message_chars + 1)
    request: AsyncBoltRequest = build_app_mention_request(f"{BOT_MENTION} one-shot {long_message}")
    response = await dispatch_and_settle(app, request, timeout_seconds=5.0)

    assert response.status == 200

    received.drain()

    post_bodies = received.get_bodies("/chat.postMessage")
    texts = [b.get("text", "") for b in post_bodies]

    assert any("too long" in t for t in texts)


@pytest.mark.asyncio
async def test_unknown_command(
    app: AsyncApp,
    build_app_mention_request,
    received: ReceivedRequests,
) -> None:
    """unknown command: help text with supported commands posted."""
    request: AsyncBoltRequest = build_app_mention_request(f"{BOT_MENTION} hello")
    response = await dispatch_and_settle(app, request, timeout_seconds=5.0)

    assert response.status == 200

    received.drain()

    post_bodies = received.get_bodies("/chat.postMessage")
    texts = [b.get("text", "") for b in post_bodies]

    assert any("Supported commands" in t for t in texts)


@pytest.mark.asyncio
async def test_one_shot_success(
    app: AsyncApp,
    build_app_mention_request,
    received: ReceivedRequests,
) -> None:
    """one-shot success: status posted, progress updates via chat_update, PR/run URLs posted."""
    result = RunResult(
        exit_code=0,
        output=(
            "Creating branch...\nPushing...\n"
            "PR: https://github.com/test/repo/pull/42\n"
            "Run: https://github.com/test/repo/actions/runs/999"
        ),
    )

    async def fake_stream(
        message: str,
        *,
        timeout_seconds: float,
        on_line: Callable[[str], Awaitable[None]] | None,
    ) -> RunResult:
        if on_line is not None:
            await on_line("Creating branch...")
            await on_line("Pushing...")
            await on_line("PR: https://github.com/test/repo/pull/42")
            await on_line("Run: https://github.com/test/repo/actions/runs/999")
        return result

    with patch(
        "erkbot.slack_handlers.stream_erk_one_shot",
        side_effect=fake_stream,
    ):
        request: AsyncBoltRequest = build_app_mention_request(f"{BOT_MENTION} one-shot fix readme")
        response = await dispatch_and_settle(app, request, timeout_seconds=5.0)

    assert response.status == 200

    received.drain()

    post_bodies = received.get_bodies("/chat.postMessage")
    texts = [b.get("text", "") for b in post_bodies]

    assert any("Running" in t and "one-shot" in t for t in texts)
    assert any("https://github.com/test/repo/pull/42" in t for t in texts)

    update_count = received.get_count("/chat.update")
    assert update_count >= 1


@pytest.mark.asyncio
async def test_one_shot_failure(
    app: AsyncApp,
    build_app_mention_request,
    received: ReceivedRequests,
) -> None:
    """one-shot failure: failure message with exit code, tail output in code blocks."""

    async def fake_stream(
        message: str,
        *,
        timeout_seconds: float,
        on_line: Callable[[str], Awaitable[None]] | None,
    ) -> RunResult:
        if on_line is not None:
            await on_line("Step 1: clone")
            await on_line("Step 2: error occurred")
            await on_line("Fatal: process exited with code 1")
        return RunResult(
            exit_code=1,
            output="Step 1: clone\nStep 2: error occurred\nFatal: process exited with code 1",
        )

    with patch(
        "erkbot.slack_handlers.stream_erk_one_shot",
        side_effect=fake_stream,
    ):
        request: AsyncBoltRequest = build_app_mention_request(f"{BOT_MENTION} one-shot fix readme")
        response = await dispatch_and_settle(app, request, timeout_seconds=5.0)

    assert response.status == 200

    received.drain()

    post_bodies = received.get_bodies("/chat.postMessage")
    texts = [b.get("text", "") for b in post_bodies]

    assert any("failed" in t and "exit 1" in t for t in texts)
    assert any("Fatal:" in t or "error occurred" in t for t in texts)


@pytest.mark.asyncio
async def test_one_shot_update_fallback(
    app: AsyncApp,
    build_app_mention_request,
    mock_server: MockServerThread,
    received: ReceivedRequests,
) -> None:
    """one-shot with chat_update errors: fallback notice posted, output as threaded replies."""
    mock_server.set_error("/chat.update", "channel_not_found")

    async def fake_stream(
        message: str,
        *,
        timeout_seconds: float,
        on_line: Callable[[str], Awaitable[None]] | None,
    ) -> RunResult:
        if on_line is not None:
            await on_line("Creating branch...")
            await on_line("Done!")
        return RunResult(exit_code=0, output="Creating branch...\nDone!")

    with patch(
        "erkbot.slack_handlers.stream_erk_one_shot",
        side_effect=fake_stream,
    ):
        request: AsyncBoltRequest = build_app_mention_request(f"{BOT_MENTION} one-shot fix readme")
        response = await dispatch_and_settle(app, request, timeout_seconds=5.0)

    assert response.status == 200

    received.drain()

    post_bodies = received.get_bodies("/chat.postMessage")
    texts = [b.get("text", "") for b in post_bodies]

    assert any("unavailable" in t.lower() or "channel_not_found" in t for t in texts)
    assert any("Creating branch" in t or "Done" in t for t in texts)
