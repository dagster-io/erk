"""Tests for FakeGitHubIssues test infrastructure.

These tests verify that FakeGitHubIssues correctly simulates GitHub issue operations,
providing reliable test doubles for tests that use issue functionality.
"""

from datetime import UTC, datetime

import pytest
from erk_shared.github.issues import FakeGitHubIssues

from tests.test_utils.github_helpers import create_test_issue
from tests.test_utils.paths import sentinel_path


def test_fake_github_issues_initialization() -> None:
    """Test that FakeGitHubIssues initializes with empty state."""
    issues = FakeGitHubIssues()

    result = issues.list_issues(sentinel_path())
    assert result == []


def test_fake_github_issues_create_issue_returns_number() -> None:
    """Test create_issue returns predictable issue number."""
    issues = FakeGitHubIssues(next_issue_number=42)

    result = issues.create_issue(
        sentinel_path(),
        title="Test Issue",
        body="Test body",
        labels=["plan", "erk"],
    )

    assert result.number == 42
    assert result.url == "https://github.com/test-owner/test-repo/issues/42"


def test_fake_github_issues_create_issue_increments_number() -> None:
    """Test create_issue increments issue numbers sequentially."""
    issues = FakeGitHubIssues(next_issue_number=1)

    result1 = issues.create_issue(sentinel_path(), "Issue 1", "Body 1", ["label1"])
    result2 = issues.create_issue(sentinel_path(), "Issue 2", "Body 2", ["label2"])
    result3 = issues.create_issue(sentinel_path(), "Issue 3", "Body 3", ["label3"])

    assert result1.number == 1
    assert result2.number == 2
    assert result3.number == 3


def test_fake_github_issues_create_issue_tracks_mutation() -> None:
    """Test create_issue tracks created issues in mutation list."""
    issues = FakeGitHubIssues()

    issues.create_issue(sentinel_path(), "Title 1", "Body 1", ["label1", "label2"])
    issues.create_issue(sentinel_path(), "Title 2", "Body 2", ["label3"])

    assert issues.created_issues == [
        ("Title 1", "Body 1", ["label1", "label2"]),
        ("Title 2", "Body 2", ["label3"]),
    ]


def test_fake_github_issues_created_issues_empty_initially() -> None:
    """Test created_issues property is empty list initially."""
    issues = FakeGitHubIssues()

    assert issues.created_issues == []


def test_fake_github_issues_created_issues_read_only() -> None:
    """Test created_issues property returns list that can be read."""
    issues = FakeGitHubIssues()
    issues.create_issue(sentinel_path(), "Title", "Body", ["label"])

    # Should be able to read the list
    created = issues.created_issues
    assert len(created) == 1
    assert created[0] == ("Title", "Body", ["label"])


def test_fake_github_issues_get_issue_existing() -> None:
    """Test get_issue returns stored issue for existing number."""
    pre_configured = {42: create_test_issue(42, "Existing Issue", "Existing body")}
    issues = FakeGitHubIssues(issues=pre_configured)

    result = issues.get_issue(sentinel_path(), 42)

    assert result.number == 42
    assert result.title == "Existing Issue"
    assert result.body == "Existing body"
    assert result.state == "OPEN"
    assert result.url == "https://github.com/owner/repo/issues/42"


def test_fake_github_issues_get_issue_missing() -> None:
    """Test get_issue raises RuntimeError for missing issue."""
    issues = FakeGitHubIssues()

    with pytest.raises(RuntimeError, match="Issue #999 not found"):
        issues.get_issue(sentinel_path(), 999)


def test_fake_github_issues_get_issue_created() -> None:
    """Test get_issue returns issue that was created via create_issue."""
    issues = FakeGitHubIssues(next_issue_number=10)

    created = issues.create_issue(
        sentinel_path(),
        title="Created Issue",
        body="Created body",
        labels=["test"],
    )

    result = issues.get_issue(sentinel_path(), created.number)

    assert result.number == 10
    assert result.title == "Created Issue"
    assert result.body == "Created body"
    assert result.state == "OPEN"
    assert result.url == "https://github.com/test-owner/test-repo/issues/10"


