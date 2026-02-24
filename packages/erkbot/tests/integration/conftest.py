# NOTE: @patch usage is deliberate here. erk-slack-bot is a standalone package that
# tests third-party Slack SDK wiring and does not use erk's gateway layer.

import asyncio
import json
import time
from collections.abc import Generator
from typing import Any

import pytest
import pytest_asyncio
from erkbot.config import Settings
from erkbot.slack_handlers import register_handlers
from slack_bolt.async_app import AsyncApp
from slack_bolt.request.async_request import AsyncBoltRequest
from slack_bolt.response import BoltResponse
from slack_sdk.signature import SignatureVerifier
from slack_sdk.web.async_client import AsyncWebClient

from erk_shared.gateway.time.fake import FakeTime
from tests.mock_web_api_server.mock_server_thread import (
    MockServerThread,
    setup_mock_server,
    teardown_mock_server,
)
from tests.mock_web_api_server.received_requests import ReceivedRequests


async def dispatch_and_settle(
    app: AsyncApp,
    request: AsyncBoltRequest,
    *,
    timeout_seconds: float,
) -> BoltResponse:
    """Dispatch a Bolt request and wait for all spawned tasks to complete.

    Bolt's AsyncApp dispatches event handlers asynchronously via
    asyncio.ensure_future(), and handlers may spawn additional background
    tasks via asyncio.create_task(). This function awaits all such tasks
    before returning, eliminating the need for sleep-based settling.
    """
    before = asyncio.all_tasks()
    response = await app.async_dispatch(request)

    deadline = asyncio.get_event_loop().time() + timeout_seconds
    while True:
        await asyncio.sleep(0)
        new_pending = [t for t in (asyncio.all_tasks() - before) if not t.done()]
        if not new_pending:
            break
        if asyncio.get_event_loop().time() > deadline:
            task_names = [t.get_name() for t in new_pending]
            raise TimeoutError(f"Tasks did not settle within {timeout_seconds}s: {task_names}")
        await asyncio.gather(*new_pending, return_exceptions=True)

    return response


SIGNING_SECRET = "test-signing-secret-for-integration"
BOT_ID = "B123"
BOT_USER_ID = "U_BOT"
TEST_USER = "U_HUMAN"
TEST_CHANNEL = "C123"


@pytest.fixture(scope="session")
def mock_server() -> Generator[MockServerThread, None, None]:
    server = setup_mock_server()
    yield server
    teardown_mock_server(server)


@pytest.fixture()
def _reset_server(mock_server: MockServerThread) -> Generator[None, None, None]:
    mock_server.reset()
    yield
    mock_server.reset()


@pytest.fixture()
def settings() -> Settings:
    return Settings(SLACK_BOT_TOKEN="xoxb-valid", SLACK_APP_TOKEN="xapp-test")


@pytest.fixture()
def signing_secret() -> str:
    return SIGNING_SECRET


@pytest.fixture()
def signature_verifier(signing_secret: str) -> SignatureVerifier:
    return SignatureVerifier(signing_secret)


@pytest_asyncio.fixture()
async def app(
    mock_server: MockServerThread,
    settings: Settings,
    signing_secret: str,
    _reset_server: None,
) -> AsyncApp:
    """Create a real AsyncApp wired to the mock server."""
    web_client = AsyncWebClient(token="xoxb-valid", base_url=f"{mock_server.base_url}/")
    bolt_app = AsyncApp(
        client=web_client,
        signing_secret=signing_secret,
    )
    register_handlers(bolt_app, settings=settings, bot=None, time=FakeTime())
    return bolt_app


@pytest.fixture()
def received(mock_server: MockServerThread) -> ReceivedRequests:
    return ReceivedRequests(mock_server.queue)


def _build_event_request(
    *,
    event_type: str,
    event_body: dict[str, Any],
    verifier: SignatureVerifier,
) -> AsyncBoltRequest:
    """Build a signed AsyncBoltRequest for an event callback."""
    body_dict = {
        "type": "event_callback",
        "team_id": "T123",
        "event_id": "Ev_test",
        "event": event_body,
    }
    body_str = json.dumps(body_dict)
    timestamp = str(int(time.time()))
    signature = verifier.generate_signature(timestamp=timestamp, body=body_str)
    return AsyncBoltRequest(
        body=body_str,
        headers={
            "content-type": ["application/json"],
            "x-slack-signature": [signature],
            "x-slack-request-timestamp": [timestamp],
        },
    )


@pytest.fixture()
def build_app_mention_request(signature_verifier: SignatureVerifier):
    """Factory fixture: builds a signed app_mention AsyncBoltRequest."""

    def _build(text: str) -> AsyncBoltRequest:
        return _build_event_request(
            event_type="app_mention",
            event_body={
                "type": "app_mention",
                "user": TEST_USER,
                "text": text,
                "channel": TEST_CHANNEL,
                "ts": "1234567890.000001",
            },
            verifier=signature_verifier,
        )

    return _build


@pytest.fixture()
def build_message_request(signature_verifier: SignatureVerifier):
    """Factory fixture: builds a signed message AsyncBoltRequest."""

    def _build(text: str) -> AsyncBoltRequest:
        return _build_event_request(
            event_type="message",
            event_body={
                "type": "message",
                "user": TEST_USER,
                "text": text,
                "channel": TEST_CHANNEL,
                "ts": "1234567890.000001",
            },
            verifier=signature_verifier,
        )

    return _build
