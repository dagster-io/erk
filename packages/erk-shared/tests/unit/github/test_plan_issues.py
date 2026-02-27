"""Tests for plan_issues.py - objective issue creation and create_plan_draft_pr."""

from pathlib import Path

import pytest

from erk_shared.gateway.branch_manager.fake import FakeBranchManager
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.plan_issues import (
    CreatePlanIssueResult,
    create_objective_issue,
)
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.create_plan_draft_pr import (
    CreatePlanDraftPRResult,
    create_plan_draft_pr,
)


def _create_plan(
    *,
    tmp_path: Path,
    plan_content: str = "# My Feature Plan\n\nImplementation steps...",
    title: str | None = None,
    labels: list[str] | None = None,
    source_repo: str | None = None,
    objective_id: int | None = None,
    created_from_session: str | None = None,
    learned_from_issue: int | None = None,
    fake_github: FakeGitHub | None = None,
    fake_issues: FakeGitHubIssues | None = None,
    fake_git: FakeGit | None = None,
    fake_time: FakeTime | None = None,
) -> CreatePlanDraftPRResult:
    """Helper to create a plan draft PR with sensible defaults."""
    if fake_issues is None:
        fake_issues = FakeGitHubIssues(username="testuser")
    if fake_github is None:
        fake_github = FakeGitHub(issues_gateway=fake_issues)
    if fake_git is None:
        fake_git = FakeGit(trunk_branches={tmp_path: "main"})
    if fake_time is None:
        fake_time = FakeTime()
    if labels is None:
        labels = ["erk-pr", "erk-plan"]

    return create_plan_draft_pr(
        git=fake_git,
        github=fake_github,
        github_issues=fake_issues,
        branch_manager=FakeBranchManager(),
        time=fake_time,
        repo_root=tmp_path,
        cwd=tmp_path,
        plan_content=plan_content,
        title=title,
        labels=labels,
        source_repo=source_repo,
        objective_id=objective_id,
        created_from_session=created_from_session,
        created_from_workflow_run_url=None,
        learned_from_issue=learned_from_issue,
    )


class TestCreatePlanDraftPRSuccess:
    """Test successful draft PR creation scenarios."""

    def test_creates_standard_plan_pr(self, tmp_path: Path) -> None:
        """Create a standard plan draft PR with minimal options."""
        fake_issues = FakeGitHubIssues(username="testuser")
        fake_github = FakeGitHub(issues_gateway=fake_issues)

        result = _create_plan(tmp_path=tmp_path, fake_github=fake_github, fake_issues=fake_issues)

        assert result.success is True
        assert result.plan_number == 1
        assert result.plan_url is not None
        assert result.title == "My Feature Plan"
        assert result.branch_name is not None
        assert result.error is None

        # Verify draft PR was created
        assert len(fake_github.created_prs) == 1

    def test_creates_learn_plan_pr(self, tmp_path: Path) -> None:
        """Create a learn plan draft PR with learn-specific labels."""
        fake_issues = FakeGitHubIssues(username="testuser")
        fake_github = FakeGitHub(issues_gateway=fake_issues)

        result = _create_plan(
            tmp_path=tmp_path,
            plan_content="# Extraction Plan: main\n\nAnalysis...",
            labels=["erk-pr", "erk-learn"],
            fake_github=fake_github,
            fake_issues=fake_issues,
        )

        assert result.success is True
        assert result.title == "Extraction Plan: main"

        # Verify draft PR was created with learn tag
        assert len(fake_github.created_prs) == 1
        _branch, pr_title, _body, _base, _draft = fake_github.created_prs[0]
        assert "[erk-learn]" in pr_title

    def test_uses_provided_title(self, tmp_path: Path) -> None:
        """Use provided title instead of extracting from H1."""
        result = _create_plan(
            tmp_path=tmp_path,
            plan_content="# Wrong Title\n\nContent...",
            title="Correct Title",
        )

        assert result.success is True
        assert result.title == "Correct Title"

    def test_branch_name_contains_title_slug(self, tmp_path: Path) -> None:
        """Branch name should be derived from title."""
        result = _create_plan(tmp_path=tmp_path)

        assert result.success is True
        assert result.branch_name is not None
        assert result.branch_name.startswith("plnd/")


