"""Smoke tests for UserFacingError exception handling system."""

from unittest.mock import Mock, patch

from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from csbot.slackbot.exceptions import UserFacingError
from csbot.slackbot.webapp.error_handling import handle_generic_exception, handle_user_facing_error


class TestUserFacingError:
    """Test UserFacingError exception class and factory methods."""

    def test_basic_initialization(self):
        """Test basic UserFacingError initialization."""
        error = UserFacingError(
            title="Test Error",
            message="This is a test error message",
            details="Technical details here",
            error_type="test",
            suggested_actions=["Action 1", "Action 2"],
            support_info={"key": "value"},
        )

        assert error.title == "Test Error"
        assert error.message == "This is a test error message"
        assert error.details == "Technical details here"
        assert error.error_type == "test"
        assert error.suggested_actions == ["Action 1", "Action 2"]
        assert error.support_info == {"key": "value"}
        assert str(error) == "This is a test error message"

    def test_get_error_context(self):
        """Test get_error_context returns complete context for template rendering."""
        error = UserFacingError(
            title="Test Error",
            message="Test message",
            context={"custom_key": "custom_value"},
            error_type="test",
            suggested_actions=["Action 1"],
            support_info={"support_key": "support_value"},
        )

        context = error.get_error_context()

        assert context["title"] == "Test Error"
        assert context["message"] == "Test message"
        assert context["error_type"] == "test"
        assert context["suggested_actions"] == ["Action 1"]
        assert context["support_info"] == {"support_key": "support_value"}
        assert context["custom_key"] == "custom_value"

    def test_get_support_details(self):
        """Test get_support_details formats error information correctly."""
        error = UserFacingError(
            title="Test Error",
            message="Test message",
            details="Technical details",
            error_type="test",
            context={"context_key": "context_value"},
            support_info={"support_key": "support_value"},
        )

        support_details = error.get_support_details()

        assert "Error Type: test" in support_details
        assert "Title: Test Error" in support_details
        assert "Message: Test message" in support_details
        assert "Technical Details: Technical details" in support_details
        assert "Context:" in support_details
        assert "  context_key: context_value" in support_details
        assert "Support Information:" in support_details
        assert "  support_key: support_value" in support_details

    def test_bot_configuration_error(self):
        """Test bot_configuration_error factory method."""
        error = UserFacingError.bot_configuration_error(
            team_id="T123456789",
            organization="Test Org",
        )

        assert error.title == "Bot Not Configured"
        assert "T123456789" in error.message
        assert error.error_type == "configuration"
        assert error.context["team_id"] == "T123456789"
        assert error.context["organization"] == "Test Org"
        assert error.support_info["error_category"] == "bot_configuration"
        assert len(error.suggested_actions) > 0

    def test_bot_configuration_error_without_organization(self):
        """Test bot_configuration_error factory method without organization."""
        error = UserFacingError.bot_configuration_error(team_id="T123456789")

        assert error.title == "Bot Not Configured"
        assert "T123456789" in error.message
        assert error.context["team_id"] == "T123456789"
        assert "organization" not in error.context

    def test_onboarding_error(self):
        """Test onboarding_error factory method."""
        error = UserFacingError.onboarding_error(
            step="Slack team creation",
            organization="Test Org",
            team_id="T123456789",
            error_details="API returned 500 error",
        )

        assert error.title == "Account Setup Failed"
        assert "Slack team creation" in error.message
        assert error.error_type == "onboarding"
        assert error.context["step"] == "Slack team creation"
        assert error.context["organization"] == "Test Org"
        assert error.context["team_id"] == "T123456789"
        assert error.details == "API returned 500 error"
        assert error.support_info["error_category"] == "onboarding"

    def test_onboarding_error_minimal(self):
        """Test onboarding_error factory method with minimal parameters."""
        error = UserFacingError.onboarding_error(
            step="Authentication",
            organization="Test Org",
        )

        assert error.title == "Account Setup Failed"
        assert "Authentication" in error.message
        assert error.context["organization"] == "Test Org"
        assert "team_id" not in error.context
        assert error.details is None

    def test_slack_api_error_domain_taken(self):
        """Test slack_api_error factory method for domain_taken error."""
        error = UserFacingError.slack_api_error(
            operation="team creation",
            slack_error="domain_taken",
            organization="Test Org",
            team_id="T123456789",
        )

        assert error.title == "Slack Integration Error"
        assert "domain generated from your organization name is already in use" in error.message
        assert error.error_type == "slack_api"
        assert error.context["operation"] == "team creation"
        assert error.context["slack_error"] == "domain_taken"
        assert error.support_info["slack_error_code"] == "domain_taken"
        assert "Go back and choose a different organization name" in error.suggested_actions

    def test_slack_api_error_invalid_auth(self):
        """Test slack_api_error factory method for invalid_auth error."""
        error = UserFacingError.slack_api_error(
            operation="channel listing",
            slack_error="invalid_auth",
            organization="Test Org",
        )

        assert error.title == "Slack Integration Error"
        assert "Bot authentication failed" in error.message
        assert "bot apps need approval" in error.message
        assert "Your workspace was created successfully" in error.suggested_actions

    def test_slack_api_error_generic(self):
        """Test slack_api_error factory method for generic error."""
        error = UserFacingError.slack_api_error(
            operation="user invitation",
            slack_error="rate_limited",
        )

        assert error.title == "Slack Integration Error"
        assert "A Slack API error occurred during user invitation" in error.message
        assert "Contact support with the error details" in error.suggested_actions

    def test_from_generic_exception(self):
        """Test from_generic_exception factory method."""
        original_exception = ValueError("Something went wrong")
        context = {"request_id": "12345"}

        error = UserFacingError.from_generic_exception(
            exception=original_exception,
            additional_context=context,
        )

        assert error.title == "System Error"
        assert "unexpected error occurred" in error.message
        assert error.error_type == "system"
        assert error.details == "ValueError: Something went wrong"
        assert error.context["original_exception_type"] == "ValueError"
        assert error.context["original_exception_message"] == "Something went wrong"
        assert error.context["request_id"] == "12345"
        assert error.support_info["error_category"] == "system_error"


