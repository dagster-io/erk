"""Background thread running an HTTP server on an auto-assigned port."""

import threading
from http.server import HTTPServer
from queue import Queue

from tests.mock_web_api_server.mock_handler import MockHandler


class MockServerThread(threading.Thread):
    """Runs a mock Slack Web API server in a background thread.

    Uses port=0 for auto-assignment to avoid CI conflicts.
    """

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.queue: Queue = Queue()  # type: ignore[type-arg]
        self.error_endpoints: dict[str, str] = {}

        # Configure handler class state before binding
        MockHandler.received_requests = self.queue
        MockHandler.error_endpoints = self.error_endpoints
        MockHandler._post_message_counter = 0
        MockHandler._counter_lock = threading.Lock()

        self.server = HTTPServer(("localhost", 0), MockHandler)
        self.host, self.port = self.server.server_address

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def run(self) -> None:
        self.server.serve_forever(poll_interval=0.05)

    def stop(self) -> None:
        self.server.shutdown()
        self.join(timeout=5)

    def set_error(self, endpoint: str, error_code: str) -> None:
        """Configure an endpoint to return an error response."""
        self.error_endpoints[endpoint] = error_code

    def clear_error(self, endpoint: str) -> None:
        """Remove error configuration for an endpoint."""
        self.error_endpoints.pop(endpoint, None)

    def reset(self) -> None:
        """Clear all recorded requests and error configurations."""
        while not self.queue.empty():
            self.queue.get_nowait()
        self.error_endpoints.clear()
        MockHandler._post_message_counter = 0


def setup_mock_server() -> MockServerThread:
    """Create and start a mock server thread."""
    server = MockServerThread()
    server.start()
    return server


def teardown_mock_server(server: MockServerThread) -> None:
    """Stop and clean up a mock server thread."""
    server.stop()
