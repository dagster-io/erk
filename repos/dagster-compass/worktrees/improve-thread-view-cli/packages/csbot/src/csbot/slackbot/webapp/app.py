import os
from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp_jinja2
import jinja2
from aiohttp import web
from ddtrace.contrib.aiohttp import trace_app
from ddtrace.trace import tracer

from csbot.slackbot.webapp.middleware import build_error_middleware

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer


def build_web_application(bot_server: "CompassBotServer"):
    app = web.Application()

    if os.getenv("DD_ENV"):
        trace_app(app, tracer, service="compass-bot")

    # we wrap trace middleware with error middleware so that tracing
    # sees the underlying exception
    app.middlewares.insert(0, build_error_middleware(bot_server))

    # Setup Jinja2 templating with aiohttp integration
    templates_dir = Path(__file__).parent / "templates"
    env_name = os.getenv("COMPASS_ENV")

    async def add_env_context(request: web.Request) -> dict[str, str | None]:
        return {"env_name": env_name}

    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(templates_dir),
        autoescape=True,
        context_processors=[add_env_context],
    )

    return app
