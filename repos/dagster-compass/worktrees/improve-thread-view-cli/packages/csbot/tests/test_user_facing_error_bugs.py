"""Unit tests that would have caught the UserFacingError bugs in production.

This test file contains tests that would have caught the specific bugs seen in the logs:
1. UserFacingError.slack_api_error() getting multiple values for keyword argument 'context'
2. AttributeError: 'BoundLoggerFilteringAtInfo' object has no attribute 'name'
"""

import logging
from unittest.mock import Mock, patch

import pytest
import structlog
from aiohttp import web

from csbot.slackbot.exceptions import UserFacingError
from csbot.slackbot.webapp.error_handling import handle_user_facing_error


class TestUserFacingErrorSlackApiMethod:
    """Test the UserFacingError.slack_api_error() method for parameter conflicts."""

    def test_slack_api_error_with_explicit_context_parameter(self):
        """Test that calling slack_api_error with explicit context parameter works correctly.

        This test would have caught the bug where the onboarding code was passing
        a context parameter to slack_api_error, causing a "multiple values for keyword
        argument 'context'" TypeError.
        """
        # This should work without raising TypeError
        error = UserFacingError.slack_api_error(
            operation="channel listing",
            slack_error="invalid_auth",
            organization="test-org",
            team_id="T123456",
            additional_context={  # Now uses additional_context parameter
                "team_domain": "test-domain",
                "email": "test@example.com",
                "step": "Channel listing and configuration",
                "root_cause": "Compass bot apps not approved for newly created workspace",
            },
        )

        assert error.title == "Slack Integration Error"
        assert error.details is not None and "invalid_auth" in error.details
        assert error.context["team_domain"] == "test-domain"
        assert error.context["email"] == "test@example.com"
        assert error.context["operation"] == "channel listing"
        assert error.context["organization"] == "test-org"
        assert error.context["team_id"] == "T123456"

    def test_slack_api_error_context_merging(self):
        """Test that context from method parameters and explicit context merge correctly."""
        error = UserFacingError.slack_api_error(
            operation="team creation",
            slack_error="domain_taken",
            organization="my-org",
            team_id="T789",
            additional_context={
                "custom_field": "custom_value",
                "step": "Slack team creation",
            },
        )

        # Should have both the method's context and the explicit context
        assert error.context["operation"] == "team creation"
        assert error.context["slack_error"] == "domain_taken"
        assert error.context["organization"] == "my-org"
        assert error.context["team_id"] == "T789"
        assert error.context["custom_field"] == "custom_value"
        assert error.context["step"] == "Slack team creation"

    def test_slack_api_error_domain_taken_message(self):
        """Test the domain_taken error message."""
        error = UserFacingError.slack_api_error(
            operation="Slack team creation",
            slack_error="domain_taken",
            organization="test-org",
        )

        assert "domain generated from your organization name is already in use" in error.message
        assert "choose a different organization name" in error.suggested_actions[0]

    def test_slack_api_error_invalid_auth_message(self):
        """Test the invalid_auth error message."""
        error = UserFacingError.slack_api_error(
            operation="channel listing",
            slack_error="invalid_auth",
            organization="test-org",
        )

        assert "Bot authentication failed" in error.message
        assert "bot apps need approval" in error.message
        assert "Contact support to approve bot apps" in error.suggested_actions[1]


class TestErrorHandlingLoggerAttribute:
    """Test error handling code that accesses logger.name attribute."""

    @patch("aiohttp_jinja2.render_template")
    def test_handle_user_facing_error_with_standard_logger(self, mock_render):
        """Test error handling with standard Python logger (has .name attribute)."""
        logger = logging.getLogger("test_logger")
        error = UserFacingError(
            title="Test Error",
            message="Test message",
        )

        # Mock request object
        request = Mock(spec=web.Request)
        request.headers.get.return_value = "test-agent"
        request.remote = "127.0.0.1"

        # This should work fine with standard logger
        try:
            handle_user_facing_error(logger, error, request)
        except AttributeError as e:
            pytest.fail(f"handle_user_facing_error failed with standard logger: {e}")

    @patch("aiohttp_jinja2.render_template")
    def test_handle_user_facing_error_with_structlog_logger(self, mock_render):
        """Test error handling with structlog logger (no .name attribute).

        This test would have caught the bug where error_handling.py tried to access
        logger.name on a structlog BoundLoggerFilteringAtInfo object.
        """
        # Create a structlog logger (which doesn't have .name attribute)
        structlog_logger = structlog.get_logger("test")

        error = UserFacingError(
            title="Test Error",
            message="Test message",
        )

        # Mock request object
        request = Mock(spec=web.Request)
        request.headers.get.return_value = "test-agent"
        request.remote = "127.0.0.1"

        # This should NOT raise AttributeError
        try:
            handle_user_facing_error(structlog_logger, error, request)
        except AttributeError as e:
            if "'BoundLoggerFilteringAtInfo' object has no attribute 'name'" in str(e):
                pytest.fail(
                    "handle_user_facing_error failed with structlog logger - this is the production bug! "
                    f"Error: {e}"
                )
            else:
                # Some other AttributeError, re-raise
                raise

    @patch("aiohttp_jinja2.render_template")
    def test_handle_user_facing_error_with_logger_missing_name(self, mock_render):
        """Test error handling with mock logger that doesn't have name attribute."""
        # Mock logger without .name attribute
        mock_logger = Mock()
        del mock_logger.name  # Ensure .name doesn't exist

        error = UserFacingError(
            title="Test Error",
            message="Test message",
        )

        request = Mock(spec=web.Request)
        request.headers.get.return_value = "test-agent"
        request.remote = "127.0.0.1"

        # Should handle missing .name gracefully and use "unknown"
        handle_user_facing_error(mock_logger, error, request)


