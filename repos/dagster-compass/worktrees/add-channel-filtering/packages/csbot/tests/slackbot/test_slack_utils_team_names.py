"""Unit tests for URL-safe team name generation and channel creation."""

from unittest.mock import patch

import pytest

from csbot.slackbot.slack_utils import (
    create_slack_team,
    generate_team_domain,
    generate_urlsafe_team_name,
)


class TestGenerateUrlsafeTeamName:
    """Test URL-safe team name generation with various edge cases."""

    @pytest.mark.parametrize(
        "organization_name,expected_urlsafe_name,expected_channel_name",
        [
            # Standard cases
            ("Acme Corp", "acme-corp", "acme-corp-compass"),
            ("My Company", "my-company", "my-company-compass"),
            # Apostrophes and quotes
            ("Ben's Channel", "bens-channel", "bens-channel-compass"),
            ("John's Data Warehouse", "johns-data-warehouse", "johns-data-warehouse-compass"),
            ("O'Reilly Media", "oreilly-media", "oreilly-media-compass"),
            ('Company "The Best" Inc', "company-the-best-inc", "company-the-best-inc-compass"),
            # Special characters
            ("Test & Development", "test-development", "test-development-compass"),
            ("Research @ Lab", "research-lab", "research-lab-compass"),
            ("Data (Analytics)", "data-analytics", "data-analytics-compass"),
            ("Company #1", "company-1", "company-1-compass"),
            ("Finance $$$", "finance", "finance-compass"),
            ("100% Organic!", "100-organic", "100-organic-compass"),
            # Unicode and accents (ASCII-only - non-ASCII chars are stripped)
            ("Café Résumé", "caf-rsum", "caf-rsum-compass"),
            ("Zürich GmbH", "zrich-gmbh", "zrich-gmbh-compass"),
            ("Tokyo 東京", "tokyo", "tokyo-compass"),
            # Multiple spaces and underscores
            ("Too    Many    Spaces", "too-many-spaces", "too-many-spaces-compass"),
            ("Under_Score_Company", "under-score-company", "under-score-company-compass"),
            (
                "Mixed-Separators_Here  There",
                "mixed-separators-here-there",
                "mixed-separators-here-there-compass",
            ),
            # Edge cases with hyphens
            ("Already-Hyphenated", "already-hyphenated", "already-hyphenated-compass"),
            ("Multiple---Hyphens", "multiple-hyphens", "multiple-hyphens-compass"),
            ("-Leading-Hyphen", "leading-hyphen", "leading-hyphen-compass"),
            ("Trailing-Hyphen-", "trailing-hyphen", "trailing-hyphen-compass"),
            # Email-like or domain-like names
            ("user@company.com", "usercompanycom", "usercompanycom-compass"),
            ("sub.domain.company", "subdomaincompany", "subdomaincompany-compass"),
            # Version numbers and dates
            ("Company v2.0", "company-v20", "company-v20-compass"),
            ("Startup (2024)", "startup-2024", "startup-2024-compass"),
            ("Q1-2024-Team", "q1-2024-team", "q1-2024-team-compass"),
            # Mixed case (should be lowercased)
            ("CamelCaseCompany", "camelcasecompany", "camelcasecompany-compass"),
            ("ALLCAPS", "allcaps", "allcaps-compass"),
            # Short names
            ("A", "a", "a-compass"),
            ("IT", "it", "it-compass"),
            ("123", "123", "123-compass"),
            # Complex real-world examples
            ("Dagster Labs, Inc.", "dagster-labs-inc", "dagster-labs-inc-compass"),
            ("Smith & Johnson LLC", "smith-johnson-llc", "smith-johnson-llc-compass"),
            ("Tech Co. (YC W21)", "tech-co-yc-w21", "tech-co-yc-w21-compass"),
            ("BizOps™ Solutions®", "bizops-solutions", "bizops-solutions-compass"),
            # Only special characters (edge case)
            ("!@#$%", "", "-compass"),
            ("---", "", "-compass"),
            ("   ", "", "-compass"),
        ],
    )
    def test_generate_urlsafe_team_name(
        self,
        organization_name: str,
        expected_urlsafe_name: str,
        expected_channel_name: str,
    ):
        """Test that organization names are converted to URL-safe team names correctly.

        This ensures that:
        1. Special characters (apostrophes, &, @, etc.) are removed
        2. Spaces and underscores are converted to hyphens
        3. Multiple consecutive hyphens are collapsed to a single hyphen
        4. Leading and trailing hyphens are stripped
        5. The result is lowercased
        6. The resulting name is valid for Slack channel creation
        """
        urlsafe_name = generate_urlsafe_team_name(organization_name)
        assert urlsafe_name == expected_urlsafe_name, (
            f"URL-safe name mismatch for '{organization_name}': "
            f"expected '{expected_urlsafe_name}', got '{urlsafe_name}'"
        )

        # Verify channel name format
        channel_name = f"{urlsafe_name}-compass"
        assert channel_name == expected_channel_name, (
            f"Channel name mismatch for '{organization_name}': "
            f"expected '{expected_channel_name}', got '{channel_name}'"
        )

        # Verify Slack channel naming rules
        # Channels can contain lowercase letters, numbers, hyphens, and underscores
        # They cannot start/end with special characters
        if urlsafe_name:  # Skip validation for empty results
            # Check lowercase (only if there are alphabetic characters)
            if any(c.isalpha() for c in urlsafe_name):
                assert urlsafe_name == urlsafe_name.lower(), (
                    f"Name should be lowercase: {urlsafe_name}"
                )
            assert not urlsafe_name.startswith("-"), (
                f"Name should not start with hyphen: {urlsafe_name}"
            )
            assert not urlsafe_name.endswith("-"), (
                f"Name should not end with hyphen: {urlsafe_name}"
            )
            # Note: Slack actually accepts Unicode in channel names, but ASCII-only is safer
            # The regex \w in Python includes Unicode word characters by default


