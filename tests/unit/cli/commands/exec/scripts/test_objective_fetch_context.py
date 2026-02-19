"""Tests for erk exec objective-fetch-context."""

import json
import textwrap
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.objective_fetch_context import objective_fetch_context
from erk_shared.context.context import ErkContext
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.draft_pr import DraftPRPlanBackend


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
    *, number: int, title: str, body: str, head_ref_name: str = "P100-test-branch"
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
      plan: "#6513"
      pr: "#6517"
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


class TestObjectiveFetchContext:
    def test_happy_path_with_all_args(self, tmp_path: Path) -> None:
        """All three args provided, returns combined JSON with roadmap."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan = _make_issue(number=6513, title="My Plan", body="plan body")
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective, 6513: plan})
        fake_github = FakeGitHub(pr_details={6517: pr})

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "P6513-some-branch"],
            obj=ErkContext.for_test(
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
        assert data["plan"]["number"] == 6513
        assert data["pr"]["number"] == 6517

    def test_roadmap_context_included(self, tmp_path: Path) -> None:
        """Roadmap context is parsed and included in output."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan = _make_issue(number=6513, title="My Plan", body="plan body")
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective, 6513: plan})
        fake_github = FakeGitHub(pr_details={6517: pr})

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "P6513-some-branch"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        roadmap = data["roadmap"]
        assert roadmap["matched_steps"] == ["1.1", "1.2"]
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
              plan: "#100"
              pr: "#200"
            - id: "1.2"
              description: "Step 2"
              status: "skipped"
              plan: null
              pr: null
            ```

            </details>

            <!-- /erk:metadata-block:objective-roadmap -->
        """)
        objective = _make_issue(number=6423, title="My Objective", body=body)
        plan = _make_issue(number=100, title="My Plan", body="plan body")
        pr = _make_pr_details(number=200, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective, 100: plan})
        fake_github = FakeGitHub(pr_details={200: pr})

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "200", "--objective", "6423", "--branch", "P100-some-branch"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                github=fake_github,
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
        plan = _make_issue(number=6513, title="My Plan", body="plan body")
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective, 6513: plan})
        fake_github = FakeGitHub(pr_details={6517: pr})

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "P6513-some-branch"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["roadmap"]["phases"] == []
        assert data["roadmap"]["matched_steps"] == []
        assert data["roadmap"]["all_complete"] is False

    def test_objective_not_found(self, tmp_path: Path) -> None:
        """Returns error JSON when objective issue not found."""
        plan = _make_issue(number=6513, title="My Plan", body="plan body")
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6513: plan})
        fake_github = FakeGitHub(pr_details={6517: pr})

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "9999", "--branch", "P6513-some-branch"],
            obj=ErkContext.for_test(
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
        """Returns error JSON when PR not found."""
        objective = _make_issue(number=6423, title="My Objective", body="objective body")
        plan = _make_issue(number=6513, title="My Plan", body="plan body")

        fake_issues = FakeGitHubIssues(issues={6423: objective, 6513: plan})
        fake_github = FakeGitHub()

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "9999", "--objective", "6423", "--branch", "P6513-some-branch"],
            obj=ErkContext.for_test(
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

    def test_bad_branch_pattern(self, tmp_path: Path) -> None:
        """Returns error JSON when branch doesn't match any plan pattern."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeGitHub()

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "feature-branch"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
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
        fake_github = FakeGitHub(pr_details={6517: pr})

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423", "--branch", "P6513-some-branch"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                github=fake_github,
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
        plan = _make_issue(number=6513, title="My Plan", body="plan body")
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective, 6513: plan})
        fake_github = FakeGitHub(pr_details={6517: pr})
        fake_git = FakeGit(current_branches={tmp_path: "P6513-some-branch"})

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423"],
            obj=ErkContext.for_test(
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
        assert data["plan"]["number"] == 6513

    def test_discover_objective_from_plan_metadata(self, tmp_path: Path) -> None:
        """Auto-discovers objective when --objective is omitted."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan = _make_issue(number=6513, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        pr = _make_pr_details(number=6517, title="PR Title", body="pr body")

        fake_issues = FakeGitHubIssues(issues={6423: objective, 6513: plan})
        fake_github = FakeGitHub(pr_details={6517: pr})

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--branch", "P6513-some-branch"],
            obj=ErkContext.for_test(
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

    def test_discover_pr_from_branch(self, tmp_path: Path) -> None:
        """Auto-discovers PR when --pr is omitted."""
        objective = _make_issue(number=6423, title="My Objective", body=ROADMAP_BODY)
        plan = _make_issue(number=6513, title="My Plan", body="plan body")
        pr = _make_pr_details(
            number=6517, title="PR Title", body="pr body", head_ref_name="P6513-some-branch"
        )

        fake_issues = FakeGitHubIssues(issues={6423: objective, 6513: plan})
        fake_github = FakeGitHub(
            pr_details={6517: pr},
            prs_by_branch={"P6513-some-branch": pr},
        )

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--objective", "6423", "--branch", "P6513-some-branch"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                github=fake_github,
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
        plan = _make_issue(number=6513, title="My Plan", body=PLAN_BODY_WITH_OBJECTIVE)
        pr = _make_pr_details(
            number=6517, title="PR Title", body="pr body", head_ref_name="P6513-some-branch"
        )

        fake_issues = FakeGitHubIssues(issues={6423: objective, 6513: plan})
        fake_github = FakeGitHub(
            pr_details={6517: pr},
            prs_by_branch={"P6513-some-branch": pr},
        )
        fake_git = FakeGit(current_branches={tmp_path: "P6513-some-branch"})

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            [],
            obj=ErkContext.for_test(
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
        assert data["objective"]["number"] == 6423
        assert data["plan"]["number"] == 6513
        assert data["pr"]["number"] == 6517
        assert data["roadmap"]["matched_steps"] == ["1.1", "1.2"]

    def test_discover_branch_detached_head_error(self, tmp_path: Path) -> None:
        """Returns error when branch discovery finds detached HEAD."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeGitHub()
        fake_git = FakeGit(current_branches={tmp_path: None})

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--objective", "6423"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
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
        plan = _make_issue(number=6513, title="My Plan", body="no metadata here")

        fake_issues = FakeGitHubIssues(issues={6513: plan})
        fake_github = FakeGitHub()

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "6517", "--branch", "P6513-some-branch"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                github=fake_github,
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
        plan = _make_issue(number=6513, title="My Plan", body="plan body")

        fake_issues = FakeGitHubIssues(issues={6513: plan})
        fake_github = FakeGitHub()

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--objective", "6423", "--branch", "P6513-some-branch"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                github=fake_github,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "No PR found" in data["error"]


class TestDraftPRBackend:
    def test_happy_path_draft_pr_plan(self, tmp_path: Path) -> None:
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
        )
        draft_pr_backend = DraftPRPlanBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "8002", "--objective", "7419", "--branch", "plan-draft-pr-plan"],
            obj=context_for_test(
                github_issues=fake_issues,
                github=fake_github,
                plan_store=draft_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["objective"]["number"] == 7419
        assert data["plan"]["number"] == 8001
        assert data["plan"]["title"] == "Draft PR Plan"
        assert data["pr"]["number"] == 8002

    def test_draft_pr_objective_discovery(self, tmp_path: Path) -> None:
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
        )
        draft_pr_backend = DraftPRPlanBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "8002", "--branch", "plan-draft-pr-plan"],
            obj=context_for_test(
                github_issues=fake_issues,
                github=fake_github,
                plan_store=draft_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["objective"]["number"] == 7419

    def test_draft_pr_plan_not_found(self, tmp_path: Path) -> None:
        """Returns error when no PR exists for a plan-... branch."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeGitHub()
        draft_pr_backend = DraftPRPlanBackend(fake_github, fake_issues, time=FakeTime())

        runner = CliRunner()
        result = runner.invoke(
            objective_fetch_context,
            ["--pr", "8002", "--objective", "7419", "--branch", "plan-no-such-plan"],
            obj=context_for_test(
                github_issues=fake_issues,
                github=fake_github,
                plan_store=draft_pr_backend,
                repo_root=tmp_path,
                cwd=tmp_path,
            ),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "No plan found for branch" in data["error"]
