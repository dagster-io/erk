"""Tests for erk exec objective-fetch-context."""

import json
import textwrap
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.objective_fetch_context import objective_fetch_context
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo
from erk_shared.gateway.github.types import PRDetails, PRNotFound
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from tests.test_utils.plan_helpers import issue_info_to_pr_details


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
    *, number: int, title: str, body: str, head_ref_name: str = "plnd/test-branch-01-01-1200"
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

    <!-- erk:metadata-block:objective-roadmap -->

    <details>
    <summary><code>objective-roadmap</code></summary>

    ```yaml
    schema_version: "2"
    steps:
    - id: "1.1"
      description: "Add user model"
      status: "done"
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

DRAFT_PR_BODY_WITH_OBJECTIVE = textwrap.dedent("""\
    <!-- erk:metadata-block:plan-header -->

    <details>
    <summary><code>plan-header</code></summary>

    ```yaml
    objective_issue: 7419
    title: Draft PR Plan
    ```

    </details>

    <!-- /erk:metadata-block:plan-header -->

    ---

    # Draft PR plan content
""")


ROADMAP_BODY_WITH_COMMENT_ID = textwrap.dedent("""\
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
      pr: "#6517"
    ```

    </details>

    <!-- /erk:metadata-block:objective-roadmap -->
""")

OBJECTIVE_COMMENT_BODY = textwrap.dedent("""\
    <!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
    <!-- erk:metadata-block:objective-body -->
    <details open>
    <summary><strong>Objective</strong></summary>

    ## Design Decisions

    Use JWT for authentication.

    ## Implementation Context

    The auth module lives in src/auth/.

    </details>
    <!-- /erk:metadata-block:objective-body -->
