"""Tests for GitHubEntity — main entry point combining state and log."""

from datetime import UTC, datetime
from pathlib import Path

from erk_shared.entity_store.entity import GitHubEntity
from erk_shared.entity_store.log import EntityLog
from erk_shared.entity_store.state import EntityState, entity_state_set_field
from erk_shared.entity_store.types import EntityKind
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import (
    create_metadata_block,
    render_erk_issue_event,
    render_metadata_block,
)
from erk_shared.gateway.github.types import PRDetails

REPO_ROOT = Path("/fake/repo")
NOW = datetime(2024, 1, 1, tzinfo=UTC)


def _make_issue_info(
    *,
    number: int,
    body: str,
) -> IssueInfo:
    return IssueInfo(
        number=number,
        title="Test Issue",
        body=body,
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=[],
        assignees=[],
        created_at=NOW,
        updated_at=NOW,
        author="test-user",
    )


def _make_pr_details(
    *,
    number: int,
    body: str,
) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/test/repo/pull/{number}",
        title="Test PR",
        body=body,
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test",
        repo="repo",
    )


def _render_block(key: str, data: dict) -> str:
    block = create_metadata_block(key, data, schema=None)
    return render_metadata_block(block)


def _render_event_comment(key: str, data: dict) -> str:
    block = create_metadata_block(key, data, schema=None)
    return render_erk_issue_event(
        title=f"Event: {key}",
        metadata=block,
        description="",
    )


class TestGitHubEntityProperties:
    """Tests for GitHubEntity property accessors."""

    def test_number_property(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body="")})
        github = FakeGitHub(issues_gateway=issues)
        entity = GitHubEntity.create(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        assert entity.number == 1

    def test_kind_property(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body="")})
        github = FakeGitHub(issues_gateway=issues)
        entity = GitHubEntity.create(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        assert entity.kind is EntityKind.ISSUE

    def test_state_returns_entity_state(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body="")})
        github = FakeGitHub(issues_gateway=issues)
        entity = GitHubEntity.create(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        assert isinstance(entity.state, EntityState)

    def test_log_returns_entity_log(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body="")})
        github = FakeGitHub(issues_gateway=issues)
        entity = GitHubEntity.create(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        assert isinstance(entity.log, EntityLog)


class TestGitHubEntityIssueWorkflow:
    """Integration tests: state + log working together on an issue."""

    def test_set_state_then_append_log(self) -> None:
        block_text = _render_block("plan-header", {"status": "draft"})
        issues = FakeGitHubIssues(
            issues={1: _make_issue_info(number=1, body=block_text)},
        )
        github = FakeGitHub(issues_gateway=issues)
        entity = GitHubEntity.create(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )

        # Update state
        entity_state_set_field(entity.state, "plan-header", "status", "active")
        assert entity.state.get_field("plan-header", "status") == "active"

        # Append log entry
        cid = entity.log.append(
            "workflow-started",
            {"started_at": "2024-01-01T00:00:00Z"},
            title="Workflow Started",
            description="Starting implementation",
            schema=None,
        )
        assert isinstance(cid, int)
        assert len(issues.added_comments) == 1

    def test_read_state_and_log_independently(self) -> None:
        block_text = _render_block("plan-header", {"status": "active", "version": 2})
        log_comment = _render_event_comment(
            "submission-queued",
            {"queued_at": "2024-01-01T00:00:00Z", "status": "queued"},
        )
        issues = FakeGitHubIssues(
            issues={1: _make_issue_info(number=1, body=block_text)},
            comments={1: [log_comment]},
        )
        github = FakeGitHub(issues_gateway=issues)
        entity = GitHubEntity.create(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )

        # Read state
        assert entity.state.get_field("plan-header", "status") == "active"
        assert entity.state.get_field("plan-header", "version") == 2

        # Read log
        entries = entity.log.entries("submission-queued")
        assert len(entries) == 1
        assert entries[0].data["status"] == "queued"


class TestGitHubEntityPRWorkflow:
    """Integration tests: state + log working together on a PR."""

    def test_pr_state_uses_pr_body(self) -> None:
        block_text = _render_block("plan-header", {"status": "submitted"})
        pr = _make_pr_details(number=42, body=block_text)
        issues = FakeGitHubIssues(issues={42: _make_issue_info(number=42, body="issue body")})
        github = FakeGitHub(issues_gateway=issues, pr_details={42: pr})
        entity = GitHubEntity.create(
            number=42,
            kind=EntityKind.PR,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )

        # State reads from PR body (not issue body)
        assert entity.state.get_field("plan-header", "status") == "submitted"

    def test_pr_log_uses_issue_comments(self) -> None:
        """PR log entries are stored as issue comments (PRs are issues on GitHub)."""
        log_comment = _render_event_comment(
            "impl-started",
            {"started_at": "2024-01-01T00:00:00Z"},
        )
        pr = _make_pr_details(number=42, body="")
        issues = FakeGitHubIssues(
            issues={42: _make_issue_info(number=42, body="")},
            comments={42: [log_comment]},
        )
        github = FakeGitHub(issues_gateway=issues, pr_details={42: pr})
        entity = GitHubEntity.create(
            number=42,
            kind=EntityKind.PR,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )

        entries = entity.log.entries("impl-started")
        assert len(entries) == 1

    def test_pr_append_log_adds_comment(self) -> None:
        pr = _make_pr_details(number=42, body="")
        issues = FakeGitHubIssues(issues={42: _make_issue_info(number=42, body="")})
        github = FakeGitHub(issues_gateway=issues, pr_details={42: pr})
        entity = GitHubEntity.create(
            number=42,
            kind=EntityKind.PR,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )

        cid = entity.log.append(
            "impl-started",
            {"started_at": "2024-01-01T00:00:00Z"},
            title="Implementation Started",
            description="",
            schema=None,
        )
        assert isinstance(cid, int)
        # Comment was added to issue #42 (since PRs are issues)
        assert len(issues.added_comments) == 1
        assert issues.added_comments[0][0] == 42
