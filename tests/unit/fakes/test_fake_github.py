"""Tests for FakeGitHub test infrastructure.

These tests verify that FakeGitHub correctly simulates GitHub operations,
providing reliable test doubles for CLI tests.
"""

from datetime import UTC, datetime
from pathlib import Path

from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.types import (
    GitHubRepoId,
    GitHubRepoLocation,
    PRDetails,
    PRNotFound,
    PullRequestInfo,
    WorkflowRun,
)
from tests.test_utils.paths import sentinel_path

TEST_LOCATION = GitHubRepoLocation(root=sentinel_path(), repo_id=GitHubRepoId("owner", "repo"))


def test_fake_github_ops_get_pr_base_branch_existing() -> None:
    """Test get_pr_base_branch returns configured base for existing PR."""
    pr_bases = {
        123: "main",
        456: "develop",
    }
    ops = FakeGitHub(pr_bases=pr_bases)

    result = ops.get_pr_base_branch(sentinel_path(), 123)

    assert result == "main"


def test_fake_github_ops_get_pr_base_branch_missing() -> None:
    """Test get_pr_base_branch returns None for missing PR."""
    ops = FakeGitHub()

    result = ops.get_pr_base_branch(sentinel_path(), 999)

    assert result is None, "Expected None when PR base branch not configured"


def test_fake_github_ops_get_pr_base_branch_empty_dict() -> None:
    """Test get_pr_base_branch returns None with empty pr_bases dict."""
    ops = FakeGitHub(pr_bases={})

    result = ops.get_pr_base_branch(sentinel_path(), 123)

    assert result is None, "Expected None when pr_bases is empty"


def test_fake_github_ops_update_pr_base_branch_single() -> None:
    """Test update_pr_base_branch tracks single update."""
    ops = FakeGitHub()

    ops.update_pr_base_branch(sentinel_path(), 123, "main")

    assert ops.updated_pr_bases == [(123, "main")]


def test_fake_github_ops_update_pr_base_branch_multiple() -> None:
    """Test update_pr_base_branch tracks multiple updates in order."""
    ops = FakeGitHub()

    ops.update_pr_base_branch(sentinel_path(), 123, "main")
    ops.update_pr_base_branch(sentinel_path(), 456, "develop")
    ops.update_pr_base_branch(sentinel_path(), 789, "feature-1")

    assert ops.updated_pr_bases == [
        (123, "main"),
        (456, "develop"),
        (789, "feature-1"),
    ]


def test_fake_github_ops_update_pr_base_branch_same_pr_twice() -> None:
    """Test update_pr_base_branch tracks same PR updated multiple times."""
    ops = FakeGitHub()

    ops.update_pr_base_branch(sentinel_path(), 123, "main")
    ops.update_pr_base_branch(sentinel_path(), 123, "develop")

    # Both updates should be tracked
    assert ops.updated_pr_bases == [
        (123, "main"),
        (123, "develop"),
    ]


def test_fake_github_ops_updated_pr_bases_empty_initially() -> None:
    """Test updated_pr_bases property is empty list initially."""
    ops = FakeGitHub()

    assert ops.updated_pr_bases == []


def test_fake_github_ops_updated_pr_bases_read_only() -> None:
    """Test updated_pr_bases property returns list that can be read."""
    ops = FakeGitHub()
    ops.update_pr_base_branch(sentinel_path(), 123, "main")

    # Should be able to read the list
    updates = ops.updated_pr_bases
    assert len(updates) == 1
    assert updates[0] == (123, "main")


def test_fake_github_ops_update_does_not_affect_get() -> None:
    """Test update_pr_base_branch does not modify configured pr_bases."""
    pr_bases = {123: "original-base"}
    ops = FakeGitHub(pr_bases=pr_bases)

    # Update should only track mutation, not modify configured state
    ops.update_pr_base_branch(Path("/repo"), 123, "new-base")

    # get_pr_base_branch should still return original configured value
    assert ops.get_pr_base_branch(sentinel_path(), 123) == "original-base"
    # But update should be tracked
    assert ops.updated_pr_bases == [(123, "new-base")]


