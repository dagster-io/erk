"""HTTP request handler that simulates Slack Web API endpoints."""

import json
import threading
from http.server import BaseHTTPRequestHandler
from queue import Queue
from urllib.parse import parse_qs, urlparse


class MockHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests by returning endpoint-specific Slack API responses.

    Records all requests to a shared queue for test assertions.
    Supports configurable error responses per endpoint.
    """

    # Class-level shared state, set by MockServerThread before starting
    received_requests: Queue  # type: ignore[type-arg]
    error_endpoints: dict[str, str]
    _post_message_counter: int
    _counter_lock: threading.Lock

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""
        body_str = raw_body.decode("utf-8")

        # Parse URL path and query parameters
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = {
            k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed_url.query).items()
        }

        # Parse body - try JSON first, then form-encoded
        parsed_body: dict = {}  # type: ignore[type-arg]
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            if body_str:
                parsed_body = json.loads(body_str)
        elif body_str:
            parsed_body = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(body_str).items()}

        # Merge query params into parsed body (query params as fallback)
        for key, value in query_params.items():
            if key not in parsed_body:
                parsed_body[key] = value

        # Record the request
        self.received_requests.put((path, parsed_body))

        # Check for configured errors
        if path in self.error_endpoints:
            response = json.dumps({"ok": False, "error": self.error_endpoints[path]})
            self._send_response(200, response)
            return

        # Endpoint-specific responses
        if path == "/auth.test":
            response = json.dumps(
                {
                    "ok": True,
                    "url": "https://test-workspace.slack.com/",
                    "team": "Test Team",
                    "user": "testbot",
                    "team_id": "T123",
                    "user_id": "U123",
                    "bot_id": "B123",
                }
            )
        elif path == "/chat.postMessage":
            with self._counter_lock:
                MockHandler._post_message_counter += 1
                ts = f"1234567890.{MockHandler._post_message_counter:06d}"
            channel = parsed_body.get("channel", "C123")
            response = json.dumps(
                {
                    "ok": True,
                    "channel": channel,
                    "ts": ts,
                    "message": {"text": parsed_body.get("text", ""), "ts": ts},
                }
            )
        elif path == "/chat.update":
            response = json.dumps({"ok": True})
        elif path == "/reactions.add":
            response = json.dumps({"ok": True})
        else:
            response = json.dumps({"ok": True})

        self._send_response(200, response)

    def _send_response(self, status: int, body: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json;charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        # Suppress request logging during tests
        pass
