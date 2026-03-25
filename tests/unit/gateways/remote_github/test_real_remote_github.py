"""Tests for RealRemoteGitHub using FakeHttpClient.

Layer 2 tests: verify API endpoint construction, response parsing,
error handling, and polling logic without real network calls.
"""

import base64

import pytest

from erk_shared.gateway.http.abc import HttpError
from erk_shared.gateway.remote_github.real import RealRemoteGitHub, _parse_pr_response
from erk_shared.gateway.remote_github.types import RemotePRInfo, RemotePRNotFound
from tests.fakes.gateway.http import FakeHttpClient
from tests.fakes.gateway.time import FakeTime


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

    remote.add_labels(owner="o", repo="r", issue_number=42, labels=("erk-pr",))

    req = http.requests[0]
    assert req.method == "POST"
    assert req.endpoint == "repos/o/r/issues/42/labels"
    assert req.data == {"labels": ["erk-pr"]}


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


# --- get_issue ---


def test_get_issue_returns_parsed_issue() -> None:
    remote, http, _ = _make_remote()
    http.set_response(
        "repos/o/r/issues/42",
        response={
            "number": 42,
            "title": "Test Issue",
            "body": "Issue body",
            "state": "open",
            "html_url": "https://github.com/o/r/issues/42",
            "labels": [{"name": "erk-pr"}],
            "assignees": [{"login": "alice"}],
            "user": {"login": "bob"},
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-16T12:00:00Z",
        },
    )

    result = remote.get_issue(owner="o", repo="r", number=42)

    from erk_shared.gateway.github.issues.types import IssueInfo

    assert isinstance(result, IssueInfo)
    assert result.number == 42
    assert result.title == "Test Issue"
    assert result.body == "Issue body"
    assert result.state == "OPEN"
    assert result.labels == ["erk-pr"]
    assert result.assignees == ["alice"]
    assert result.author == "bob"


def test_get_issue_returns_not_found_on_404() -> None:
    remote, http, _ = _make_remote()
    http.set_error("repos/o/r/issues/999", status_code=404, message="Not Found")

    from erk_shared.gateway.github.issues.types import IssueNotFound

    result = remote.get_issue(owner="o", repo="r", number=999)
    assert isinstance(result, IssueNotFound)
    assert result.issue_number == 999


def test_get_issue_raises_on_non_404_error() -> None:
    remote, http, _ = _make_remote()
    http.set_error("repos/o/r/issues/42", status_code=500, message="Server Error")

    with pytest.raises(HttpError, match="500"):
        remote.get_issue(owner="o", repo="r", number=42)


# --- get_pr ---


def test_get_pr_returns_parsed_pr() -> None:
    remote, http, _ = _make_remote()
    http.set_response(
        "repos/o/r/pulls/42",
        response={
            "number": 42,
            "title": "Fix bug",
            "state": "open",
            "merged": False,
            "html_url": "https://github.com/o/r/pull/42",
            "head": {"ref": "fix-bug"},
            "base": {"ref": "main"},
            "labels": [{"name": "erk-pr"}],
        },
    )

    result = remote.get_pr(owner="o", repo="r", number=42)

    assert isinstance(result, RemotePRInfo)
    assert result.number == 42
    assert result.title == "Fix bug"
    assert result.state == "OPEN"
    assert result.url == "https://github.com/o/r/pull/42"
    assert result.head_ref_name == "fix-bug"
    assert result.base_ref_name == "main"
    assert result.owner == "o"
    assert result.repo == "r"
    assert result.labels == ["erk-pr"]


def test_get_pr_returns_not_found_on_404() -> None:
    remote, http, _ = _make_remote()
    http.set_error("repos/o/r/pulls/999", status_code=404, message="Not Found")

    result = remote.get_pr(owner="o", repo="r", number=999)
    assert isinstance(result, RemotePRNotFound)
    assert result.pr_number == 999


def test_get_pr_raises_on_non_404_error() -> None:
    remote, http, _ = _make_remote()
    http.set_error("repos/o/r/pulls/42", status_code=500, message="Server Error")

    with pytest.raises(HttpError, match="500"):
        remote.get_pr(owner="o", repo="r", number=42)


# --- _parse_pr_response ---