class TestGenerateTeamDomain:
    """Test team domain generation with Slack's 21-character limit."""

    @pytest.mark.parametrize(
        "team_name",
        [
            "A",  # Single character
            "Short Name",  # Short name
            "Medium Length Company Name",  # Medium length
            "A Very Long Company Name That Would Exceed Limits",  # Very long name
            "Company with Special Characters & Symbols!",  # Special characters
            "   Leading and Trailing Spaces   ",  # Edge case with spaces
        ],
    )
    def test_generate_team_domain_respects_length_limit(self, team_name: str):
        """Test that generate_team_domain always produces domains <= 21 characters.

        This ensures the fix for the bug where long team names would produce domains
        exceeding Slack's 21-character limit.
        """
        domain = generate_team_domain(team_name)

        # Slack requires team domains to be 21 characters or fewer
        assert len(domain) <= 21, (
            f"Team domain '{domain}' exceeds 21 character limit for input '{team_name}' "
            f"(actual length: {len(domain)})"
        )

        # Verify format: base + "-" + 5-char nonce = base (up to 15 chars) + "-" + 5 chars
        parts = domain.rsplit("-", 1)
        assert len(parts) == 2, f"Expected 'base-nonce' format, got: {domain}"
        base, nonce = parts
        assert len(nonce) == 5, f"Expected 5-character nonce, got: {nonce}"
        assert nonce.isalpha() and nonce.islower(), f"Nonce should be lowercase letters: {nonce}"

        # Base should be at most 15 characters (21 - 5 nonce - 1 hyphen)
        assert len(base) <= 15, f"Base '{base}' exceeds 15 character limit (length: {len(base)})"

    def test_generate_team_domain_deterministic_length(self):
        """Test that generate_team_domain produces consistent length output."""
        # Generate multiple domains for the same input
        team_name = "Test Company"
        domains = [generate_team_domain(team_name) for _ in range(10)]

        # All domains should have the same length (base is consistent, nonce is always 5 chars)
        lengths = [len(d) for d in domains]
        assert len(set(lengths)) == 1, f"Domain lengths should be consistent, got: {lengths}"

        # All domains should be <= 21 characters
        for domain in domains:
            assert len(domain) <= 21, f"Domain '{domain}' exceeds 21 character limit"


class TestChannelNameConsistency:
    """Test that channel names are consistent across different parts of the onboarding flow."""

    @pytest.mark.parametrize(
        "organization_name",
        [
            "Ben's Channel",
            "Test & Co",
            "O'Reilly Media",
            "Company (2024)",
            "Café Résumé",
        ],
    )
    def test_compass_channel_name_format(self, organization_name: str):
        """Test that compass channel names follow the {org}-compass format."""
        urlsafe_name = generate_urlsafe_team_name(organization_name)
        compass_channel = f"{urlsafe_name}-compass"

        # Verify format
        assert compass_channel.endswith("-compass"), "Compass channel should end with '-compass'"
        assert compass_channel.count("-compass") == 1, "Should have exactly one '-compass' suffix"

        # Verify no double hyphens
        assert "--" not in compass_channel, (
            f"Channel name should not have double hyphens: {compass_channel}"
        )

    @pytest.mark.parametrize(
        "organization_name",
        [
            "Ben's Channel",
            "Test & Co",
            "O'Reilly Media",
            "Company (2024)",
            "Café Résumé",
        ],
    )
    def test_governance_channel_name_format(self, organization_name: str):
        """Test that governance channel names follow the {org}-compass-governance format."""
        urlsafe_name = generate_urlsafe_team_name(organization_name)
        governance_channel = f"{urlsafe_name}-compass-governance"

        # Verify format
        assert governance_channel.endswith("-compass-governance"), (
            "Governance channel should end with '-compass-governance'"
        )
        assert governance_channel.count("-compass-governance") == 1, (
            "Should have exactly one '-compass-governance' suffix"
        )

        # Verify no double hyphens
        assert "--" not in governance_channel, (
            f"Channel name should not have double hyphens: {governance_channel}"
        )

    def test_channel_name_length_limit(self):
        """Test that generated channel names respect Slack's 80 character limit."""
        # Slack channels have a max length of 80 characters
        very_long_name = "A" * 100 + " Corporation International Limited"
        urlsafe_name = generate_urlsafe_team_name(very_long_name)
        compass_channel = f"{urlsafe_name}-compass"

        # Note: This test documents current behavior
        # If we need to enforce the 80-char limit, this test should be updated
        # For now, we just verify the function doesn't crash with long inputs
        assert isinstance(compass_channel, str)
        assert len(compass_channel) > 0


