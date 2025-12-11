"""
Standard aiohttp error handling middleware for HTML error pages.

This middleware catches HTTP exceptions and renders appropriate HTML error pages
using aiohttp-jinja2, following aiohttp best practices.
"""

import functools
import logging
import os
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

import aiohttp_jinja2
from aiohttp import web

from csbot.slackbot.exceptions import UserFacingError
from csbot.slackbot.webapp.error_handling import handle_generic_exception, handle_user_facing_error

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer

logger = logging.getLogger(__name__)


def dev_only(handler):
    @functools.wraps(handler)
    async def wrapped(request, *args, **kwargs):
        if not os.environ.get("DEVELOPMENT"):
            return web.Response(status=404, text="Not Found")
        return await handler(request, *args, **kwargs)

    return wrapped


def build_error_middleware(bot_server: "CompassBotServer"):
    @web.middleware
    async def error_middleware(
        request: web.Request, handler: Callable[[web.Request], Awaitable[web.StreamResponse]]
    ) -> web.StreamResponse:
        """
        Standard aiohttp error handling middleware.

        Catches HTTP exceptions and renders appropriate HTML error pages.
        Follows aiohttp best practices for error handling.
        """
        try:
            return await handler(request)
        except UserFacingError as e:
            return handle_user_facing_error(bot_server.logger, e, request)

        except web.HTTPException as ex:
            # For 401 Unauthorized, render a custom error page
            if ex.status == 401:
                reason = getattr(ex, "text", None) or ex.reason or "Access denied"
                context = {"error_message": reason}
                return aiohttp_jinja2.render_template(
                    "errors/401_unauthorized.html", request, context, status=401
                )

            # Propagate other HTTPExceptions (redirects, etc) normally
            raise
        except Exception as e:
            # Convert any generic exception to a UserFacingError with sensible defaults
            return handle_generic_exception(bot_server.logger, e, request)

    return error_middleware
