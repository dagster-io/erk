import unittest

from erkbot.webhook import create_webhook_app, create_webhook_server
from starlette.testclient import TestClient


class TestHealthz(unittest.TestCase):
    def setUp(self) -> None:
        app = create_webhook_app()
        self.client = TestClient(app)

    def test_healthz_returns_ok(self) -> None:
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_unknown_route_returns_404(self) -> None:
        response = self.client.get("/nonexistent")
        self.assertEqual(response.status_code, 404)

    def test_healthz_post_returns_405(self) -> None:
        response = self.client.post("/healthz")
        self.assertEqual(response.status_code, 405)


class TestCreateWebhookServer(unittest.TestCase):
    def test_creates_server_with_config(self) -> None:
        app = create_webhook_app()
        server = create_webhook_server(app=app, host="127.0.0.1", port=9090)
        self.assertEqual(server.config.host, "127.0.0.1")
        self.assertEqual(server.config.port, 9090)
