"""Tests for FakeRemoteGitHub gateway."""

from erk_shared.gateway.remote_github.fake import FakeRemoteGitHub
from erk_shared.gateway.remote_github.types import RemotePRInfo, RemotePRNotFound


def test_get_authenticated_user_returns_configured_value() -> None:
    """Default authenticated user is returned."""
    fake = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    assert fake.get_authenticated_user() == "test-user"


def test_get_authenticated_user_custom() -> None:
    """Custom authenticated user is returned."""
    fake = FakeRemoteGitHub(
        authenticated_user="alice",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    assert fake.get_authenticated_user() == "alice"


def test_get_default_branch_name() -> None:
    """Default branch name is returned."""
    fake = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="master",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    assert fake.get_default_branch_name(owner="o", repo="r") == "master"


def test_get_default_branch_sha() -> None:
    """Default branch SHA is returned."""
    fake = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="deadbeef",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    assert fake.get_default_branch_sha(owner="o", repo="r") == "deadbeef"


def test_create_ref_records_call() -> None:
    """create_ref records the call for assertions."""
    fake = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    fake.create_ref(owner="o", repo="r", ref="refs/heads/my-branch", sha="abc123")

    assert len(fake.created_refs) == 1
    ref = fake.created_refs[0]
    assert ref.owner == "o"
    assert ref.repo == "r"
    assert ref.ref == "refs/heads/my-branch"
    assert ref.sha == "abc123"


def test_create_file_commit_records_call() -> None:
    """create_file_commit records the call and returns fake SHA."""
    fake = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    sha = fake.create_file_commit(
        owner="o",
        repo="r",
        path=".erk/impl-context/prompt.md",
        content="fix the bug",
        message="One-shot: fix the bug",
        branch="my-branch",
    )

    assert sha == "fake-commit-sha"
    assert len(fake.created_file_commits) == 1
    commit = fake.created_file_commits[0]
    assert commit.path == ".erk/impl-context/prompt.md"
    assert commit.content == "fix the bug"
    assert commit.branch == "my-branch"


def test_create_pull_request_records_call() -> None:
    """create_pull_request records and returns configured PR number."""
    fake = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=99,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    pr_number = fake.create_pull_request(
        owner="o",
        repo="r",
        head="my-branch",
        base="main",
        title="One-shot: fix bug",
        body="body text",
        draft=True,
    )

    assert pr_number == 99
    assert len(fake.created_pull_requests) == 1
    pr = fake.created_pull_requests[0]
    assert pr.head == "my-branch"
    assert pr.draft is True


def test_update_pull_request_body_records_call() -> None:
    """update_pull_request_body records the call."""
    fake = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    fake.update_pull_request_body(owner="o", repo="r", pr_number=42, body="new body")

    assert len(fake.updated_pr_bodies) == 1
    assert fake.updated_pr_bodies[0].body == "new body"


def test_add_labels_records_call() -> None:
    """add_labels records the call."""
    fake = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    fake.add_labels(owner="o", repo="r", issue_number=42, labels=("erk-pr", "erk-plan"))

    assert len(fake.added_labels) == 1
    assert fake.added_labels[0].labels == ("erk-pr", "erk-plan")


def test_dispatch_workflow_records_call() -> None:
    """dispatch_workflow records and returns configured run ID."""
    fake = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-99",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    run_id = fake.dispatch_workflow(
        owner="o",
        repo="r",
        workflow="one-shot.yml",
        ref="main",
        inputs={"prompt": "fix bug"},
    )

    assert run_id == "run-99"
    assert len(fake.dispatched_workflows) == 1
    wf = fake.dispatched_workflows[0]
    assert wf.workflow == "one-shot.yml"
    assert wf.inputs["prompt"] == "fix bug"


def test_add_issue_comment_records_call() -> None:
    """add_issue_comment records the call."""
    fake = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    fake.add_issue_comment(owner="o", repo="r", issue_number=42, body="comment")

    assert len(fake.added_issue_comments) == 1
    assert fake.added_issue_comments[0].body == "comment"


def test_mutation_properties_return_copies() -> None:
    """Mutation tracking properties return copies (not mutable references)."""
    fake = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    fake.create_ref(owner="o", repo="r", ref="refs/heads/b", sha="abc")

    refs1 = fake.created_refs
    refs2 = fake.created_refs
    assert refs1 == refs2
    assert refs1 is not refs2  # different list objects


def test_get_pr_returns_configured_pr() -> None:
    """get_pr returns a pre-configured RemotePRInfo."""
    pr = RemotePRInfo(
        number=42,
        title="Fix bug",
        state="OPEN",
        url="https://github.com/o/r/pull/42",
        head_ref_name="fix-bug",
        base_ref_name="main",
        owner="o",
        repo="r",
        labels=["erk-pr"],
    )
    fake = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
        prs={42: pr},
    )

    result = fake.get_pr(owner="o", repo="r", number=42)
    assert isinstance(result, RemotePRInfo)
    assert result.number == 42
    assert result.title == "Fix bug"
    assert result.head_ref_name == "fix-bug"
    assert result.labels == ["erk-pr"]


def test_get_pr_returns_not_found() -> None:
    """get_pr returns RemotePRNotFound when PR is not configured."""
    fake = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )

    result = fake.get_pr(owner="o", repo="r", number=999)
    assert isinstance(result, RemotePRNotFound)
    assert result.pr_number == 999
