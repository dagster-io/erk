"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from erk_bot_server.config import ServerConfig
from erk_bot_server.context import ServerContext
from erk_bot_server.integrations.claude_runner.real import RealClaudeRunner
from erk_bot_server.integrations.session_store.real import RealSessionStore
from erk_bot_server.routes.sessions import router as sessions_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup/shutdown.

    Creates production context with real implementations on startup.
    """
    config = ServerConfig.from_env()

    # Create real implementations
    session_store = RealSessionStore(redis_url=config.redis_url)
    await session_store.connect()

    claude_runner = RealClaudeRunner()

    # Store context in app state
    app.state.context = ServerContext(
        session_store=session_store,
        claude_runner=claude_runner,
    )

    yield

    # Cleanup on shutdown
    await session_store.disconnect()


def create_app(context: ServerContext | None = None) -> FastAPI:
    """Create FastAPI application.

    Args:
        context: Optional ServerContext for testing. If None, uses lifespan
                 to create production context.

    Returns:
        Configured FastAPI application
    """
    if context is not None:
        # Test mode: use provided context, no lifespan
        app = FastAPI(
            title="Erk Bot Server",
            description="FastAPI server for managing Claude CLI sessions",
            version="0.1.0",
        )
        app.state.context = context
    else:
        # Production mode: use lifespan for DI
        app = FastAPI(
            title="Erk Bot Server",
            description="FastAPI server for managing Claude CLI sessions",
            version="0.1.0",
            lifespan=lifespan,
        )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(sessions_router)

    return app


def run() -> None:
    """Run the server (entry point for CLI)."""
    config = ServerConfig.from_env()
    app = create_app()
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        reload=config.debug,
    )


if __name__ == "__main__":
    run()