def test_parse_pr_response_merged_state() -> None:
    data = {
        "number": 1,
        "title": "PR",
        "state": "closed",
        "merged": True,
        "html_url": "",
        "head": {"ref": "branch"},
        "base": {"ref": "main"},
        "labels": [],
    }
    result = _parse_pr_response(data, owner="o", repo_name="r")
    assert result.state == "MERGED"


def test_parse_pr_response_open_state() -> None:
    data = {
        "number": 1,
        "title": "PR",
        "state": "open",
        "merged": False,
        "html_url": "",
        "head": {"ref": "branch"},
        "base": {"ref": "main"},
        "labels": [],
    }
    result = _parse_pr_response(data, owner="o", repo_name="r")
    assert result.state == "OPEN"


def test_parse_pr_response_closed_state() -> None:
    data = {
        "number": 1,
        "title": "PR",
        "state": "closed",
        "merged": False,
        "html_url": "",
        "head": {"ref": "branch"},
        "base": {"ref": "main"},
        "labels": [],
    }
    result = _parse_pr_response(data, owner="o", repo_name="r")
    assert result.state == "CLOSED"


def test_parse_pr_response_labels() -> None:
    data = {
        "number": 1,
        "title": "PR",
        "state": "open",
        "merged": False,
        "html_url": "",
        "head": {"ref": "branch"},
        "base": {"ref": "main"},
        "labels": [{"name": "bug"}, {"name": "priority"}],
    }
    result = _parse_pr_response(data, owner="o", repo_name="r")
    assert result.labels == ["bug", "priority"]


def test_parse_pr_response_head_base_refs() -> None:
    data = {
        "number": 1,
        "title": "PR",
        "state": "open",
        "merged": False,
        "html_url": "",
        "head": {"ref": "feature-branch"},
        "base": {"ref": "develop"},
        "labels": [],
    }
    result = _parse_pr_response(data, owner="o", repo_name="r")
    assert result.head_ref_name == "feature-branch"
    assert result.base_ref_name == "develop"


# --- get_issue_comments ---


def test_get_issue_comments_returns_bodies() -> None:
    remote, http, _ = _make_remote()
    http.set_list_response(
        "repos/o/r/issues/42/comments?per_page=100",
        response=[
            {"body": "First comment"},
            {"body": "Second comment"},
        ],
    )

    result = remote.get_issue_comments(owner="o", repo="r", number=42)
    assert result == ["First comment", "Second comment"]


def test_get_issue_comments_returns_empty_for_no_comments() -> None:
    remote, http, _ = _make_remote()
    http.set_list_response(
        "repos/o/r/issues/42/comments?per_page=100",
        response=[],
    )

    result = remote.get_issue_comments(owner="o", repo="r", number=42)
    assert result == []


# --- list_issues ---