def test_fake_github_ops_full_workflow() -> None:
    """Test complete workflow: configure state, query, and track mutations."""
    # Configure initial state
    prs = {
        "feature-1": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/repo/pull/123",
            is_draft=False,
            title=None,
            checks_passing=True,
            owner="testowner",
            repo="testrepo",
        ),
        "feature-2": PullRequestInfo(
            number=456,
            state="OPEN",
            url="https://github.com/repo/pull/456",
            is_draft=False,
            title=None,
            checks_passing=True,
            owner="testowner",
            repo="testrepo",
        ),
    }
    pr_bases = {
        123: "main",
        456: "feature-1",
    }
    pr_details = {
        123: PRDetails(
            number=123,
            url="https://github.com/repo/pull/123",
            title="Feature 1",
            body="",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature-1",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="testowner",
            repo="testrepo",
        ),
        456: PRDetails(
            number=456,
            url="https://github.com/repo/pull/456",
            title="Feature 2",
            body="",
            state="OPEN",
            is_draft=False,
            base_ref_name="feature-1",
            head_ref_name="feature-2",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="testowner",
            repo="testrepo",
        ),
    }
    ops = FakeGitHub(prs=prs, pr_bases=pr_bases, pr_details=pr_details)

    # Query operations
    pr = ops.get_pr_for_branch(sentinel_path(), "feature-1")
    assert pr is not None
    assert pr.number == 123

    base = ops.get_pr_base_branch(sentinel_path(), 123)
    assert base == "main"

    # Mutation tracking
    ops.update_pr_base_branch(Path("/repo"), 456, "main")
    ops.update_pr_base_branch(sentinel_path(), 123, "develop")

    # Verify mutations tracked
    assert ops.updated_pr_bases == [(456, "main"), (123, "develop")]

    # Verify configured state unchanged
    assert ops.get_pr_base_branch(sentinel_path(), 123) == "main"
    assert ops.get_pr_base_branch(sentinel_path(), 456) == "feature-1"


def test_fake_github_ops_merge_pr_single() -> None:
    """Test merge_pr tracks single PR merge."""
    ops = FakeGitHub()

    ops.merge_pr(sentinel_path(), 123, squash=True, verbose=False)

    assert ops.merged_prs == [123]


def test_fake_github_ops_merge_pr_multiple() -> None:
    """Test merge_pr tracks multiple PR merges in order."""
    ops = FakeGitHub()

    ops.merge_pr(sentinel_path(), 123, squash=True, verbose=False)
    ops.merge_pr(sentinel_path(), 456, squash=True, verbose=False)
    ops.merge_pr(sentinel_path(), 789, squash=False, verbose=True)

    assert ops.merged_prs == [123, 456, 789]


def test_fake_github_ops_merge_pr_same_pr_twice() -> None:
    """Test merge_pr tracks same PR merged multiple times."""
    ops = FakeGitHub()

    ops.merge_pr(sentinel_path(), 123, squash=True, verbose=False)
    ops.merge_pr(sentinel_path(), 123, squash=True, verbose=False)

    # Both merges should be tracked
    assert ops.merged_prs == [123, 123]


def test_fake_github_ops_merged_prs_empty_initially() -> None:
    """Test merged_prs property is empty list initially."""
    ops = FakeGitHub()

    assert ops.merged_prs == []


def test_fake_github_ops_merged_prs_read_only() -> None:
    """Test merged_prs property returns list that can be read."""
    ops = FakeGitHub()
    ops.merge_pr(sentinel_path(), 123, squash=True, verbose=False)

    # Should be able to read the list
    merges = ops.merged_prs
    assert len(merges) == 1
    assert merges[0] == 123


def test_fake_github_list_workflow_runs_empty() -> None:
    """Test list_workflow_runs returns empty list when no runs configured."""
    ops = FakeGitHub()

    result = ops.list_workflow_runs(sentinel_path(), "implement-plan.yml")

    assert result == []


def test_fake_github_list_workflow_runs_configured() -> None:
    """Test list_workflow_runs returns pre-configured runs."""
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
        ),
        WorkflowRun(
            run_id="456",
            status="completed",
            conclusion="failure",
            branch="feat-2",
            head_sha="def456",
        ),
    ]
    ops = FakeGitHub(workflow_runs=workflow_runs)

    result = ops.list_workflow_runs(sentinel_path(), "implement-plan.yml")

    assert len(result) == 2
    assert result[0].run_id == "123"
    assert result[0].status == "completed"
    assert result[0].conclusion == "success"
    assert result[0].branch == "feat-1"
    assert result[1].run_id == "456"
    assert result[1].conclusion == "failure"


