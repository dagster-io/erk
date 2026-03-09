"""Tests for FakeHttpClient."""

import pytest

from erk_shared.fakes.http import FakeHttpClient
from erk_shared.gateway.http.abc import HttpError


def test_get_list_returns_configured_response() -> None:
    """get_list returns the configured list response for the endpoint."""
    client = FakeHttpClient()
    client.set_list_response("repos/owner/repo/issues", response=[{"number": 1}])

    result = client.get_list("repos/owner/repo/issues")

    assert result == [{"number": 1}]


def test_get_list_returns_empty_list_for_unconfigured_endpoint() -> None:
    """get_list returns empty list when no response is configured."""
    client = FakeHttpClient()

    result = client.get_list("repos/owner/repo/issues")

    assert result == []


def test_get_list_records_request() -> None:
    """get_list records the request for later assertion."""
    client = FakeHttpClient()

    client.get_list("repos/owner/repo/issues")

    assert len(client.requests) == 1
    assert client.requests[0].method == "GET"
    assert client.requests[0].endpoint == "repos/owner/repo/issues"
    assert client.requests[0].data is None


def test_get_list_raises_configured_error() -> None:
    """get_list raises HttpError when error is configured for endpoint."""
    client = FakeHttpClient()
    client.set_error("repos/owner/repo/issues", status_code=404, message="Not found")

    with pytest.raises(HttpError) as exc_info:
        client.get_list("repos/owner/repo/issues")

    assert exc_info.value.status_code == 404


def test_graphql_returns_configured_response() -> None:
    """graphql returns the configured response for the graphql endpoint."""
    client = FakeHttpClient()
    client.set_response("graphql", response={"data": {"viewer": {"login": "test"}}})

    result = client.graphql(query="{ viewer { login } }", variables={})

    assert result == {"data": {"viewer": {"login": "test"}}}


def test_graphql_records_request_with_query_and_variables() -> None:
    """graphql records the request including query and variables."""
    client = FakeHttpClient()

    client.graphql(query="query { node }", variables={"id": "abc"})

    assert len(client.requests) == 1
    assert client.requests[0].method == "POST"
    assert client.requests[0].endpoint == "graphql"
    assert client.requests[0].data == {"query": "query { node }", "variables": {"id": "abc"}}


def test_graphql_raises_configured_error() -> None:
    """graphql raises HttpError when error is configured for graphql endpoint."""
    client = FakeHttpClient()
    client.set_error("graphql", status_code=500, message="Internal error")

    with pytest.raises(HttpError):
        client.graphql(query="{ viewer }", variables={})