""")


class TestObjectiveFetchContext:
    def test_happy_path_with_all_args(self, tmp_path: Path) -> None:
        """All three args provided, returns combined JSON with roadmap."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        # Create draft PR as plan (PlannedPRBackend resolves plnd/ branches to PRs)
        plan_pr = _make_pr_details(
            number=6513,
            title="My Plan",
            body="plan body",
            head_ref_name="plnd/some-branch-01-01-1200",
        )
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective})
        fake_github = FakeGitHub(
            pr_details={6517: pr, 6513: plan_pr},
            prs_by_branch={"plnd/some-branch-01-01-1200": plan_pr},
            issues_gateway=fake_issues,
        )
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "plnd/some-branch-01-01-1200"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["objective"]["number"] == 6423
        assert data["objective"]["objective_content"] is None
        assert data["plan"]["number"] == "6513"
        assert data["pr"]["number"] == 6517

    def test_roadmap_context_included(self, tmp_path: Path) -> None:
        """Roadmap context is parsed and included in output."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan_pr = _make_pr_details(
            number=6513,
            title="My Plan",
            body="plan body",
            head_ref_name="plnd/some-branch-01-01-1200",
        )
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective})
        fake_github = FakeGitHub(
            pr_details={6517: pr, 6513: plan_pr},
            prs_by_branch={"plnd/some-branch-01-01-1200": plan_pr},
            issues_gateway=fake_issues,
        )
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "plnd/some-branch-01-01-1200"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        roadmap = data["roadmap"]
        assert roadmap["summary"]["total_nodes"] == 3
        assert roadmap["summary"]["done"] == 1
        assert roadmap["summary"]["in_progress"] == 1
        assert roadmap["summary"]["pending"] == 1
        assert roadmap["all_complete"] is False
        assert roadmap["next_node"]["id"] == "2.1"
        assert len(roadmap["phases"]) == 2

    def test_roadmap_all_complete(self, tmp_path: Path) -> None:
        """all_complete is True when all steps are done or skipped."""
        body = textwrap.dedent("""\
            <!-- erk:metadata-block:objective-roadmap -->

            <details>
            <summary><code>objective-roadmap</code></summary>

            ```yaml
            schema_version: "2"
            steps:
            - id: "1.1"
              description: "Step 1"
              status: "done"
              pr: "#200"
            - id: "1.2"
              description: "Step 2"
              status: "skipped"
              pr: null
            ```

            </details>

            <!-- /erk:metadata-block:objective-roadmap -->
        """)
        objective = _make_issue(number=6423, title="My Objective", body=body)
        plan_pr = _make_pr_details(
            number=100,
            title="My Plan",
            body="plan body",
            head_ref_name="plnd/some-branch-01-01-1200",
        )
        pr = _make_pr_details(number=200, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective})
        fake_github = FakeGitHub(
            pr_details={200: pr, 100: plan_pr},
            prs_by_branch={"plnd/some-branch-01-01-1200": plan_pr},
            issues_gateway=fake_issues,
        )
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "200", "--objective", "6423", "--branch", "plnd/some-branch-01-01-1200"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["roadmap"]["all_complete"] is True
        assert data["roadmap"]["next_node"] is None

    def test_roadmap_no_metadata_block(self, tmp_path: Path) -> None:
        """Returns empty roadmap when objective has no roadmap metadata block."""
        objective = _make_issue(number=6423, title="My Objective", body="No roadmap here")
        plan_pr = _make_pr_details(
            number=6513,
            title="My Plan",
            body="plan body",
            head_ref_name="plnd/some-branch-01-01-1200",
        )
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective})
        fake_github = FakeGitHub(
            pr_details={6517: pr, 6513: plan_pr},
            prs_by_branch={"plnd/some-branch-01-01-1200": plan_pr},
            issues_gateway=fake_issues,
        )
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "plnd/some-branch-01-01-1200"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["roadmap"]["phases"] == []
        assert data["roadmap"]["all_complete"] is False

    def test_objective_not_found(self, tmp_path: Path) -> None:
        """Returns error JSON when objective issue not found."""
        plan_pr = _make_pr_details(
            number=6513,
            title="My Plan",
            body="plan body",
            head_ref_name="plnd/some-branch-01-01-1200",
        )
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={})
        fake_github = FakeGitHub(
            pr_details={6517: pr, 6513: plan_pr},
            prs_by_branch={"plnd/some-branch-01-01-1200": plan_pr},
            issues_gateway=fake_issues,
        )
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "9999", "--branch", "plnd/some-branch-01-01-1200"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "9999" in data["error"]

    def test_pr_not_found(self, tmp_path: Path) -> None:
        """Returns error JSON when PR not found."""
        objective = _make_issue(number=6423, title="My Objective", body="objective body")
        plan_pr = _make_pr_details(
            number=6513,
            title="My Plan",
            body="plan body",
            head_ref_name="plnd/some-branch-01-01-1200",
        )

        fake_issues = FakeGitHubIssues(issues={6423: objective})
        fake_github = FakeGitHub(
            pr_details={6513: plan_pr},
            prs_by_branch={"plnd/some-branch-01-01-1200": plan_pr},
            issues_gateway=fake_issues,
        )
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "9999", "--objective", "6423", "--branch", "plnd/some-branch-01-01-1200"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "9999" in data["error"]

    def test_bad_branch_pattern(self, tmp_path: Path) -> None:
        """Returns error JSON when branch doesn't match any plan pattern."""
        fake_github = FakeGitHub()

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "feature-branch"],
            obj=context_for_test(
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "No plan found for branch" in data["error"]
        assert "feature-branch" in data["error"]

    def test_plan_not_found(self, tmp_path: Path) -> None:
        """Returns error JSON when plan issue not found."""
        objective = _make_issue(number=6423, title="My Objective", body="objective body")
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective})
        # No plan PR configured for the branch - will trigger PlanNotFound
        fake_github = FakeGitHub(pr_details={6517: pr}, issues_gateway=fake_issues)
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "plnd/some-branch-01-01-1200"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "No plan found for branch" in data["error"]