def test_fake_github_list_workflow_runs_ignores_workflow_param() -> None:
    """Test list_workflow_runs returns all configured runs regardless of workflow."""
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
        ),
    ]
    ops = FakeGitHub(workflow_runs=workflow_runs)

    # Should return same data regardless of workflow parameter
    result1 = ops.list_workflow_runs(sentinel_path(), "implement-plan.yml")
    result2 = ops.list_workflow_runs(sentinel_path(), "other-workflow.yml")

    assert result1 == result2
    assert len(result1) == 1


def test_fake_github_list_workflow_runs_ignores_limit_param() -> None:
    """Test list_workflow_runs returns all configured runs regardless of limit."""
    workflow_runs = [
        WorkflowRun(
            run_id=str(i),
            status="completed",
            conclusion="success",
            branch=f"feat-{i}",
            head_sha=f"sha{i}",
        )
        for i in range(10)
    ]
    ops = FakeGitHub(workflow_runs=workflow_runs)

    # Should return all runs regardless of limit parameter
    result = ops.list_workflow_runs(sentinel_path(), "implement-plan.yml", limit=5)

    assert len(result) == 10  # All runs returned, limit ignored


def test_fake_github_list_workflow_runs_with_in_progress() -> None:
    """Test list_workflow_runs handles runs with None conclusion (in progress)."""
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="in_progress",
            conclusion=None,  # No conclusion yet
            branch="feat-1",
            head_sha="abc123",
        ),
        WorkflowRun(
            run_id="456",
            status="queued",
            conclusion=None,
            branch="feat-2",
            head_sha="def456",
        ),
    ]
    ops = FakeGitHub(workflow_runs=workflow_runs)

    result = ops.list_workflow_runs(sentinel_path(), "implement-plan.yml")

    assert len(result) == 2
    assert result[0].conclusion is None
    assert result[1].conclusion is None


def test_fake_github_get_workflow_run_node_id_returns_fake_for_any_run() -> None:
    """Test get_workflow_run_node_id returns a generated fake node_id for any run_id."""
    ops = FakeGitHub()

    result = ops.get_workflow_run_node_id(sentinel_path(), "12345")

    # Should generate a fake node_id for convenience in tests
    assert result == "WFR_fake_node_id_12345"


def test_fake_github_get_workflow_run_node_id_from_workflow_runs_list() -> None:
    """Test get_workflow_run_node_id finds run in workflow_runs list."""
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
        ),
    ]
    ops = FakeGitHub(workflow_runs=workflow_runs)

    result = ops.get_workflow_run_node_id(sentinel_path(), "123")

    # Should generate fake node_id for run found in workflow_runs
    assert result == "WFR_fake_node_id_123"


def test_fake_github_get_workflow_run_node_id_from_node_id_mapping() -> None:
    """Test get_workflow_run_node_id returns node_id from pre-configured mapping."""
    workflow_run = WorkflowRun(
        run_id="456",
        status="in_progress",
        conclusion=None,
        branch="feat-2",
        head_sha="def456",
    )
    ops = FakeGitHub(workflow_runs_by_node_id={"WFR_kwXXXX": workflow_run})

    result = ops.get_workflow_run_node_id(sentinel_path(), "456")

    # Should return the configured node_id
    assert result == "WFR_kwXXXX"


def test_fake_github_get_workflow_run_node_id_prefers_node_id_mapping() -> None:
    """Test get_workflow_run_node_id prefers node_id mapping over generating fake."""
    workflow_run = WorkflowRun(
        run_id="789",
        status="completed",
        conclusion="success",
        branch="main",
        head_sha="ghi789",
    )
    ops = FakeGitHub(
        workflow_runs=[workflow_run],
        workflow_runs_by_node_id={"WFR_real_node": workflow_run},
    )

    result = ops.get_workflow_run_node_id(sentinel_path(), "789")

    # Should return real node_id from mapping, not generated one
    assert result == "WFR_real_node"


def test_fake_github_get_issues_with_pr_linkages_empty() -> None:
    """Test get_issues_with_pr_linkages returns empty when no issues configured."""
    ops = FakeGitHub()

    issues, pr_linkages = ops.get_issues_with_pr_linkages(
        location=TEST_LOCATION,
        labels=["erk-plan"],
    )

    assert issues == []
    assert pr_linkages == {}