def test_fake_github_issues_add_comment_existing_issue() -> None:
    """Test add_comment tracks mutation for existing issue."""
    pre_configured = {42: create_test_issue(42, "Test", "Body")}
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.add_comment(sentinel_path(), 42, "This is a comment")

    assert issues.added_comments == [(42, "This is a comment")]


def test_fake_github_issues_add_comment_missing_issue() -> None:
    """Test add_comment raises RuntimeError for missing issue."""
    issues = FakeGitHubIssues()

    with pytest.raises(RuntimeError, match="Issue #999 not found"):
        issues.add_comment(sentinel_path(), 999, "Comment body")


def test_fake_github_issues_add_comment_multiple() -> None:
    """Test add_comment tracks multiple comments in order."""
    pre_configured = {
        10: create_test_issue(10, "Issue 10", "Body", url="http://url/10"),
        20: create_test_issue(20, "Issue 20", "Body", url="http://url/20"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.add_comment(sentinel_path(), 10, "First comment")
    issues.add_comment(sentinel_path(), 20, "Second comment")
    issues.add_comment(sentinel_path(), 10, "Third comment on issue 10")

    assert issues.added_comments == [
        (10, "First comment"),
        (20, "Second comment"),
        (10, "Third comment on issue 10"),
    ]


def test_fake_github_issues_added_comments_empty_initially() -> None:
    """Test added_comments property is empty list initially."""
    issues = FakeGitHubIssues()

    assert issues.added_comments == []


def test_fake_github_issues_update_issue_body_existing_issue() -> None:
    """Test update_issue_body updates body for existing issue."""
    pre_configured = {42: create_test_issue(42, "Test", "Original body")}
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.update_issue_body(sentinel_path(), 42, "Updated body content")

    # Verify body was updated
    updated_issue = issues.get_issue(sentinel_path(), 42)
    assert updated_issue.body == "Updated body content"
    assert updated_issue.title == "Test"  # Title unchanged
    assert updated_issue.number == 42  # Number unchanged


def test_fake_github_issues_update_issue_body_missing_issue() -> None:
    """Test update_issue_body raises RuntimeError for missing issue."""
    issues = FakeGitHubIssues()

    with pytest.raises(RuntimeError, match="Issue #999 not found"):
        issues.update_issue_body(sentinel_path(), 999, "New body")


def test_fake_github_issues_update_issue_body_updates_timestamp() -> None:
    """Test update_issue_body updates the updated_at timestamp."""
    creation_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    pre_configured = {
        42: create_test_issue(
            42, "Test", "Original body", created_at=creation_time, updated_at=creation_time
        )
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    # Update the body
    issues.update_issue_body(sentinel_path(), 42, "Updated body")

    # Verify timestamp was updated (should be later than creation time)
    updated_issue = issues.get_issue(sentinel_path(), 42)
    assert updated_issue.created_at == creation_time  # Creation time unchanged
    assert updated_issue.updated_at > creation_time  # Update time advanced


def test_fake_github_issues_added_comments_read_only() -> None:
    """Test added_comments property returns list that can be read."""
    pre_configured = {42: create_test_issue(42, "Test", "Body", url="http://url")}
    issues = FakeGitHubIssues(issues=pre_configured)
    issues.add_comment(sentinel_path(), 42, "Comment")

    # Should be able to read the list
    comments = issues.added_comments
    assert len(comments) == 1
    assert comments[0] == (42, "Comment")


def test_fake_github_issues_list_issues_empty() -> None:
    """Test list_issues returns empty list when no issues exist."""
    issues = FakeGitHubIssues()

    result = issues.list_issues(sentinel_path())

    assert result == []


def test_fake_github_issues_list_issues_all() -> None:
    """Test list_issues returns all issues when no filters applied."""
    pre_configured = {
        1: create_test_issue(1, "Issue 1", "Body 1", url="http://url/1"),
        2: create_test_issue(2, "Issue 2", "Body 2", "CLOSED", "http://url/2"),
        3: create_test_issue(3, "Issue 3", "Body 3", url="http://url/3"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    result = issues.list_issues(sentinel_path())

    assert len(result) == 3
    assert result[0].number == 1
    assert result[1].number == 2
    assert result[2].number == 3


def test_fake_github_issues_list_issues_filter_open() -> None:
    """Test list_issues filters by state=open."""
    pre_configured = {
        1: create_test_issue(1, "Issue 1", "Body 1", url="http://url/1"),
        2: create_test_issue(2, "Issue 2", "Body 2", "CLOSED", "http://url/2"),
        3: create_test_issue(3, "Issue 3", "Body 3", url="http://url/3"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    result = issues.list_issues(sentinel_path(), state="open")

    assert len(result) == 2
    assert result[0].number == 1
    assert result[0].state == "OPEN"
    assert result[1].number == 3
    assert result[1].state == "OPEN"


def test_fake_github_issues_list_issues_filter_closed() -> None:
    """Test list_issues filters by state=closed."""
    pre_configured = {
        1: create_test_issue(1, "Issue 1", "Body 1", url="http://url/1"),
        2: create_test_issue(2, "Issue 2", "Body 2", "CLOSED", "http://url/2"),
        3: create_test_issue(3, "Issue 3", "Body 3", "CLOSED", "http://url/3"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    result = issues.list_issues(sentinel_path(), state="closed")

    assert len(result) == 2
    assert result[0].number == 2
    assert result[0].state == "CLOSED"
    assert result[1].number == 3
    assert result[1].state == "CLOSED"


def test_fake_github_issues_list_issues_state_all() -> None:
    """Test list_issues with state=all returns all issues."""
    pre_configured = {
        1: create_test_issue(1, "Issue 1", "Body 1", url="http://url/1"),
        2: create_test_issue(2, "Issue 2", "Body 2", "CLOSED", "http://url/2"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    result = issues.list_issues(sentinel_path(), state="all")

    assert len(result) == 2


def test_fake_github_issues_list_issues_includes_created() -> None:
    """Test list_issues includes issues created via create_issue."""
    issues = FakeGitHubIssues(next_issue_number=1)

    issues.create_issue(sentinel_path(), "Created Issue", "Body", ["label"])

    result = issues.list_issues(sentinel_path())

    assert len(result) == 1
    assert result[0].number == 1
    assert result[0].title == "Created Issue"
    assert result[0].state == "OPEN"


def test_fake_github_issues_full_workflow() -> None:
    """Test complete workflow: create, get, comment, list."""
    # Start with one pre-configured issue
    pre_configured = {100: create_test_issue(100, "Existing", "Body", url="http://url/100")}
    issues = FakeGitHubIssues(issues=pre_configured, next_issue_number=200)

    # Create new issue
    new_result = issues.create_issue(
        sentinel_path(),
        title="New Issue",
        body="New body",
        labels=["plan", "erk"],
    )
    assert new_result.number == 200

    # Get created issue
    new_issue = issues.get_issue(sentinel_path(), 200)
    assert new_issue.title == "New Issue"
    assert new_issue.state == "OPEN"

    # Add comments
    issues.add_comment(sentinel_path(), 100, "Comment on existing")
    issues.add_comment(sentinel_path(), 200, "Comment on new")

    # List all issues
    all_issues = issues.list_issues(sentinel_path())
    assert len(all_issues) == 2

    # Verify mutation tracking
    assert issues.created_issues == [("New Issue", "New body", ["plan", "erk"])]
    assert issues.added_comments == [
        (100, "Comment on existing"),
        (200, "Comment on new"),
    ]


def test_fake_github_issues_empty_labels() -> None:
    """Test create_issue with empty labels list."""
    issues = FakeGitHubIssues()

    result = issues.create_issue(sentinel_path(), "Title", "Body", [])

    assert result.number == 1
    assert issues.created_issues == [("Title", "Body", [])]


def test_fake_github_issues_label_filtering_implemented() -> None:
    """Test that label filtering filters issues by required labels."""
    pre_configured = {
        1: create_test_issue(
            1, "Issue 1", "Body 1", url="http://url/1", labels=["erk-plan", "bug"]
        ),
        2: create_test_issue(2, "Issue 2", "Body 2", url="http://url/2", labels=["erk-plan"]),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    # Filter for issues with a label that exists on issue 1 but not issue 2
    result = issues.list_issues(sentinel_path(), labels=["erk-plan", "bug"])

    # Only issue 1 has both labels
    assert len(result) == 1
    assert result[0].number == 1


def test_fake_github_issues_label_filtering_returns_none_when_no_match() -> None:
    """Test that label filtering returns empty list when no issues match."""
    pre_configured = {
        1: create_test_issue(1, "Issue 1", "Body 1", url="http://url/1"),
        2: create_test_issue(2, "Issue 2", "Body 2", url="http://url/2"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    # Filter for a label that doesn't exist on any issue
    result = issues.list_issues(sentinel_path(), labels=["nonexistent"])

    # No issues have this label
    assert len(result) == 0


def test_fake_github_issues_state_case_sensitivity() -> None:
    """Test state filtering handles uppercase/lowercase properly."""
    pre_configured = {
        1: create_test_issue(1, "Open Issue", "Body", url="http://url/1"),
        2: create_test_issue(2, "Closed Issue", "Body", "CLOSED", "http://url/2"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    # Lowercase "open" should match uppercase "OPEN" state
    result = issues.list_issues(sentinel_path(), state="open")

    assert len(result) == 1
    assert result[0].state == "OPEN"


def test_fake_github_issues_mutation_tracking_independent() -> None:
    """Test that created_issues and added_comments track independently."""
    issues = FakeGitHubIssues(next_issue_number=1)

    # Create issues
    result1 = issues.create_issue(sentinel_path(), "Issue 1", "Body 1", ["label1"])
    result2 = issues.create_issue(sentinel_path(), "Issue 2", "Body 2", ["label2"])

    # Add comments
    issues.add_comment(sentinel_path(), result1.number, "Comment 1")
    issues.add_comment(sentinel_path(), result2.number, "Comment 2")

    # Verify both tracking lists are independent
    assert len(issues.created_issues) == 2
    assert len(issues.added_comments) == 2

    # Verify correct values
    assert issues.created_issues[0][0] == "Issue 1"
    assert issues.created_issues[1][0] == "Issue 2"
    assert issues.added_comments[0] == (1, "Comment 1")
    assert issues.added_comments[1] == (2, "Comment 2")


def test_fake_github_issues_pre_configured_and_created_coexist() -> None:
    """Test that pre-configured and dynamically created issues coexist."""
    pre_configured = {100: create_test_issue(100, "Pre-configured", "Body", url="http://url/100")}
    issues = FakeGitHubIssues(issues=pre_configured, next_issue_number=1)

    # Create new issue
    new_result = issues.create_issue(sentinel_path(), "New", "Body", ["label"])

    # Both should be retrievable
    pre_issue = issues.get_issue(sentinel_path(), 100)
    assert pre_issue.title == "Pre-configured"

    new_issue = issues.get_issue(sentinel_path(), new_result.number)
    assert new_issue.title == "New"

    # List should include both
    all_issues = issues.list_issues(sentinel_path())
    assert len(all_issues) == 2


def test_fake_github_issues_url_generation() -> None:
    """Test that created issues get properly formatted URLs."""
    issues = FakeGitHubIssues(next_issue_number=42)

    result = issues.create_issue(sentinel_path(), "Title", "Body", [])

    created_issue = issues.get_issue(sentinel_path(), result.number)

    assert created_issue.url == "https://github.com/test-owner/test-repo/issues/42"


def test_fake_github_issues_created_state_always_open() -> None:
    """Test that created issues always have OPEN state."""
    issues = FakeGitHubIssues()

    result = issues.create_issue(sentinel_path(), "Title", "Body", [])

    created_issue = issues.get_issue(sentinel_path(), result.number)

    assert created_issue.state == "OPEN"


def test_fake_github_issues_multiple_comments_same_issue() -> None:
    """Test adding multiple comments to the same issue."""
    pre_configured = {42: create_test_issue(42, "Test", "Body", url="http://url/42")}
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.add_comment(sentinel_path(), 42, "Comment 1")
    issues.add_comment(sentinel_path(), 42, "Comment 2")
    issues.add_comment(sentinel_path(), 42, "Comment 3")

    # All comments should be tracked
    assert issues.added_comments == [
        (42, "Comment 1"),
        (42, "Comment 2"),
        (42, "Comment 3"),
    ]


def test_fake_github_issues_ensure_label_exists_creates_new() -> None:
    """Test ensure_label_exists creates label when it doesn't exist."""
    issues = FakeGitHubIssues()

    issues.ensure_label_exists(
        sentinel_path(),
        label="erk-plan",
        description="Implementation plan created by erk",
        color="0E8A16",
    )

    assert "erk-plan" in issues.labels
    assert issues.created_labels == [("erk-plan", "Implementation plan created by erk", "0E8A16")]


def test_fake_github_issues_ensure_label_exists_idempotent() -> None:
    """Test ensure_label_exists doesn't create duplicate labels."""
    issues = FakeGitHubIssues(labels={"erk-plan"})

    issues.ensure_label_exists(
        sentinel_path(),
        label="erk-plan",
        description="Implementation plan created by erk",
        color="0E8A16",
    )

    # Label already exists, no new creation
    assert "erk-plan" in issues.labels
    assert issues.created_labels == []


def test_fake_github_issues_ensure_label_exists_multiple() -> None:
    """Test ensure_label_exists tracks multiple label creations."""
    issues = FakeGitHubIssues()

    issues.ensure_label_exists(sentinel_path(), "label1", "Description 1", "FF0000")
    issues.ensure_label_exists(sentinel_path(), "label2", "Description 2", "00FF00")
    issues.ensure_label_exists(sentinel_path(), "label3", "Description 3", "0000FF")

    assert "label1" in issues.labels
    assert "label2" in issues.labels
    assert "label3" in issues.labels
    assert issues.created_labels == [
        ("label1", "Description 1", "FF0000"),
        ("label2", "Description 2", "00FF00"),
        ("label3", "Description 3", "0000FF"),
    ]


def test_fake_github_issues_ensure_label_exists_mixed_existing_new() -> None:
    """Test ensure_label_exists with mix of existing and new labels."""
    issues = FakeGitHubIssues(labels={"existing-label"})

    issues.ensure_label_exists(sentinel_path(), "existing-label", "Desc 1", "111111")
    issues.ensure_label_exists(sentinel_path(), "new-label", "Desc 2", "222222")

    # Only new label should be in created_labels
    assert "existing-label" in issues.labels
    assert "new-label" in issues.labels
    assert issues.created_labels == [("new-label", "Desc 2", "222222")]


def test_fake_github_issues_labels_property_read_only() -> None:
    """Test labels property returns a copy (read-only access)."""
    issues = FakeGitHubIssues(labels={"label1"})

    labels = issues.labels
    labels.add("label2")  # Modify the returned copy

    # Original should be unchanged
    assert "label2" not in issues.labels
    assert issues.labels == {"label1"}


def test_fake_github_issues_created_labels_empty_initially() -> None:
    """Test created_labels property is empty list initially."""
    issues = FakeGitHubIssues()

    assert issues.created_labels == []


def test_fake_github_issues_created_labels_read_only() -> None:
    """Test created_labels property returns list that can be read."""
    issues = FakeGitHubIssues()
    issues.ensure_label_exists(sentinel_path(), "test-label", "Test description", "000000")

    # Should be able to read the list
    created = issues.created_labels
    assert len(created) == 1
    assert created[0] == ("test-label", "Test description", "000000")


def test_list_issues_respects_limit() -> None:
    """Test list_issues applies limit correctly."""
    now = datetime.now(UTC)
    issues_dict = {
        1: create_test_issue(
            number=1,
            title="Issue 1",
            body="Body 1",
            created_at=now,
            updated_at=now,
        ),
        2: create_test_issue(
            number=2,
            title="Issue 2",
            body="Body 2",
            created_at=now,
            updated_at=now,
        ),
        3: create_test_issue(
            number=3,
            title="Issue 3",
            body="Body 3",
            created_at=now,
            updated_at=now,
        ),
    }
    fake = FakeGitHubIssues(issues=issues_dict)

    # Test limit=2 returns only 2 issues
    result = fake.list_issues(sentinel_path(), limit=2)
    assert len(result) == 2

    # Test limit=None returns all issues
    result = fake.list_issues(sentinel_path(), limit=None)
    assert len(result) == 3


def test_get_issue_comments_empty() -> None:
    """Test get_issue_comments returns empty list when no comments exist."""
    fake = FakeGitHubIssues()

    result = fake.get_issue_comments(sentinel_path(), 123)

    assert result == []


def test_get_issue_comments_with_comments() -> None:
    """Test get_issue_comments returns comments for issue."""
    comments = {
        42: ["First comment", "Second comment"],
        100: ["Another comment"],
    }
    fake = FakeGitHubIssues(comments=comments)

    result = fake.get_issue_comments(sentinel_path(), 42)

    assert result == ["First comment", "Second comment"]


def test_get_multiple_issue_comments_empty_list() -> None:
    """Test get_multiple_issue_comments with empty issue list."""
    fake = FakeGitHubIssues()

    result = fake.get_multiple_issue_comments(sentinel_path(), [])

    assert result == {}


def test_get_multiple_issue_comments_no_comments() -> None:
    """Test get_multiple_issue_comments when issues have no comments."""
    fake = FakeGitHubIssues()

    result = fake.get_multiple_issue_comments(sentinel_path(), [1, 2, 3])

    assert result == {1: [], 2: [], 3: []}


def test_get_multiple_issue_comments_with_comments() -> None:
    """Test get_multiple_issue_comments returns all comments for multiple issues."""
    comments = {
        1: ["Comment on issue 1"],
        2: ["First comment on 2", "Second comment on 2"],
        3: [],
        4: ["Comment on issue 4"],
    }
    fake = FakeGitHubIssues(comments=comments)

    result = fake.get_multiple_issue_comments(sentinel_path(), [1, 2, 3, 4])

    assert result == {
        1: ["Comment on issue 1"],
        2: ["First comment on 2", "Second comment on 2"],
        3: [],
        4: ["Comment on issue 4"],
    }


def test_get_multiple_issue_comments_partial_match() -> None:
    """Test get_multiple_issue_comments with mix of existing and non-existing issues."""
    comments = {
        10: ["Comment on 10"],
        20: ["Comment on 20"],
    }
    fake = FakeGitHubIssues(comments=comments)

    # Request issues 10, 20, 30 - only 10 and 20 have comments
    result = fake.get_multiple_issue_comments(sentinel_path(), [10, 20, 30])

    assert result == {
        10: ["Comment on 10"],
        20: ["Comment on 20"],
        30: [],  # No comments for issue 30
    }


def test_get_multiple_issue_comments_single_issue() -> None:
    """Test get_multiple_issue_comments works with single issue."""
    comments = {
        42: ["Single comment"],
    }
    fake = FakeGitHubIssues(comments=comments)

    result = fake.get_multiple_issue_comments(sentinel_path(), [42])

    assert result == {42: ["Single comment"]}


def test_get_current_username_default() -> None:
    """Test get_current_username returns default 'testuser'."""
    fake = FakeGitHubIssues()

    result = fake.get_current_username()

    assert result == "testuser"


def test_get_current_username_custom() -> None:
    """Test get_current_username returns custom username from constructor."""
    fake = FakeGitHubIssues(username="custom-user")

    result = fake.get_current_username()

    assert result == "custom-user"


def test_get_current_username_none() -> None:
    """Test get_current_username returns None when simulating unauthenticated state."""
    fake = FakeGitHubIssues(username=None)

    result = fake.get_current_username()

    assert result is None


# ============================================================================
# close_issue() tests
# ============================================================================


def test_close_issue_updates_state() -> None:
    """Test close_issue changes issue state from OPEN to closed."""
    pre_configured = {42: create_test_issue(42, "Test Issue", "Body")}
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.close_issue(sentinel_path(), 42)

    updated_issue = issues.get_issue(sentinel_path(), 42)
    assert updated_issue.state == "closed"


def test_close_issue_missing_raises() -> None:
    """Test close_issue raises RuntimeError for non-existent issue."""
    issues = FakeGitHubIssues()

    with pytest.raises(RuntimeError, match="Issue #999 not found"):
        issues.close_issue(sentinel_path(), 999)


def test_close_issue_tracks_mutation() -> None:
    """Test close_issue tracks closed issue number in closed_issues list."""
    pre_configured = {42: create_test_issue(42, "Test Issue", "Body")}
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.close_issue(sentinel_path(), 42)

    assert 42 in issues.closed_issues


def test_close_issue_preserves_other_fields() -> None:
    """Test close_issue preserves title, body, labels unchanged."""
    pre_configured = {
        42: create_test_issue(42, "Test Issue", "Test body", labels=["bug", "urgent"])
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.close_issue(sentinel_path(), 42)

    updated_issue = issues.get_issue(sentinel_path(), 42)
    assert updated_issue.title == "Test Issue"
    assert updated_issue.body == "Test body"
    assert updated_issue.labels == ["bug", "urgent"]
    assert updated_issue.number == 42


# ============================================================================
# closed_issues property tests
# ============================================================================


def test_closed_issues_empty_initially() -> None:
    """Test closed_issues property is empty list on new instance."""
    issues = FakeGitHubIssues()

    assert issues.closed_issues == []


def test_closed_issues_tracks_multiple() -> None:
    """Test closed_issues tracks multiple closes in order."""
    pre_configured = {
        10: create_test_issue(10, "Issue 10", "Body"),
        20: create_test_issue(20, "Issue 20", "Body"),
        30: create_test_issue(30, "Issue 30", "Body"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.close_issue(sentinel_path(), 20)
    issues.close_issue(sentinel_path(), 10)
    issues.close_issue(sentinel_path(), 30)

    assert issues.closed_issues == [20, 10, 30]


# ============================================================================
# ensure_label_on_issue() tests
# ============================================================================


def test_ensure_label_on_issue_adds_label() -> None:
    """Test ensure_label_on_issue adds label when not present."""
    pre_configured = {42: create_test_issue(42, "Test Issue", "Body", labels=[])}
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.ensure_label_on_issue(sentinel_path(), 42, "new-label")

    updated_issue = issues.get_issue(sentinel_path(), 42)
    assert "new-label" in updated_issue.labels


def test_ensure_label_on_issue_idempotent() -> None:
    """Test ensure_label_on_issue is idempotent (no duplicate when already present)."""
    pre_configured = {42: create_test_issue(42, "Test Issue", "Body", labels=["existing"])}
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.ensure_label_on_issue(sentinel_path(), 42, "existing")

    updated_issue = issues.get_issue(sentinel_path(), 42)
    # Label should appear only once
    assert updated_issue.labels.count("existing") == 1


def test_ensure_label_on_issue_missing_raises() -> None:
    """Test ensure_label_on_issue raises RuntimeError for non-existent issue."""
    issues = FakeGitHubIssues()

    with pytest.raises(RuntimeError, match="Issue #999 not found"):
        issues.ensure_label_on_issue(sentinel_path(), 999, "label")


def test_ensure_label_on_issue_appends_to_existing() -> None:
    """Test ensure_label_on_issue preserves existing labels."""
    pre_configured = {42: create_test_issue(42, "Test Issue", "Body", labels=["label1", "label2"])}
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.ensure_label_on_issue(sentinel_path(), 42, "label3")

    updated_issue = issues.get_issue(sentinel_path(), 42)
    assert updated_issue.labels == ["label1", "label2", "label3"]


# ============================================================================
# remove_label_from_issue() tests
# ============================================================================


def test_remove_label_from_issue_removes() -> None:
    """Test remove_label_from_issue removes label when present."""
    pre_configured = {
        42: create_test_issue(42, "Test Issue", "Body", labels=["bug", "enhancement"])
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.remove_label_from_issue(sentinel_path(), 42, "bug")

    updated_issue = issues.get_issue(sentinel_path(), 42)
    assert "bug" not in updated_issue.labels
    assert "enhancement" in updated_issue.labels


def test_remove_label_from_issue_missing_raises() -> None:
    """Test remove_label_from_issue raises RuntimeError for non-existent issue."""
    issues = FakeGitHubIssues()

    with pytest.raises(RuntimeError, match="Issue #999 not found"):
        issues.remove_label_from_issue(sentinel_path(), 999, "label")


def test_remove_label_from_issue_preserves_others() -> None:
    """Test remove_label_from_issue preserves other labels unchanged."""
    pre_configured = {
        42: create_test_issue(42, "Test Issue", "Body", labels=["keep1", "remove", "keep2"])
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.remove_label_from_issue(sentinel_path(), 42, "remove")

    updated_issue = issues.get_issue(sentinel_path(), 42)
    assert updated_issue.labels == ["keep1", "keep2"]


def test_remove_label_from_issue_idempotent() -> None:
    """Test remove_label_from_issue is idempotent (no error when label not on issue)."""
    pre_configured = {42: create_test_issue(42, "Test Issue", "Body", labels=["other"])}
    issues = FakeGitHubIssues(issues=pre_configured)

    # Should not raise error when label doesn't exist on issue
    issues.remove_label_from_issue(sentinel_path(), 42, "nonexistent")

    updated_issue = issues.get_issue(sentinel_path(), 42)
    assert updated_issue.labels == ["other"]


# ============================================================================
# get_prs_referencing_issue() tests
# ============================================================================


def test_get_prs_referencing_issue_empty() -> None:
    """Test get_prs_referencing_issue returns empty list when no PRs configured."""
    issues = FakeGitHubIssues()

    result = issues.get_prs_referencing_issue(sentinel_path(), 42)

    assert result == []


def test_get_prs_referencing_issue_returns_configured_prs() -> None:
    """Test get_prs_referencing_issue returns pre-configured PRs."""
    from erk_shared.github.issues.types import PRReference

    pr_refs = {
        42: [
            PRReference(number=100, state="OPEN", is_draft=True),
            PRReference(number=101, state="MERGED", is_draft=False),
        ],
        99: [
            PRReference(number=200, state="CLOSED", is_draft=False),
        ],
    }
    issues = FakeGitHubIssues(pr_references=pr_refs)

    result = issues.get_prs_referencing_issue(sentinel_path(), 42)

    assert len(result) == 2
    assert result[0].number == 100
    assert result[0].state == "OPEN"
    assert result[0].is_draft is True
    assert result[1].number == 101
    assert result[1].state == "MERGED"
    assert result[1].is_draft is False


def test_get_prs_referencing_issue_different_issue_numbers() -> None:
    """Test get_prs_referencing_issue returns correct PRs for each issue."""
    from erk_shared.github.issues.types import PRReference

    pr_refs = {
        10: [PRReference(number=100, state="OPEN", is_draft=True)],
        20: [PRReference(number=200, state="CLOSED", is_draft=False)],
    }
    issues = FakeGitHubIssues(pr_references=pr_refs)

    result_10 = issues.get_prs_referencing_issue(sentinel_path(), 10)
    result_20 = issues.get_prs_referencing_issue(sentinel_path(), 20)
    result_30 = issues.get_prs_referencing_issue(sentinel_path(), 30)

    assert len(result_10) == 1
    assert result_10[0].number == 100
    assert len(result_20) == 1
    assert result_20[0].number == 200
    assert result_30 == []  # No PRs configured for issue 30