class TestDiscoveryMode:
    def test_discover_branch_from_git(self, tmp_path: Path) -> None:
        """Auto-discovers branch when --branch is omitted."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan_pr = _make_pr_details(
            number=6513,
            title="My Plan",
            body="plan body",
            head_ref_name="plnd/some-branch-01-01-1200",
        )
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective})
        fake_github = FakeGitHub(
            pr_details={6517: pr, 6513: plan_pr},
            prs_by_branch={"plnd/some-branch-01-01-1200": plan_pr},
            issues_gateway=fake_issues,
        )
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())
        fake_git = FakeGit(current_branches={tmp_path: "plnd/some-branch-01-01-1200"})

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                git=fake_git,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["plan"]["number"] == "6513"

    def test_discover_objective_from_plan_metadata(self, tmp_path: Path) -> None:
        """Auto-discovers objective when --objective is omitted."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        # Plan PR with objective metadata in body
        plan_pr = _make_pr_details(
            number=6513,
            title="My Plan",
            body=PLAN_BODY_WITH_OBJECTIVE,
            head_ref_name="plnd/some-branch-01-01-1200",
        )
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective})
        fake_github = FakeGitHub(
            pr_details={6517: pr, 6513: plan_pr},
            prs_by_branch={"plnd/some-branch-01-01-1200": plan_pr},
            issues_gateway=fake_issues,
        )
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--branch", "plnd/some-branch-01-01-1200"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["objective"]["number"] == 6423

    def test_discover_pr_from_branch(self, tmp_path: Path) -> None:
        """Auto-discovers PR when --pr is omitted."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan_pr = _make_pr_details(
            number=6513,
            title="My Plan",
            body="plan body",
            head_ref_name="plnd/some-branch-01-01-1200",
        )
        pr = _make_pr_details(
            number=6517,
            title="PR Title",
            body="pr body",
            head_ref_name="plnd/some-branch-01-01-1200",
        )

        fake_issues = FakeGitHubIssues(issues={6423: objective})
        fake_github = FakeGitHub(
            pr_details={6517: pr, 6513: plan_pr},
            prs_by_branch={"plnd/some-branch-01-01-1200": pr},
            issues_gateway=fake_issues,
        )
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--objective", "6423", "--branch", "plnd/some-branch-01-01-1200"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["pr"]["number"] == 6517

    def test_discover_all_from_git_state(self, tmp_path: Path) -> None:
        """Discovers branch, objective, and PR when no args provided."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan_pr = _make_pr_details(
            number=6513,
            title="My Plan",
            body=PLAN_BODY_WITH_OBJECTIVE,
            head_ref_name="plnd/some-branch-01-01-1200",
        )
        pr = _make_pr_details(
            number=6517,
            title="PR Title",
            body="pr body",
            head_ref_name="plnd/some-branch-01-01-1200",
        )

        fake_issues = FakeGitHubIssues(issues={6423: objective})
        fake_github = FakeGitHub(
            pr_details={6517: pr, 6513: plan_pr},
            # prs_by_branch maps to plan_pr for plan resolution
            prs_by_branch={"plnd/some-branch-01-01-1200": plan_pr},
            issues_gateway=fake_issues,
        )

        # Mock get_pr_for_branch to return plan_pr first (for plan resolution),
        # then pr for PR discovery
        call_count = [0]

        def mock_get_pr_for_branch(repo_root: Path, branch: str) -> PRDetails | PRNotFound:
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: plan resolution via PlannedPRBackend
                return plan_pr
            else:
                # Second call: PR discovery
                return pr

        fake_github.get_pr_for_branch = mock_get_pr_for_branch

        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())
        fake_git = FakeGit(current_branches={tmp_path: "plnd/some-branch-01-01-1200"})

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            [],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                git=fake_git,
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
        assert data["roadmap"]["summary"]["total_nodes"] >= 2

    def test_discover_branch_detached_head_error(self, tmp_path: Path) -> None:
        """Returns error when branch discovery finds detached HEAD."""
        fake_github = FakeGitHub()
        fake_git = FakeGit(current_branches={tmp_path: None})

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423"],
            obj=context_for_test(
                github=fake_github,
                git=fake_git,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "detached HEAD" in data["error"]

    def test_discover_objective_no_metadata_error(self, tmp_path: Path) -> None:
        """Returns error when plan has no objective_issue in metadata."""
        plan_pr = _make_pr_details(
            number=6513,
            title="My Plan",
            body="no metadata here",
            head_ref_name="plnd/some-branch-01-01-1200",
        )

        fake_issues = FakeGitHubIssues(issues={})
        fake_github = FakeGitHub(
            pr_details={6513: plan_pr},
            prs_by_branch={"plnd/some-branch-01-01-1200": plan_pr},
            issues_gateway=fake_issues,
        )
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--branch", "plnd/some-branch-01-01-1200"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "objective_issue" in data["error"]

    def test_discover_pr_not_found_error(self, tmp_path: Path) -> None:
        """Returns error when no PR found for the branch."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan_pr = _make_pr_details(
            number=6513,
            title="My Plan",
            body="plan body",
            head_ref_name="plnd/some-branch-01-01-1200",
        )

        fake_issues = FakeGitHubIssues(issues={6423: objective})
        fake_github = FakeGitHub(
            pr_details={6513: plan_pr},
            prs_by_branch={"plnd/some-branch-01-01-1200": plan_pr},
            issues_gateway=fake_issues,
        )

        # Mock get_pr_for_branch to return plan_pr for plan resolution,
        # then PRNotFound for PR discovery
        call_count = [0]

        def mock_get_pr_for_branch(repo_root: Path, branch: str) -> PRDetails | PRNotFound:
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: plan resolution
                return plan_pr
            else:
                # Second call: PR discovery fails
                return PRNotFound(branch=branch)

        fake_github.get_pr_for_branch = mock_get_pr_for_branch

        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--objective", "6423", "--branch", "plnd/some-branch-01-01-1200"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        fail_msg = f"Unexpected exit code. Output: {result.output}, Exception: {result.exception}"
        assert result.exit_code == 1, fail_msg
        assert result.output, f"Empty output. Exception: {result.exception}"
        data = json.loads(result.output)
        assert data["success"] is False
        assert "No PR found" in data["error"]


class TestPlannedPRBackend:
    def test_happy_path_planned_pr_plan(self, tmp_path: Path) -> None:
        """Draft PR branch with plan-header resolves plan and objective correctly."""
        objective = _make_issue(number=7419, title="My Objective", body=ROADMAP_BODY)
        draft_pr = _make_pr_details(
            number=8001,
            title="Draft PR Plan",
            body=DRAFT_PR_BODY_WITH_OBJECTIVE,
            head_ref_name="plan-draft-pr-plan",
        )
        pr = _make_pr_details(
            number=8002,
            title="Impl PR",
            body="implementation pr body",
            head_ref_name="plan-draft-pr-plan",
        )

        fake_issues = FakeGitHubIssues(issues={7419: objective})
        fake_github = FakeGitHub(
            prs_by_branch={"plan-draft-pr-plan": draft_pr},
            pr_details={8002: pr},
            issues_gateway=fake_issues,
        )
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "8002", "--objective", "7419", "--branch", "plan-draft-pr-plan"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["objective"]["number"] == 7419
        assert data["plan"]["number"] == "8001"
        assert data["plan"]["title"] == "Draft PR Plan"
        assert data["pr"]["number"] == 8002

    def test_planned_pr_objective_discovery(self, tmp_path: Path) -> None:
        """Auto-discovers objective from draft PR plan's plan-header metadata."""
        objective = _make_issue(number=7419, title="My Objective", body=ROADMAP_BODY)
        draft_pr = _make_pr_details(
            number=8001,
            title="Draft PR Plan",
            body=DRAFT_PR_BODY_WITH_OBJECTIVE,
            head_ref_name="plan-draft-pr-plan",
        )
        pr = _make_pr_details(
            number=8002,
            title="Impl PR",
            body="implementation pr body",
            head_ref_name="plan-draft-pr-plan",
        )

        fake_issues = FakeGitHubIssues(issues={7419: objective})
        fake_github = FakeGitHub(
            prs_by_branch={"plan-draft-pr-plan": draft_pr},
            pr_details={8002: pr},
            issues_gateway=fake_issues,
        )
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "8002", "--branch", "plan-draft-pr-plan"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["objective"]["number"] == 7419

    def test_planned_pr_plan_not_found(self, tmp_path: Path) -> None:
        """Returns error when no PR exists for a plan-... branch."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeGitHub()
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "8002", "--objective", "7419", "--branch", "plan-no-such-plan"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "No plan found for branch" in data["error"]


class TestDirectPlanLookup:
    def test_plan_flag_skips_branch_discovery(self, tmp_path: Path) -> None:
        """--plan flag does direct plan lookup, skipping branch-based discovery."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan = _make_issue(number=6513, title="My Plan", body="plan body")
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective, 6513: plan})
        fake_github = FakeGitHub(
            pr_details={6517: pr, 6513: issue_info_to_pr_details(plan)},
            issues_gateway=fake_issues,
        )

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423", "--plan", "6513"],
            obj=context_for_test(
                github=fake_github,
                plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["plan"]["number"] == "6513"
        assert data["objective"]["number"] == 6423

    def test_plan_flag_not_found(self, tmp_path: Path) -> None:
        """Returns error when --plan references a non-existent plan."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeGitHub(issues_gateway=fake_issues)

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423", "--plan", "9999"],
            obj=context_for_test(
                github=fake_github,
                plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "9999" in data["error"]

    def test_plan_flag_without_pr_and_branch_errors(self, tmp_path: Path) -> None:
        """Returns error when --plan used without --pr and --branch (can't auto-discover PR)."""
        plan = _make_issue(number=6513, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)

        fake_issues = FakeGitHubIssues(issues={6423: objective, 6513: plan})
        fake_github = FakeGitHub(
            pr_details={6513: issue_info_to_pr_details(plan)},
            issues_gateway=fake_issues,
        )
        # No branch set, no PR provided - should error
        fake_git = FakeGit(current_branches={tmp_path: "master"})

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--objective", "6423", "--plan", "6513"],
            obj=context_for_test(
                github=fake_github,
                plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
                git=fake_git,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "Cannot auto-discover PR" in data["error"]


class TestObjectiveContent:
    def test_objective_content_from_comment(self, tmp_path: Path) -> None:
        """objective_content is populated from the first comment's objective-body block."""
        objective = _make_issue(
            number=6423, title="My Objective", body=ROADMAP_BODY_WITH_COMMENT_ID
        )
        plan_pr = _make_pr_details(
            number=6513,
            title="My Plan",
            body="plan body",
            head_ref_name="plnd/some-branch-01-01-1200",
        )
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        comment = IssueComment(
            body=OBJECTIVE_COMMENT_BODY,
            url="https://github.com/owner/repo/issues/6423#issuecomment-55555",
            id=55555,
            author="testuser",
        )
        fake_issues = FakeGitHubIssues(
            issues={6423: objective},
            comments_with_urls={6423: [comment]},
        )
        fake_github = FakeGitHub(
            pr_details={6517: pr, 6513: plan_pr},
            prs_by_branch={"plnd/some-branch-01-01-1200": plan_pr},
            issues_gateway=fake_issues,
        )
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "plnd/some-branch-01-01-1200"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        content = data["objective"]["objective_content"]
        assert content is not None
        assert "Design Decisions" in content
        assert "Use JWT for authentication" in content
        assert "Implementation Context" in content

    def test_objective_content_none_without_header(self, tmp_path: Path) -> None:
        """objective_content is None when objective has no objective-header block."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan_pr = _make_pr_details(
            number=6513,
            title="My Plan",
            body="plan body",
            head_ref_name="plnd/some-branch-01-01-1200",
        )
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective})
        fake_github = FakeGitHub(
            pr_details={6517: pr, 6513: plan_pr},
            prs_by_branch={"plnd/some-branch-01-01-1200": plan_pr},
            issues_gateway=fake_issues,
        )
        planned_pr_backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "plnd/some-branch-01-01-1200"],
            obj=context_for_test(
                github=fake_github,
                plan_store=planned_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["objective"]["objective_content"] is None