def test_list_issues_constructs_correct_query() -> None:
    remote, http, _ = _make_remote()
    http.set_list_response(
        "repos/o/r/issues?state=open&labels=erk-pr&per_page=100",
        response=[
            {
                "number": 1,
                "title": "Issue 1",
                "body": "body1",
                "state": "open",
                "html_url": "https://github.com/o/r/issues/1",
                "labels": [],
                "assignees": [],
                "user": {"login": "alice"},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        ],
    )

    result = remote.list_issues(
        owner="o", repo="r", labels=("erk-pr",), state="open", limit=None, creator=None
    )
    assert len(result) == 1
    assert result[0].number == 1


def test_list_issues_skips_pull_requests() -> None:
    remote, http, _ = _make_remote()
    http.set_list_response(
        "repos/o/r/issues?state=open&labels=erk-pr&per_page=100",
        response=[
            {
                "number": 1,
                "title": "Issue",
                "body": "",
                "state": "open",
                "html_url": "",
                "labels": [],
                "assignees": [],
                "user": {},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
            {
                "number": 2,
                "title": "PR masquerading as issue",
                "body": "",
                "state": "open",
                "html_url": "",
                "labels": [],
                "assignees": [],
                "user": {},
                "pull_request": {"url": "https://api.github.com/repos/o/r/pulls/2"},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        ],
    )

    result = remote.list_issues(
        owner="o", repo="r", labels=("erk-pr",), state="open", limit=None, creator=None
    )
    assert len(result) == 1
    assert result[0].number == 1


def test_list_issues_respects_limit() -> None:
    remote, http, _ = _make_remote()
    http.set_list_response(
        "repos/o/r/issues?state=open&labels=erk-pr&per_page=100",
        response=[
            {
                "number": i,
                "title": f"Issue {i}",
                "body": "",
                "state": "open",
                "html_url": "",
                "labels": [],
                "assignees": [],
                "user": {},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
            for i in range(1, 6)
        ],
    )

    result = remote.list_issues(
        owner="o", repo="r", labels=("erk-pr",), state="open", limit=2, creator=None
    )
    assert len(result) == 2


def test_list_issues_includes_creator_param() -> None:
    remote, http, _ = _make_remote()
    http.set_list_response(
        "repos/o/r/issues?state=open&labels=erk-pr&per_page=100&creator=alice",
        response=[],
    )

    result = remote.list_issues(
        owner="o", repo="r", labels=("erk-pr",), state="open", limit=None, creator="alice"
    )
    assert result == []

    req = http.requests[0]
    assert "creator=alice" in req.endpoint


# --- close_issue ---


def test_close_issue_patches_correct_endpoint() -> None:
    remote, http, _ = _make_remote()

    remote.close_issue(owner="o", repo="r", number=42)

    req = http.requests[0]
    assert req.method == "PATCH"
    assert req.endpoint == "repos/o/r/issues/42"
    assert req.data == {"state": "closed"}


# --- close_pr ---


def test_close_pr_patches_correct_endpoint() -> None:
    remote, http, _ = _make_remote()

    remote.close_pr(owner="o", repo="r", number=42)

    req = http.requests[0]
    assert req.method == "PATCH"
    assert req.endpoint == "repos/o/r/pulls/42"
    assert req.data == {"state": "closed"}


# --- check_auth_status ---


def test_check_auth_status_returns_authenticated() -> None:
    remote, http, _ = _make_remote()
    http.set_response("user", response={"login": "alice"})

    is_auth, username, error = remote.check_auth_status()
    assert is_auth is True
    assert username == "alice"
    assert error is None


def test_check_auth_status_returns_false_on_missing_login() -> None:
    remote, http, _ = _make_remote()
    http.set_response("user", response={})

    is_auth, username, error = remote.check_auth_status()
    assert is_auth is False
    assert username is None
    assert error is not None
    assert "without login" in error


def test_check_auth_status_returns_false_on_http_error() -> None:
    remote, http, _ = _make_remote()
    http.set_error("user", status_code=401, message="Bad credentials")

    is_auth, username, error = remote.check_auth_status()
    assert is_auth is False
    assert username is None
    assert error is not None
    assert "Authentication failed" in error


# --- HttpError propagation ---


def test_http_error_propagates() -> None:
    remote, http, _ = _make_remote()
    http.set_error("user", status_code=401, message="Bad credentials")

    with pytest.raises(HttpError, match="401"):
        remote.get_authenticated_user()


# --- get_comment_by_id ---


def test_get_comment_by_id_returns_body() -> None:
    remote, http, _ = _make_remote()
    http.set_response("repos/o/r/issues/comments/123", response={"body": "Comment text"})

    result = remote.get_comment_by_id(owner="o", repo="r", comment_id=123)

    assert result == "Comment text"


def test_get_comment_by_id_returns_empty_string_when_no_body() -> None:
    remote, http, _ = _make_remote()
    http.set_response("repos/o/r/issues/comments/123", response={})

    result = remote.get_comment_by_id(owner="o", repo="r", comment_id=123)

    assert result == ""


# --- update_issue_body ---


def test_update_issue_body_patches_correct_endpoint() -> None:
    remote, http, _ = _make_remote()

    remote.update_issue_body(owner="o", repo="r", number=42, body="new body")

    req = http.requests[0]
    assert req.method == "PATCH"
    assert req.endpoint == "repos/o/r/issues/42"
    assert req.data == {"body": "new body"}


# --- update_comment ---


def test_update_comment_patches_correct_endpoint() -> None:
    remote, http, _ = _make_remote()

    remote.update_comment(owner="o", repo="r", comment_id=123, body="updated text")

    req = http.requests[0]
    assert req.method == "PATCH"
    assert req.endpoint == "repos/o/r/issues/comments/123"
    assert req.data == {"body": "updated text"}