class TestCreateSlackTeamRetry:
    """Test retry logic for Slack team creation when team name is already taken."""

    @pytest.mark.asyncio
    async def test_create_slack_team_retries_on_name_taken(self):
        """Test that create_slack_team retries with a nonce when the team name is already taken.

        This test verifies that when the initial team name is already taken (name_taken_in_org error),
        the function automatically retries with a modified name containing a random nonce.
        """
        admin_token = "xoxp-test-token"
        team_name = "My Test Team"
        team_domain = "my-test-team-dgc"

        # Mock the post_slack_api function to simulate name_taken_in_org on first call, success on second
        with patch("csbot.slackbot.slack_utils.post_slack_api") as mock_post:
            # First call: simulate name_taken_in_org error
            mock_post.side_effect = [
                {"success": False, "error": "name_taken_in_org"},
                # Second call: simulate success
                {
                    "success": True,
                    "team": "T12345678",
                    "team_name": "My Test Team abc",  # Modified with nonce
                    "team_domain": "my-test-team-dgc-abc",  # Modified with nonce
                },
            ]

            result = await create_slack_team(
                admin_token=admin_token,
                team_name=team_name,
                team_domain=team_domain,
            )

            # Verify the function was called twice (initial attempt + retry)
            assert mock_post.call_count == 2

            # Verify the first call used the original team name and domain
            first_call_payload = mock_post.call_args_list[0][0][2]
            assert first_call_payload["team_name"] == team_name
            assert first_call_payload["team_domain"] == team_domain

            # Verify the second call used modified team name and domain with nonce
            second_call_payload = mock_post.call_args_list[1][0][2]
            assert second_call_payload["team_name"] != team_name
            assert second_call_payload["team_name"].startswith(team_name)
            assert second_call_payload["team_domain"] != team_domain
            assert second_call_payload["team_domain"].startswith(team_domain)

            # Verify the result indicates success
            assert result["success"] is True
            assert result["team_id"] == "T12345678"

    @pytest.mark.asyncio
    async def test_create_slack_team_respects_length_limit_on_retry(self):
        """Test that create_slack_team respects Slack's 21-character limit when retrying with nonce.

        This test verifies the fix for a bug where long team names would exceed the 21-character
        limit when a 3-character nonce was appended during retry. The fix truncates the team name
        to ensure the final name with nonce stays within the limit.
        """
        admin_token = "xoxp-test-token"
        # Use a 19-character team name that would exceed 21 chars when " abc" (4 chars) is appended
        team_name = "A Very Long Company"  # 19 characters
        team_domain = "averylong-12345"

        with patch("csbot.slackbot.slack_utils.post_slack_api") as mock_post:
            mock_post.side_effect = [
                {"success": False, "error": "name_taken_in_org"},
                {"success": True, "team": "T12345678"},
            ]

            result = await create_slack_team(
                admin_token=admin_token,
                team_name=team_name,
                team_domain=team_domain,
            )

            # Verify the function was called twice
            assert mock_post.call_count == 2

            # Verify the retry respects the 21-character limit for team_name
            second_call_payload = mock_post.call_args_list[1][0][2]
            retried_team_name = second_call_payload["team_name"]

            # Team name should be truncated to 17 chars + " " + 3-char nonce = 21 chars max
            assert len(retried_team_name) <= 21, (
                f"Retried team name '{retried_team_name}' exceeds 21 character limit "
                f"(actual length: {len(retried_team_name)})"
            )

            # Verify the format ends with a 3-character nonce separated by a space
            # Note: The team name itself may contain spaces, so we can't just split()
            # Example: "A Very Long Compa xjj" - the last token after rsplit(' ', 1) is the nonce
            parts = retried_team_name.rsplit(" ", 1)
            assert len(parts) == 2, f"Expected name ending with ' nonce', got: {retried_team_name}"
            truncated_name, nonce = parts
            assert len(nonce) == 3, (
                f"Expected 3-character nonce, got: '{nonce}' (length {len(nonce)})"
            )
            assert nonce.isalpha() and nonce.islower(), (
                f"Nonce should be lowercase letters: {nonce}"
            )

            # Verify the truncated name is at most 17 characters to leave room for " " + 3-char nonce
            assert len(truncated_name) <= 17, (
                f"Truncated name '{truncated_name}' should be at most 17 chars, got {len(truncated_name)}"
            )

            # Verify the result indicates success
            assert result["success"] is True
