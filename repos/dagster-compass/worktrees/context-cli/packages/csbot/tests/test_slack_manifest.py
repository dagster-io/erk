"""
Tests for Slack bot manifest parsing and validation.
"""

import json
from pathlib import Path

from csbot.slack_manifest import SlackBotManifest


def test_local_dev_manifest_parses_correctly():
    """Test that the checked-in local dev manifest file parses into the Pydantic model."""
    manifest_path = (
        Path(__file__).parent.parent.parent.parent
        / "infra"
        / "slack_bot_manifests"
        / "local_dev_manifest.json"
    )

    # Ensure the test file exists
    assert manifest_path.exists(), f"Manifest file not found: {manifest_path}"

    # Load and parse the JSON
    with open(manifest_path) as f:
        manifest_data = json.load(f)

    # Validate it parses into the Pydantic model without errors
    manifest = SlackBotManifest.model_validate(manifest_data)

    # Verify key properties are correctly parsed
    assert manifest.display_information.name == "Compass (local dev)"
    assert (
        manifest.display_information.description
        == "Locally served Compass instance configured for websockets"
    )
    assert manifest.features.bot_user.display_name == "Compass (local dev)"
    assert manifest.features.bot_user.always_online is False

    # Verify OAuth scopes are parsed correctly
    expected_bot_scopes = [
        "app_mentions:read",
        "channels:history",
        "channels:join",
        "channels:manage",
        "channels:read",
        "channels:write.invites",
        "chat:write",
        "conversations.connect:manage",
        "conversations.connect:read",
        "conversations.connect:write",
        "files:read",
        "files:write",
        "groups:history",
        "groups:read",
        "groups:write",
        "groups:write.invites",
        "im:history",
        "mpim:history",
        "mpim:read",
        "users:read",
        "chat:write.customize",
        "users:read.email",
        "pins:write",
        "pins:read",
    ]
    assert manifest.oauth_config.scopes.bot == expected_bot_scopes
    assert manifest.oauth_config.scopes.user is None

    # Verify settings are parsed correctly
    assert manifest.settings.socket_mode_enabled is True
    assert manifest.settings.org_deploy_enabled is True
    assert manifest.settings.token_rotation_enabled is False
    assert manifest.settings.interactivity.is_enabled is True

    # Verify event subscriptions
    expected_bot_events = [
        "app_mention",
        "member_joined_channel",
        "message.channels",
        "message.groups",
        "message.im",
        "message.mpim",
        "shared_channel_invite_accepted",
    ]
    assert manifest.settings.event_subscriptions.bot_events == expected_bot_events
