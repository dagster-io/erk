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
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo
from erk_shared.gateway.github.types import PRDetails


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
      plan: "#6513"
      pr: null
    - id: "1.2"
      description: "Add JWT library"
      status: "in_progress"
      plan: "#6513"
      pr: null
    - id: "2.1"
      description: "Implement login"
      status: "pending"
      plan: null
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
        plan = _make_issue(number=6513, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        pr = _make_pr_details(number=6517, title="Add auth system", body="pr body")

        comment = IssueComment(
            body=OBJECTIVE_COMMENT_BODY,
            url="https://github.com/owner/repo/issues/6423#issuecomment-55555",
            id=55555,
            author="testuser",
        )
        fake_issues = FakeGitHubIssues(
            issues={6423: objective, 6513: plan},
            comments_with_urls={6423: [comment]},
        )
        fake_github = FakeGitHub(pr_details={6517: pr})

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
                "--plan",
                "6513",
            ],
            obj=context_for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["objective"]["number"] == 6423
        assert data["plan"]["number"] == "6513"
        assert data["pr"]["number"] == 6517

        # Node updates recorded
        node_updates = data["node_updates"]
        assert len(node_updates) == 2
        assert node_updates[0]["node_id"] == "1.1"
        assert node_updates[1]["node_id"] == "1.2"

        # Action comment was posted
        assert data["action_comment_id"] is not None
        assert len(fake_issues.added_comments) == 1
        issue_number, body, _comment_id = fake_issues.added_comments[0]
        assert issue_number == 6423
        assert "Landed PR #6517" in body
        assert "Add auth system" in body

        # Issue body was updated
        assert len(fake_issues.updated_bodies) == 1

        # Roadmap reflects the updates
        roadmap = data["roadmap"]
        assert roadmap["summary"]["done"] == 2

    def test_objective_content_included(self, tmp_path: Path) -> None:
        """Objective prose content from the first comment is included."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan = _make_issue(number=6513, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        comment = IssueComment(
            body=OBJECTIVE_COMMENT_BODY,
            url="https://github.com/owner/repo/issues/6423#issuecomment-55555",
            id=55555,
            author="testuser",
        )
        fake_issues = FakeGitHubIssues(
            issues={6423: objective, 6513: plan},
            comments_with_urls={6423: [comment]},
        )
        fake_github = FakeGitHub(pr_details={6517: pr})

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
                "--plan",
                "6513",
            ],
            obj=context_for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["objective"]["objective_content"] is not None
        assert "Design Decisions" in data["objective"]["objective_content"]


class TestApplyLandedUpdateNoMatchedSteps:
    def test_no_matched_steps_still_posts_comment(self, tmp_path: Path) -> None:
        """When plan has no matched nodes, still posts action comment."""
        # Roadmap with no nodes matching plan #6513
        body_no_match = textwrap.dedent("""\
            <!-- erk:metadata-block:objective-roadmap -->

            <details>
            <summary><code>objective-roadmap</code></summary>

            ```yaml
            schema_version: "2"
            steps:
            - id: "1.1"
              description: "Unrelated step"
              status: "pending"
              plan: null
              pr: null
            ```

            </details>

            <!-- /erk:metadata-block:objective-roadmap -->
        """)
        objective = _make_issue(number=6423, title="My Objective", body=body_no_match)
        plan = _make_issue(number=6513, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective, 6513: plan})
        fake_github = FakeGitHub(pr_details={6517: pr})

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
                "--plan",
                "6513",
            ],
            obj=context_for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["node_updates"] == []

        # Action comment still posted
        assert len(fake_issues.added_comments) == 1

        # Issue body NOT updated (no nodes to update)
        assert len(fake_issues.updated_bodies) == 0


class TestApplyLandedUpdateErrors:
    def test_objective_not_found(self, tmp_path: Path) -> None:
        """Returns error when objective issue not found."""
        plan = _make_issue(number=6513, title="My Plan", body="plan body")
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6513: plan})
        fake_github = FakeGitHub(pr_details={6517: pr})

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
                "--plan",
                "6513",
            ],
            obj=context_for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "9999" in data["error"]

    def test_pr_not_found(self, tmp_path: Path) -> None:
        """Returns error when PR not found."""
        objective = _make_issue(number=6423, title="My Objective", body="objective body")
        plan = _make_issue(number=6513, title="My Plan", body="plan body")

        fake_issues = FakeGitHubIssues(issues={6423: objective, 6513: plan})
        fake_github = FakeGitHub()

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
                "--plan",
                "6513",
            ],
            obj=context_for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "9999" in data["error"]

    def test_bad_branch_no_plan(self, tmp_path: Path) -> None:
        """Returns error when branch doesn't match any plan pattern."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeGitHub()

        runner = CliRunner()
        result = runner.invoke(
            objective_apply_landed_update,
            ["--pr", "6517", "--objective", "6423", "--branch", "feature-branch"],
            obj=context_for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "No plan found" in data["error"]


class TestApplyLandedUpdateDiscovery:
    def test_discover_branch_from_git(self, tmp_path: Path) -> None:
        """Auto-discovers branch when --branch is omitted."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan = _make_issue(number=6513, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        comment = IssueComment(
            body=OBJECTIVE_COMMENT_BODY,
            url="https://github.com/owner/repo/issues/6423#issuecomment-55555",
            id=55555,
            author="testuser",
        )
        fake_issues = FakeGitHubIssues(
            issues={6423: objective, 6513: plan},
            comments_with_urls={6423: [comment]},
        )
        fake_github = FakeGitHub(pr_details={6517: pr})
        fake_git = FakeGit(current_branches={tmp_path: "plnd/some-branch"})

        runner = CliRunner()
        result = runner.invoke(
            objective_apply_landed_update,
            ["--pr", "6517", "--objective", "6423", "--plan", "6513"],
            obj=context_for_test(
                github_issues=fake_issues,
                github=fake_github,
                git=fake_git,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["plan"]["number"] == "6513"

    def test_plan_direct_lookup_skips_branch_discovery(self, tmp_path: Path) -> None:
        """--plan enables direct plan lookup, avoiding branch-based discovery."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan = _make_issue(number=6513, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        comment = IssueComment(
            body=OBJECTIVE_COMMENT_BODY,
            url="https://github.com/owner/repo/issues/6423#issuecomment-55555",
            id=55555,
            author="testuser",
        )
        fake_issues = FakeGitHubIssues(
            issues={6423: objective, 6513: plan},
            comments_with_urls={6423: [comment]},
        )
        fake_github = FakeGitHub(pr_details={6517: pr})

        runner = CliRunner()
        # Use a branch name that does NOT encode the plan number —
        # branch-based discovery would fail, but --plan bypasses it.
        result = runner.invoke(
            objective_apply_landed_update,
            [
                "--pr",
                "6517",
                "--objective",
                "6423",
                "--branch",
                "plnd/unrelated-branch-name",
                "--plan",
                "6513",
            ],
            obj=context_for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["plan"]["number"] == "6513"

    def test_plan_direct_lookup_not_found(self, tmp_path: Path) -> None:
        """--plan returns error when the specified plan doesn't exist."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeGitHub()

        runner = CliRunner()
        result = runner.invoke(
            objective_apply_landed_update,
            [
                "--pr",
                "6517",
                "--objective",
                "6423",
                "--branch",
                "some-branch",
                "--plan",
                "9999",
            ],
            obj=context_for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "9999" in data["error"]