class TestCreatePlanDraftPRTitleExtraction:
    """Test title extraction from various plan formats."""

    def test_extracts_h1_title(self, tmp_path: Path) -> None:
        """Extract title from H1 heading."""
        result = _create_plan(
            tmp_path=tmp_path,
            plan_content="# Feature: Add Auth\n\nDetails...",
        )

        assert result.title == "Feature: Add Auth"

    def test_strips_plan_prefix(self, tmp_path: Path) -> None:
        """Strip common plan prefixes from title."""
        result = _create_plan(
            tmp_path=tmp_path,
            plan_content="# Plan: Add Feature X\n\nDetails...",
        )

        assert result.title == "Add Feature X"


class TestCreatePlanDraftPRResultDataclass:
    """Test CreatePlanDraftPRResult and CreatePlanIssueResult dataclasses."""

    def test_draft_pr_result_is_frozen(self) -> None:
        """Verify result is immutable."""
        result = CreatePlanDraftPRResult(
            success=True,
            plan_number=1,
            plan_url="https://example.com/1",
            branch_name="plnd/test-01-15-1430",
            title="Test",
            error=None,
        )

        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]

    def test_plan_issue_result_is_frozen(self) -> None:
        """Verify CreatePlanIssueResult is immutable."""
        result = CreatePlanIssueResult(
            success=True,
            plan_number=1,
            plan_url="https://example.com/1",
            title="Test",
            error=None,
        )

        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]


