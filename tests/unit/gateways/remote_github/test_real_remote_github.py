"""Tests for RealRemoteGitHub using FakeHttpClient.

Layer 2 tests: verify API endpoint construction, response parsing,
error handling, and polling logic without real network calls.
"""

import base64

import pytest

from erk_shared.gateway.http.abc import HttpError
from erk_shared.gateway.http.fake import FakeHttpClient
from erk_shared.gateway.remote_github.real import RealRemoteGitHub
from erk_shared.gateway.time.fake import FakeTime


def _make_remote(
    *, http: FakeHttpClient | None = None, time: FakeTime | None = None
) -> tuple[RealRemoteGitHub, FakeHttpClient, FakeTime]:
    """Create a RealRemoteGitHub with fakes."""
    http = http or FakeHttpClient()
    time = time or FakeTime()
    remote = RealRemoteGitHub(http_client=http, time=time)
    return remote, http, time


# --- get_authenticated_user ---


def test_get_authenticated_user_returns_login() -> None:
    remote, http, _ = _make_remote()
    http.set_response("user", response={"login": "alice"})

    assert remote.get_authenticated_user() == "alice"


def test_get_authenticated_user_raises_on_missing_login() -> None:
    remote, http, _ = _make_remote()
    http.set_response("user", response={})

    with pytest.raises(RuntimeError, match="without login field"):
        remote.get_authenticated_user()


# --- get_default_branch_name ---


def test_get_default_branch_name_returns_branch() -> None:
    remote, http, _ = _make_remote()
    http.set_response("repos/owner/repo", response={"default_branch": "main"})

    assert remote.get_default_branch_name(owner="owner", repo="repo") == "main"


def test_get_default_branch_name_raises_on_missing() -> None:
    remote, http, _ = _make_remote()
    http.set_response("repos/o/r", response={})

    with pytest.raises(RuntimeError, match="without default_branch field"):
        remote.get_default_branch_name(owner="o", repo="r")


# --- get_default_branch_sha ---


def test_get_default_branch_sha_returns_sha() -> None:
    remote, http, _ = _make_remote()
    http.set_response("repos/o/r", response={"default_branch": "main"})
    http.set_response(
        "repos/o/r/git/ref/heads/main",
        response={"object": {"sha": "abc123"}},
    )

    assert remote.get_default_branch_sha(owner="o", repo="r") == "abc123"


def test_get_default_branch_sha_raises_on_missing_sha() -> None:
    remote, http, _ = _make_remote()
    http.set_response("repos/o/r", response={"default_branch": "main"})
    http.set_response("repos/o/r/git/ref/heads/main", response={"object": {}})

    with pytest.raises(RuntimeError, match="without SHA"):
        remote.get_default_branch_sha(owner="o", repo="r")


# --- create_ref ---


def test_create_ref_posts_correct_endpoint() -> None:
    remote, http, _ = _make_remote()

    remote.create_ref(owner="o", repo="r", ref="refs/heads/my-branch", sha="abc")

    assert len(http.requests) == 1
    req = http.requests[0]
    assert req.method == "POST"
    assert req.endpoint == "repos/o/r/git/refs"
    assert req.data == {"ref": "refs/heads/my-branch", "sha": "abc"}


# --- create_file_commit ---


def test_create_file_commit_base64_encodes_content() -> None:
    remote, http, _ = _make_remote()
    http.set_response(
        "repos/o/r/contents/.erk/impl-context/prompt.md",
        response={"commit": {"sha": "deadbeef"}},
    )

    sha = remote.create_file_commit(
        owner="o",
        repo="r",
        path=".erk/impl-context/prompt.md",
        content="fix the bug\n",
        message="One-shot: fix the bug",
        branch="my-branch",
    )

    assert sha == "deadbeef"
    req = http.requests[0]
    assert req.method == "PUT"
    expected_b64 = base64.b64encode(b"fix the bug\n").decode("ascii")
    assert req.data is not None
    assert req.data["content"] == expected_b64
    assert req.data["branch"] == "my-branch"


def test_create_file_commit_raises_on_missing_sha() -> None:
    remote, http, _ = _make_remote()
    http.set_response(
        "repos/o/r/contents/file.md",
        response={"commit": {}},
    )

    with pytest.raises(RuntimeError, match="without commit SHA"):
        remote.create_file_commit(
            owner="o",
            repo="r",
            path="file.md",
            content="hello",
            message="msg",
            branch="br",
        )


# --- create_pull_request ---


def test_create_pull_request_returns_number() -> None:
    remote, http, _ = _make_remote()
    http.set_response("repos/o/r/pulls", response={"number": 42})

    pr_num = remote.create_pull_request(
        owner="o",
        repo="r",
        head="feature",
        base="main",
        title="My PR",
        body="body",
        draft=True,
    )

    assert pr_num == 42
    req = http.requests[0]
    assert req.data is not None
    assert req.data["draft"] is True


