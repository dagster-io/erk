"""Unit tests for RealHttpClient with mocked httpx calls.

These tests verify that RealHttpClient correctly constructs HTTP requests
and handles responses without making actual network calls.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from erk_shared.gateway.http.abc import HttpError
from erk_shared.gateway.http.real import RealHttpClient


def _make_client() -> RealHttpClient:
    return RealHttpClient(token="test-token", base_url="https://api.github.com")


def _mock_response(*, status_code: int = 200, json_data: object = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = "error text"
    return response


def _mock_no_content_response() -> MagicMock:
    """Mock a 204 No Content response with empty body."""
    response = MagicMock()
    response.status_code = 204
    response.content = b""
    response.text = ""
    response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    return response


def test_get_sends_correct_request() -> None:
    """GET request uses correct method, URL, and headers."""
    with patch("httpx.request") as mock_request:
        mock_request.return_value = _mock_response(json_data={"id": 1})
        client = _make_client()

        result = client.get("repos/owner/repo/issues/42")

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"
        assert args[1] == "https://api.github.com/repos/owner/repo/issues/42"
        assert kwargs["headers"]["Authorization"] == "Bearer test-token"
        assert kwargs["json"] is None
        assert result == {"id": 1}


def test_post_sends_json_body() -> None:
    """POST request includes JSON body."""
    with patch("httpx.request") as mock_request:
        mock_request.return_value = _mock_response(json_data={"created": True})
        client = _make_client()

        result = client.post("repos/owner/repo/issues", data={"title": "New"})

        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert kwargs["json"] == {"title": "New"}
        assert result == {"created": True}


def test_patch_sends_json_body() -> None:
    """PATCH request includes JSON body."""
    with patch("httpx.request") as mock_request:
        mock_request.return_value = _mock_response(json_data={"updated": True})
        client = _make_client()

        result = client.patch("repos/owner/repo/issues/1", data={"state": "closed"})

        args, kwargs = mock_request.call_args
        assert args[0] == "PATCH"
        assert kwargs["json"] == {"state": "closed"}
        assert result == {"updated": True}


def test_get_list_returns_list() -> None:
    """get_list returns a list response."""
    with patch("httpx.request") as mock_request:
        mock_request.return_value = _mock_response(json_data=[{"number": 1}, {"number": 2}])
        client = _make_client()

        result = client.get_list("repos/owner/repo/issues")

        assert result == [{"number": 1}, {"number": 2}]


def test_graphql_sends_query_and_variables() -> None:
    """GraphQL request posts to /graphql with query and variables."""
    with patch("httpx.request") as mock_request:
        mock_request.return_value = _mock_response(json_data={"data": {"viewer": {}}})
        client = _make_client()

        result = client.graphql(query="{ viewer { login } }", variables={"id": "abc"})

        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert args[1] == "https://api.github.com/graphql"
        assert kwargs["json"] == {"query": "{ viewer { login } }", "variables": {"id": "abc"}}
        assert result == {"data": {"viewer": {}}}


def test_error_raises_http_error() -> None:
    """Status code >= 400 raises HttpError."""
    with patch("httpx.request") as mock_request:
        mock_request.return_value = _mock_response(status_code=404)
        client = _make_client()

        with pytest.raises(HttpError) as exc_info:
            client.get("repos/owner/repo/issues/999")

        assert exc_info.value.status_code == 404
        assert exc_info.value.endpoint == "repos/owner/repo/issues/999"


def test_headers_include_github_api_version() -> None:
    """Headers include required GitHub API version."""
    with patch("httpx.request") as mock_request:
        mock_request.return_value = _mock_response()
        client = _make_client()

        client.get("repos/owner/repo")

        headers = mock_request.call_args[1]["headers"]
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"
        assert headers["Accept"] == "application/vnd.github+json"


def test_timeout_is_set() -> None:
    """Requests use a 30s timeout."""
    with patch("httpx.request") as mock_request:
        mock_request.return_value = _mock_response()
        client = _make_client()

        client.get("repos/owner/repo")

        assert mock_request.call_args[1]["timeout"] == 30.0


def test_supports_direct_api() -> None:
    """RealHttpClient reports it supports direct API calls."""
    client = _make_client()
    assert client.supports_direct_api is True


# --- 204 No Content handling ---


def test_post_handles_204_no_content() -> None:
    """POST returns empty dict when response has no body (e.g. workflow dispatch)."""
    with patch("httpx.request") as mock_request:
        mock_request.return_value = _mock_no_content_response()
        client = _make_client()

        result = client.post("repos/o/r/actions/workflows/wf.yml/dispatches", data={"ref": "main"})

        assert result == {}


def test_put_handles_204_no_content() -> None:
    """PUT returns empty dict when response has no body."""
    with patch("httpx.request") as mock_request:
        mock_request.return_value = _mock_no_content_response()
        client = _make_client()

        result = client.put("repos/o/r/some/endpoint", data={"key": "val"})

        assert result == {}


def test_patch_handles_204_no_content() -> None:
    """PATCH returns empty dict when response has no body."""
    with patch("httpx.request") as mock_request:
        mock_request.return_value = _mock_no_content_response()
        client = _make_client()

        result = client.patch("repos/o/r/some/endpoint", data={"key": "val"})

        assert result == {}