class TestCreateObjectiveIssue:
    """Test objective issue creation using create_objective_issue()."""

    def test_creates_objective_issue_with_correct_labels(self, tmp_path: Path) -> None:
        """Objective issues use only erk-objective label (NOT erk-plan)."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Objective\n\n## Goal\n\nBuild a feature..."

        result = create_objective_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            time=FakeTime(),
            title=None,
            extra_labels=None,
            slug=None,
        )

        assert result.success is True
        assert result.plan_number == 1
        assert result.title == "My Objective"

        # Verify labels only include erk-objective (NOT erk-plan)
        _, body, labels = fake_gh.created_issues[0]
        assert labels == ["erk-objective"]

        # Verify only erk-objective label was created
        assert "erk-objective" in fake_gh.labels
        assert "erk-plan" not in fake_gh.labels

    def test_objective_has_no_title_tag(self, tmp_path: Path) -> None:
        """Objective issues have no title tag."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Objective\n\nContent..."

        result = create_objective_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            time=FakeTime(),
            title=None,
            extra_labels=None,
            slug=None,
        )

        assert result.success is True

        # Title should be just the extracted title, no suffix
        title, _, _ = fake_gh.created_issues[0]
        assert title == "My Objective"
        assert "[erk-plan]" not in title
        assert "[erk-objective]" not in title

    def test_objective_v2_body_has_metadata_and_content_in_comment(self, tmp_path: Path) -> None:
        """V2 format: body has metadata block, content is in first comment."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Objective\n\n## Goal\n\nBuild something great."

        result = create_objective_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            time=FakeTime(),
            title=None,
            extra_labels=None,
            slug=None,
        )

        assert result.success is True

        # Body should have metadata block (objective-header)
        _, body, _ = fake_gh.created_issues[0]
        assert "objective-header" in body
        assert "created_by: testuser" in body

        # Plan content should be in the first comment, not the body
        assert len(fake_gh.added_comments) == 1
        _issue_num, comment_body, _comment_id = fake_gh.added_comments[0]
        assert "# My Objective" in comment_body
        assert "## Goal" in comment_body
        assert "Build something great." in comment_body

    def test_objective_v2_has_content_comment(self, tmp_path: Path) -> None:
        """V2 format: objective content is added as first comment."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Objective\n\nContent..."

        result = create_objective_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            time=FakeTime(),
            title=None,
            extra_labels=None,
            slug=None,
        )

        assert result.success is True

        # V2: content is in the first comment
        assert len(fake_gh.added_comments) == 1
        _issue_num, comment_body, _comment_id = fake_gh.added_comments[0]
        assert "objective-body" in comment_body
        assert "Content..." in comment_body

    def test_objective_has_no_commands_section(self, tmp_path: Path) -> None:
        """Objective issues have no commands section."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Objective\n\nContent..."

        result = create_objective_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            time=FakeTime(),
            title=None,
            extra_labels=None,
            slug=None,
        )

        assert result.success is True

        # Body is updated (to set objective_comment_id), but should NOT have commands section
        assert len(fake_gh.updated_bodies) == 1
        _issue_num, updated_body = fake_gh.updated_bodies[0]
        assert "## Commands" not in updated_body
        assert "erk br co --for-plan" not in updated_body

    def test_objective_with_extra_labels(self, tmp_path: Path) -> None:
        """Objective issues can have extra labels."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Objective\n\nContent..."

        result = create_objective_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            time=FakeTime(),
            title=None,
            extra_labels=["priority-high"],
            slug=None,
        )

        assert result.success is True

        _, _, labels = fake_gh.created_issues[0]
        assert "erk-plan" not in labels  # objectives don't get erk-plan
        assert "erk-objective" in labels
        assert "priority-high" in labels

    def test_objective_with_roadmap_uses_details_format(self, tmp_path: Path) -> None:
        """Objective with roadmap phases produces <details> wrapped roadmap block."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = (
            "# My Objective\n\n"
            "## Roadmap\n\n"
            "### Phase 1: Foundation\n\n"
            "| Node | Description | Status | Plan | PR |\n"
            "|------|-------------|--------|------|-----|\n"
            "| 1.1 | Set up structure | pending | - | - |\n"
            "| 1.2 | Add types | pending | - | - |\n"
            "\n"
            "<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->\n"
            "<!-- erk:metadata-block:objective-roadmap -->\n"
            "<details>\n"
            "<summary><code>objective-roadmap</code></summary>\n"
            "\n"
            "```yaml\n"
            "\n"
            "schema_version: '2'\n"
            "steps:\n"
            "  - id: '1.1'\n"
            "    description: Set up structure\n"
            "    status: pending\n"
            "    plan: null\n"
            "    pr: null\n"
            "  - id: '1.2'\n"
            "    description: Add types\n"
            "    status: pending\n"
            "    plan: null\n"
            "    pr: null\n"
            "\n"
            "```\n"
            "\n"
            "</details>\n"
            "<!-- /erk:metadata-block:objective-roadmap -->\n"
        )

        result = create_objective_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            time=FakeTime(),
            title=None,
            extra_labels=None,
            slug=None,
        )

        assert result.success is True

        # The updated body should contain the roadmap block in <details> format
        _, updated_body = fake_gh.updated_bodies[0]
        assert "objective-roadmap" in updated_body
        assert "<details>" in updated_body
        assert "<summary><code>objective-roadmap</code></summary>" in updated_body
        assert "```yaml" in updated_body
        assert "schema_version: '3'" in updated_body


class TestCreateObjectiveIssueSlugValidation:
    """Test slug validation gate in create_objective_issue()."""

    def test_invalid_slug_returns_failure_no_issue_created(self, tmp_path: Path) -> None:
        """Invalid slug returns success=False with descriptive error, no issue created."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Objective\n\nContent..."

        result = create_objective_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            time=FakeTime(),
            title=None,
            extra_labels=None,
            slug="INVALID SLUG",
        )

        assert result.success is False
        assert result.plan_number is None
        assert result.error is not None
        assert "Invalid objective slug" in result.error
        assert "INVALID SLUG" in result.error
        # Title should be populated (extraction happens before validation)
        assert result.title == "My Objective"
        # No issue should have been created
        assert len(fake_gh.created_issues) == 0

    def test_valid_slug_passes_through_to_issue_body(self, tmp_path: Path) -> None:
        """Valid slug passes validation and appears in issue body."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Objective\n\nContent..."

        result = create_objective_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            time=FakeTime(),
            title=None,
            extra_labels=None,
            slug="build-auth-system",
        )

        assert result.success is True
        assert result.plan_number is not None

        # Verify slug appears in the issue body
        _, body, _ = fake_gh.created_issues[0]
        assert "slug: build-auth-system" in body

    def test_none_slug_skips_validation(self, tmp_path: Path) -> None:
        """None slug skips validation entirely and succeeds."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Objective\n\nContent..."

        result = create_objective_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            time=FakeTime(),
            title=None,
            extra_labels=None,
            slug=None,
        )

        assert result.success is True
        assert result.plan_number is not None

        # Verify no slug in body
        _, body, _ = fake_gh.created_issues[0]
        assert "slug:" not in body
