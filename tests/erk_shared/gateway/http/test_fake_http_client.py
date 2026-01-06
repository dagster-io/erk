"""Tests for FakeHttpClient - Layer 1 fake infrastructure tests."""

import pytest

from erk_shared.gateway.http.abc import HttpError
from erk_shared.gateway.http.fake import FakeHttpClient, RecordedRequest


def test_patch_records_request() -> None:
    """PATCH request should be recorded."""
    client = FakeHttpClient()
    client.set_response("repos/owner/repo/issues/123", response={"state": "closed"})

    result = client.patch("repos/owner/repo/issues/123", data={"state": "closed"})

    assert result == {"state": "closed"}
    assert len(client.requests) == 1
    assert client.requests[0] == RecordedRequest(
        method="PATCH",
        endpoint="repos/owner/repo/issues/123",
        data={"state": "closed"},
    )


def test_post_records_request() -> None:
    """POST request should be recorded."""
    client = FakeHttpClient()
    client.set_response("repos/owner/repo/issues", response={"number": 456})

    result = client.post("repos/owner/repo/issues", data={"title": "New issue"})

    assert result == {"number": 456}
    assert len(client.requests) == 1
    assert client.requests[0] == RecordedRequest(
        method="POST",
        endpoint="repos/owner/repo/issues",
        data={"title": "New issue"},
    )


def test_get_records_request() -> None:
    """GET request should be recorded with None data."""
    client = FakeHttpClient()
    client.set_response("repos/owner/repo/issues/789", response={"title": "Test"})

    result = client.get("repos/owner/repo/issues/789")

    assert result == {"title": "Test"}
    assert len(client.requests) == 1
    assert client.requests[0] == RecordedRequest(
        method="GET",
        endpoint="repos/owner/repo/issues/789",
        data=None,
    )


def test_unconfigured_endpoint_returns_empty_dict() -> None:
    """Unconfigured endpoints should return empty dict."""
    client = FakeHttpClient()

    result = client.get("repos/unknown/endpoint")

    assert result == {}


def test_set_error_raises_on_request() -> None:
    """Configured errors should raise HttpError."""
    client = FakeHttpClient()
    client.set_error(
        "repos/owner/repo/issues/123",
        status_code=404,
        message="Not Found",
    )

    with pytest.raises(HttpError) as exc_info:
        client.patch("repos/owner/repo/issues/123", data={"state": "closed"})

    assert exc_info.value.status_code == 404
    assert exc_info.value.endpoint == "repos/owner/repo/issues/123"


def test_multiple_requests_tracked() -> None:
    """Multiple requests should be tracked in order."""
    client = FakeHttpClient()

    client.get("endpoint1")
    client.post("endpoint2", data={"key": "value"})
    client.patch("endpoint3", data={"other": "data"})

    assert len(client.requests) == 3
    assert client.requests[0].method == "GET"
    assert client.requests[1].method == "POST"
    assert client.requests[2].method == "PATCH"


def test_requests_returns_copy() -> None:
    """requests property should return a copy to prevent mutation."""
    client = FakeHttpClient()
    client.get("endpoint")

    requests = client.requests
    requests.clear()

    # Original should be unchanged
    assert len(client.requests) == 1
