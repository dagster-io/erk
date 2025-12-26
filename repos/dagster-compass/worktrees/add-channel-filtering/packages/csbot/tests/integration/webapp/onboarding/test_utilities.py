"""Tests for onboarding utility functions."""

from csbot.slackbot.slack_utils import (
    generate_team_description,
    generate_team_domain,
    generate_urlsafe_team_name,
)
from csbot.slackbot.webapp.onboarding.shared import is_valid_email


class TestUtilityFunctions:
    """Test utility functions used in the onboarding flow."""

    def test_is_valid_email(self):
        """Test email validation function."""
        # Valid emails
        assert is_valid_email("user@example.com")
        assert is_valid_email("test.user+tag@domain.co.uk")
        assert is_valid_email("a@b.co")

        # Invalid emails
        assert not is_valid_email("")
        assert not is_valid_email("invalid")
        assert not is_valid_email("@domain.com")
        assert not is_valid_email("user@")
        assert not is_valid_email("user@domain")
        assert not is_valid_email("user@@domain.com")

    def test_generate_urlsafe_team_name(self):
        """Test URL-safe team name generation."""
        assert generate_urlsafe_team_name("Pied Piper") == "pied-piper"
        assert generate_urlsafe_team_name("ABC Corp!") == "abc-corp"
        assert generate_urlsafe_team_name("Test__Company") == "test-company"
        assert generate_urlsafe_team_name("Multiple---Dashes") == "multiple-dashes"

    def test_generate_team_domain(self):
        """Test team domain generation with Slack requirements."""
        # Domain should have format: base-name + "-" + 5-char random nonce
        result1 = generate_team_domain("Pied Piper")
        assert result1.startswith("pied-piper-")
        assert len(result1) <= 21
        # Verify nonce is 5 characters (total: "pied-piper-" = 11 + 5 = 16)
        nonce1 = result1.split("-")[-1]
        assert len(nonce1) == 5
        assert nonce1.islower()
        assert nonce1.isalpha()

        result2 = generate_team_domain("ABC Corp")
        assert result2.startswith("abc-corp-")
        assert len(result2) <= 21
        nonce2 = result2.split("-")[-1]
        assert len(nonce2) == 5

        # Test truncation to 21 chars max
        long_name = "Very Long Company Name That Exceeds Limits"
        result3 = generate_team_domain(long_name)
        assert len(result3) <= 21
        # Should end with 5-char nonce after truncation
        nonce3 = result3.split("-")[-1]
        assert len(nonce3) == 5
        assert nonce3.isalpha()

    def test_generate_team_description(self):
        """Test team description generation."""
        assert generate_team_description("Pied Piper") == "Team workspace for Pied Piper"