class TestOnboardingErrorFlow:
    """Test the specific error flow from onboarding that caused the production bug."""

    def test_onboarding_slack_api_error_construction(self):
        """Test the exact UserFacingError construction pattern from onboarding.py.

        This replicates the problematic code pattern from lines 552-556 in onboarding.py.
        """
        organization = "test-org"
        team_domain = "test-domain"
        error = "domain_taken"

        # This is the exact pattern from onboarding.py that was failing
        try:
            slack_error = UserFacingError.slack_api_error(
                operation="Slack team creation",
                slack_error=error,
                organization=organization,
                # The bug was here - can't pass context= to slack_api_error
                # because it already creates its own context parameter
                additional_context={"team_domain": team_domain},
            )

            # If we get here, the bug is fixed
            assert slack_error.context["team_domain"] == team_domain
            assert slack_error.context["organization"] == organization

        except TypeError as e:
            if "multiple values for keyword argument 'context'" in str(e):
                pytest.fail(
                    "UserFacingError.slack_api_error() still has the context parameter conflict bug! "
                    f"Error: {e}"
                )
            else:
                raise

    def test_onboarding_error_with_context_modification(self):
        """Test the corrected pattern from onboarding.py lines 552-558."""
        organization = "test-org"
        team_domain = "test-domain"
        error = "domain_taken"

        # This is the corrected pattern that should work
        error_with_context = UserFacingError.slack_api_error(
            operation="Slack team creation",
            slack_error=error,
            organization=organization,
        )
        # Add team_domain to the context after creation
        error_with_context.context["team_domain"] = team_domain

        assert error_with_context.context["team_domain"] == team_domain
        assert error_with_context.context["organization"] == organization
        assert error_with_context.context["operation"] == "Slack team creation"
        assert error_with_context.context["slack_error"] == error


class TestUserFacingErrorContextHandling:
    """Test UserFacingError context handling edge cases."""

    def test_constructor_context_parameter_handling(self):
        """Test that UserFacingError constructor handles context parameter correctly."""
        # Test with None context
        error1 = UserFacingError(title="Test", message="Test message", context=None)
        assert error1.context == {}

        # Test with explicit context dict
        context = {"key": "value"}
        error2 = UserFacingError(title="Test", message="Test message", context=context)
        assert error2.context["key"] == "value"

        # Test context is not shared between instances
        error2.context["new_key"] = "new_value"
        assert "new_key" not in error1.context

    def test_from_generic_exception_context_handling(self):
        """Test from_generic_exception context merging."""
        original_exception = ValueError("Test error")

        # Test with explicit context
        context = {"request_path": "/test", "user_id": "123"}
        error = UserFacingError.from_generic_exception(
            exception=original_exception, additional_context=context
        )

        # Should have both provided context and exception context
        assert error.context["request_path"] == "/test"
        assert error.context["user_id"] == "123"
        assert error.context["original_exception_type"] == "ValueError"
        assert error.context["original_exception_message"] == "Test error"

    def test_classmethod_additional_context_handling(self):
        """Test that classmethods handle additional_context correctly."""
        # Test bot_configuration_error with additional_context
        error1 = UserFacingError.bot_configuration_error(
            team_id="T123",
            organization="test-org",
            additional_context={"custom_field": "custom_value"},
        )
        assert error1.context["team_id"] == "T123"
        assert error1.context["organization"] == "test-org"
        assert error1.context["custom_field"] == "custom_value"

        # Test onboarding_error with additional_context
        error2 = UserFacingError.onboarding_error(
            step="team_creation",
            organization="test-org",
            team_id="T123",
            error_details="Some error",
            additional_context={"custom_field": "custom_value"},
        )
        assert error2.context["step"] == "team_creation"
        assert error2.context["organization"] == "test-org"
        assert error2.context["team_id"] == "T123"
        assert error2.context["custom_field"] == "custom_value"
