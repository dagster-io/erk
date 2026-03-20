"""Tests for PR command remote paths (--repo flag / NoRepoSentinel)."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import NoRepoSentinel
from erk_shared.core.plan_list_service import PlanListData
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import MetadataBlock, render_metadata_block
from erk_shared.plan_store.planned_pr_lifecycle import build_plan_stage_body
from erk_shared.plan_store.types import Plan, PlanState
from tests.fakes.gateway.console import FakeConsole
from tests.fakes.gateway.core import FakePlanListService
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.fakes.tests.prompt_executor import FakePromptExecutor
from tests.test_utils.test_context import context_for_test


def _make_fake_remote(
    *,
    issues: dict[int, IssueInfo] | None = None,
    issue_comments: dict[int, list[str]] | None = None,
) -> FakeRemoteGitHub:
    """Create a FakeRemoteGitHub with sensible defaults."""
    return FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=issues,
        issue_comments=issue_comments,
    )


def _make_issue(number: int, *, title: str = "Test Plan", state: str = "OPEN") -> IssueInfo:
    """Create a test IssueInfo."""
    return IssueInfo(
        number=number,
        title=title,
        body="Test plan body content",
        state=state,
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        author="test-author",
    )


def _build_remote_context(
    fake_remote: FakeRemoteGitHub,
    *,
    target_repo: str | None = "owner/repo",
) -> context_for_test:
    """Build ErkContext configured for remote mode testing."""
    return context_for_test(
        repo=NoRepoSentinel(),
        remote_github=fake_remote,
    )


# --- pr view --repo ---


def test_view_remote_displays_plan() -> None:
    """Test pr view with --repo flag displays plan data."""
    issue = _make_issue(42, title="Remote Plan Title")
    fake_remote = _make_fake_remote(issues={42: issue})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["pr", "view", "42", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 0
    assert "Remote Plan Title" in result.output
    assert "#42" in result.output
    assert "OPEN" in result.output


def test_view_remote_with_full_flag() -> None:
    """Test pr view --repo --full shows the body."""
    issue = IssueInfo(
        number=42,
        title="Full View Plan",
        body="Detailed plan body here",
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        author="test-author",
    )
    fake_remote = _make_fake_remote(issues={42: issue})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["pr", "view", "42", "--repo", "owner/repo", "--full"], obj=ctx)

    assert result.exit_code == 0
    assert "Detailed plan body here" in result.output


def test_view_remote_not_found() -> None:
    """Test pr view --repo with non-existent plan."""
    fake_remote = _make_fake_remote(issues={})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["pr", "view", "999", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 1
    assert "PR #999 not found" in result.output


def test_view_remote_requires_identifier() -> None:
    """Test pr view --repo without identifier gives error."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["pr", "view", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 1
    assert "identifier is required in remote mode" in result.output


# --- pr close --repo ---


