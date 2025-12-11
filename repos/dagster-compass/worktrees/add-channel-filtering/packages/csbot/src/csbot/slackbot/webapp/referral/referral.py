from datetime import timedelta
from typing import TYPE_CHECKING

from aiohttp import web

from csbot.slackbot.webapp.htmlstring import HtmlString
from csbot.slackbot.webapp.referral.utils import (
    is_valid_org_referral_token,
    is_valid_promo_token,
    is_valid_uuid_token,
)
from csbot.slackbot.webapp.utils import _is_test_environment

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer

# Standard cookie name for referral token
REFERRAL_TOKEN_COOKIE_NAME = "compass_referral_token"

# Query parameter name for referral token in URLs
REFERRAL_TOKEN_QUERY_PARAM = "referral-token"


def create_bad_request_exception(
    error_message: HtmlString,
) -> web.HTTPBadRequest:
    """
    Create an HTTPBadRequest exception with custom error message.

    The actual HTML rendering will be handled by error middleware,
    but we can pass custom text to be included in the error page.
    """
    return web.HTTPBadRequest(text=error_message.unsafe_html)


def set_referral_token_cookie_from_token(request: web.Request, bot_server: "CompassBotServer"):
    """Extract referral token from query parameter, validate it, and redirect with cookie if valid.

    This strips the token from the URL to prevent leakage into logs/history
    while preserving all other query parameters (filters, pagination, etc.).

    Token is validated before being set as a cookie to prevent accepting malformed, expired, or
    forged tokens.

    Args:
        request: aiohttp request object
        bot_server: Bot server instance (used to determine secure cookie setting)

    Raises:
        HTTPFound: Redirect to same URL without token parameter, with cookie set
        HTTPUnauthorized: If token is present but invalid/expired
    """
    querystring_token = request.query.get(REFERRAL_TOKEN_QUERY_PARAM)
    if querystring_token:
        if not (
            is_valid_uuid_token(querystring_token)
            or is_valid_org_referral_token(querystring_token)
            or is_valid_promo_token(querystring_token)
        ):
            bot_server.logger.warning(
                f"Unexpected value format for referral token query parameter for {request.path}."
            )
            error_msg = HtmlString(
                unsafe_html="<h1>Unexpected referral token</h1><p>Unexpected value format of the provided referral token. Contact support.</p>"
            )
            raise create_bad_request_exception(error_msg)

        # Preserve all query parameters except the referral token parameter
        preserved_params = {
            k: v for k, v in request.query.items() if k != REFERRAL_TOKEN_QUERY_PARAM
        }
        redirect_path = request.url.path
        if preserved_params:
            query_string = "&".join(f"{k}={v}" for k, v in preserved_params.items())
            redirect_url = f"{redirect_path}?{query_string}"
        else:
            redirect_url = redirect_path

        redirect = web.HTTPFound(redirect_url)

        # Set referral cookie using centralized helper (6 hours = 21600 seconds)
        set_referral_token_cookie(
            response=redirect,
            token=querystring_token,
            max_age=timedelta(hours=6),
            bot_server=bot_server,
        )
        raise redirect


def set_referral_token_cookie(
    response: web.Response,
    token: str,
    max_age: timedelta,
    bot_server: "CompassBotServer",
) -> None:
    """Set referral token cookie on response with proper security settings.

    Args:
        response: aiohttp Response object to set cookie on
        token: referral token string
        max_age: Cookie expiration duration
        bot_server: Bot server instance (for environment detection)
    """
    is_secure = not _is_test_environment(bot_server)
    response.set_cookie(
        REFERRAL_TOKEN_COOKIE_NAME,
        token,
        max_age=int(max_age.total_seconds()),
        httponly=True,
        secure=is_secure,
        samesite="Lax",
    )
