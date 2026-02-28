"""Tests for EntityState — mutable KV metadata on entity body."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from erk_shared.entity_store.state import (
    EntityState,
    entity_state_set,
    entity_state_set_field,
    entity_state_update,
)
from erk_shared.entity_store.types import EntityKind
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import (
    create_metadata_block,
    render_metadata_block,
)
from erk_shared.gateway.github.metadata.types import MetadataBlockSchema
from erk_shared.gateway.github.types import PRDetails

REPO_ROOT = Path("/fake/repo")
NOW = datetime(2024, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class _NoopSchema(MetadataBlockSchema):
    """Test schema that accepts any data."""

    def validate(self, data: dict[str, Any]) -> None:
        pass

    def get_key(self) -> str:
        return "test"


NOOP_SCHEMA = _NoopSchema()


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


class TestEntityStateIssue:
    """Tests for EntityState operating on issues."""

    def test_get_returns_none_when_no_block(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body="No metadata here")})
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        assert state.get("plan-header") is None

    def test_get_returns_data_when_block_exists(self) -> None:
        block_text = _render_block("plan-header", {"status": "draft", "version": 1})
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body=block_text)})
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        result = state.get("plan-header")
        assert result is not None
        assert result["status"] == "draft"
        assert result["version"] == 1

    def test_get_field_returns_specific_field(self) -> None:
        block_text = _render_block("plan-header", {"status": "draft", "version": 2})
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body=block_text)})
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        assert state.get_field("plan-header", "status") == "draft"
        assert state.get_field("plan-header", "version") == 2

    def test_get_field_returns_none_for_missing_block(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body="No blocks")})
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        assert state.get_field("plan-header", "status") is None

    def test_get_field_returns_none_for_missing_field(self) -> None:
        block_text = _render_block("plan-header", {"status": "draft"})
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body=block_text)})
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        assert state.get_field("plan-header", "nonexistent") is None

    def test_has_returns_true_when_block_exists(self) -> None:
        block_text = _render_block("plan-header", {"status": "draft"})
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body=block_text)})
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        assert state.has("plan-header") is True

    def test_has_returns_false_when_no_block(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body="No blocks")})
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        assert state.has("plan-header") is False

    def test_set_creates_new_block_on_empty_body(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body="")})
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        entity_state_set(state, "plan-header", {"status": "active"}, schema=NOOP_SCHEMA)

        # Verify the body was updated
        assert len(issues.updated_bodies) == 1
        _, new_body = issues.updated_bodies[0]
        assert "plan-header" in new_body
        assert "active" in new_body

    def test_set_replaces_existing_block(self) -> None:
        block_text = _render_block("plan-header", {"status": "draft"})
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body=block_text)})
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        entity_state_set(
            state, "plan-header", {"status": "active", "version": 2}, schema=NOOP_SCHEMA
        )

        assert len(issues.updated_bodies) == 1
        _, new_body = issues.updated_bodies[0]
        assert "active" in new_body
        assert "version" in new_body

    def test_set_then_get_round_trip(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body="")})
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        entity_state_set(
            state, "plan-header", {"status": "active", "version": 3}, schema=NOOP_SCHEMA
        )

        # After set, the fake's issue body was updated, so get should work
        result = state.get("plan-header")
        assert result is not None
        assert result["status"] == "active"
        assert result["version"] == 3

    def test_set_field_updates_single_field(self) -> None:
        block_text = _render_block("plan-header", {"status": "draft", "version": 1})
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body=block_text)})
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        entity_state_set_field(state, "plan-header", "status", "active", schema=NOOP_SCHEMA)

        result = state.get("plan-header")
        assert result is not None
        assert result["status"] == "active"
        assert result["version"] == 1  # Unchanged

    def test_update_changes_multiple_fields(self) -> None:
        block_text = _render_block(
            "plan-header", {"status": "draft", "version": 1, "author": "alice"}
        )
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body=block_text)})
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        entity_state_update(
            state, "plan-header", {"status": "active", "version": 2}, schema=NOOP_SCHEMA
        )

        result = state.get("plan-header")
        assert result is not None
        assert result["status"] == "active"
        assert result["version"] == 2
        assert result["author"] == "alice"  # Unchanged

    def test_update_raises_when_block_missing(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body="No blocks")})
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        with pytest.raises(ValueError, match="not found"):
            entity_state_update(state, "plan-header", {"status": "active"}, schema=NOOP_SCHEMA)

    def test_multiple_blocks_in_same_body(self) -> None:
        block1 = _render_block("plan-header", {"status": "draft"})
        block2 = _render_block("objective-header", {"created_by": "alice"})
        combined_body = f"{block1}\n\n{block2}"
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1, body=combined_body)})
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=1,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        assert state.get_field("plan-header", "status") == "draft"
        assert state.get_field("objective-header", "created_by") == "alice"


class TestEntityStatePR:
    """Tests for EntityState operating on PRs."""

    def test_get_from_pr_body(self) -> None:
        block_text = _render_block("plan-header", {"status": "active"})
        pr = _make_pr_details(number=42, body=block_text)
        issues = FakeGitHubIssues()
        github = FakeGitHub(issues_gateway=issues, pr_details={42: pr})
        state = EntityState(
            number=42,
            kind=EntityKind.PR,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        result = state.get("plan-header")
        assert result is not None
        assert result["status"] == "active"

    def test_set_on_pr_updates_pr_body(self) -> None:
        pr = _make_pr_details(number=42, body="")
        issues = FakeGitHubIssues()
        github = FakeGitHub(issues_gateway=issues, pr_details={42: pr})
        state = EntityState(
            number=42,
            kind=EntityKind.PR,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        entity_state_set(state, "plan-header", {"status": "active"}, schema=NOOP_SCHEMA)

        # Verify the PR body was updated via FakeGitHub
        assert len(github._updated_pr_bodies) == 1
        pr_number, new_body = github._updated_pr_bodies[0]
        assert pr_number == 42
        assert "plan-header" in new_body

    def test_pr_not_found_raises_runtime_error(self) -> None:
        issues = FakeGitHubIssues()
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=999,
            kind=EntityKind.PR,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        with pytest.raises(RuntimeError, match="PR #999 not found"):
            state.get("plan-header")

    def test_issue_not_found_raises_runtime_error(self) -> None:
        issues = FakeGitHubIssues()
        github = FakeGitHub(issues_gateway=issues)
        state = EntityState(
            number=999,
            kind=EntityKind.ISSUE,
            github=github,
            github_issues=issues,
            repo_root=REPO_ROOT,
        )
        with pytest.raises(RuntimeError, match="Issue #999 not found"):
            state.get("plan-header")
