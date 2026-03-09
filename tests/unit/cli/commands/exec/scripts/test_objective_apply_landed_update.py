"""Tests for erk exec objective-apply-landed-update."""

import json
import textwrap
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.objective_apply_landed_update import (
    objective_apply_landed_update,
)
from erk_shared.context.testing import context_for_test
from erk_shared.fakes.git import FakeGit
from erk_shared.fakes.github import FakeLocalGitHub
from erk_shared.fakes.github_issues import FakeGitHubIssues
from erk_shared.fakes.remote_github import FakeRemoteGitHub
from erk_shared.fakes.time import FakeTime
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo
from erk_shared.gateway.github.types import PRDetails, RepoInfo
from erk_shared.plan_store.planned_pr import PlannedPRBackend

_TEST_REPO_INFO = RepoInfo(owner="test-owner", name="test-repo")


def _make_remote(
    issues: dict[int, IssueInfo] | None = None,
    *,
    comments_by_id: dict[int, str] | None = None,
) -> FakeRemoteGitHub:
    return FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=issues if issues is not None else {},
        issue_comments=None,
        pr_references=None,
        comments_by_id=comments_by_id,
    )


def _make_issue(*, number: int, title: str, body: str) -> IssueInfo:
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-objective"],
        assignees=[],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        author="testuser",
    )


def _make_pr_details(
    *, number: int, title: str, body: str, head_ref_name: str = "plnd/test-branch"
) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=title,
        body=body,
        state="MERGED",
        is_draft=False,
        base_ref_name="master",
        head_ref_name=head_ref_name,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


ROADMAP_BODY = textwrap.dedent("""\
    # My Objective

    <!-- erk:metadata-block:objective-header -->

    <details>
    <summary><code>objective-header</code></summary>

    ```yaml
    created_at: '2026-01-01T00:00:00Z'
    created_by: testuser
    objective_comment_id: 55555
    slug: null
    ```

    </details>

    <!-- /erk:metadata-block:objective-header -->

    <!-- erk:metadata-block:objective-roadmap -->

    <details>
    <summary><code>objective-roadmap</code></summary>

    ```yaml
    schema_version: "2"
    steps:
    - id: "1.1"
      description: "Add user model"
      status: "in_progress"
      pr: null
    - id: "1.2"
      description: "Add JWT library"
      status: "in_progress"
      pr: null
    - id: "2.1"
      description: "Implement login"
      status: "pending"
      pr: null
    ```

    </details>

    <!-- /erk:metadata-block:objective-roadmap -->

    ## Roadmap
""")

PLAN_BODY_WITH_OBJECTIVE = textwrap.dedent("""\
    <!-- erk:metadata-block:plan-header -->

    <details>
    <summary><code>plan-header</code></summary>

    ```yaml
    objective_issue: 6423
    title: My Plan
    ```

    </details>

    <!-- /erk:metadata-block:plan-header -->

    # Plan content
""")

OBJECTIVE_COMMENT_BODY = textwrap.dedent("""\
    <!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
    <!-- erk:metadata-block:objective-body -->
    <details open>
    <summary><strong>Objective</strong></summary>

    ## Design Decisions

    Use JWT for authentication.

    </details>
    <!-- /erk:metadata-block:objective-body -->
""")


