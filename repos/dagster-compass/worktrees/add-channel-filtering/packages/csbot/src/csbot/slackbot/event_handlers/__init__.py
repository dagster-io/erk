"""
Slack Event Handlers

Two transport modes for receiving Slack events:
- HTTP: Production webhooks (scalable, requires public endpoints)
- WebSocket: Development Socket Mode (simple, works behind firewalls)
"""

from .abstract import AbstractSlackEventHandler
from .http_handler import HttpSlackEventHandler
from .websocket_handler import WebSocketSlackEventHandler

__all__ = [
    "AbstractSlackEventHandler",
    "HttpSlackEventHandler",
    "WebSocketSlackEventHandler",
]