def test_close_remote_closes_plan() -> None:
    """Test pr close with --repo flag closes the plan."""
    issue = _make_issue(42)
    fake_remote = _make_fake_remote(issues={42: issue})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["pr", "close", "42", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 0
    assert "Closed PR #42" in result.output
    assert len(fake_remote.closed_issues) == 1
    assert fake_remote.closed_issues[0].number == 42


def test_close_remote_not_found() -> None:
    """Test pr close --repo with non-existent plan."""
    fake_remote = _make_fake_remote(issues={})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["pr", "close", "999", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 1
    assert "PR #999 not found" in result.output


# --- pr log --repo ---


def test_log_remote_displays_events() -> None:
    """Test pr log with --repo flag parses events from comments."""
    issue = _make_issue(42)
    # Comment with an erk-plan metadata block
    comment_body = """<!-- erk:metadata-block:erk-plan -->
<details>
<summary><code>erk-plan</code></summary>

```yaml

timestamp: "2024-01-15T10:30:00Z"
worktree_name: test-wt

```

</details>
<!-- /erk:metadata-block:erk-plan -->
"""
    fake_remote = _make_fake_remote(
        issues={42: issue},
        issue_comments={42: [comment_body]},
    )
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["pr", "log", "42", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 0
    assert "PR #42 Event Timeline" in result.output
    assert "PR created" in result.output


def test_log_remote_not_found() -> None:
    """Test pr log --repo with non-existent plan."""
    fake_remote = _make_fake_remote(issues={})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["pr", "log", "999", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 1
    assert "PR '999' not found" in result.output


def test_log_remote_no_events() -> None:
    """Test pr log --repo with no events."""
    issue = _make_issue(42)
    fake_remote = _make_fake_remote(
        issues={42: issue},
        issue_comments={42: []},
    )
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["pr", "log", "42", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 0
    assert "No events found" in result.output


# --- pr check --repo ---


def test_check_remote_requires_identifier() -> None:
    """Test pr check --repo without identifier gives error."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["pr", "check", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 1
    assert "local git repository" in result.output


def test_check_remote_plan_not_found() -> None:
    """Test pr check --repo with non-existent plan."""
    fake_remote = _make_fake_remote(issues={})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["pr", "check", "999", "--repo", "owner/repo"], obj=ctx)

    assert result.exit_code == 1
    assert "PR #999 not found" in result.output


# --- repo_resolution edge cases ---


def test_invalid_repo_format() -> None:
    """Test --repo with invalid format gives helpful error."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(cli, ["pr", "view", "42", "--repo", "invalid"], obj=ctx)

    assert result.exit_code != 0
    assert "Invalid --repo format" in result.output


# --- pr duplicate-check --repo ---


def _make_plan(
    *,
    pr_identifier: str,
    title: str,
    body: str,
) -> Plan:
    return Plan(
        pr_identifier=pr_identifier,
        title=title,
        body=body,
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/issues/{pr_identifier}",
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )


def _make_plan_list_service(plans: list[Plan]) -> FakePlanListService:
    return FakePlanListService(
        data=PlanListData(plans=plans, pr_linkages={}, workflow_runs={}),
    )


def _non_interactive_console() -> FakeConsole:
    return FakeConsole(
        is_interactive=False,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=None,
    )


def test_duplicate_check_remote_no_duplicates() -> None:
    """Test pr duplicate-check --repo with no duplicates returns success."""
    executor = FakePromptExecutor(
        simulated_prompt_output='{"duplicates": []}',
    )
    existing = _make_plan(
        pr_identifier="100", title="[erk-pr] Refactor auth", body="Restructure auth flow"
    )

    issue = _make_issue(200, title="New Plan")
    fake_remote = _make_fake_remote(issues={200: issue})

    ctx = context_for_test(
        repo=NoRepoSentinel(),
        remote_github=fake_remote,
        prompt_executor=executor,
        console=_non_interactive_console(),
        plan_list_service=_make_plan_list_service([existing]),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pr", "duplicate-check", "--plan", "200", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code == 0
    assert "No duplicates found" in result.output


def test_duplicate_check_remote_finds_duplicate() -> None:
    """Test pr duplicate-check --repo detects duplicates."""
    llm_output = '{"duplicates": [{"plan_id": "100", "explanation": "Both refactor auth"}]}'
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    existing = _make_plan(
        pr_identifier="100", title="[erk-pr] Refactor auth", body="Restructure auth flow"
    )

    issue = _make_issue(200, title="New Plan")
    fake_remote = _make_fake_remote(issues={200: issue})

    ctx = context_for_test(
        repo=NoRepoSentinel(),
        remote_github=fake_remote,
        prompt_executor=executor,
        console=_non_interactive_console(),
        plan_list_service=_make_plan_list_service([existing]),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pr", "duplicate-check", "--plan", "200", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code == 1
    assert "Potential duplicate(s) found" in result.output
    assert "Both refactor auth" in result.output


# --- pr list --repo ---


def test_list_remote_shows_plans() -> None:
    """Test pr list --repo displays plans."""
    plan1 = _make_plan(pr_identifier="1", title="Plan One", body="body")
    plan2 = _make_plan(pr_identifier="2", title="Plan Two", body="body")

    fake_remote = _make_fake_remote()

    ctx = context_for_test(
        repo=NoRepoSentinel(),
        remote_github=fake_remote,
        plan_list_service=_make_plan_list_service([plan1, plan2]),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pr", "list", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code == 0
    assert "Found 2 PR(s)" in result.output
    assert "#1" in result.output
    assert "#2" in result.output


def test_list_remote_empty() -> None:
    """Test pr list --repo with no plans."""
    fake_remote = _make_fake_remote()

    ctx = context_for_test(
        repo=NoRepoSentinel(),
        remote_github=fake_remote,
        plan_list_service=_make_plan_list_service([]),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pr", "list", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code == 0
    assert "No PRs found" in result.output


# --- pr dispatch --repo ---


def _make_plan_header_body(*, branch_name: str) -> str:
    """Build a plan-header metadata block with a branch name."""
    return render_metadata_block(
        MetadataBlock(
            key="plan-header",
            data={
                "schema_version": "2",
                "created_at": "2024-01-01T00:00:00+00:00",
                "created_by": "test-user",
                "branch_name": branch_name,
            },
        )
    )


def _make_plan_issue(
    number: int,
    *,
    title: str = "[erk-pr] Test Plan",
    branch_name: str = "plnd/test-plan",
    state: str = "OPEN",
    labels: list[str] | None = None,
) -> IssueInfo:
    """Create a test IssueInfo with plan-header metadata in the body."""
    plan_header = _make_plan_header_body(branch_name=branch_name)
    plan_content = "# Plan: Test\n\n- Step 1\n- Step 2"
    body = build_plan_stage_body(plan_header, plan_content, summary="")
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state=state,
        url=f"https://github.com/owner/repo/pull/{number}",
        labels=labels if labels is not None else ["erk-pr"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        author="test-author",
    )


def test_dispatch_remote_dispatches_workflow() -> None:
    """Test pr dispatch --repo dispatches workflow via RemoteGitHub."""
    issue = _make_plan_issue(
        42, title="[erk-pr] Remote Dispatch Plan", branch_name="plnd/remote-test"
    )
    fake_remote = _make_fake_remote(issues={42: issue})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pr", "dispatch", "42", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Unexpected failure:\n{result.output}"
    assert "Workflow dispatched" in result.output
    assert "1 PR(s) dispatched successfully" in result.output

    # Verify workflow was dispatched
    assert len(fake_remote.dispatched_workflows) == 1
    dispatched = fake_remote.dispatched_workflows[0]
    assert dispatched.inputs["pr_number"] == "42"
    assert dispatched.inputs["plan_backend"] == "planned_pr"
    assert dispatched.inputs["branch_name"] == "plnd/remote-test"

    # Verify impl-context files were committed to the branch
    assert len(fake_remote.created_file_commits) >= 1
    committed_paths = [c.path for c in fake_remote.created_file_commits]
    assert any(".erk/impl-context/plan.md" in p for p in committed_paths)


def test_dispatch_remote_plan_not_found() -> None:
    """Test pr dispatch --repo with non-existent plan."""
    fake_remote = _make_fake_remote(issues={})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pr", "dispatch", "999", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code != 0
    assert "PR #999 not found" in result.output


def test_dispatch_remote_missing_title_prefix() -> None:
    """Test pr dispatch --repo rejects plan without [erk-pr] title prefix."""
    issue = _make_plan_issue(42, title="No prefix plan")
    fake_remote = _make_fake_remote(issues={42: issue})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pr", "dispatch", "42", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code != 0
    assert "does not have '[erk-pr]' title prefix" in result.output


def test_dispatch_remote_closed_plan() -> None:
    """Test pr dispatch --repo rejects closed plan."""
    issue = _make_plan_issue(42, state="CLOSED")
    fake_remote = _make_fake_remote(issues={42: issue})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pr", "dispatch", "42", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code != 0
    assert "is CLOSED" in result.output


def test_dispatch_remote_requires_plan_number() -> None:
    """Test pr dispatch --repo without plan number gives error."""
    fake_remote = _make_fake_remote()
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pr", "dispatch", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code != 0
    assert "PR number(s) required in remote mode" in result.output


def test_dispatch_remote_multiple_plans() -> None:
    """Test pr dispatch --repo dispatches multiple plans."""
    issue_1 = _make_plan_issue(10, title="[erk-pr] Plan A", branch_name="plnd/plan-a")
    issue_2 = _make_plan_issue(20, title="[erk-pr] Plan B", branch_name="plnd/plan-b")
    fake_remote = _make_fake_remote(issues={10: issue_1, 20: issue_2})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pr", "dispatch", "10", "20", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Unexpected failure:\n{result.output}"
    assert "2 PR(s) dispatched successfully" in result.output
    assert len(fake_remote.dispatched_workflows) == 2


def test_dispatch_remote_posts_queued_comment() -> None:
    """Test pr dispatch --repo posts a queued event comment."""
    issue = _make_plan_issue(42, branch_name="plnd/comment-test")
    fake_remote = _make_fake_remote(issues={42: issue})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pr", "dispatch", "42", "--repo", "owner/repo"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Unexpected failure:\n{result.output}"
    assert "Queued event comment posted" in result.output
    assert len(fake_remote.added_issue_comments) == 1
    assert fake_remote.added_issue_comments[0].issue_number == 42


def test_dispatch_remote_with_base_branch() -> None:
    """Test pr dispatch --repo --base threads base branch to workflow inputs."""
    issue = _make_plan_issue(42, branch_name="plnd/base-test")
    fake_remote = _make_fake_remote(issues={42: issue})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pr", "dispatch", "42", "--repo", "owner/repo", "--base", "develop"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Unexpected failure:\n{result.output}"
    dispatched = fake_remote.dispatched_workflows[0]
    assert dispatched.inputs["base_branch"] == "develop"


def test_dispatch_remote_with_ref() -> None:
    """Test pr dispatch --repo --ref threads ref to workflow dispatch."""
    issue = _make_plan_issue(42, branch_name="plnd/ref-test")
    fake_remote = _make_fake_remote(issues={42: issue})
    ctx = _build_remote_context(fake_remote)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pr", "dispatch", "42", "--repo", "owner/repo", "--ref", "custom-ref"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Unexpected failure:\n{result.output}"
    dispatched = fake_remote.dispatched_workflows[0]
    assert dispatched.ref == "custom-ref"
