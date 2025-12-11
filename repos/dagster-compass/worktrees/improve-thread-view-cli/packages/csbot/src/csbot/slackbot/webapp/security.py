from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, urlencode, urlparse

import jwt
from aiohttp import web

from csbot.slackbot.webapp.htmlstring import HtmlString
from csbot.slackbot.webapp.utils import _is_test_environment


@dataclass(frozen=True)
class OrganizationContext:
    """Organization authentication context extracted from JWT token."""

    organization_id: int
    team_id: str


@dataclass(frozen=True)
class LegacyViewerContext(OrganizationContext):
    """Viewer authentication context with organization and user information.

    This extends OrganizationContext with the user_id extracted from the legacy jwt token.
    """

    slack_user_id: str | None
    email: str | None


@dataclass(frozen=True)
class ViewerContext(OrganizationContext):
    """Viewer authentication context with organization and user information.

    This extends OrganizationContext with the authenticated user's OrgUser record.
    """

    org_user: "OrgUser"

    def has_permission(self, permission: "Permission") -> bool:
        """Check if the viewer has the specified permission.

        Args:
            permission: Permission to check from Permission enum

        Returns:
            True if user has the permission, False otherwise

        Note:
            Currently, organization admins have all permissions.
            In the future, this could be extended to support more granular permissions.
        """
        # Organization admins have all permissions
        if self.org_user.is_org_admin:
            return True

        # Non-admin users don't have any permissions yet
        # TODO: Add support for per-user permission grants
        return False


@dataclass(frozen=True)
class OnboardingViewerContext(OrganizationContext):
    email: str


if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance
    from csbot.slackbot.storage.interface import OrgUser
    from csbot.slackbot.webapp.grants import Permission

# Standard cookie name for JWT authentication
JWT_AUTH_COOKIE_NAME = "compass_auth_token"

# Cookie name for user-based authentication (contains org_user_id)
COMPASS_AUTH_COOKIE_NAME = "compass_auth"

# Cookie name for onboarding authentication (contains email)
ONBOARDING_AUTH_COOKIE_NAME = "compass_onboarding_auth"

# Query parameter name for JWT token in URLs
JWT_AUTH_QUERY_PARAM = "auth_token"


def create_unauthorized_exception(
    error_message: HtmlString,
) -> web.HTTPUnauthorized:
    """
    Create an HTTPUnauthorized exception with custom error message.

    The actual HTML rendering will be handled by error middleware,
    but we can pass custom text to be included in the error page.
    """
    return web.HTTPUnauthorized(text=error_message.unsafe_html)


def _clear_all_auth_cookies(response: web.Response, keep_cookie: str | None = None) -> None:
    """Clear all authentication cookies except the one being kept.

    This removes any existing onboarding, legacy JWT, and compass auth cookies
    except for the one specified in keep_cookie (if provided).

    Args:
        response: aiohttp Response object to clear cookies from
        keep_cookie: Optional cookie name to keep (not delete)
    """
    # Clear all authentication cookies except the one we're keeping
    for cookie_name in [
        ONBOARDING_AUTH_COOKIE_NAME,
        JWT_AUTH_COOKIE_NAME,
        COMPASS_AUTH_COOKIE_NAME,
    ]:
        if cookie_name != keep_cookie:
            response.del_cookie(cookie_name)


