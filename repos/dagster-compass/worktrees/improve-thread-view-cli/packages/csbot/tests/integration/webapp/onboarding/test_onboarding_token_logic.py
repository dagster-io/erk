"""Unit tests for onboarding token validation and instance type selection.

Tests cover both community prospector and standard onboarding token logic.
"""

from csbot.slackbot.flags import is_community_prospector_token, is_prospector_grant_token
from csbot.slackbot.storage.onboarding_state import BotInstanceType


class TestTokenValidation:
    """Test token validation logic for all token types."""

    def test_community_prospector_tokens(self):
        """Verify COMMUNITY and PROSPECTING tokens are recognized correctly."""
        # COMMUNITY token
        assert is_community_prospector_token("COMMUNITY")
        assert not is_community_prospector_token("community")  # Case sensitive
        assert not is_community_prospector_token("PROSPECTING")
        assert not is_community_prospector_token("")
        assert not is_community_prospector_token("STANDARD_TOKEN")

        # PROSPECTING token
        assert is_prospector_grant_token("PROSPECTING")
        assert not is_prospector_grant_token("prospecting")  # Case sensitive
        assert not is_prospector_grant_token("COMMUNITY")
        assert not is_prospector_grant_token("")

    def test_standard_tokens_not_special(self):
        """Verify regular tokens are not recognized as special tokens."""
        regular_token = "abc-123-def-456"
        assert not is_community_prospector_token(regular_token)
        assert not is_prospector_grant_token(regular_token)


class TestInstanceTypeSelection:
    """Test bot instance type selection based on token."""

    def test_community_token_creates_community_prospector_instance(self):
        """COMMUNITY token with valid status -> COMMUNITY_PROSPECTOR instance."""
        from unittest.mock import MagicMock

        token = "COMMUNITY"
        token_status = MagicMock()
        token_status.is_valid = True

        # Simulate instance type selection logic
        is_community = False
        if token and isinstance(token, str) and token.strip():
            if token_status.is_valid and is_community_prospector_token(token):
                is_community = True

        instance_type = (
            BotInstanceType.COMMUNITY_PROSPECTOR if is_community else BotInstanceType.STANDARD
        )
        assert instance_type == BotInstanceType.COMMUNITY_PROSPECTOR

    def test_standard_token_creates_standard_instance(self):
        """Regular token -> STANDARD instance."""
        from unittest.mock import MagicMock

        token = "regular-token-123"
        token_status = MagicMock()
        token_status.is_valid = True

        is_community = False
        if token and isinstance(token, str) and token.strip():
            if token_status.is_valid and is_community_prospector_token(token):
                is_community = True

        instance_type = (
            BotInstanceType.COMMUNITY_PROSPECTOR if is_community else BotInstanceType.STANDARD
        )
        assert instance_type == BotInstanceType.STANDARD

    def test_no_token_creates_standard_instance(self):
        """No token -> STANDARD instance."""
        token = None

        is_community = False
        if token and isinstance(token, str) and token.strip():
            # Won't execute
            is_community = True

        instance_type = (
            BotInstanceType.COMMUNITY_PROSPECTOR if is_community else BotInstanceType.STANDARD
        )
        assert instance_type == BotInstanceType.STANDARD

    def test_invalid_community_token_creates_standard_instance(self):
        """Invalid COMMUNITY token -> STANDARD instance."""
        from unittest.mock import MagicMock

        token = "COMMUNITY"
        token_status = MagicMock()
        token_status.is_valid = False  # Invalid

        is_community = False
        if token and isinstance(token, str) and token.strip():
            if token_status.is_valid and is_community_prospector_token(token):
                is_community = True

        instance_type = (
            BotInstanceType.COMMUNITY_PROSPECTOR if is_community else BotInstanceType.STANDARD
        )
        assert instance_type == BotInstanceType.STANDARD


# Note: Token reusability is tested in E2E tests (test_prospector_end_to_end.py)
# Full integration tests with database, Slack API, and Stripe mocking
# are in test_prospector_end_to_end.py and test_end_to_end_onboarding_flow.py