class TestErrorHandling:
    """Test error handling utilities."""

    def create_mock_request(self, method="POST", path="/test"):
        """Create a mock aiohttp request for testing."""
        return make_mocked_request(
            method,
            path,
            headers={"User-Agent": "Test Agent"},
        )

    @patch("aiohttp_jinja2.render_template")
    def test_handle_user_facing_error(self, mock_jinja):
        """Test handle_user_facing_error renders error page correctly."""
        # Setup mock template
        mock_jinja.return_value = "<html>Template Rendered</html>"

        # Create test error and request
        error = UserFacingError(
            title="Test Error",
            message="Test message",
            error_type="configuration",
        )
        request = self.create_mock_request()
        logger = Mock()

        # Call function
        response = handle_user_facing_error(logger, error, request)
        assert response == "<html>Template Rendered</html>"

        # Verify logging
        logger.error.assert_called_once()
        assert "UserFacingError: Test Error - Test message" in logger.error.call_args[0][0]

        # Verify template was called with correct context
        args, kwargs = mock_jinja.call_args
        assert kwargs["status"] == 400  # configuration error should return 400
        render_context = args[2]
        assert render_context["title"] == "Test Error"
        assert render_context["message"] == "Test message"
        assert render_context["error_type"] == "configuration"
        assert render_context["user_agent"] == "Test Agent"

    @patch("aiohttp_jinja2.render_template")
    def test_handle_user_facing_error_system_error(self, mock_jinja):
        """Test handle_user_facing_error returns 500 for system errors."""
        mock_jinja.return_value = "<html>Template Rendered</html>"

        error = UserFacingError(
            title="System Error",
            message="Internal error",
            error_type="system",
        )
        request = self.create_mock_request()
        logger = Mock()

        handle_user_facing_error(logger, error, request)
        _, kwargs = mock_jinja.call_args
        assert kwargs["status"] == 500

    @patch("csbot.slackbot.webapp.error_handling.handle_user_facing_error")
    def test_handle_generic_exception(self, mock_handle_user_facing):
        """Test handle_generic_exception converts exception to UserFacingError."""
        mock_handle_user_facing.return_value = web.Response(text="Error handled")

        original_exception = RuntimeError("Database connection failed")
        request = self.create_mock_request(method="GET", path="/onboarding")
        logger = Mock()
        context = {"session_id": "abc123"}

        response = handle_generic_exception(logger, original_exception, request, context)

        # Verify response
        assert response.text == "Error handled"

        # Verify UserFacingError was created and passed to handler
        mock_handle_user_facing.assert_called_once()
        args = mock_handle_user_facing.call_args[0]

        assert args[0] == logger
        user_facing_error = args[1]
        assert args[2] == request

        # Verify the UserFacingError was created correctly
        assert isinstance(user_facing_error, UserFacingError)
        assert user_facing_error.title == "System Error"
        assert "unexpected error occurred" in user_facing_error.message
        assert user_facing_error.error_type == "system"
        assert user_facing_error.context["original_exception_type"] == "RuntimeError"
        assert (
            user_facing_error.context["original_exception_message"] == "Database connection failed"
        )
        assert user_facing_error.context["request_method"] == "GET"
        assert user_facing_error.context["request_path"] == "/onboarding"
        assert user_facing_error.context["session_id"] == "abc123"

    def test_error_context_merging(self):
        """Test that context is set correctly in factory methods."""
        error = UserFacingError.bot_configuration_error(
            team_id="T123456789",
            organization="Test Org",
        )

        # Verify context was set properly by the factory method
        assert error.context["team_id"] == "T123456789"
        assert error.context["organization"] == "Test Org"

        # Test that additional context merges correctly
        error2 = UserFacingError.from_generic_exception(
            exception=ValueError("test"),
            additional_context={"session_id": "abc123", "request_id": "req456"},
        )

        # Verify custom context was merged with factory-generated context
        assert error2.context["session_id"] == "abc123"
        assert error2.context["request_id"] == "req456"
        assert error2.context["original_exception_type"] == "ValueError"
        assert error2.context["original_exception_message"] == "test"

    def test_empty_context_handling(self):
        """Test that empty or None context is handled properly."""
        error = UserFacingError(
            title="Test",
            message="Test message",
            context=None,
        )

        assert error.context == {}

        # Test get_error_context doesn't fail
        context = error.get_error_context()
        assert isinstance(context, dict)
        assert context["title"] == "Test"

    def test_empty_lists_handling(self):
        """Test that empty lists are handled properly."""
        error = UserFacingError(
            title="Test",
            message="Test message",
            suggested_actions=None,
            support_info=None,
        )

        assert error.suggested_actions == []
        assert error.support_info == {}

        # Test get_support_details doesn't fail with empty data
        support_details = error.get_support_details()
        assert isinstance(support_details, str)
        assert "Error Type:" in support_details