async def ensure_auth_token_cookie_from_token(request: web.Request, bot_server: "CompassBotServer"):
    """Extract JWT token from query parameter, validate it, and redirect with cookie if valid.

    This strips the token from the URL to prevent leakage into logs/history
    while preserving all other query parameters (filters, pagination, etc.).

    Token is validated before being set as a cookie. If the token contains a user_id,
    resolves it to an OrgUser (creating one if needed) and sets a compass_auth cookie
    with the org_user_id. Otherwise, sets the JWT token as a cookie.

    Args:
        request: aiohttp request object
        bot_server: Bot server instance (used to determine secure cookie setting)

    Raises:
        HTTPFound: Redirect to same URL without token parameter, with cookie set
        HTTPUnauthorized: If token is present but invalid/expired
    """
    querystring_token = request.query.get(JWT_AUTH_QUERY_PARAM)
    if querystring_token:
        try:
            decoded = jwt.decode(
                querystring_token,
                bot_server.config.jwt_secret.get_secret_value(),
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError as e:
            bot_server.logger.warning(
                f"JWT auth failed: Expired token in query parameter for {request.path}: {e}"
            )
            error_msg = HtmlString(
                unsafe_html="<h1>Session Expired</h1><p>The authentication link has expired. Please return to Slack and generate a new link.</p>"
            )
            raise create_unauthorized_exception(error_msg)
        except jwt.InvalidTokenError as e:
            bot_server.logger.warning(
                f"JWT auth failed: Invalid token in query parameter for {request.path}: {e}"
            )
            error_msg = HtmlString(
                unsafe_html="<h1>Invalid Authentication</h1><p>The authentication link is invalid. Please return to Slack and generate a new link.</p>"
            )
            raise create_unauthorized_exception(error_msg)

        # Preserve all query parameters except the JWT token parameter
        preserved_params = {k: v for k, v in request.query.items() if k != JWT_AUTH_QUERY_PARAM}
        redirect_path = request.url.path
        if preserved_params:
            query_string = "&".join(f"{k}={v}" for k, v in preserved_params.items())
            redirect_url = f"{redirect_path}?{query_string}"
        else:
            redirect_url = redirect_path

        redirect = web.HTTPFound(redirect_url)

        # Check if token contains user_id - if so, resolve to OrgUser and set compass_auth cookie
        user_id = decoded.get("user_id")
        organization_id = decoded.get("organization_id")
        team_id = decoded.get("team_id")

        if user_id and organization_id and team_id:
            # Try to get existing OrgUser
            org_user = await bot_server.bot_manager.storage.get_org_user_by_slack_user_id(
                slack_user_id=user_id,
                organization_id=organization_id,
            )

            # Create OrgUser if it doesn't exist
            if not org_user:
                # Import locally to avoid circular dependency
                from csbot.slackbot.channel_bot.personalization import get_cached_user_info

                bot = bot_server.get_bot_for_team(team_id)
                user_info = await get_cached_user_info(bot.client, bot.kv_store, user_id)
                if user_info and not user_info.is_bot and user_info.email:
                    org_user = await bot_server.bot_manager.storage.add_org_user(
                        slack_user_id=user_id,
                        email=user_info.email,
                        organization_id=organization_id,
                        is_org_admin=True,
                        name=user_info.real_name,
                    )

            if org_user:
                # Create signed JWT token with org_user_id... we allow a longer expiry, because we can invalidate
                # server side, based on permissions
                set_compass_auth_cookie(
                    response=redirect,
                    max_age=timedelta(hours=24 * 7),
                    bot_server=bot_server,
                    org_user=org_user,
                    team_id=team_id,
                )
            else:
                # Fallback to slack-user based JWT cookie if OrgUser creation failed
                set_jwt_auth_cookie(
                    response=redirect,
                    token=querystring_token,
                    max_age=timedelta(hours=6),
                    bot_server=bot_server,
                )
        else:
            # No user_id in token - fallback to org-based JWT cookie
            set_jwt_auth_cookie(
                response=redirect,
                token=querystring_token,
                max_age=timedelta(hours=6),
                bot_server=bot_server,
            )
        raise redirect


async def check_compass_cookie(
    request: web.Request, bot_server: "CompassBotServer"
) -> ViewerContext | None:
    compass_token = request.cookies.get(COMPASS_AUTH_COOKIE_NAME)
    if not compass_token:
        return None

    try:
        decoded = jwt.decode(
            compass_token, bot_server.config.jwt_secret.get_secret_value(), algorithms=["HS256"]
        )
        org_user_id = decoded.get("org_user_id")

        if org_user_id:
            # Fetch user from database
            org_user = await bot_server.bot_manager.storage.get_org_user_by_id(org_user_id)

            if org_user:
                # Extract organization context from user
                organization_id = org_user.organization_id
                team_id = decoded.get("team_id")

                if team_id:
                    # Validate that at least one bot exists for this organization
                    org_context = OrganizationContext(
                        organization_id=organization_id, team_id=team_id
                    )
                    if not find_bot_for_organization(bot_server, org_context):
                        # No bot found for this organization - invalid context
                        return None

                    return ViewerContext(
                        organization_id=organization_id, team_id=team_id, org_user=org_user
                    )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        pass
    return None


async def check_onboarding_cookie(
    request: web.Request, bot_server: "CompassBotServer"
) -> OnboardingViewerContext | None:
    token = request.cookies.get(ONBOARDING_AUTH_COOKIE_NAME)
    if not token:
        return None
    try:
        decoded = jwt.decode(
            token, bot_server.config.jwt_secret.get_secret_value(), algorithms=["HS256"]
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

    organization_id = decoded.get("organization_id")
    team_id = decoded.get("team_id")
    email = decoded.get("email")

    if not organization_id or not team_id or not email:
        return None

    return OnboardingViewerContext(organization_id=organization_id, team_id=team_id, email=email)


async def check_legacy_jwt_cookie(
    request: web.Request, bot_server: "CompassBotServer", require_user: bool
) -> LegacyViewerContext | None:
    # Fall back to JWT cookie (legacy authentication)
    token = request.cookies.get(JWT_AUTH_COOKIE_NAME)
    if not token:
        return None

    try:
        decoded = jwt.decode(
            token, bot_server.config.jwt_secret.get_secret_value(), algorithms=["HS256"]
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

    organization_id = decoded.get("organization_id")
    team_id = decoded.get("team_id")

    if not organization_id or not team_id:
        return None

    user_id = decoded.get("user_id")
    if not user_id and require_user:
        return None

    email = decoded.get("email")
    return LegacyViewerContext(
        organization_id=organization_id, team_id=team_id, slack_user_id=user_id, email=email
    )


async def ensure_token_is_valid(
    bot_server: "CompassBotServer",
    error_message: Callable[[], Awaitable[HtmlString]],
    request: web.Request,
    require_user: bool = True,
) -> OrganizationContext:
    """Validate JWT token and optionally require user_id claim.

    Uses organization-based authentication (organization_id + team_id).
    Checks compass_auth cookie first (contains org_user_id), then falls back to JWT cookie.

    Args:
        bot_server: Bot server instance
        error_message: Function to generate error message
        request: aiohttp request object
        require_user: If True, requires tokens to include user_id (should be True for all flows except for onboarding)

    Returns:
        OrganizationContext with organization_id and team_id from the authenticated token

    Raises:
        HTTPUnauthorized: If token is invalid or required claims are missing
    """
    await ensure_auth_token_cookie_from_token(request, bot_server)

    # Try compass_auth cookie first (user-based authentication)
    viewer_context = await check_compass_cookie(request, bot_server)
    if viewer_context:
        return viewer_context

    if not require_user:
        org_context = await check_onboarding_cookie(request, bot_server)
        if org_context:
            return org_context

    legacy_context = await check_legacy_jwt_cookie(request, bot_server, require_user)
    if legacy_context:
        return legacy_context

    error_msg = HtmlString(
        unsafe_html="<h1>Access Denied</h1><p>Please access this page through the Slack admin panel to get a valid session.</p>"
    )
    raise create_unauthorized_exception(error_msg)


def require_jwt_user_auth(
    bot_server: "CompassBotServer",
    error_message: Callable[[], HtmlString] | None = None,
) -> Callable[[Callable], Callable]:
    """Decorator to require JWT authentication with user_id for route handlers.

    This decorator is for user-initiated flows where user_id is required.
    For onboarding flows without a user, use require_jwt_org_auth instead.

    Args:
        bot_server: Bot server instance
        error_message: Function to generate error message (optional)

    Returns:
        Decorator function that validates JWT and injects organization_context into handler

    Example:
        @require_jwt_user_auth(
            bot_server=bot_server,
            error_message=lambda: HtmlString(unsafe_html="<h1>Access Denied</h1>")
        )
        async def my_handler(request: web.Request, organization_context: OrganizationContext) -> web.Response:
            # organization_context is automatically injected and validated
            ...
    """
    if error_message is None:

        def default_error_message() -> HtmlString:
            return HtmlString(
                unsafe_html="<h1>Access Denied</h1><p>You don't have permission to access this resource.</p>"
            )

        error_message = default_error_message

    def decorator(handler: Callable) -> Callable:
        @wraps(handler)
        async def wrapper(request: web.Request) -> web.Response:
            organization_context = await ensure_token_is_valid(
                bot_server=bot_server,
                error_message=lambda: _async_error_message(error_message),
                request=request,
                require_user=True,
            )

            # Verify that at least one bot exists for this organization
            organization_bot = find_bot_for_organization(bot_server, organization_context)
            if not organization_bot:
                # Log details about all registered bots for debugging
                bot_server.logger.warning(
                    "JWT auth failed: No bot found for organization",
                    extra={
                        "path": request.path,
                        "organization_id": organization_context.organization_id,
                        "team_id": organization_context.team_id,
                        "registered_bots_count": len(bot_server.bots),
                        "registered_bot_keys": [
                            f"{k.team_id}/{k.channel_name}" for k in bot_server.bots.keys()
                        ],
                    },
                )
                error_msg = HtmlString(
                    unsafe_html="<h1>Bot Not Found</h1><p>No bot found for your organization. Please return to Slack and ensure your bot is properly configured.</p>"
                )
                raise create_unauthorized_exception(error_msg)

            # Pass organization_context to handler (handlers can look up bots themselves if needed)
            return await handler(request, organization_context)

        return wrapper

    return decorator


def require_user(bot_server: "CompassBotServer"):
    """Decorator to require user auth for endpoint handlers.

    Validates authentication via cookies.
    """

    def decorator(handler: Callable) -> Callable:
        @wraps(handler)
        async def wrapper(request: web.Request) -> web.Response:
            # Try compass cookie first (user-based auth with permissions)
            viewer_context = await check_compass_cookie(request, bot_server)
            if viewer_context:
                return await handler(request, viewer_context)

            legacy_context = await check_legacy_jwt_cookie(request, bot_server, require_user=True)
            if legacy_context:
                return await handler(request, legacy_context)

            return web.json_response(
                {"error": "Unauthorized", "message": "Login required"},
                status=401,
            )

        return wrapper

    return decorator


def require_permission(
    bot_server: "CompassBotServer",
    permission: "Permission",
    allow_onboarding_access: bool = False,
) -> Callable[[Callable], Callable]:
    """Decorator to require specific permission for API endpoint handlers.

    Validates authentication via cookies and checks if the required permission is present.
    Returns JSON error responses (suitable for API endpoints).

    Args:
        bot_server: Bot server instance
        permission: Required permission from Permission enum
        allow_onboarding_access: If True, allows access via onboarding cookie when permission check fails

    Returns:
        Decorator function that validates authentication and checks permissions

    Example:
        @require_permission(
            bot_server=bot_server,
            permission=Permission.MANAGE_CONNECTIONS,
            allow_onboarding_access=True
        )
        async def my_api_handler(request: web.Request, organization_context: OrganizationContext) -> web.Response:
            # organization_context is automatically injected and permission is validated
            return web.json_response({"success": True})
    """

    def decorator(handler: Callable) -> Callable:
        @wraps(handler)
        async def wrapper(request: web.Request) -> web.Response:
            # Try compass cookie first (user-based auth with permissions)
            viewer_context = await check_compass_cookie(request, bot_server)
            if viewer_context and viewer_context.has_permission(permission):
                return await handler(request, viewer_context)

            # If allow_onboarding_access is True, try onboarding cookie
            if allow_onboarding_access:
                context = await check_onboarding_cookie(request, bot_server)
                if context:
                    # Onboarding access granted, proceed with handler
                    return await handler(request, context)

            # check the legacy cookie until we've migrated / backfilled org users
            legacy_context = await check_legacy_jwt_cookie(
                request, bot_server, not allow_onboarding_access
            )
            if legacy_context:
                return await handler(request, legacy_context)

            return web.json_response(
                {"error": "Unauthorized", "message": f"Permission required: {permission.value}"},
                status=401,
            )

        return wrapper

    return decorator


async def _async_error_message(error_message: Callable[[], HtmlString]) -> HtmlString:
    """Helper to convert sync error message callable to async."""
    return error_message()


def find_governance_bot_for_organization(
    bot_server: "CompassBotServer", organization_context: OrganizationContext
) -> "CompassChannelBaseBotInstance | None":
    """Find governance or combined bot for a given organization context.

    DEPRECATED: Use find_bot_for_organization instead for non-governance-specific lookups.

    Args:
        bot_server: Bot server instance
        organization_context: Organization context from JWT token

    Returns:
        Bot instance if found, None otherwise
    """
    from csbot.slackbot.channel_bot.bot import BotTypeCombined, BotTypeGovernance

    for bot_instance in bot_server.bots.values():
        if (
            bot_instance.bot_config.organization_id == organization_context.organization_id
            and bot_instance.bot_config.team_id == organization_context.team_id
        ):
            if isinstance(bot_instance.bot_type, (BotTypeGovernance, BotTypeCombined)):
                return bot_instance
    return None


def find_governance_bot_for_organization_with_connection(
    bot_server: "CompassBotServer", organization_context: OrganizationContext, connection_name: str
) -> "CompassChannelBaseBotInstance | None":
    """Find governance or combined bot for a given organization context.

    DEPRECATED: Use find_bot_for_organization instead for non-governance-specific lookups.

    Args:
        bot_server: Bot server instance
        organization_context: Organization context from JWT token

    Returns:
        Bot instance if found, None otherwise
    """
    from csbot.slackbot.channel_bot.bot import BotTypeCombined, BotTypeGovernance

    for bot_instance in bot_server.bots.values():
        if (
            bot_instance.bot_config.organization_id == organization_context.organization_id
            and bot_instance.bot_config.team_id == organization_context.team_id
            and connection_name in bot_instance.profile.connections
        ):
            if isinstance(bot_instance.bot_type, (BotTypeGovernance, BotTypeCombined)):
                return bot_instance
    return None


def find_qa_bot_for_organization_with_connection(
    bot_server: "CompassBotServer",
    organization_context: OrganizationContext,
    connection_name: str,
) -> "CompassChannelBaseBotInstance | None":
    """Find data channel bot (QA or Combined) that has a specific connection.

    This function finds the bot instance that has the connection in its profile,
    which is needed for dataset operations that require database access.

    In a legacy setup with separate governance and data bots, this returns the
    data bot. In a combined bot setup, this returns the combined bot.

    Args:
        bot_server: Bot server instance
        organization_context: Organization context from JWT token
        connection_name: Name of the connection to find

    Returns:
        Bot instance with the connection if found, None otherwise
    """
    for bot_instance in bot_server.bots.values():
        if (
            bot_instance.bot_config.organization_id == organization_context.organization_id
            and bot_instance.bot_config.team_id == organization_context.team_id
            and connection_name in bot_instance.profile.connections
        ):
            return bot_instance
    return None


def find_bot_for_organization(
    bot_server: "CompassBotServer", organization_context: OrganizationContext
) -> "CompassChannelBaseBotInstance | None":
    """Find any bot instance for a given organization context.

    No longer requires a governance bot - works with any bot type.

    Args:
        bot_server: Bot server instance
        organization_context: Organization context from JWT token

    Returns:
        Bot instance if found, None otherwise
    """
    for bot_instance in bot_server.bots.values():
        if (
            bot_instance.bot_config.organization_id == organization_context.organization_id
            and bot_instance.bot_config.team_id == organization_context.team_id
        ):
            return bot_instance
    return None


def create_organization_jwt_token(
    jwt_secret: str,
    organization_id: int,
    team_id: str,
    max_age: timedelta,
    user_id: str | None = None,
    email: str | None = None,
) -> str:
    """Create JWT token for organization-based authentication.

    Used during onboarding or system operations where no user context exists yet.

    Args:
        jwt_secret: JWT secret for signing tokens
        organization_id: Organization ID
        team_id: Slack team ID
        max_age: Token expiration duration
        user_id: Optional Slack user ID for attribution (use None for system operations)

    Returns:
        Encoded JWT token string
    """
    payload = {
        "organization_id": organization_id,
        "team_id": team_id,
        "exp": datetime.now(UTC) + max_age,
    }
    if user_id is not None:
        payload["user_id"] = user_id
    if email is not None:
        payload["email"] = email
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


def create_slack_user_jwt_token(
    jwt_secret: str,
    organization_id: int,
    team_id: str,
    user_id: str,
    max_age: timedelta,
) -> str:
    """Create JWT token for user-initiated flows.

    This is the standard token creation function for user-initiated operations.
    Always includes user_id for attribution and audit trail.

    Args:
        jwt_secret: JWT secret for signing tokens
        organization_id: Organization ID
        team_id: Slack team ID
        user_id: Slack user ID (required for user-initiated flows)
        max_age: Token expiration duration

    Returns:
        Encoded JWT token string
    """
    return create_organization_jwt_token(
        jwt_secret=jwt_secret,
        organization_id=organization_id,
        team_id=team_id,
        user_id=user_id,
        max_age=max_age,
    )


def set_jwt_auth_cookie(
    response: web.Response,
    token: str,
    max_age: timedelta,
    bot_server: "CompassBotServer",
) -> None:
    """Set JWT authentication cookie on response with proper security settings.

    Centralizes cookie setting logic including:
    - Cookie name (JWT_AUTH_COOKIE_NAME)
    - Security flags (httponly, secure, samesite)
    - Environment-aware secure flag
    - Clears other auth cookies before setting this one

    Args:
        response: aiohttp Response object to set cookie on
        token: JWT token string
        max_age: Cookie expiration duration
        bot_server: Bot server instance (for environment detection)
    """
    # Clear other auth cookies before setting this one
    _clear_all_auth_cookies(response, keep_cookie=JWT_AUTH_COOKIE_NAME)

    is_secure = not _is_test_environment(bot_server)
    response.set_cookie(
        JWT_AUTH_COOKIE_NAME,
        token,
        max_age=int(max_age.total_seconds()),
        httponly=True,
        secure=is_secure,
        samesite="Lax",
    )


def set_onboarding_auth_cookie(
    response: web.Response,
    bot_server: "CompassBotServer",
    max_age: timedelta,
    organization_id: int,
    team_id: str,
    email: str,
) -> None:
    """Set onboarding auth cookie on response with proper security settings.

    Similar to set_jwt_auth_cookie but uses ONBOARDING_AUTH_COOKIE_NAME.
    The token contains organization_id, team_id, and email.
    Clears other auth cookies before setting this one.

    Args:
        response: aiohttp Response object to set cookie on
        bot_server: Bot server instance (for environment detection)
        max_age: Cookie expiration duration
        organization_id: Organization ID
        team_id: Slack team ID
        email: User email
    """
    # Clear other auth cookies before setting this one
    _clear_all_auth_cookies(response, keep_cookie=ONBOARDING_AUTH_COOKIE_NAME)

    is_secure = not _is_test_environment(bot_server)
    token = jwt.encode(
        {
            "organization_id": organization_id,
            "team_id": team_id,
            "email": email,
            "exp": datetime.now(UTC) + max_age,
        },
        bot_server.config.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    response.set_cookie(
        ONBOARDING_AUTH_COOKIE_NAME,
        token,
        max_age=int(max_age.total_seconds()),
        httponly=True,
        secure=is_secure,
        samesite="Lax",
    )


def set_compass_auth_cookie(
    response: web.Response,
    max_age: timedelta,
    bot_server: "CompassBotServer",
    org_user: "OrgUser",
    team_id: str,
) -> None:
    """Set compass_auth cookie on response with proper security settings.

    Similar to set_jwt_auth_cookie but uses COMPASS_AUTH_COOKIE_NAME.
    The token contains org_user_id in its claims.
    Clears other auth cookies before setting this one.

    Args:
        response: aiohttp Response object to set cookie on
        max_age: Cookie expiration duration
        bot_server: Bot server instance (for environment detection)
        org_user: OrgUser instance
        team_id: Slack team ID
    """
    # Clear other auth cookies before setting this one
    _clear_all_auth_cookies(response, keep_cookie=COMPASS_AUTH_COOKIE_NAME)

    is_secure = not _is_test_environment(bot_server)
    token = jwt.encode(
        {
            "organization_id": org_user.organization_id,
            "org_user_id": org_user.id,
            "team_id": team_id,
            "exp": datetime.now(UTC) + max_age,
        },
        bot_server.config.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    response.set_cookie(
        COMPASS_AUTH_COOKIE_NAME,
        token,
        max_age=int(max_age.total_seconds()),
        httponly=True,
        secure=is_secure,
        samesite="Lax",
    )


def create_link(
    bot: "CompassChannelBaseBotInstance", user_id: str, path: str, max_age: timedelta
) -> str:
    """Create authenticated link for user-initiated flows.

    Uses user-based authentication (organization_id + team_id + user_id).
    Always includes user_id for attribution and audit trail.

    Args:
        bot: Bot instance (provides organization and team context)
        user_id: Slack user ID for attribution
        path: URL path (must not contain query parameters)
        max_age: Token expiration duration

    Returns:
        Full URL with JWT token in query string
    """
    jwt_token = create_slack_user_jwt_token(
        jwt_secret=bot.server_config.jwt_secret.get_secret_value(),
        organization_id=bot.bot_config.organization_id,
        team_id=bot.bot_config.team_id,
        user_id=user_id,
        max_age=max_age,
    )
    if "?" in path:
        raise ValueError("Path cannot contain query parameters")
    if not path.startswith("/"):
        path = "/" + path
    return f"{bot.server_config.public_url}{path}?{JWT_AUTH_QUERY_PARAM}={jwt_token}"


def create_governance_link(
    bot: "CompassChannelBaseBotInstance",
    pr_or_issue_number: str | int,
    *,
    user_id: str,
    max_age: timedelta | None = None,
) -> str:
    """Create a JWT-authenticated link to view the governance page.

    It includes request id in the query parameters to allow for easy navigation to the request.
    """
    if max_age is None:
        # max_age=None defaults to 6 hours for context update links
        max_age = timedelta(hours=6)

    request_id = str(pr_or_issue_number)
    governance_link = create_link(
        bot,
        user_id,
        "/context-governance",
        max_age,
    )
    parsed = urlparse(governance_link)
    query_params = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key != "request"
    ]
    query_params.append(("request", request_id))
    return parsed._replace(query=urlencode(query_params)).geturl()