def test_create_pull_request_raises_on_missing_number() -> None:
    remote, http, _ = _make_remote()
    http.set_response("repos/o/r/pulls", response={})

    with pytest.raises(RuntimeError, match="without number field"):
        remote.create_pull_request(
            owner="o", repo="r", head="h", base="b", title="t", body="b", draft=False
        )


# --- update_pull_request_body ---


def test_update_pull_request_body_patches_correct_endpoint() -> None:
    remote, http, _ = _make_remote()

    remote.update_pull_request_body(owner="o", repo="r", pr_number=42, body="new body")

    req = http.requests[0]
    assert req.method == "PATCH"
    assert req.endpoint == "repos/o/r/pulls/42"
    assert req.data == {"body": "new body"}


# --- add_labels ---


def test_add_labels_posts_correct_data() -> None:
    remote, http, _ = _make_remote()

    remote.add_labels(owner="o", repo="r", issue_number=42, labels=("erk-pr", "erk-plan"))

    req = http.requests[0]
    assert req.method == "POST"
    assert req.endpoint == "repos/o/r/issues/42/labels"
    assert req.data == {"labels": ["erk-pr", "erk-plan"]}


# --- dispatch_workflow ---


def test_dispatch_workflow_polls_and_returns_run_id() -> None:
    remote, http, time = _make_remote()

    # The dispatch POST returns empty (204-like)
    http.set_response("repos/o/r/actions/workflows/one-shot.yml/dispatches", response={})

    # The poll GET returns a matching run on the first attempt.
    # We need to match the endpoint pattern which includes query params.
    # FakeHttpClient matches on exact endpoint string, so we use set_response
    # for the runs endpoint.
    http.set_response(
        "repos/o/r/actions/workflows/one-shot.yml/runs?per_page=10",
        response={
            "workflow_runs": [
                {
                    "id": 99999,
                    "display_title": "One-shot :abc123",
                    "conclusion": None,
                },
            ]
        },
    )

    # Monkey-patch _generate_distinct_id to return a known value
    import erk_shared.gateway.remote_github.real as real_module

    original_fn = real_module._generate_distinct_id
    real_module._generate_distinct_id = lambda: "abc123"
    try:
        run_id = remote.dispatch_workflow(
            owner="o",
            repo="r",
            workflow="one-shot.yml",
            ref="main",
            inputs={"prompt": "fix bug"},
        )
    finally:
        real_module._generate_distinct_id = original_fn

    assert run_id == "99999"


def test_dispatch_workflow_raises_on_skipped_run() -> None:
    remote, http, time = _make_remote()

    http.set_response("repos/o/r/actions/workflows/wf.yml/dispatches", response={})
    http.set_response(
        "repos/o/r/actions/workflows/wf.yml/runs?per_page=10",
        response={
            "workflow_runs": [
                {
                    "id": 100,
                    "display_title": "One-shot :testid",
                    "conclusion": "skipped",
                },
            ]
        },
    )

    import erk_shared.gateway.remote_github.real as real_module

    original_fn = real_module._generate_distinct_id
    real_module._generate_distinct_id = lambda: "testid"
    try:
        with pytest.raises(RuntimeError, match="was skipped"):
            remote.dispatch_workflow(owner="o", repo="r", workflow="wf.yml", ref="main", inputs={})
    finally:
        real_module._generate_distinct_id = original_fn


def test_dispatch_workflow_raises_on_timeout() -> None:
    remote, http, time = _make_remote()

    http.set_response("repos/o/r/actions/workflows/wf.yml/dispatches", response={})
    # Return no matching runs — will always miss
    http.set_response(
        "repos/o/r/actions/workflows/wf.yml/runs?per_page=10",
        response={"workflow_runs": []},
    )

    with pytest.raises(RuntimeError, match="Timed out"):
        remote.dispatch_workflow(owner="o", repo="r", workflow="wf.yml", ref="main", inputs={})


# --- add_issue_comment ---


def test_add_issue_comment_posts_correct_data() -> None:
    remote, http, _ = _make_remote()

    remote.add_issue_comment(owner="o", repo="r", issue_number=42, body="Great work!")

    req = http.requests[0]
    assert req.method == "POST"
    assert req.endpoint == "repos/o/r/issues/42/comments"
    assert req.data == {"body": "Great work!"}


# --- HttpError propagation ---


def test_http_error_propagates() -> None:
    remote, http, _ = _make_remote()
    http.set_error("user", status_code=401, message="Bad credentials")

    with pytest.raises(HttpError, match="401"):
        remote.get_authenticated_user()