def test_fake_github_get_issues_with_pr_linkages_filters_by_labels() -> None:
    """Test get_issues_with_pr_linkages filters by required labels."""
    now = datetime.now(UTC)
    issue1 = IssueInfo(
        number=1,
        title="Plan Issue",
        body="",
        state="OPEN",
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )
    issue2 = IssueInfo(
        number=2,
        title="Non-Plan Issue",
        body="",
        state="OPEN",
        url="https://github.com/owner/repo/issues/2",
        labels=["bug"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )
    ops = FakeGitHub(issues=[issue1, issue2])

    issues, _ = ops.get_issues_with_pr_linkages(
        location=TEST_LOCATION,
        labels=["erk-plan"],
    )

    assert len(issues) == 1
    assert issues[0].number == 1


def test_fake_github_get_issues_with_pr_linkages_filters_by_state() -> None:
    """Test get_issues_with_pr_linkages filters by state."""
    now = datetime.now(UTC)
    open_issue = IssueInfo(
        number=1,
        title="Open Plan",
        body="",
        state="OPEN",
        url="",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )
    closed_issue = IssueInfo(
        number=2,
        title="Closed Plan",
        body="",
        state="CLOSED",
        url="",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )
    ops = FakeGitHub(issues=[open_issue, closed_issue])

    issues, _ = ops.get_issues_with_pr_linkages(
        location=TEST_LOCATION,
        labels=["erk-plan"],
        state="open",
    )

    assert len(issues) == 1
    assert issues[0].title == "Open Plan"


def test_fake_github_get_issues_with_pr_linkages_returns_pr_linkages() -> None:
    """Test get_issues_with_pr_linkages returns PR linkages for matching issues."""
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=42,
        title="Test Plan",
        body="",
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )
    pr = PullRequestInfo(
        number=123,
        state="OPEN",
        url="https://github.com/owner/repo/pull/123",
        is_draft=False,
        title="Implementation PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )
    ops = FakeGitHub(
        issues=[issue],
        pr_issue_linkages={42: [pr]},
    )

    issues, pr_linkages = ops.get_issues_with_pr_linkages(
        location=TEST_LOCATION,
        labels=["erk-plan"],
    )

    assert len(issues) == 1
    assert 42 in pr_linkages
    assert pr_linkages[42][0].number == 123


def test_fake_github_get_issues_with_pr_linkages_respects_limit() -> None:
    """Test get_issues_with_pr_linkages respects limit parameter."""
    now = datetime.now(UTC)
    issues = [
        IssueInfo(
            number=i,
            title=f"Plan {i}",
            body="",
            state="OPEN",
            url=f"https://github.com/owner/repo/issues/{i}",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        for i in range(10)
    ]
    ops = FakeGitHub(issues=issues)

    result_issues, _ = ops.get_issues_with_pr_linkages(
        location=TEST_LOCATION,
        labels=["erk-plan"],
        limit=3,
    )

    assert len(result_issues) == 3


def test_fake_github_get_issues_with_pr_linkages_no_linkages_for_filtered_issues() -> None:
    """Test get_issues_with_pr_linkages doesn't return linkages for filtered-out issues."""
    now = datetime.now(UTC)
    issue1 = IssueInfo(
        number=1,
        title="Plan",
        body="",
        state="OPEN",
        url="",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )
    issue2 = IssueInfo(
        number=2,
        title="Bug",
        body="",
        state="OPEN",
        url="",
        labels=["bug"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )
    pr = PullRequestInfo(
        number=99,
        state="OPEN",
        url="",
        is_draft=False,
        title="PR for Bug",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )
    # Issue 2 has PR linkage but doesn't match label filter
    ops = FakeGitHub(
        issues=[issue1, issue2],
        pr_issue_linkages={2: [pr]},
    )

    issues, pr_linkages = ops.get_issues_with_pr_linkages(
        location=TEST_LOCATION,
        labels=["erk-plan"],
    )

    # Only issue 1 matches, so no PR linkages should be returned
    assert len(issues) == 1
    assert 2 not in pr_linkages


def test_fake_github_get_pr_returns_configured_details() -> None:
    """Test get_pr returns pre-configured PRDetails."""
    pr_details = PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Add feature",
        body="This PR adds a feature",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
        labels=("enhancement", "reviewed"),
    )
    ops = FakeGitHub(pr_details={123: pr_details})

    result = ops.get_pr(sentinel_path(), 123)

    assert result.number == 123
    assert result.title == "Add feature"
    assert result.body == "This PR adds a feature"
    assert result.state == "OPEN"
    assert result.base_ref_name == "main"
    assert result.head_ref_name == "feature-branch"
    assert result.is_cross_repository is False
    assert result.mergeable == "MERGEABLE"
    assert result.merge_state_status == "CLEAN"
    assert result.labels == ("enhancement", "reviewed")


def test_fake_github_get_pr_returns_pr_not_found_for_missing_pr() -> None:
    """Test get_pr returns PRNotFound when PR number not found."""
    ops = FakeGitHub()

    result = ops.get_pr(sentinel_path(), 999)

    assert isinstance(result, PRNotFound)
    assert result.pr_number == 999
    assert result.branch is None


def test_fake_github_get_pr_returns_pr_not_found_with_empty_dict() -> None:
    """Test get_pr returns PRNotFound with explicitly empty pr_details dict."""
    ops = FakeGitHub(pr_details={})

    result = ops.get_pr(sentinel_path(), 123)

    assert isinstance(result, PRNotFound)
    assert result.pr_number == 123


def test_fake_github_get_pr_multiple_prs() -> None:
    """Test get_pr returns correct PR when multiple are configured."""
    pr1 = PRDetails(
        number=100,
        url="https://github.com/owner/repo/pull/100",
        title="First PR",
        body="First body",
        state="MERGED",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feat-1",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )
    pr2 = PRDetails(
        number=200,
        url="https://github.com/owner/repo/pull/200",
        title="Second PR",
        body="Second body",
        state="OPEN",
        is_draft=True,
        base_ref_name="develop",
        head_ref_name="feat-2",
        is_cross_repository=True,
        mergeable="CONFLICTING",
        merge_state_status="DIRTY",
        owner="owner",
        repo="repo",
        labels=("wip",),
    )
    ops = FakeGitHub(pr_details={100: pr1, 200: pr2})

    result1 = ops.get_pr(sentinel_path(), 100)
    result2 = ops.get_pr(sentinel_path(), 200)

    assert result1.title == "First PR"
    assert result1.state == "MERGED"

    assert result2.title == "Second PR"
    assert result2.is_draft is True
    assert result2.is_cross_repository is True
    assert result2.mergeable == "CONFLICTING"


def test_fake_github_get_pr_for_branch_returns_details() -> None:
    """Test get_pr_for_branch returns PRDetails when branch has a PR."""
    pr_info = PullRequestInfo(
        number=123,
        state="OPEN",
        url="https://github.com/owner/repo/pull/123",
        is_draft=False,
        title="Add feature",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )
    pr_details = PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Add feature",
        body="This PR adds a feature",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
        labels=("enhancement",),
    )
    ops = FakeGitHub(
        prs={"feature-branch": pr_info},
        pr_details={123: pr_details},
    )

    result = ops.get_pr_for_branch(sentinel_path(), "feature-branch")

    assert result is not None
    assert result.number == 123
    assert result.title == "Add feature"
    assert result.body == "This PR adds a feature"
    assert result.state == "OPEN"
    assert result.base_ref_name == "main"
    assert result.head_ref_name == "feature-branch"
    assert result.mergeable == "MERGEABLE"
    assert result.labels == ("enhancement",)


def test_fake_github_get_pr_for_branch_returns_pr_not_found_for_missing_branch() -> None:
    """Test get_pr_for_branch returns PRNotFound when branch has no PR."""
    ops = FakeGitHub()

    result = ops.get_pr_for_branch(sentinel_path(), "nonexistent-branch")

    assert isinstance(result, PRNotFound)
    assert result.branch == "nonexistent-branch"
    assert result.pr_number is None


def test_fake_github_get_pr_for_branch_returns_pr_not_found_when_pr_exists_but_no_details() -> None:
    """Test get_pr_for_branch returns PRNotFound when PR exists but details not configured."""
    pr_info = PullRequestInfo(
        number=456,
        state="OPEN",
        url="https://github.com/owner/repo/pull/456",
        is_draft=False,
        title="Some PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )
    # prs configured but pr_details not configured for this PR number
    ops = FakeGitHub(prs={"some-branch": pr_info})

    result = ops.get_pr_for_branch(sentinel_path(), "some-branch")

    assert isinstance(result, PRNotFound)
    assert result.branch == "some-branch"


def test_fake_github_merge_pr_returns_true_on_success() -> None:
    """Test merge_pr returns True (not just truthy) on success."""
    ops = FakeGitHub(merge_should_succeed=True)

    result = ops.merge_pr(sentinel_path(), 123)

    assert result is True
    assert ops.merged_prs == [123]


def test_fake_github_merge_pr_returns_error_string_on_failure() -> None:
    """Test merge_pr returns error message string on failure."""
    ops = FakeGitHub(merge_should_succeed=False)

    result = ops.merge_pr(sentinel_path(), 123)

    assert isinstance(result, str)
    assert "Merge failed" in result
    assert ops.merged_prs == []  # PR was not merged


# Tests for create_pr_review_comment


def test_fake_github_create_pr_review_comment_returns_int_id() -> None:
    """Test create_pr_review_comment returns an integer comment ID."""
    ops = FakeGitHub()

    result = ops.create_pr_review_comment(
        repo_root=sentinel_path(),
        pr_number=123,
        body="**Dignified Python**: Use LBYL pattern",
        commit_sha="abc123",
        path="src/foo.py",
        line=42,
    )

    # Must return an integer ID, not None or string
    assert isinstance(result, int)
    assert result > 0


def test_fake_github_create_pr_review_comment_tracks_mutation() -> None:
    """Test create_pr_review_comment tracks the comment in mutation list."""
    ops = FakeGitHub()

    ops.create_pr_review_comment(
        repo_root=sentinel_path(),
        pr_number=123,
        body="Comment body",
        commit_sha="abc123",
        path="src/foo.py",
        line=42,
    )

    assert ops.pr_review_comments == [(123, "Comment body", "abc123", "src/foo.py", 42)]


def test_fake_github_create_pr_review_comment_increments_ids() -> None:
    """Test create_pr_review_comment returns unique incrementing IDs."""
    ops = FakeGitHub()

    id1 = ops.create_pr_review_comment(
        repo_root=sentinel_path(),
        pr_number=123,
        body="First",
        commit_sha="sha1",
        path="file1.py",
        line=1,
    )
    id2 = ops.create_pr_review_comment(
        repo_root=sentinel_path(),
        pr_number=123,
        body="Second",
        commit_sha="sha2",
        path="file2.py",
        line=2,
    )

    assert id2 > id1
    assert len(ops.pr_review_comments) == 2


# Tests for create_pr_comment


def test_fake_github_create_pr_comment_returns_int_id() -> None:
    """Test create_pr_comment returns an integer comment ID."""
    ops = FakeGitHub()

    result = ops.create_pr_comment(sentinel_path(), 123, "Summary comment")

    # Must return an integer ID, not None or string
    assert isinstance(result, int)
    assert result > 0


def test_fake_github_create_pr_comment_tracks_mutation() -> None:
    """Test create_pr_comment tracks the comment in mutation list."""
    ops = FakeGitHub()

    ops.create_pr_comment(sentinel_path(), 123, "Summary comment body")

    assert ops.pr_comments == [(123, "Summary comment body")]


# Tests for find_pr_comment_by_marker


def test_fake_github_find_pr_comment_by_marker_returns_none_when_not_found() -> None:
    """Test find_pr_comment_by_marker returns None when no matching comment."""
    ops = FakeGitHub()

    result = ops.find_pr_comment_by_marker(sentinel_path(), 123, "<!-- my-marker -->")

    assert result is None


def test_fake_github_find_pr_comment_by_marker_finds_matching_comment() -> None:
    """Test find_pr_comment_by_marker finds comment containing marker."""
    ops = FakeGitHub()

    # Create a comment with a marker
    ops.create_pr_comment(sentinel_path(), 123, "Header\n\n<!-- my-marker -->\n\nBody")

    result = ops.find_pr_comment_by_marker(sentinel_path(), 123, "<!-- my-marker -->")

    # Should find the comment we just created
    assert result is not None
    assert isinstance(result, int)


def test_fake_github_find_pr_comment_by_marker_ignores_different_pr() -> None:
    """Test find_pr_comment_by_marker only searches specified PR."""
    ops = FakeGitHub()

    # Create comment on PR 123
    ops.create_pr_comment(sentinel_path(), 123, "<!-- marker -->\nOn PR 123")

    # Search on PR 456
    result = ops.find_pr_comment_by_marker(sentinel_path(), 456, "<!-- marker -->")

    # Should not find it
    assert result is None


# Tests for update_pr_comment


def test_fake_github_update_pr_comment_tracks_mutation() -> None:
    """Test update_pr_comment tracks the update in mutation list."""
    ops = FakeGitHub()

    ops.update_pr_comment(sentinel_path(), 12345, "Updated body")

    assert ops.pr_comment_updates == [(12345, "Updated body")]
