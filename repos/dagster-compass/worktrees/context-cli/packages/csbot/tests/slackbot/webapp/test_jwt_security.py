"""Unit tests for JWT authentication logic in security.py.

Tests pure JWT encoding, decoding, validation, and helper functions
without HTTP integration. These tests focus on:

- JWT token creation and encoding
- JWT token decoding and claim validation
- Token expiration detection
- Signature validation
- Path format validation

These tests run fast (~0.01s each) because they don't require HTTP infrastructure.
For HTTP integration tests (middleware, redirects, cookies), see:
packages/csbot/tests/integration/webapp/test_organization_jwt_auth.py
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import jwt as jwt_lib
import pytest
from pydantic import SecretStr

from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance
from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig
from csbot.slackbot.webapp.security import (
    JWT_AUTH_QUERY_PARAM,
    create_link,
)


@pytest.fixture
def jwt_secret() -> str:
    """Test secret key for JWT signing."""
    return "test-secret-key-for-jwt"


@pytest.fixture
def organization_id() -> int:
    """Test organization ID."""
    return 123


@pytest.fixture
def team_id() -> str:
    """Test team ID."""
    return "T123456789"


@pytest.fixture
def user_id() -> str:
    """Test user ID."""
    return "U123456"


@pytest.fixture
def mock_bot_config(organization_id: int, team_id: str) -> Mock:
    """Create mock bot configuration."""
    mock_config = Mock(spec=CompassBotSingleChannelConfig)
    mock_config.organization_id = organization_id
    mock_config.team_id = team_id
    mock_config.organization_name = "Test Organization"
    return mock_config


@pytest.fixture
def mock_bot(mock_bot_config: Mock, jwt_secret: str) -> Mock:
    """Create mock bot instance with server config."""
    mock_bot_instance = Mock(spec=CompassChannelBaseBotInstance)
    mock_bot_instance.bot_config = mock_bot_config

    mock_server_config = Mock()
    mock_server_config.jwt_secret = SecretStr(jwt_secret)
    mock_server_config.public_url = "http://localhost:8080"
    mock_bot_instance.server_config = mock_server_config

    return mock_bot_instance


# Token Validation Tests


def test_jwt_expired_token_raises_exception(
    jwt_secret: str, organization_id: int, team_id: str, user_id: str
):
    """Test that expired JWT tokens raise ExpiredSignatureError."""
    # Create expired token
    jwt_payload = {
        "organization_id": organization_id,
        "team_id": team_id,
        "user_id": user_id,
        "exp": datetime.now(UTC) - timedelta(hours=1),  # Expired 1 hour ago
    }
    token = jwt_lib.encode(jwt_payload, jwt_secret, algorithm="HS256")

    # Attempt to decode should raise ExpiredSignatureError
    with pytest.raises(jwt_lib.ExpiredSignatureError):
        jwt_lib.decode(token, jwt_secret, algorithms=["HS256"])


def test_jwt_invalid_signature_raises_exception(
    jwt_secret: str, organization_id: int, team_id: str, user_id: str
):
    """Test that JWT tokens with invalid signatures raise InvalidSignatureError."""
    # Create valid token
    jwt_payload = {
        "organization_id": organization_id,
        "team_id": team_id,
        "user_id": user_id,
        "exp": datetime.now(UTC) + timedelta(hours=3),
    }
    token = jwt_lib.encode(jwt_payload, jwt_secret, algorithm="HS256")

    # Tamper with token signature
    parts = token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.{'x' * len(parts[2])}"

    # Attempt to decode should raise InvalidSignatureError
    with pytest.raises(jwt_lib.InvalidSignatureError):
        jwt_lib.decode(tampered_token, jwt_secret, algorithms=["HS256"])


def test_jwt_missing_organization_id_invalid(jwt_secret: str, team_id: str, user_id: str):
    """Test that JWT tokens without organization_id can be decoded but lack required claim."""
    # Create token without organization_id
    jwt_payload = {
        "team_id": team_id,
        "user_id": user_id,
        "exp": datetime.now(UTC) + timedelta(hours=3),
    }
    token = jwt_lib.encode(jwt_payload, jwt_secret, algorithm="HS256")

    # Token decodes successfully
    decoded = jwt_lib.decode(token, jwt_secret, algorithms=["HS256"])

    # But organization_id is missing
    assert "organization_id" not in decoded
    assert decoded["team_id"] == team_id
    assert decoded["user_id"] == user_id


def test_jwt_missing_team_id_invalid(jwt_secret: str, organization_id: int, user_id: str):
    """Test that JWT tokens without team_id can be decoded but lack required claim."""
    # Create token without team_id
    jwt_payload = {
        "organization_id": organization_id,
        "user_id": user_id,
        "exp": datetime.now(UTC) + timedelta(hours=3),
    }
    token = jwt_lib.encode(jwt_payload, jwt_secret, algorithm="HS256")

    # Token decodes successfully
    decoded = jwt_lib.decode(token, jwt_secret, algorithms=["HS256"])

    # But team_id is missing
    assert "team_id" not in decoded
    assert decoded["organization_id"] == organization_id
    assert decoded["user_id"] == user_id


def test_jwt_missing_user_id_invalid(jwt_secret: str, organization_id: int, team_id: str):
    """Test that JWT tokens without user_id can be decoded but lack user claim."""
    # Create token without user_id
    jwt_payload = {
        "organization_id": organization_id,
        "team_id": team_id,
        "exp": datetime.now(UTC) + timedelta(hours=3),
    }
    token = jwt_lib.encode(jwt_payload, jwt_secret, algorithm="HS256")

    # Token decodes successfully
    decoded = jwt_lib.decode(token, jwt_secret, algorithms=["HS256"])

    # But user_id is missing
    assert "user_id" not in decoded
    assert decoded["organization_id"] == organization_id
    assert decoded["team_id"] == team_id


# Token Creation Tests


def test_create_link_generates_valid_jwt_token(mock_bot: Mock, user_id: str, jwt_secret: str):
    """Test that create_link() generates valid JWT tokens with correct claims."""
    path = "/test/page"
    max_age = timedelta(hours=2)

    link = create_link(mock_bot, user_id=user_id, path=path, max_age=max_age)

    # Verify link format
    assert link.startswith(f"http://localhost:8080/test/page?{JWT_AUTH_QUERY_PARAM}=")

    # Extract and decode token
    token = link.split(f"?{JWT_AUTH_QUERY_PARAM}=")[1]
    decoded = jwt_lib.decode(token, jwt_secret, algorithms=["HS256"])

    # Verify organization-based claims
    assert decoded["organization_id"] == mock_bot.bot_config.organization_id
    assert decoded["team_id"] == mock_bot.bot_config.team_id
    assert decoded["user_id"] == user_id

    # Verify no legacy bot_id
    assert "bot_id" not in decoded

    # Verify expiration is approximately correct (within 1 minute)
    exp_time = datetime.fromtimestamp(decoded["exp"], tz=UTC)
    now = datetime.now(UTC)
    time_diff = (exp_time - now).total_seconds()
    assert abs(time_diff - 2 * 3600) < 60  # Within 1 minute of 2 hours


def test_create_link_path_validation(mock_bot: Mock, user_id: str):
    """Test that create_link() validates path format correctly."""
    max_age = timedelta(hours=2)

    # Test path with query parameters is rejected
    with pytest.raises(ValueError) as exc_info:
        create_link(mock_bot, user_id=user_id, path="/test/page?foo=bar", max_age=max_age)
    assert "cannot contain query parameters" in str(exc_info.value)

    # Test path without leading slash is corrected
    link = create_link(mock_bot, user_id=user_id, path="test/page", max_age=max_age)
    assert f"/test/page?{JWT_AUTH_QUERY_PARAM}=" in link
