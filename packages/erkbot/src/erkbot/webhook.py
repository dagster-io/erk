import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def create_webhook_app() -> Starlette:
    routes = [
        Route("/healthz", healthz, methods=["GET"]),
    ]
    return Starlette(routes=routes)


def create_webhook_server(*, app: Starlette, host: str, port: int) -> uvicorn.Server:
    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    return uvicorn.Server(config)
