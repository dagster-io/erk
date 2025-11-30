"""Server configuration from environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ServerConfig:
    """Server configuration loaded from environment variables."""

    host: str
    port: int
    redis_url: str
    debug: bool

    @staticmethod
    def from_env() -> "ServerConfig":
        """Load configuration from environment variables."""
        return ServerConfig(
            host=os.environ.get("ERK_BOT_HOST", "0.0.0.0"),
            port=int(os.environ.get("ERK_BOT_PORT", "8000")),
            redis_url=os.environ.get("ERK_BOT_REDIS_URL", "redis://localhost:6379"),
            debug=os.environ.get("ERK_BOT_DEBUG", "false").lower() == "true",
        )
