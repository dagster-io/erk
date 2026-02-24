# NOTE: @patch usage is deliberate here. erk-slack-bot is a standalone package that
# tests third-party Slack SDK wiring and does not use erk's gateway layer.

import pytest
from slack_bolt.async_app import AsyncApp
from slack_bolt.request.async_request import AsyncBoltRequest

from tests.integration.conftest import dispatch_and_settle
from tests.mock_web_api_server.received_requests import ReceivedRequests


@pytest.mark.asyncio
async def test_ping(
    app: AsyncApp,
    build_message_request,
    received: ReceivedRequests,
) -> None:
    """Dispatching 'ping' through Bolt calls reactions.add and posts 'Pong!'."""
    request: AsyncBoltRequest = build_message_request("ping")
    response = await dispatch_and_settle(app, request, timeout_seconds=5.0)

    assert response.status == 200

    received.drain()

    assert received.get_count("/reactions.add") >= 1
    reaction_bodies = received.get_bodies("/reactions.add")
    assert any(b.get("name") == "eyes" for b in reaction_bodies)

    post_bodies = received.get_bodies("/chat.postMessage")
    assert any("Pong!" in b.get("text", "") for b in post_bodies)