class TestApplyLandedUpdateHappyPath:
    def test_updates_nodes_and_posts_comment(self, tmp_path: Path) -> None:
        """All matched nodes updated to done, action comment posted, returns rich JSON."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan = _make_issue(number=6517, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        pr = _make_pr_details(number=6517, title="Add auth system", body="pr body")

        comment = IssueComment(
            body=OBJECTIVE_COMMENT_BODY,
            url="https://github.com/owner/repo/issues/6423#issuecomment-55555",
            id=55555,
            author="testuser",
        )
        fake_issues = FakeGitHubIssues(
            issues={6423: objective, 6517: plan},
            comments_with_urls={6423: [comment]},
        )
        fake_github = FakeLocalGitHub(
            issues_gateway=fake_issues,
            pr_details={6517: pr},
        )
        remote = _make_remote(
            {6423: objective, 6513: plan},
            comments_by_id={55555: OBJECTIVE_COMMENT_BODY},
        )

        runner = CliRunner()
        result = runner.invoke(
            objective_apply_landed_update,
            [
                "--pr",
                "6517",
                "--objective",
                "6423",
                "--branch",
                "plnd/some-branch",
                "--node",
                "1.1",
                "--node",
                "1.2",
            ],
            obj=context_for_test(
                github=fake_github,
                plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
                remote_github=remote,
                repo_root=tmp_path,
                cwd=tmp_path,
                repo_info=_TEST_REPO_INFO,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["objective"]["number"] == 6423
        assert data["plan"]["number"] == "6517"
        assert data["pr"]["number"] == 6517

        # Node updates recorded
        node_updates = data["node_updates"]
        assert len(node_updates) == 2
        assert node_updates[0]["node_id"] == "1.1"
        assert node_updates[1]["node_id"] == "1.2"

        # Action comment was posted
        assert data["action_comment_id"] is not None
        assert len(remote.added_issue_comments) == 1
        added_comment = remote.added_issue_comments[0]
        assert added_comment.issue_number == 6423
        assert "Landed PR #6517" in added_comment.body
        assert "Add auth system" in added_comment.body

        # Issue body was updated
        assert len(remote.updated_issue_bodies) == 1

        # Roadmap reflects the updates
        roadmap = data["roadmap"]
        assert roadmap["summary"]["done"] == 2

    def test_objective_content_included(self, tmp_path: Path) -> None:
        """Objective prose content from the first comment is included."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan = _make_issue(number=6517, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        comment = IssueComment(
            body=OBJECTIVE_COMMENT_BODY,
            url="https://github.com/owner/repo/issues/6423#issuecomment-55555",
            id=55555,
            author="testuser",
        )
        fake_issues = FakeGitHubIssues(
            issues={6423: objective, 6517: plan},
            comments_with_urls={6423: [comment]},
        )
        fake_github = FakeLocalGitHub(
            issues_gateway=fake_issues,
            pr_details={6517: pr},
        )

        runner = CliRunner()
        result = runner.invoke(
            objective_apply_landed_update,
            [
                "--pr",
                "6517",
                "--objective",
                "6423",
                "--branch",
                "plnd/some-branch",
                "--node",
                "1.1",
                "--node",
                "1.2",
            ],
            obj=context_for_test(
                github=fake_github,
                plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
                remote_github=_make_remote(
                    {6423: objective, 6513: plan},
                    comments_by_id={55555: OBJECTIVE_COMMENT_BODY},
                ),
                repo_root=tmp_path,
                cwd=tmp_path,
                repo_info=_TEST_REPO_INFO,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["objective"]["objective_content"] is not None
        assert "Design Decisions" in data["objective"]["objective_content"]


class TestApplyLandedUpdateNoNodes:
    def test_no_node_flags_still_posts_comment(self, tmp_path: Path) -> None:
        """When no --node flags are passed, still posts action comment."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan = _make_issue(number=6517, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        comment = IssueComment(
            body=OBJECTIVE_COMMENT_BODY,
            url="https://github.com/owner/repo/issues/6423#issuecomment-55555",
            id=55555,
            author="testuser",
        )
        fake_issues = FakeGitHubIssues(
            issues={6423: objective, 6517: plan},
            comments_with_urls={6423: [comment]},
        )
        fake_github = FakeLocalGitHub(
            issues_gateway=fake_issues,
            pr_details={6517: pr},
        )
        remote = _make_remote(
            {6423: objective, 6513: plan},
            comments_by_id={55555: OBJECTIVE_COMMENT_BODY},
        )

        runner = CliRunner()
        result = runner.invoke(
            objective_apply_landed_update,
            [
                "--pr",
                "6517",
                "--objective",
                "6423",
                "--branch",
                "plnd/some-branch",
            ],
            obj=context_for_test(
                github=fake_github,
                plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
                remote_github=remote,
                repo_root=tmp_path,
                cwd=tmp_path,
                repo_info=_TEST_REPO_INFO,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["node_updates"] == []

        # Action comment still posted
        assert len(remote.added_issue_comments) == 1

        # Issue body NOT updated (no nodes to update)
        assert len(remote.updated_issue_bodies) == 0


ROADMAP_BODY_WITH_PR_REF = textwrap.dedent("""\
    # My Objective

    <!-- erk:metadata-block:objective-header -->

    <details>
    <summary><code>objective-header</code></summary>

    ```yaml
    created_at: '2026-01-01T00:00:00Z'
    created_by: testuser
    objective_comment_id: 55555
    slug: null
    ```

    </details>

    <!-- /erk:metadata-block:objective-header -->

    <!-- erk:metadata-block:objective-roadmap -->

    <details>
    <summary><code>objective-roadmap</code></summary>

    ```yaml
    schema_version: "2"
    steps:
    - id: "1.1"
      description: "Add user model"
      status: "in_progress"
      pr: "#6517"
    - id: "1.2"
      description: "Add JWT library"
      status: "in_progress"
      pr: null
    - id: "2.1"
      description: "Implement login"
      status: "pending"
      pr: null
    ```

    </details>

    <!-- /erk:metadata-block:objective-roadmap -->

    ## Roadmap
""")


class TestApplyLandedUpdateAutoMatch:
    def test_auto_matches_nodes_by_pr_ref(self, tmp_path: Path) -> None:
        """When no --node flags are passed, auto-matches nodes whose pr field references the PR."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY_WITH_PR_REF)
        plan = _make_issue(number=6517, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        pr = _make_pr_details(number=6517, title="Add auth system", body="pr body")

        comment = IssueComment(
            body=OBJECTIVE_COMMENT_BODY,
            url="https://github.com/owner/repo/issues/6423#issuecomment-55555",
            id=55555,
            author="testuser",
        )
        fake_issues = FakeGitHubIssues(
            issues={6423: objective, 6517: plan},
            comments_with_urls={6423: [comment]},
        )
        fake_github = FakeLocalGitHub(
            issues_gateway=fake_issues,
            pr_details={6517: pr},
        )
        remote = _make_remote(
            {6423: objective, 6513: plan},
            comments_by_id={55555: OBJECTIVE_COMMENT_BODY},
        )

        runner = CliRunner()
        result = runner.invoke(
            objective_apply_landed_update,
            [
                "--pr",
                "6517",
                "--objective",
                "6423",
                "--branch",
                "plnd/some-branch",
            ],
            obj=context_for_test(
                github=fake_github,
                plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
                remote_github=remote,
                repo_root=tmp_path,
                cwd=tmp_path,
                repo_info=_TEST_REPO_INFO,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True

        # Node 1.1 was auto-matched (its pr field is "#6517")
        node_updates = data["node_updates"]
        assert len(node_updates) == 1
        assert node_updates[0]["node_id"] == "1.1"

        # Issue body was updated
        assert len(remote.updated_issue_bodies) == 1


class TestApplyLandedUpdateErrors:
    def test_objective_not_found(self, tmp_path: Path) -> None:
        """Returns error when objective issue not found."""
        plan = _make_issue(number=6517, title="My Plan", body="plan body")
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6517: plan})
        fake_github = FakeLocalGitHub(
            issues_gateway=fake_issues,
            pr_details={6517: pr},
        )

        runner = CliRunner()
        result = runner.invoke(
            objective_apply_landed_update,
            [
                "--pr",
                "6517",
                "--objective",
                "9999",
                "--branch",
                "plnd/some-branch",
            ],
            obj=context_for_test(
                github=fake_github,
                plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
                remote_github=_make_remote({6513: plan}),
                repo_root=tmp_path,
                cwd=tmp_path,
                repo_info=_TEST_REPO_INFO,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "9999" in data["error"]

    def test_pr_not_found(self, tmp_path: Path) -> None:
        """Returns error when PR (and thus plan) not found."""
        objective = _make_issue(number=6423, title="My Objective", body="objective body")

        fake_issues = FakeGitHubIssues(issues={6423: objective})
        fake_github = FakeLocalGitHub(issues_gateway=fake_issues)

        runner = CliRunner()
        result = runner.invoke(
            objective_apply_landed_update,
            [
                "--pr",
                "9999",
                "--objective",
                "6423",
                "--branch",
                "plnd/some-branch",
            ],
            obj=context_for_test(
                github=fake_github,
                plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
                repo_root=tmp_path,
                cwd=tmp_path,
                repo_info=_TEST_REPO_INFO,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "9999" in data["error"]

    def test_plan_not_found_for_pr(self, tmp_path: Path) -> None:
        """Returns error when no plan (PR) exists for the given PR number."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeLocalGitHub(issues_gateway=fake_issues)

        runner = CliRunner()
        result = runner.invoke(
            objective_apply_landed_update,
            [
                "--pr",
                "6517",
                "--objective",
                "6423",
                "--branch",
                "plnd/some-branch",
            ],
            obj=context_for_test(
                github=fake_github,
                plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
                repo_root=tmp_path,
                cwd=tmp_path,
                repo_info=_TEST_REPO_INFO,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "6517" in data["error"]


ROADMAP_BODY_ALL_DONE = textwrap.dedent("""\
    # My Objective

    <!-- erk:metadata-block:objective-header -->

    <details>
    <summary><code>objective-header</code></summary>

    ```yaml
    created_at: '2026-01-01T00:00:00Z'
    created_by: testuser
    objective_comment_id: 55555
    slug: null
    ```

    </details>

    <!-- /erk:metadata-block:objective-header -->

    <!-- erk:metadata-block:objective-roadmap -->

    <details>
    <summary><code>objective-roadmap</code></summary>

    ```yaml
    schema_version: "2"
    steps:
    - id: "1.1"
      description: "Add user model"
      status: "done"
      pr: "#6500"
    - id: "1.2"
      description: "Add JWT library"
      status: "done"
      pr: "#6510"
    ```

    </details>

    <!-- /erk:metadata-block:objective-roadmap -->

    ## Roadmap
""")


class TestApplyLandedUpdateAutoClose:
    def test_auto_close_when_all_nodes_complete(self, tmp_path: Path) -> None:
        """All nodes done + --auto-close → auto_closed: true, issue closed."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY_ALL_DONE)
        plan = _make_issue(number=6517, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        pr = _make_pr_details(number=6517, title="Final cleanup", body="pr body")

        comment = IssueComment(
            body=OBJECTIVE_COMMENT_BODY,
            url="https://github.com/owner/repo/issues/6423#issuecomment-55555",
            id=55555,
            author="testuser",
        )
        fake_issues = FakeGitHubIssues(
            issues={6423: objective, 6517: plan},
            comments_with_urls={6423: [comment]},
        )
        fake_github = FakeLocalGitHub(
            issues_gateway=fake_issues,
            pr_details={6517: pr},
        )
        remote = _make_remote(
            {6423: objective, 6517: plan},
            comments_by_id={55555: OBJECTIVE_COMMENT_BODY},
        )

        runner = CliRunner()
        result = runner.invoke(
            objective_apply_landed_update,
            [
                "--pr",
                "6517",
                "--objective",
                "6423",
                "--branch",
                "plnd/some-branch",
                "--auto-close",
            ],
            obj=context_for_test(
                github=fake_github,
                plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
                remote_github=remote,
                repo_root=tmp_path,
                cwd=tmp_path,
                repo_info=_TEST_REPO_INFO,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["auto_closed"] is True

        # Issue was closed
        assert 6423 in fake_issues.closed_issues

        # Action comment says "Objective Complete"
        assert len(remote.added_issue_comments) == 1
        assert "Objective Complete" in remote.added_issue_comments[0].body

    def test_no_auto_close_when_not_all_complete(self, tmp_path: Path) -> None:
        """Some nodes pending + --auto-close → auto_closed: false, issue stays open."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan = _make_issue(number=6517, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        pr = _make_pr_details(number=6517, title="Add auth system", body="pr body")

        comment = IssueComment(
            body=OBJECTIVE_COMMENT_BODY,
            url="https://github.com/owner/repo/issues/6423#issuecomment-55555",
            id=55555,
            author="testuser",
        )
        fake_issues = FakeGitHubIssues(
            issues={6423: objective, 6517: plan},
            comments_with_urls={6423: [comment]},
        )
        fake_github = FakeLocalGitHub(
            issues_gateway=fake_issues,
            pr_details={6517: pr},
        )
        remote = _make_remote(
            {6423: objective, 6517: plan},
            comments_by_id={55555: OBJECTIVE_COMMENT_BODY},
        )

        runner = CliRunner()
        result = runner.invoke(
            objective_apply_landed_update,
            [
                "--pr",
                "6517",
                "--objective",
                "6423",
                "--branch",
                "plnd/some-branch",
                "--node",
                "1.1",
                "--auto-close",
            ],
            obj=context_for_test(
                github=fake_github,
                plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
                remote_github=remote,
                repo_root=tmp_path,
                cwd=tmp_path,
                repo_info=_TEST_REPO_INFO,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["auto_closed"] is False

        # Issue was NOT closed
        assert 6423 not in fake_issues.closed_issues

        # Action comment says "Landed PR" (not "Objective Complete")
        assert len(remote.added_issue_comments) == 1
        assert "Landed PR #6517" in remote.added_issue_comments[0].body


class TestApplyLandedUpdateDiscovery:
    def test_discover_branch_from_git(self, tmp_path: Path) -> None:
        """Auto-discovers branch when --branch is omitted."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan = _make_issue(number=6517, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        comment = IssueComment(
            body=OBJECTIVE_COMMENT_BODY,
            url="https://github.com/owner/repo/issues/6423#issuecomment-55555",
            id=55555,
            author="testuser",
        )
        fake_issues = FakeGitHubIssues(
            issues={6423: objective, 6517: plan},
            comments_with_urls={6423: [comment]},
        )
        fake_github = FakeLocalGitHub(
            issues_gateway=fake_issues,
            pr_details={6517: pr},
        )
        fake_git = FakeGit(current_branches={tmp_path: "plnd/some-branch"})

        runner = CliRunner()
        result = runner.invoke(
            objective_apply_landed_update,
            [
                "--pr",
                "6517",
                "--objective",
                "6423",
                "--node",
                "1.1",
                "--node",
                "1.2",
            ],
            obj=context_for_test(
                github=fake_github,
                plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
                git=fake_git,
                repo_root=tmp_path,
                cwd=tmp_path,
                repo_info=_TEST_REPO_INFO,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["plan"]["number"] == "6517"
